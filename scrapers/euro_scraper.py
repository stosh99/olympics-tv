#!/usr/bin/env python3
"""
European TV Olympics Broadcast Schedule Scraper
Fetches Olympic broadcast schedules from epg.pw and Allente APIs,
filters for Olympic content, and loads into PostgreSQL.

Sources:
  - epg.pw: UK, Germany, Italy, France, Denmark (14 channels, no auth)
  - Allente: Norway, Sweden, Finland (12 channels, no auth)
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta, timezone
import hashlib
import time
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'olympics_tv'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

# Olympic keyword patterns per language for content filtering
OLYMPIC_KEYWORDS = [
    # English
    'olympic', 'olympics', 'winter games', 'cortina', 'milano cortina',
    # German
    'olympisch', 'winterspiele', 'olympia',
    # Italian
    'olimpiad', 'olimpic', 'giochi invernali', 'giochi olimpici',
    # French
    'olympique', 'jeux olymp', "jeux d'hiver",
    # Norwegian
    'ol 2026', 'ol-', 'vinter-ol', 'olympiske',
    # Swedish
    'os 2026', 'olympisk', 'vinter-os',
    # Danish
    'ol 2026', 'vinter-ol', 'olympisk',
    # Finnish
    'olympialais', 'talviolympialaiset',
    # Sport names (work across most languages)
    'biathlon', 'bobsleigh', 'bobsled', 'curling', 'skeleton',
    'luge', 'freestyle', 'snowboard',
]

# Sport-specific keywords per language (for channels that use generic Olympic titles)
SPORT_KEYWORDS_MULTI = {
    'alpine': ['alpint', 'alpin', 'sci alpino', 'ski alpin', 'alpine', 'slalom', 'downhill',
               'giant slalom', 'super-g', 'combined', 'discesa'],
    'cross_country': ['langrenn', 'längdskidor', 'sci di fondo', 'ski de fond', 'cross-country',
                      'cross country', 'skiathlon', 'staffetta', 'relay'],
    'biathlon': ['biathlon', 'skiskyting', 'skidskytte', 'biathle'],
    'ski_jumping': ['skihopp', 'backhoppning', 'salto', 'saut à ski', 'ski jumping', 'skispringen'],
    'ice_hockey': ['hockey', 'ishockey', 'eishockey', 'hockey sur glace'],
    'figure_skating': ['kunstløp', 'konståkning', 'pattinaggio', 'patinage', 'figure skating',
                       'eiskunstlauf'],
    'speed_skating': ['skøyter', 'skridskor', 'speed skating', 'eisschnelllauf',
                      'pattinaggio velocità', 'patinage de vitesse'],
    'short_track': ['short track', 'shorttrack'],
    'curling': ['curling'],
    'bobsled': ['bob', 'bobsleigh', 'bobsled'],
    'luge': ['luge', 'rodel', 'rodeln', 'slittino', 'aking'],
    'skeleton': ['skeleton'],
    'freestyle': ['freestyle', 'moguls', 'halfpipe', 'slopestyle', 'big air', 'aerials'],
    'snowboard': ['snowboard'],
    'nordic_combined': ['kombinert', 'kombination', 'combinata', 'combiné', 'nordic combined'],
}


class EuroScraper:
    def __init__(self):
        self.conn = None
        self.channels = {}  # channel_code -> channel row
        self.stats = {'raw_saved': 0, 'olympic_found': 0, 'broadcasts_upserted': 0}
        self.connect()
        self.load_channels()

    def connect(self):
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    def load_channels(self):
        """Load channel config from euro_channels table."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT channel_code, display_name, country_code, source,
                   source_channel_id, timezone, language
            FROM euro_channels WHERE is_active = TRUE
        """)
        for row in cur.fetchall():
            self.channels[row[0]] = {
                'channel_code': row[0], 'display_name': row[1],
                'country_code': row[2], 'source': row[3],
                'source_channel_id': row[4], 'timezone': row[5],
                'language': row[6]
            }
        cur.close()
        logger.info(f"Loaded {len(self.channels)} active channels")

    def is_olympic_content(self, title, description=''):
        """Check if a program is Olympic content based on title/description keywords."""
        text = f"{title} {description}".lower()
        for kw in OLYMPIC_KEYWORDS:
            if kw in text:
                return True
        # Also match '2026' combined with any sport keyword
        if '2026' in text:
            for sport, keywords in SPORT_KEYWORDS_MULTI.items():
                for kw in keywords:
                    if kw in text:
                        return True
        return False

    def generate_broadcast_id(self, channel_code, start_time_str, title):
        """Generate a stable unique ID for a broadcast."""
        raw = f"{channel_code}|{start_time_str}|{title}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    # ── epg.pw API ──────────────────────────────────────────────

    def fetch_epg_pw(self, channel_code, date_str):
        """Fetch EPG data from epg.pw for one channel/date.
        date_str: YYYYMMDD format
        Returns list of program dicts or None on error.
        """
        ch = self.channels[channel_code]
        url = f"https://epg.pw/api/epg.json?channel_id={ch['source_channel_id']}&date={date_str}&timezone={ch['timezone']}"
        try:
            resp = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            resp.raise_for_status()
            data = resp.json()
            return data
        except Exception as e:
            logger.warning(f"epg.pw fetch failed for {channel_code}: {e}")
            return None

    def parse_epg_pw_programs(self, channel_code, raw_data):
        """Parse epg.pw response into normalized broadcast records."""
        programs = raw_data.get('epg_list', [])
        results = []
        for p in programs:
            title = p.get('title', '')
            desc = p.get('desc', '')
            if not self.is_olympic_content(title, desc):
                continue
            start = p.get('start_date', p.get('start', ''))
            end = p.get('end_date', p.get('end', ''))
            broadcast_id = self.generate_broadcast_id(channel_code, start, title)
            results.append({
                'broadcast_id': broadcast_id,
                'channel_code': channel_code,
                'title_original': title[:500] if title else None,
                'title_english': None,  # epg.pw doesn't provide translations
                'description': desc[:2000] if desc else None,
                'start_time': start,
                'end_time': end if end else None,
                'duration_minutes': None,
                'is_live': False,  # epg.pw doesn't indicate live
                'is_replay': False,
                'source_event_id': None,
            })
        return results

    # ── Allente API ─────────────────────────────────────────────

    def fetch_allente(self, country_code, date_str_iso):
        """Fetch EPG data from Allente for one country/date.
        country_code: NO, SE, FI
        date_str_iso: YYYY-MM-DD format
        Returns full response dict or None.
        """
        domain_map = {'NO': 'no', 'SE': 'se', 'FI': 'fi'}
        domain = domain_map.get(country_code)
        if not domain:
            return None
        url = f"https://cs-vcb.allente.{domain}/epg/events?date={date_str_iso}"
        try:
            resp = requests.get(url, timeout=20, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Allente fetch failed for {country_code}: {e}")
            return None

    def parse_allente_programs(self, allente_data, target_channels):
        """Parse Allente response for specific channels, filter Olympic content.
        target_channels: dict of source_channel_id -> channel_code
        """
        results = []
        for ch in allente_data.get('channels', []):
            allente_id = str(ch.get('id', ''))
            # Allente IDs can be with or without leading zeros
            channel_code = target_channels.get(allente_id)
            if not channel_code:
                # Try without leading zeros
                channel_code = target_channels.get(allente_id.lstrip('0'))
                if not channel_code:
                    continue

            for evt in ch.get('events', []):
                title = evt.get('title', '')
                desc = evt.get('details', {}).get('description', '') if isinstance(evt.get('details'), dict) else ''
                if not self.is_olympic_content(title, desc):
                    continue
                start = evt.get('time', '')
                duration = evt.get('details', {}).get('duration', 0) if isinstance(evt.get('details'), dict) else 0
                is_live = evt.get('live', False)
                source_id = str(evt.get('id', ''))

                broadcast_id = self.generate_broadcast_id(channel_code, start, title)
                results.append({
                    'broadcast_id': broadcast_id,
                    'channel_code': channel_code,
                    'title_original': title[:500] if title else None,
                    'title_english': None,
                    'description': desc[:2000] if desc else None,
                    'start_time': start,
                    'end_time': None,
                    'duration_minutes': duration if duration else None,
                    'is_live': bool(is_live),
                    'is_replay': False,
                    'source_event_id': source_id if source_id else None,
                })
        return results

    # ── Database operations ─────────────────────────────────────

    def save_raw(self, channel_code, date_queried, source, raw_json):
        """Archive raw API response."""
        cur = self.conn.cursor()
        try:
            cur.execute("""
                INSERT INTO euro_broadcasts_raw (channel_code, date_queried, source, raw_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (channel_code, date_queried, source)
                DO UPDATE SET raw_json = EXCLUDED.raw_json, fetched_at = NOW()
            """, (channel_code, date_queried, source, json.dumps(raw_json)))
            self.conn.commit()
            self.stats['raw_saved'] += 1
        except Exception as e:
            self.conn.rollback()
            logger.warning(f"Failed to save raw for {channel_code}/{date_queried}: {e}")
        finally:
            cur.close()

    def upsert_broadcasts(self, broadcasts):
        """Upsert normalized Olympic broadcasts."""
        if not broadcasts:
            return
        cur = self.conn.cursor()
        try:
            for b in broadcasts:
                cur.execute("""
                    INSERT INTO euro_broadcasts (
                        broadcast_id, channel_code, title_original, title_english,
                        description, start_time, end_time, duration_minutes,
                        is_live, is_replay, source_event_id
                    ) VALUES (
                        %(broadcast_id)s, %(channel_code)s, %(title_original)s, %(title_english)s,
                        %(description)s, %(start_time)s, %(end_time)s, %(duration_minutes)s,
                        %(is_live)s, %(is_replay)s, %(source_event_id)s
                    )
                    ON CONFLICT (broadcast_id) DO UPDATE SET
                        title_original = EXCLUDED.title_original,
                        description = EXCLUDED.description,
                        start_time = EXCLUDED.start_time,
                        end_time = EXCLUDED.end_time,
                        duration_minutes = EXCLUDED.duration_minutes,
                        is_live = EXCLUDED.is_live,
                        source_event_id = EXCLUDED.source_event_id,
                        updated_at = NOW()
                """, b)
            self.conn.commit()
            self.stats['broadcasts_upserted'] += len(broadcasts)
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to upsert broadcasts: {e}")
            raise
        finally:
            cur.close()

    # ── Main orchestration ──────────────────────────────────────

    def scrape_date(self, target_date):
        """Scrape all channels for a single date."""
        date_epg = target_date.strftime('%Y%m%d')    # epg.pw format
        date_iso = target_date.strftime('%Y-%m-%d')   # Allente format
        date_db = target_date.date() if hasattr(target_date, 'date') else target_date

        logger.info(f"═══ Scraping {date_iso} ═══")

        # ── epg.pw channels ──
        epg_pw_channels = {k: v for k, v in self.channels.items() if v['source'] == 'epg_pw'}
        for code, ch in epg_pw_channels.items():
            raw = self.fetch_epg_pw(code, date_epg)
            if raw is None:
                continue
            self.save_raw(code, date_db, 'epg_pw', raw)
            broadcasts = self.parse_epg_pw_programs(code, raw)
            if broadcasts:
                self.upsert_broadcasts(broadcasts)
                self.stats['olympic_found'] += len(broadcasts)
                logger.info(f"  {ch['display_name']:20s} → {len(broadcasts)} Olympic programs")
            time.sleep(0.5)  # Be polite to epg.pw

        # ── Allente channels (one call per country) ──
        allente_countries = {}
        for code, ch in self.channels.items():
            if ch['source'] == 'allente':
                cc = ch['country_code']
                if cc not in allente_countries:
                    allente_countries[cc] = {}
                # Map source_channel_id -> channel_code for lookup
                allente_countries[cc][ch['source_channel_id']] = code
                # Also map without leading zeros
                allente_countries[cc][ch['source_channel_id'].lstrip('0')] = code

        for country_code, channel_map in allente_countries.items():
            raw = self.fetch_allente(country_code, date_iso)
            if raw is None:
                continue
            # Save raw per channel (extract each channel's data from the bulk response)
            for ch_data in raw.get('channels', []):
                allente_id = str(ch_data.get('id', ''))
                ch_code = channel_map.get(allente_id) or channel_map.get(allente_id.lstrip('0'))
                if ch_code:
                    self.save_raw(ch_code, date_db, 'allente', ch_data)
            broadcasts = self.parse_allente_programs(raw, channel_map)
            if broadcasts:
                self.upsert_broadcasts(broadcasts)
                self.stats['olympic_found'] += len(broadcasts)
                # Log per-channel breakdown
                by_ch = {}
                for b in broadcasts:
                    by_ch[b['channel_code']] = by_ch.get(b['channel_code'], 0) + 1
                for ch_code, count in by_ch.items():
                    ch_name = self.channels[ch_code]['display_name']
                    logger.info(f"  {ch_name:20s} → {count} Olympic programs")
            time.sleep(0.5)

    def run(self, days_ahead=3, days_back=0):
        """Scrape Euro broadcasts for a date range.
        days_ahead: how many days into the future (default 3)
        days_back: how many days in the past (default 0, today only)
        """
        today = datetime.now(timezone.utc).date()
        olympics_end = datetime(2026, 2, 22).date()

        start_date = today - timedelta(days=days_back)
        end_date = min(today + timedelta(days=days_ahead), olympics_end)

        logger.info(f"Euro TV scraper starting: {start_date} to {end_date}")
        logger.info(f"Active channels: {len(self.channels)}")

        current = start_date
        while current <= end_date:
            self.scrape_date(datetime.combine(current, datetime.min.time()))
            current += timedelta(days=1)

        logger.info("═══ Scrape Complete ═══")
        logger.info(f"  Raw responses saved: {self.stats['raw_saved']}")
        logger.info(f"  Olympic programs found: {self.stats['olympic_found']}")
        logger.info(f"  Broadcasts upserted: {self.stats['broadcasts_upserted']}")

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


def main():
    scraper = EuroScraper()
    try:
        # Scrape today + next 2 days (EPG data is usually 2-3 days ahead)
        scraper.run(days_ahead=2, days_back=0)
    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        raise
    finally:
        scraper.close()


if __name__ == '__main__':
    main()
