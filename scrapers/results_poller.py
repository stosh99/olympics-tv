#!/usr/bin/env python3
"""
Results Poller - Checks for newly finished Olympic events and extracts results.
Designed to run every 10-15 minutes via cron/systemd timer.
Only fetches today's date from the Olympics API (1 API call per run).
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
import psycopg2
from datetime import datetime, timezone
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'olympics_tv'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

API_BASE = "https://www.olympics.com/wmr-owg2026/schedules/api/ENG/schedule/lite/day"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.olympics.com/'
}


def fetch_today_schedule():
    """Fetch today's schedule from Olympics API"""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    url = f"{API_BASE}/{today}"
    logger.info(f"Fetching schedule for {today}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch schedule: {e}")
        return None


def get_existing_result_units(cur):
    """Get set of event_unit_codes that already have results"""
    cur.execute("SELECT DISTINCT event_unit_code FROM results")
    return {row[0] for row in cur.fetchall()}


def extract_results(unit):
    """Extract result rows from a single unit's competitors"""
    results = []
    event_unit_code = unit['id'].rstrip('-')
    
    for c in unit.get('competitors', []):
        code = c.get('code')
        if not code or code == 'TBD':
            continue
        r = c.get('results', {})
        if not r:
            continue

        position = r.get('position')
        if position:
            try:
                position = int(position)
            except (ValueError, TypeError):
                position = None

        wlt = r.get('winnerLoserTie')
        if wlt:
            wlt = wlt[0]

        results.append((
            event_unit_code,
            code,
            c.get('noc'),
            c.get('name'),
            position,
            r.get('mark'),
            wlt,
            r.get('medalType')
        ))
    return results


def update_schedule_unit(cur, unit):
    """Update schedule_units with latest status and competitors_json"""
    event_unit_code = unit['id'].rstrip('-')
    cur.execute("""
        UPDATE schedule_units 
        SET status = %s, competitors_json = %s, updated_at = NOW()
        WHERE event_unit_code = %s
    """, (
        unit.get('status'),
        json.dumps(unit.get('competitors', [])),
        event_unit_code
    ))


def run():
    data = fetch_today_schedule()
    if not data:
        return

    units = data.get('units', [])
    if not units:
        logger.info("No units for today")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    existing = get_existing_result_units(cur)
    
    new_results = 0
    updated_units = 0
    new_events = []

    for unit in units:
        if unit.get('status') != 'FINISHED':
            continue

        event_unit_code = unit['id'].rstrip('-')

        # Always update schedule_units with latest data
        update_schedule_unit(cur, unit)
        updated_units += 1

        # Skip if we already have results for this event
        if event_unit_code in existing:
            continue

        results = extract_results(unit)
        if not results:
            continue

        for row in results:
            try:
                cur.execute("""
                    INSERT INTO results (event_unit_code, competitor_code, noc,
                        competitor_name, position, mark, winner_loser_tie,
                        medal_type, detected_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (event_unit_code, competitor_code) DO NOTHING
                """, row)
                new_results += 1
            except Exception as e:
                logger.error(f"Insert error {row[0]}/{row[1]}: {e}")
                conn.rollback()
                continue

        new_events.append(event_unit_code)
        logger.info(f"NEW RESULTS: {event_unit_code} ({len(results)} competitors)")

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"Poll complete: {updated_units} units updated, "
                f"{len(new_events)} new events, {new_results} result rows added")
    
    if new_events:
        logger.info(f"New event codes: {new_events}")


if __name__ == '__main__':
    run()
