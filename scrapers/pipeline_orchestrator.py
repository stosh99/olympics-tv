#!/usr/bin/env python3
"""
Pipeline Orchestrator - End-to-end commentary generation.
Ties together: detect → resolve → scrape → write → edit → store

Usage:
    # Process a single event
    python pipeline_orchestrator.py SSKW500M--------------FNL-000100
    
    # Process all unprocessed finished events
    python pipeline_orchestrator.py --all
    
    # Process all medal events only
    python pipeline_orchestrator.py --medals
    
    # Dry run (resolve + show queries, no scraping/writing)
    python pipeline_orchestrator.py --dry-run SSKW500M--------------FNL-000100
"""

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import json
import psycopg2
import logging
import argparse
from datetime import datetime

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



def get_pending_events(mode='all'):
    """Find finished events that don't have commentary yet."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    base_query = """
        SELECT DISTINCT r.event_unit_code, d.name as discipline,
               e.name as event, su.medal_flag, su.start_time
        FROM results r
        JOIN schedule_units su ON r.event_unit_code = su.event_unit_code
        JOIN events e ON su.event_id = e.event_id
        JOIN disciplines d ON e.discipline_code = d.code
        LEFT JOIN commentary c
            ON c.event_unit_code = r.event_unit_code
            AND c.commentary_type = 'post_event'
            AND c.content IS NOT NULL
        WHERE su.status = 'FINISHED'
        AND c.id IS NULL
    """

    if mode == 'medals':
        base_query += " AND su.medal_flag > 0"

    base_query += " ORDER BY su.start_time DESC"

    cur.execute(base_query)
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


def update_commentary_status(event_unit_code, status, error_message=None, commentary_type='post_event'):
    """Update or insert commentary status in DB."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Check if row exists for this specific event_unit_code + commentary_type
    cur.execute(
        "SELECT id FROM commentary WHERE event_unit_code = %s AND commentary_type = %s",
        (event_unit_code, commentary_type)
    )
    existing = cur.fetchone()

    if existing:
        if error_message:
            cur.execute("""
                UPDATE commentary SET status = %s, error_message = %s, updated_at = NOW()
                WHERE event_unit_code = %s AND commentary_type = %s
            """, (status, error_message, event_unit_code, commentary_type))
        else:
            cur.execute("""
                UPDATE commentary SET status = %s, updated_at = NOW()
                WHERE event_unit_code = %s AND commentary_type = %s
            """, (status, event_unit_code, commentary_type))
    else:
        cur.execute("""
            INSERT INTO commentary (event_unit_code, commentary_type, commentary_date,
                                    status, created_at, updated_at)
            VALUES (%s, %s, NOW(), %s, NOW(), NOW())
        """, (event_unit_code, commentary_type, status))

    conn.commit()
    cur.close()
    conn.close()



def save_commentary(event_unit_code, content, proofed_content, sources_meta,
                     raw_scrape_data, writer_usage, editor_result):
    """Save completed commentary to DB."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    corrections = editor_result.get('corrections', '') if editor_result else ''
    llm_model = writer_usage.get('model', '') if writer_usage else ''
    prompt_ver = writer_usage.get('prompt_version', '') if writer_usage else ''

    # Extract token usage data
    input_tokens = 0
    output_tokens = 0
    estimated_cost = 0.0
    if writer_usage and 'usage' in writer_usage:
        usage = writer_usage['usage']
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        estimated_cost = usage.get('estimated_cost', 0.0)

    cur.execute("""
        UPDATE commentary SET
            content = %s,
            proofed_content = %s,
            sources = %s,
            raw_scrape_data = %s,
            status = 'proofed',
            llm_model = %s,
            prompt_version = %s,
            input_tokens = %s,
            output_tokens = %s,
            estimated_cost = %s,
            updated_at = NOW()
        WHERE event_unit_code = %s AND commentary_type = %s
    """, (
        content,
        proofed_content,
        json.dumps(sources_meta),
        json.dumps({'consolidated_text': raw_scrape_data, 'corrections': corrections}),
        llm_model,
        prompt_ver,
        input_tokens,
        output_tokens,
        estimated_cost,
        event_unit_code,
        'post_event',
    ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Saved commentary for {event_unit_code}")


def process_event(event_unit_code, dry_run=False, commentary_type='post_event'):
    """
    Full pipeline for a single event:
    resolve → scrape → write → edit → store
    """
    from source_resolver import resolve_sources

    logger.info(f"\n{'='*60}")
    logger.info(f"PROCESSING [{commentary_type}]: {event_unit_code}")
    logger.info(f"{'='*60}")

    # Step 1: Resolve sources
    logger.info("Step 1: Resolving sources...")
    resolved = resolve_sources(event_unit_code)
    if not resolved:
        logger.error(f"Failed to resolve sources for {event_unit_code}")
        update_commentary_status(event_unit_code, 'failed', 'Source resolution failed', commentary_type)
        return False

    logger.info(f"  Event: {resolved['event_label']}")
    logger.info(f"  Queries: {len(resolved['queries'])}")
    for q in resolved['queries']:
        logger.info(f"    [{q['type']}] {q['query']}")

    if dry_run:
        logger.info("DRY RUN - stopping before scrape")
        return True

    # Lazy imports - only needed for actual processing
    from source_scraper import scrape_for_event, build_consolidated_file
    from commentary_writer import write_commentary
    from commentary_editor import edit_commentary

    # Step 2: Scrape
    logger.info("Step 2: Scraping sources...")
    update_commentary_status(event_unit_code, 'scraping', commentary_type=commentary_type)
    
    articles = scrape_for_event(resolved)
    if not articles:
        logger.warning(f"No articles found for {event_unit_code} - writing with results only")
        articles = []
    
    consolidated = build_consolidated_file(resolved, articles)
    sources_meta = [{
        'url': a['url'], 'domain': a['domain'], 
        'title': a['title'], 'query_type': a['query_type'],
    } for a in articles]

    logger.info(f"  Got {len(articles)} articles, {len(consolidated)} chars consolidated")


    # Step 3: Write commentary
    logger.info("Step 3: Writing commentary...")
    update_commentary_status(event_unit_code, 'writing', commentary_type=commentary_type)
    
    writer_result = write_commentary(consolidated)
    if not writer_result:
        logger.error(f"Commentary writing failed for {event_unit_code}")
        update_commentary_status(event_unit_code, 'failed', 'Writer LLM call failed', commentary_type)
        return False
    
    content = writer_result['content']
    logger.info(f"  Written: {len(content)} chars, ${writer_result['usage']['estimated_cost']}")

    # Step 4: Edit/proof
    logger.info("Step 4: Editing (fact-check + prose polish)...")
    
    editor_result = edit_commentary(content, resolved, sources_meta, consolidated)
    if not editor_result:
        # Editor failed - save unproofed version
        logger.warning(f"Editor failed for {event_unit_code} - saving unproofed")
        save_commentary(
            event_unit_code, content, content, sources_meta,
            consolidated, writer_result['usage'], None
        )
        return True

    proofed = editor_result['proofed_content']
    logger.info(f"  Corrections: {editor_result['corrections'][:100] if editor_result['corrections'] else 'None'}")

    # Step 5: Store
    logger.info("Step 5: Saving to database...")
    save_commentary(
        event_unit_code, content, proofed, sources_meta,
        consolidated, writer_result['usage'], editor_result
    )

    total_cost = writer_result['usage']['estimated_cost'] + editor_result.get('estimated_cost', 0)
    logger.info(f"DONE! Total cost: ${total_cost:.4f}")
    return True


def run_batch(mode='all', dry_run=False, limit=None):
    """Process multiple events."""
    events = get_pending_events(mode)
    
    if limit:
        events = events[:limit]

    logger.info(f"Found {len(events)} pending events (mode={mode})")
    
    if not events:
        logger.info("Nothing to process")
        return

    success = 0
    failed = 0
    
    for evt in events:
        medal = "[MEDAL]" if evt['medal_flag'] else "      "
        logger.info(f"{medal} {evt['discipline']} - {evt['event']} ({evt['event_unit_code'][:20]}...)")
    
    if dry_run:
        logger.info("\nDRY RUN - no processing")
        return

    for evt in events:
        try:
            ok = process_event(evt['event_unit_code'], dry_run=dry_run)
            if ok:
                success += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Unexpected error processing {evt['event_unit_code']}: {e}")
            update_commentary_status(evt['event_unit_code'], 'failed', str(e)[:500])
            failed += 1

    logger.info(f"\nBatch complete: {success} success, {failed} failed out of {len(events)}")



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Olympics Commentary Pipeline')
    parser.add_argument('event_code', nargs='?', help='Specific event_unit_code to process')
    parser.add_argument('--all', action='store_true', help='Process all pending events')
    parser.add_argument('--medals', action='store_true', help='Process only medal events')
    parser.add_argument('--dry-run', action='store_true', help='Show queries without scraping/writing')
    parser.add_argument('--limit', type=int, help='Max events to process in batch mode')

    args = parser.parse_args()

    if args.event_code:
        # Single event
        process_event(args.event_code, dry_run=args.dry_run)
    elif args.all:
        run_batch(mode='all', dry_run=args.dry_run, limit=args.limit)
    elif args.medals:
        run_batch(mode='medals', dry_run=args.dry_run, limit=args.limit)
    else:
        # Default: show pending events
        events = get_pending_events()
        medal_events = [e for e in events if e['medal_flag']]
        print(f"\nPending events: {len(events)} total, {len(medal_events)} medal events")
        print("\nMedal events waiting for commentary:")
        for e in medal_events[:20]:
            print(f"  [MEDAL] {e['discipline']} - {e['event']}")
            print(f"     Code: {e['event_unit_code']}")
        if len(events) > len(medal_events):
            print(f"\n  + {len(events) - len(medal_events)} non-medal events")
        print("\nUsage:")
        print("  python pipeline_orchestrator.py <event_code>     # Single event")
        print("  python pipeline_orchestrator.py --medals          # All medal events")
        print("  python pipeline_orchestrator.py --all             # Everything")
        print("  python pipeline_orchestrator.py --dry-run --all   # Preview only")
