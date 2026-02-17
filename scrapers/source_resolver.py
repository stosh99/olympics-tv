#!/usr/bin/env python3
"""
Source Resolver - Given an event_unit_code, builds the search queries
needed to gather commentary sources.

Queries:
1. General event search
2. Gold country search
3. Silver country search
4. Bronze country search
5. USA search (always, unless USA already covered by 2-4)
"""

from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'olympics_tv'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}


def get_event_context(cur, event_unit_code):
    """Get event details and results from DB"""
    cur.execute("""
        SELECT d.name as discipline, e.name as event, su.event_unit_name,
               su.start_time, su.medal_flag
        FROM schedule_units su
        JOIN events e ON su.event_id = e.event_id
        JOIN disciplines d ON e.discipline_code = d.code
        WHERE su.event_unit_code = %s
    """, (event_unit_code,))
    row = cur.fetchone()
    if not row:
        return None
    
    context = {
        'discipline': row[0],
        'event': row[1],
        'unit_name': row[2],
        'start_time': row[3],
        'medal_flag': row[4],
    }

    # Get results ordered by position/medal
    cur.execute("""
        SELECT competitor_name, noc, position, mark, medal_type, winner_loser_tie
        FROM results
        WHERE event_unit_code = %s
        ORDER BY 
            CASE WHEN medal_type = 'ME_GOLD' THEN 1
                 WHEN medal_type = 'ME_SILVER' THEN 2
                 WHEN medal_type = 'ME_BRONZE' THEN 3
                 ELSE 4 END,
            position NULLS LAST
    """, (event_unit_code,))
    
    context['results'] = [{
        'name': r[0], 'noc': r[1], 'position': r[2],
        'mark': r[3], 'medal_type': r[4], 'wlt': r[5]
    } for r in cur.fetchall()]

    return context


def get_medal_nocs(context):
    """Extract NOCs for gold, silver, bronze"""
    nocs = {}
    for r in context['results']:
        if r['medal_type'] == 'ME_GOLD' and 'gold' not in nocs:
            nocs['gold'] = r['noc']
        elif r['medal_type'] == 'ME_SILVER' and 'silver' not in nocs:
            nocs['silver'] = r['noc']
        elif r['medal_type'] == 'ME_BRONZE' and 'bronze' not in nocs:
            nocs['bronze'] = r['noc']
    
    # For non-medal events, use top finishers or winner/loser
    if not nocs:
        for r in context['results']:
            if r['wlt'] == 'W' and 'winner' not in nocs:
                nocs['winner'] = r['noc']
            elif r['position'] == 1 and 'winner' not in nocs:
                nocs['winner'] = r['noc']
    
    return nocs


def get_country_names(cur, nocs):
    """Look up country names from NOC codes"""
    if not nocs:
        return {}
    codes = list(set(nocs.values()))
    cur.execute(
        "SELECT noc, country_name FROM country_sources WHERE noc = ANY(%s)",
        (codes,)
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def build_event_label(context):
    """Build a clean event label for search queries"""
    # Use event name if it's descriptive, otherwise combine discipline + unit
    event = context['event']
    discipline = context['discipline']
    
    # If event name already contains the discipline, just use event
    if discipline.lower() in event.lower():
        return event
    return f"{discipline} {event}"


def resolve_sources(event_unit_code):
    """Main function - returns list of search queries for an event"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    context = get_event_context(cur, event_unit_code)
    if not context:
        logger.error(f"Event not found: {event_unit_code}")
        cur.close()
        conn.close()
        return None

    event_label = build_event_label(context)
    event_date = context['start_time'].strftime('%B %d, %Y')
    medal_nocs = get_medal_nocs(context)
    country_names = get_country_names(cur, medal_nocs)

    queries = []

    # 1. General event search (include unit name for non-medal events for specificity)
    if context['medal_flag']:
        general_label = f"{event_label} 2026 Winter Olympics results"
    else:
        general_label = f"{event_label} {context['unit_name']} 2026 Winter Olympics results"
    
    queries.append({
        'type': 'general',
        'query': general_label,
        'reason': 'Main event coverage'
    })

    # 2-4. Medal country searches (deduplicated)
    usa_covered = False
    seen_nocs = set()
    for medal_type in ['gold', 'silver', 'bronze', 'winner']:
        noc = medal_nocs.get(medal_type)
        if not noc or noc in seen_nocs:
            continue
        seen_nocs.add(noc)
        country = country_names.get(noc, noc)
        if noc == 'USA':
            usa_covered = True
        queries.append({
            'type': f'{medal_type}_country',
            'noc': noc,
            'query': f"{country} {event_label} 2026 Olympics",
            'reason': f'{medal_type.title()} medal country perspective'
        })

    # 5. USA search (if not already covered)
    if not usa_covered:
        queries.append({
            'type': 'usa',
            'noc': 'USA',
            'query': f"Team USA {event_label} 2026 Olympics",
            'reason': 'US audience perspective'
        })

    cur.close()
    conn.close()

    return {
        'event_unit_code': event_unit_code,
        'event_label': event_label,
        'event_date': event_date,
        'discipline': context['discipline'],
        'is_medal_event': context['medal_flag'],
        'results': context['results'],
        'queries': queries
    }


if __name__ == '__main__':
    import sys
    
    # Default test event or accept command line arg
    code = sys.argv[1] if len(sys.argv) > 1 else 'SSKW500M--------------FNL-000100'
    
    result = resolve_sources(code)
    if not result:
        print("Event not found")
        sys.exit(1)

    print(f"\nEvent: {result['event_label']}")
    print(f"Date: {result['event_date']}")
    print(f"Medal event: {result['is_medal_event']}")
    print(f"\nResults ({len(result['results'])} competitors):")
    for r in result['results'][:5]:
        medal = f" [{r['medal_type']}]" if r['medal_type'] else ""
        pos = f"#{r['position']}" if r['position'] else r.get('wlt', '?')
        print(f"  {pos} {r['name']} ({r['noc']}) - {r['mark']}{medal}")
    
    print(f"\nSearch Queries ({len(result['queries'])}):")
    for q in result['queries']:
        print(f"  [{q['type']}] {q['query']}")
        print(f"    Reason: {q['reason']}")
