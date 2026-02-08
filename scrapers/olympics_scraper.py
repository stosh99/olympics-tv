#!/usr/bin/env python3
"""
Olympics.com API Scraper
Loads Winter Olympics 2026 event schedules into PostgreSQL database
"""

import os
import json
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
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
    'host': '127.0.0.1',
    'port': 5432,
    'database': 'olympics_tv',
    'user': 'stosh99',
    'password': 'olympics_tv_dev'
}

# API configuration
API_BASE = "https://www.olympics.com/wmr-owg2026/schedules/api/ENG/schedule/lite/day"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.olympics.com/'
}

# Raw data directory
RAW_DATA_DIR = Path(__file__).parent.parent / 'raw_data'


class OlympicsScraper:
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
        filename = RAW_DATA_DIR / f"olympics{date_str.replace('-', '')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        return str(filename)

    def fetch_schedule(self, date_str):
        """Fetch schedule data from Olympics API"""
        url = f"{API_BASE}/{date_str}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch schedule for {date_str}: {e}")
            return None

    def log_sync(self, source='olympics.com', sync_type='incremental'):
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

    def upsert_disciplines(self, units):
        """Upsert disciplines"""
        cursor = self.conn.cursor()
        data = set()
        for unit in units:
            if 'disciplineCode' in unit and 'disciplineName' in unit:
                data.add((unit['disciplineCode'], unit['disciplineName']))

        inserted = 0
        updated = 0
        for code, name in data:
            cursor.execute(
                "INSERT INTO disciplines (code, name) VALUES (%s, %s) "
                "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING (xmax = 0) as inserted",
                (code, name)
            )
            if cursor.fetchone()[0]:
                inserted += 1
            else:
                updated += 1

        self.conn.commit()
        cursor.close()
        return inserted, updated

    def upsert_events(self, units):
        """Upsert events"""
        cursor = self.conn.cursor()
        data = set()
        for unit in units:
            if all(k in unit for k in ['eventId', 'disciplineCode', 'eventName']):
                data.add((
                    unit['eventId'],
                    unit['disciplineCode'],
                    unit.get('eventName', ''),
                    unit.get('genderCode'),
                    unit.get('eventType'),
                    unit.get('eventOrder')
                ))

        inserted = 0
        updated = 0
        for event_id, disc_code, name, gender, event_type, event_order in data:
            cursor.execute(
                "INSERT INTO events (event_id, discipline_code, name, gender_code, event_type, event_order) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (event_id) DO UPDATE SET "
                "name = EXCLUDED.name, gender_code = EXCLUDED.gender_code, event_type = EXCLUDED.event_type "
                "RETURNING (xmax = 0) as inserted",
                (event_id, disc_code, name, gender, event_type, event_order)
            )
            if cursor.fetchone()[0]:
                inserted += 1
            else:
                updated += 1

        self.conn.commit()
        cursor.close()
        return inserted, updated

    def upsert_venues(self, units):
        """Upsert venues"""
        cursor = self.conn.cursor()
        data = set()
        for unit in units:
            if 'venue' in unit:
                data.add((
                    unit['venue'],
                    unit.get('venueDescription', ''),
                    unit.get('venueLongDescription'),
                    unit.get('location'),
                    unit.get('locationDescription'),
                    unit.get('locationLongDescription')
                ))

        inserted = 0
        updated = 0
        for code, name, long_name, loc_code, loc_name, loc_long_name in data:
            cursor.execute(
                "INSERT INTO venues (code, name, long_name, location_code, location_name, location_long_name) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING (xmax = 0) as inserted",
                (code, name, long_name, loc_code, loc_name, loc_long_name)
            )
            if cursor.fetchone()[0]:
                inserted += 1
            else:
                updated += 1

        self.conn.commit()
        cursor.close()
        return inserted, updated

    def upsert_schedule_units(self, units):
        """Upsert schedule units"""
        cursor = self.conn.cursor()
        inserted = 0
        updated = 0

        for unit in units:
            if 'id' not in unit:
                continue

            event_unit_code = unit['id'].rstrip('-')
            cursor.execute(
                "INSERT INTO schedule_units ("
                "event_unit_code, event_id, event_unit_name, phase_code, phase_name, phase_type, "
                "venue_code, olympic_day, start_time, end_time, status, medal_flag, live_flag, "
                "schedule_item_type, session_code, group_id, unit_num, competitors_json, updated_at"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (event_unit_code) DO UPDATE SET "
                "event_unit_name = EXCLUDED.event_unit_name, "
                "updated_at = EXCLUDED.updated_at "
                "RETURNING (xmax = 0) as inserted",
                (
                    event_unit_code,
                    unit.get('eventId'),
                    unit.get('eventUnitName'),
                    unit.get('phaseCode'),
                    unit.get('phaseName'),
                    unit.get('phaseType'),
                    unit.get('venue'),
                    unit.get('olympicDay'),
                    unit.get('startDate'),
                    unit.get('endDate'),
                    unit.get('status'),
                    unit.get('medalFlag', 0),
                    unit.get('liveFlag', False),
                    unit.get('scheduleItemType'),
                    unit.get('sessionCode'),
                    unit.get('groupId'),
                    unit.get('unitNum'),
                    json.dumps(unit.get('competitors', [])),
                    unit.get('updatedAt')
                )
            )
            if cursor.fetchone()[0]:
                inserted += 1
            else:
                updated += 1

        self.conn.commit()
        cursor.close()
        return inserted, updated

    def upsert_competitors(self, units):
        """Upsert competitors"""
        cursor = self.conn.cursor()
        data = set()
        for unit in units:
            for competitor in unit.get('competitors', []):
                if all(k in competitor for k in ['code', 'noc', 'name']):
                    data.add((
                        competitor['code'],
                        competitor['noc'],
                        competitor['name'],
                        competitor.get('competitorType')
                    ))

        inserted = 0
        updated = 0
        for code, noc, name, comp_type in data:
            cursor.execute(
                "INSERT INTO competitors (code, noc, name, competitor_type) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING (xmax = 0) as inserted",
                (code, noc, name, comp_type)
            )
            if cursor.fetchone()[0]:
                inserted += 1
            else:
                updated += 1

        self.conn.commit()
        cursor.close()
        return inserted, updated

    def upsert_unit_competitors(self, units):
        """Upsert unit_competitors junction table"""
        cursor = self.conn.cursor()
        inserted = 0
        updated = 0

        for unit in units:
            if 'id' not in unit:
                continue
            event_unit_code = unit['id'].rstrip('-')
            for competitor in unit.get('competitors', []):
                if 'code' not in competitor:
                    continue
                # Skip TBD and other placeholder codes
                if competitor['code'] == 'TBD' or competitor['code'].upper() == 'TBD':
                    continue
                cursor.execute(
                    "INSERT INTO unit_competitors (event_unit_code, competitor_code, start_order) "
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT (event_unit_code, competitor_code) DO NOTHING "
                    "RETURNING (xmax = 0) as inserted",
                    (event_unit_code, competitor['code'], competitor.get('order'))
                )
                result = cursor.fetchone()
                if result and result[0]:
                    inserted += 1

        self.conn.commit()
        cursor.close()
        return inserted, updated

    def process_day(self, date_str):
        """Process a single day's data"""
        print(f"\n=== {date_str} ===")

        # Fetch data
        data = self.fetch_schedule(date_str)
        if not data:
            print(f"  No data for {date_str}")
            return None

        units = data.get('units', [])
        if not units:
            print(f"  No units for {date_str}")
            return None

        # Save raw JSON
        filename = self.save_raw_json(data, date_str)
        print(f"  Raw JSON saved: {filename}")

        # Log sync
        self.log_sync()

        # Upsert all tables
        disc_ins, disc_upd = self.upsert_disciplines(units)
        print(f"  Disciplines:    {disc_ins} new / {disc_upd} updated")

        event_ins, event_upd = self.upsert_events(units)
        print(f"  Events:         {event_ins} new / {event_upd} updated")

        venue_ins, venue_upd = self.upsert_venues(units)
        print(f"  Venues:         {venue_ins} new / {venue_upd} updated")

        unit_ins, unit_upd = self.upsert_schedule_units(units)
        print(f"  Schedule Units: {unit_ins} new / {unit_upd} updated")

        comp_ins, comp_upd = self.upsert_competitors(units)
        print(f"  Competitors:    {comp_ins} new / {comp_upd} updated")

        uc_ins, uc_upd = self.upsert_unit_competitors(units)
        print(f"  Unit Competitors: {uc_ins} new / {uc_upd} updated")

        # Update sync log
        total_processed = len(units)
        self.update_sync_log('success', total_processed)

        return {
            'date': date_str,
            'units': total_processed,
            'disciplines': disc_ins,
            'events': event_ins,
            'venues': venue_ins,
            'schedule_units': unit_ins,
            'competitors': comp_ins,
            'unit_competitors': uc_ins
        }

    def run(self, start_date='2026-02-03', end_date='2026-02-22'):
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
            total_units = sum(r['units'] for r in results)
            total_disciplines = sum(r['disciplines'] for r in results)
            total_events = sum(r['events'] for r in results)
            total_venues = sum(r['venues'] for r in results)
            total_schedule = sum(r['schedule_units'] for r in results)
            total_competitors = sum(r['competitors'] for r in results)
            total_uc = sum(r['unit_competitors'] for r in results)

            print(f"Days processed:  {len(results)}")
            print(f"Total units:     {total_units}")
            print(f"Disciplines:     {total_disciplines}")
            print(f"Events:          {total_events}")
            print(f"Venues:          {total_venues}")
            print(f"Schedule Units:  {total_schedule}")
            print(f"Competitors:     {total_competitors}")
            print(f"Unit Competitors: {total_uc}")
        else:
            print("No data processed")
        print("="*60)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


if __name__ == '__main__':
    scraper = OlympicsScraper()
    try:
        scraper.run()
    finally:
        scraper.close()
