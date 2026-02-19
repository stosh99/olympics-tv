#!/usr/bin/env python3
"""
Intro Orchestrator - End-to-end pre-event preview generation.
Finds tomorrow's events, scrapes preview sources, writes intros.

Usage:
    # Process all tomorrow's events
    python intro_orchestrator.py

    # Process a specific event
    python intro_orchestrator.py ALPWGS----------------FNL-000200

    # Process events for a specific date
    python intro_orchestrator.py --date 2026-02-17

    # Dry run
    python intro_orchestrator.py --dry-run

    # Medal events only
    python intro_orchestrator.py --medals
"""

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import json
import psycopg2
import logging
import argparse
from datetime import datetime, timedelta

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


def get_upcoming_events(target_date, mode='all'):
    """Find events scheduled for target_date that don't have pre_event commentary."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    query = """
        SELECT DISTINCT su.event_unit_code, d.name as discipline,
               e.name as event, su.event_unit_name, su.medal_flag,
               su.start_time, su.status
        FROM schedule_units su
        JOIN events e ON su.event_id = e.event_id
        JOIN disciplines d ON e.discipline_code = d.code
        LEFT JOIN commentary c
            ON c.event_unit_code = su.event_unit_code
            AND c.commentary_type = 'pre_event'
            AND c.content IS NOT NULL
        WHERE su.start_time::date = %s
        AND c.id IS NULL
    """

    if mode == 'medals':
        query += " AND su.medal_flag > 0"

    query += " ORDER BY su.start_time"

    cur.execute(query, (target_date,))
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


def build_preview_queries(event):
    """Build search queries for pre-event preview content."""
    discipline = event['discipline']
    event_name = event['event']

    # Build clean label
    if discipline.lower() in event_name.lower():
        event_label = event_name
    else:
        event_label = f"{discipline} {event_name}"

    queries = []

    # 1. General preview search
    queries.append({
        'type': 'preview',
        'query': f"{event_label} 2026 Winter Olympics preview",
        'reason': 'General event preview'
    })

    # 2. Favorites / contenders
    queries.append({
        'type': 'contenders',
        'query': f"{event_label} 2026 Olympics favorites contenders",
        'reason': 'Key athletes and favorites'
    })

    # 3. US angle
    queries.append({
        'type': 'usa',
        'query': f"Team USA {event_label} 2026 Olympics",
        'reason': 'US athlete perspective'
    })

    return {
        'event_unit_code': event['event_unit_code'],
        'event_label': event_label,
        'discipline': discipline,
        'start_time': event['start_time'],
        'is_medal_event': event['medal_flag'],
        'unit_name': event['unit_name'],
        'queries': queries,
    }


def build_preview_consolidated(resolved, articles):
    """Build consolidated source file for preview (no results section)."""
    lines = []

    lines.append("=== EVENT CONTEXT ===")
    lines.append(f"Event: {resolved['event_label']}")
    lines.append(f"Discipline: {resolved['discipline']}")
    lines.append(f"Scheduled: {resolved['start_time'].strftime('%B %d, %Y at %I:%M %p')} CET")
    lines.append(f"Medal Event: {'Yes' if resolved['is_medal_event'] else 'No'}")
    lines.append(f"Unit: {resolved['unit_name']}")
    lines.append("")

    for i, article in enumerate(articles, 1):
        lines.append(f"=== SOURCE {i}: {article['domain']} ===")
        lines.append(f"URL: {article['url']}")
        lines.append(f"Title: {article['title']}")
        if article.get('authors'):
            lines.append(f"Authors: {', '.join(article['authors'])}")
        if article.get('publish_date'):
            lines.append(f"Published: {article['publish_date']}")
        lines.append(f"Found via: {article['query_type']} search - {article['query_reason']}")
        lines.append(f"Snippet: {article['snippet']}")
        lines.append("---")
        lines.append(article['text'])
        lines.append("")

    if not articles:
        lines.append("=== NO SOURCES FOUND ===")
        lines.append("No preview articles could be found for this event.")
        lines.append("")

    return '\n'.join(lines)


def update_status(event_unit_code, status, error_message=None):
    """Update or insert pre_event commentary status."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM commentary WHERE event_unit_code = %s AND commentary_type = 'pre_event'",
        (event_unit_code,)
    )
    existing = cur.fetchone()

    if existing:
        if error_message:
            cur.execute("""
                UPDATE commentary SET status = %s, error_message = %s, updated_at = NOW()
                WHERE event_unit_code = %s AND commentary_type = 'pre_event'
            """, (status, error_message, event_unit_code))
        else:
            cur.execute("""
                UPDATE commentary SET status = %s, updated_at = NOW()
                WHERE event_unit_code = %s AND commentary_type = 'pre_event'
            """, (status, event_unit_code))
    else:
        cur.execute("""
            INSERT INTO commentary (event_unit_code, commentary_type, commentary_date,
                                    status, created_at, updated_at)
            VALUES (%s, 'pre_event', NOW(), %s, NOW(), NOW())
        """, (event_unit_code, status))

    conn.commit()
    cur.close()
    conn.close()


def save_intro(event_unit_code, content, proofed_content, sources_meta,
               raw_scrape_data, writer_usage, editor_result):
    """Save completed intro to DB."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    corrections = editor_result.get('corrections', '') if editor_result else ''
    llm_model = writer_usage.get('model', '') if writer_usage else ''
    prompt_ver = writer_usage.get('prompt_version', '') if writer_usage else ''

    cur.execute("""
        UPDATE commentary SET
            content = %s,
            proofed_content = %s,
            sources = %s,
            raw_scrape_data = %s,
            status = 'proofed',
            llm_model = %s,
            prompt_version = %s,
            updated_at = NOW()
        WHERE event_unit_code = %s AND commentary_type = 'pre_event'
    """, (
        content,
        proofed_content,
        json.dumps(sources_meta),
        json.dumps({'consolidated_text': raw_scrape_data, 'corrections': corrections}),
        llm_model,
        prompt_ver,
        event_unit_code,
    ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Saved intro for {event_unit_code}")


def process_event(event, dry_run=False):
    """Full pipeline for a single pre-event intro."""
    from source_scraper import scrape_for_event
    from intro_writer import write_intro
    from intro_editor import edit_intro

    euc = event['event_unit_code']
    logger.info(f"\n{'='*60}")
    logger.info(f"PREVIEW: {event['discipline']} - {event['event']}")
    logger.info(f"  Code: {euc}")
    logger.info(f"  Scheduled: {event['start_time']}")
    logger.info(f"{'='*60}")

    # Step 1: Build preview queries
    resolved = build_preview_queries(event)
    for q in resolved['queries']:
        logger.info(f"  [{q['type']}] {q['query']}")

    if dry_run:
        logger.info("DRY RUN - stopping before scrape")
        return True

    # Step 2: Scrape sources (reuse source_scraper)
    logger.info("Step 2: Scraping preview sources...")
    update_status(euc, 'scraping')

    articles = scrape_for_event(resolved)
    if not articles:
        articles = []

    consolidated = build_preview_consolidated(resolved, articles)
    sources_meta = [{
        'url': a['url'], 'domain': a['domain'],
        'title': a['title'], 'query_type': a['query_type'],
    } for a in articles]

    logger.info(f"  Got {len(articles)} articles, {len(consolidated)} chars consolidated")

    if not articles:
        logger.warning(f"  No sources found for {euc} - skipping (need sources for previews)")
        update_status(euc, 'failed', 'No preview sources found')
        return False

    # Step 3: Write intro
    logger.info("Step 3: Writing preview...")
    update_status(euc, 'writing')

    writer_result = write_intro(consolidated)
    if not writer_result:
        logger.error(f"  Writer failed for {euc}")
        update_status(euc, 'failed', 'Writer LLM call failed')
        return False

    content = writer_result['content']
    logger.info(f"  Written: {len(content)} chars, ${writer_result['usage']['estimated_cost']}")

    # Step 4: Edit
    logger.info("Step 4: Editing (source-check + prose)...")

    editor_result = edit_intro(content, consolidated)
    if not editor_result:
        logger.warning(f"  Editor failed for {euc} - saving unproofed")
        save_intro(euc, content, content, sources_meta,
                   consolidated, writer_result['usage'], None)
        return True

    proofed = editor_result['proofed_content']

    # Step 5: Store
    logger.info("Step 5: Saving to database...")
    save_intro(euc, content, proofed, sources_meta,
               consolidated, writer_result['usage'], editor_result)

    total_cost = writer_result['usage']['estimated_cost'] + editor_result.get('estimated_cost', 0)
    logger.info(f"DONE! Total cost: ${total_cost:.4f}")
    return True


def run_batch(target_date, mode='all', dry_run=False, limit=None):
    """Process upcoming events for a target date."""
    events = get_upcoming_events(target_date, mode)

    if limit:
        events = events[:limit]

    medal_count = sum(1 for e in events if e['medal_flag'])
    logger.info(f"Found {len(events)} upcoming events for {target_date} ({medal_count} medal events)")

    if not events:
        logger.info("Nothing to process")
        return

    for evt in events:
        medal = "[MEDAL]" if evt['medal_flag'] else "      "
        logger.info(f"  {medal} {evt['discipline']} - {evt['event']} @ {evt['start_time']}")

    if dry_run:
        logger.info("\nDRY RUN - no processing")
        return

    success = 0
    failed = 0

    for evt in events:
        try:
            ok = process_event(evt, dry_run=dry_run)
            if ok:
                success += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Unexpected error processing {evt['event_unit_code']}: {e}")
            update_status(evt['event_unit_code'], 'failed', str(e)[:500])
            failed += 1

    logger.info(f"\nBatch complete: {success} success, {failed} failed out of {len(events)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Olympics Pre-Event Intro Pipeline')
    parser.add_argument('event_code', nargs='?', help='Specific event_unit_code to process')
    parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD), default: tomorrow')
    parser.add_argument('--medals', action='store_true', help='Medal events only')
    parser.add_argument('--dry-run', action='store_true', help='Show events without processing')
    parser.add_argument('--limit', type=int, help='Max events to process')

    args = parser.parse_args()

    if args.date:
        target_date = args.date
    else:
        target_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    if args.event_code:
        # Single event - look it up
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT su.event_unit_code, d.name, e.name, su.event_unit_name,
                   su.medal_flag, su.start_time, su.status
            FROM schedule_units su
            JOIN events e ON su.event_id = e.event_id
            JOIN disciplines d ON e.discipline_code = d.code
            WHERE su.event_unit_code = %s
        """, (args.event_code,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            print(f"Event not found: {args.event_code}")
            sys.exit(1)

        event = {
            'event_unit_code': row[0], 'discipline': row[1],
            'event': row[2], 'unit_name': row[3],
            'medal_flag': row[4], 'start_time': row[5], 'status': row[6],
        }
        process_event(event, dry_run=args.dry_run)
    else:
        mode = 'medals' if args.medals else 'all'
        run_batch(target_date, mode=mode, dry_run=args.dry_run, limit=args.limit)
