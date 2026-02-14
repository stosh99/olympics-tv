#!/usr/bin/env python3
"""
NBC Olympics Broadcast Schedule Scraper
Loads Winter Olympics 2026 TV broadcast schedules from NBC into PostgreSQL database
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
import logging

# Configure logging
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

# API configuration
API_BASE = "https://schedules.nbcolympics.com/api/v1/schedule"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

# Raw data directory
RAW_DATA_DIR = Path(__file__).parent.parent / 'raw_data'


class NBCScraper:
    def __init__(self):
        self.conn = None
        self.sync_id = None
        self.connect()
        self.ensure_raw_data_dir()

    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def ensure_raw_data_dir(self):
        """Create raw_data directory if it doesn't exist"""
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def save_raw_json(self, data, date_str):
        """Save raw JSON response to file"""
        filename = RAW_DATA_DIR / f"nbc{date_str.replace('-', '')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        return str(filename)

    def fetch_schedule(self, date_str):
        """Fetch schedule data from NBC API"""
        url = f"{API_BASE}?timeZone=America/New_York&startDate={date_str}&inPattern=true"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch schedule for {date_str}: {e}")
            return None

    def log_sync(self, source='nbc', sync_type='incremental'):
        """Create sync_log entry"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO sync_log (source, sync_type, status, started_at) "
            "VALUES (%s, %s, %s, NOW()) RETURNING id",
            (source, sync_type, 'running')
        )
        self.sync_id = cursor.fetchone()[0]
        self.conn.commit()
        cursor.close()
        return self.sync_id

    def update_sync_log(self, status, records_processed=0):
        """Update sync_log entry"""
        if not self.sync_id:
            return
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE sync_log SET status = %s, records_processed = %s, completed_at = NOW() "
            "WHERE id = %s",
            (status, records_processed, self.sync_id)
        )
        self.conn.commit()
        cursor.close()

    def unix_to_timestamptz(self, unix_timestamp):
        """Convert Unix timestamp (seconds) to TIMESTAMPTZ string"""
        if not unix_timestamp:
            return None
        try:
            dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
            return dt.isoformat()
        except (ValueError, TypeError):
            return None

    def is_replay(self, title):
        """Check if broadcast is a replay based on title"""
        if not title:
            return False
        title_lower = title.lower()
        return any(word in title_lower for word in ['re-air', 'encore', 'replay'])

    def upsert_broadcasts_raw(self, events, date_str):
        """Upsert nbc_broadcasts_raw table"""
        cursor = self.conn.cursor()
        inserted = 0
        updated = 0

        for event in events:
            single_event = event.get('singleEvent', {})
            drupal_id = single_event.get('drupalId')

            if not drupal_id:
                continue

            cursor.execute(
                "INSERT INTO nbc_broadcasts_raw (drupal_id, date_queried, raw_json) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (drupal_id) DO UPDATE SET raw_json = EXCLUDED.raw_json "
                "RETURNING (xmax = 0) as inserted",
                (drupal_id, date_str, json.dumps(event))
            )
            if cursor.fetchone()[0]:
                inserted += 1
            else:
                updated += 1

        self.conn.commit()
        cursor.close()
        return inserted, updated

    def upsert_broadcasts(self, events):
        """Upsert nbc_broadcasts table"""
        cursor = self.conn.cursor()
        inserted = 0
        updated = 0

        for event in events:
            single_event = event.get('singleEvent', {})
            drupal_id = single_event.get('drupalId')

            if not drupal_id:
                continue

            title = single_event.get('title')
            short_title = single_event.get('shortTitle')
            start_time = self.unix_to_timestamptz(single_event.get('startDate'))
            end_time = self.unix_to_timestamptz(single_event.get('endDate'))
            network = single_event.get('network', {})
            network_name = network.get('name') if network else 'Peacock'
            if not network_name:
                network_name = 'Peacock'
            day_part = single_event.get('dayPart')
            summary = single_event.get('summary')
            short_description = single_event.get('shortDescription')
            video_url = single_event.get('videoURL')
            peacock_url = single_event.get('peacockDestinationURL')
            stream_type_array = single_event.get('streamType', [])
            stream_type = stream_type_array[0] if stream_type_array else None
            is_medal_session = single_event.get('isMedalSession', False)
            is_replay = self.is_replay(title)
            olympic_day = single_event.get('day')
            tier = single_event.get('tier')
            last_modified = single_event.get('lastModified')

            cursor.execute(
                "INSERT INTO nbc_broadcasts ("
                "drupal_id, title, short_title, start_time, end_time, network_name, day_part, "
                "summary, video_url, stream_type, is_medal_session, olympic_day, tier, last_modified, is_replay, peacock_url, short_description"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (drupal_id) DO UPDATE SET "
                "title = EXCLUDED.title, "
                "short_title = EXCLUDED.short_title, "
                "start_time = EXCLUDED.start_time, "
                "end_time = EXCLUDED.end_time, "
                "network_name = EXCLUDED.network_name, "
                "day_part = EXCLUDED.day_part, "
                "summary = EXCLUDED.summary, "
                "short_description = EXCLUDED.short_description, "
                "video_url = EXCLUDED.video_url, "
                "peacock_url = EXCLUDED.peacock_url, "
                "stream_type = EXCLUDED.stream_type, "
                "is_medal_session = EXCLUDED.is_medal_session, "
                "is_replay = EXCLUDED.is_replay, "
                "tier = EXCLUDED.tier, "
                "last_modified = EXCLUDED.last_modified "
                "RETURNING (xmax = 0) as inserted",
                (
                    drupal_id, title, short_title, start_time, end_time, network_name, day_part,
                    summary, video_url, stream_type, is_medal_session, olympic_day, tier, last_modified, is_replay, peacock_url, short_description
                )
            )
            if cursor.fetchone()[0]:
                inserted += 1
            else:
                updated += 1

        self.conn.commit()
        cursor.close()
        return inserted, updated

    def upsert_broadcast_units(self, events):
        """Upsert nbc_broadcast_units junction table"""
        cursor = self.conn.cursor()
        inserted = 0

        for event in events:
            single_event = event.get('singleEvent', {})
            drupal_id = single_event.get('drupalId')

            if not drupal_id:
                continue

            units = event.get('units', [])
            if not units:
                continue

            for unit in units:
                unit_code = unit.get('code')
                if not unit_code:
                    continue

                cursor.execute(
                    "INSERT INTO nbc_broadcast_units (broadcast_drupal_id, unit_code) "
                    "VALUES (%s, %s) "
                    "ON CONFLICT (broadcast_drupal_id, unit_code) DO NOTHING "
                    "RETURNING (xmax = 0) as inserted",
                    (drupal_id, unit_code)
                )
                result = cursor.fetchone()
                if result and result[0]:
                    inserted += 1

        self.conn.commit()
        cursor.close()
        return inserted

    def upsert_broadcast_rundown(self, events):
        """Upsert nbc_broadcast_rundown table"""
        cursor = self.conn.cursor()
        inserted = 0

        for event in events:
            single_event = event.get('singleEvent', {})
            drupal_id = single_event.get('drupalId')

            if not drupal_id:
                continue

            rundown = single_event.get('rundown', {})
            items = rundown.get('items', [])

            if not items:
                continue

            for idx, item in enumerate(items, start=1):
                header = item.get('header')
                description = item.get('description')
                segment_time = item.get('date')  # Store raw Unix timestamp as bigint

                cursor.execute(
                    "INSERT INTO nbc_broadcast_rundown (broadcast_drupal_id, segment_order, header, description, segment_time) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT (broadcast_drupal_id, segment_order) DO UPDATE SET "
                    "header = EXCLUDED.header, "
                    "description = EXCLUDED.description, "
                    "segment_time = EXCLUDED.segment_time "
                    "RETURNING (xmax = 0) as inserted",
                    (drupal_id, idx, header, description, segment_time)
                )
                if cursor.fetchone()[0]:
                    inserted += 1

        self.conn.commit()
        cursor.close()
        return inserted

    def extract_networks(self, events):
        """Extract unique networks from events"""
        networks = {}
        for event in events:
            single_event = event.get('singleEvent', {})
            network = single_event.get('network', {})
            network_name = network.get('name') if network else 'null/streaming'
            networks[network_name] = networks.get(network_name, 0) + 1
        return networks

    def process_day(self, date_str):
        """Process a single day's data"""
        print(f"\n=== NBC {date_str} ===")

        # Fetch data
        data = self.fetch_schedule(date_str)
        if not data:
            print(f"  No data for {date_str}")
            return None

        events = data.get('data', [])
        if not events:
            print(f"  No events for {date_str}")
            return None

        # Save raw JSON
        filename = self.save_raw_json(data, date_str)
        print(f"  Raw JSON saved: {filename}")

        # Log sync
        self.log_sync()

        # Upsert all tables
        raw_ins, raw_upd = self.upsert_broadcasts_raw(events, date_str)
        print(f"  Broadcasts Raw:     {raw_ins} new / {raw_upd} updated")

        bc_ins, bc_upd = self.upsert_broadcasts(events)
        print(f"  Broadcasts:         {bc_ins} new / {bc_upd} updated")

        bcu_ins = self.upsert_broadcast_units(events)
        print(f"  Broadcast Units:    {bcu_ins} new / 0 updated")

        bcr_ins = self.upsert_broadcast_rundown(events)
        print(f"  Broadcast Rundown:  {bcr_ins} new / 0 updated")

        # Extract and display networks
        networks = self.extract_networks(events)
        networks_str = ", ".join([f"{name} ({count})" for name, count in sorted(networks.items())])
        print(f"  Networks found: {networks_str}")

        # Update sync log
        total_processed = len(events)
        self.update_sync_log('success', total_processed)

        return {
            'date': date_str,
            'events': total_processed,
            'broadcasts_raw': raw_ins,
            'broadcasts': bc_ins,
            'broadcast_units': bcu_ins,
            'broadcast_rundown': bcr_ins,
            'networks': networks
        }

    def run(self, start_date='2026-02-04', end_date='2026-02-23'):
        """Run scraper for date range"""
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        results = []
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            result = self.process_day(date_str)
            if result:
                results.append(result)
            current += timedelta(days=1)
            time.sleep(1.5)  # Be polite to API

        # Print summary
        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        if results:
            total_events = sum(r['events'] for r in results)
            total_broadcasts_raw = sum(r['broadcasts_raw'] for r in results)
            total_broadcasts = sum(r['broadcasts'] for r in results)
            total_broadcast_units = sum(r['broadcast_units'] for r in results)
            total_broadcast_rundown = sum(r['broadcast_rundown'] for r in results)

            # Aggregate networks
            all_networks = {}
            for r in results:
                for network, count in r['networks'].items():
                    all_networks[network] = all_networks.get(network, 0) + count

            print(f"Days processed:      {len(results)}")
            print(f"Total events:        {total_events}")
            print(f"Broadcasts Raw:      {total_broadcasts_raw}")
            print(f"Broadcasts:          {total_broadcasts}")
            print(f"Broadcast Units:     {total_broadcast_units}")
            print(f"Broadcast Rundown:   {total_broadcast_rundown}")
            print(f"\nNetworks Summary:")
            for network, count in sorted(all_networks.items()):
                print(f"  {network}: {count}")
        else:
            print("No data processed")
        print("="*60)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


if __name__ == '__main__':
    scraper = NBCScraper()
    try:
        scraper.run()
    finally:
        scraper.close()
