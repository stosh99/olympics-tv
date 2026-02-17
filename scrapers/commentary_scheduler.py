#!/usr/bin/env python3
"""
Commentary Scheduler - Generates commentary for recent and upcoming events.

Post-event: Finds FINISHED events in the last 24 hours without commentary.
Pre-event:  Finds upcoming events in the next 24 hours without pre_event commentary.

Designed to run on a schedule (cron/Task Scheduler) or manually.

Usage:
    python commentary_scheduler.py              # Run both post and pre
    python commentary_scheduler.py --post-only   # Post-event only
    python commentary_scheduler.py --pre-only    # Pre-event only
    python commentary_scheduler.py --dry-run     # Show what would be processed
"""

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import psycopg2
import logging
import argparse
import json
import requests
from datetime import datetime, timedelta, timezone

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

OLYMPICS_API_BASE = "https://www.olympics.com/wmr-owg2026/schedules/api/ENG/schedule/lite/day"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.olympics.com/'
}


def fetch_today_schedule():
    """Fetch today's schedule from Olympics API"""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    url = f"{OLYMPICS_API_BASE}/{today}"
    logger.info(f"Fetching results from Olympics.com for {today}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch schedule: {e}")
        return None


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


def populate_results():
    """Fetch today's results from Olympics.com and populate results table"""
    data = fetch_today_schedule()
    if not data:
        logger.info("No schedule data received")
        return

    units = data.get('units', [])
    if not units:
        logger.info("No units in schedule")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Get existing result units
    cur.execute("SELECT DISTINCT event_unit_code FROM results")
    existing = {row[0] for row in cur.fetchall()}

    new_results = 0
    new_events = []

    for unit in units:
        if unit.get('status') != 'FINISHED':
            continue

        event_unit_code = unit['id'].rstrip('-')

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
        logger.info(f"  NEW RESULTS: {event_unit_code} ({len(results)} competitors)")

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"Results: {len(new_events)} new events, {new_results} result rows added")


def get_post_event_pending():
    """Find events with results in the last 24 hours without post_event commentary."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT su.event_unit_code, d.name as discipline,
               e.name as event, su.medal_flag, su.start_time
        FROM schedule_units su
        JOIN events e ON su.event_id = e.event_id
        JOIN disciplines d ON e.discipline_code = d.code
        JOIN results r ON r.event_unit_code = su.event_unit_code
        WHERE su.start_time >= NOW() - INTERVAL '24 hours'
        AND su.event_unit_code NOT IN (
            SELECT event_unit_code FROM commentary
            WHERE commentary_type = 'post_event'
            AND status IN ('published', 'proofed', 'writing', 'analyzing')
            AND event_unit_code IS NOT NULL
        )
        ORDER BY su.medal_flag DESC, su.start_time
    """)

    events = [{
        'event_unit_code': row[0],
        'discipline': row[1],
        'event': row[2],
        'medal_flag': row[3],
        'start_time': row[4],
    } for row in cur.fetchall()]

    cur.close()
    conn.close()
    return events


def get_pre_event_pending():
    """Find upcoming events in the next 24 hours without pre_event commentary."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT su.event_unit_code, d.name as discipline,
               e.name as event, su.event_unit_name, su.medal_flag,
               su.start_time, su.status
        FROM schedule_units su
        JOIN events e ON su.event_id = e.event_id
        JOIN disciplines d ON e.discipline_code = d.code
        WHERE su.start_time > NOW()
        AND su.start_time <= NOW() + INTERVAL '24 hours'
        AND su.event_unit_code NOT IN (
            SELECT event_unit_code FROM commentary
            WHERE commentary_type = 'pre_event'
            AND status IN ('proofed', 'published', 'writing')
            AND event_unit_code IS NOT NULL
        )
        ORDER BY su.medal_flag DESC, su.start_time
    """)

    events = [{
        'event_unit_code': row[0],
        'discipline': row[1],
        'event': row[2],
        'unit_name': row[3],
        'medal_flag': row[4],
        'start_time': row[5],
        'status': row[6],
    } for row in cur.fetchall()]

    cur.close()
    conn.close()
    return events


def run_post_events(dry_run=False):
    """Generate post-event commentary for recent finished events."""
    from pipeline_orchestrator import process_event, update_commentary_status

    events = get_post_event_pending()
    medal_count = sum(1 for e in events if e['medal_flag'])

    logger.info(f"POST-EVENT: {len(events)} pending ({medal_count} medal)")

    if not events:
        logger.info("POST-EVENT: Nothing to process")
        return 0, 0

    for evt in events:
        medal = "[MEDAL]" if evt['medal_flag'] else "      "
        logger.info(f"  {medal} {evt['discipline']} - {evt['event']}")

    if dry_run:
        return 0, 0

    success = 0
    failed = 0

    for evt in events:
        try:
            ok = process_event(evt['event_unit_code'])
            if ok:
                success += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Error processing {evt['event_unit_code']}: {e}")
            update_commentary_status(evt['event_unit_code'], 'failed', str(e)[:500])
            failed += 1

    return success, failed


def run_pre_events(dry_run=False):
    """Generate pre-event commentary for upcoming events."""
    from intro_orchestrator import process_event, update_status

    events = get_pre_event_pending()
    medal_count = sum(1 for e in events if e['medal_flag'])

    logger.info(f"PRE-EVENT: {len(events)} pending ({medal_count} medal)")

    if not events:
        logger.info("PRE-EVENT: Nothing to process")
        return 0, 0

    for evt in events:
        medal = "[MEDAL]" if evt['medal_flag'] else "      "
        logger.info(f"  {medal} {evt['discipline']} - {evt['event']} @ {evt['start_time']}")

    if dry_run:
        return 0, 0

    success = 0
    failed = 0

    for evt in events:
        # Skip training runs and practice sessions
        unit_name = (evt.get('unit_name') or '').lower()
        if any(skip in unit_name for skip in ['training', 'practice', 'warm']):
            logger.info(f"  Skipping {evt['event_unit_code']} (training/practice)")
            continue

        try:
            ok = process_event(evt)
            if ok:
                success += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Error processing {evt['event_unit_code']}: {e}")
            update_status(evt['event_unit_code'], 'failed', str(e)[:500])
            failed += 1

    return success, failed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Commentary Scheduler')
    parser.add_argument('--post-only', action='store_true', help='Only run post-event commentary')
    parser.add_argument('--pre-only', action='store_true', help='Only run pre-event commentary')
    parser.add_argument('--dry-run', action='store_true', help='Show pending events without processing')

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("COMMENTARY SCHEDULER")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # Step 1: Populate results before generating commentary
    logger.info("")
    logger.info("--- Populating Results ---")
    populate_results()

    run_post = not args.pre_only
    run_pre = not args.post_only

    post_success, post_failed = 0, 0
    pre_success, pre_failed = 0, 0

    if run_post:
        logger.info("")
        logger.info("--- Post-Event (last 24 hours) ---")
        post_success, post_failed = run_post_events(dry_run=args.dry_run)

    if run_pre:
        logger.info("")
        logger.info("--- Pre-Event (next 24 hours) ---")
        pre_success, pre_failed = run_pre_events(dry_run=args.dry_run)

    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info(f"  Post-event: {post_success} success, {post_failed} failed")
    logger.info(f"  Pre-event:  {pre_success} success, {pre_failed} failed")
    logger.info("=" * 60)
