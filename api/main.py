"""
FastAPI backend for Olympics TV schedule
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional, List, Dict
import logging
import os

from api.database import init_connection_pool, close_all_connections, execute_query_dict
from api.models import (
    ScheduleResponse, Event, Competitor, Broadcast,
    TVResponse, BroadcastDetail, LinkedEvent, RundownSegment,
    DatesResponse, DateInfo
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Olympics TV API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """Initialize connection pool on startup"""
    init_connection_pool()
    logger.info("API started")


@app.on_event("shutdown")
def shutdown():
    """Close connection pool on shutdown"""
    close_all_connections()
    logger.info("API shutdown")


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "Olympics TV API",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.get("/api/schedule/{date}", response_model=ScheduleResponse)
def get_schedule(date: str):
    """
    Get all Olympic events for a given date with linked NBC broadcasts.
    Format: YYYY-MM-DD
    """
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Query Olympic events for the date
    query = """
        SELECT
            su.event_unit_code,
            su.event_unit_name,
            d.name as discipline,
            e.name as event_name,
            e.gender_code as gender,
            su.start_time,
            su.end_time,
            v.name as venue,
            su.medal_flag,
            su.phase_name,
            su.status
        FROM schedule_units su
        LEFT JOIN events e ON su.event_id = e.event_id
        LEFT JOIN disciplines d ON e.discipline_code = d.code
        LEFT JOIN venues v ON su.venue_code = v.code
        WHERE DATE(su.start_time) = %s
        ORDER BY su.start_time
    """

    events_data = execute_query_dict(query, (date,))

    if not events_data:
        return ScheduleResponse(
            date=date,
            medal_events_count=0,
            total_events=0,
            events=[]
        )

    # Build events with competitors and broadcasts
    events = []
    medal_count = 0

    for event_data in events_data:
        event_unit_code = event_data['event_unit_code']

        # Get competitors for this event
        competitors_query = """
            SELECT c.code, c.name, c.noc, c.competitor_type
            FROM unit_competitors uc
            JOIN competitors c ON uc.competitor_code = c.code
            WHERE uc.event_unit_code = %s
            ORDER BY uc.start_order
        """
        competitors_data = execute_query_dict(competitors_query, (event_unit_code,))
        competitors = [
            Competitor(
                code=c['code'],
                name=c['name'],
                noc=c['noc'],
                competitor_type=c['competitor_type']
            )
            for c in competitors_data
        ]

        # Get broadcasts for this event
        broadcasts_query = """
            SELECT
                nb.drupal_id,
                nb.title,
                nb.network_name as network,
                nb.start_time,
                nb.end_time,
                nb.day_part,
                nb.summary,
                nb.video_url,
                nb.is_replay
            FROM nbc_broadcast_units nbu
            JOIN nbc_broadcasts nb ON nbu.broadcast_drupal_id = nb.drupal_id
            WHERE nbu.unit_code = %s
            ORDER BY nb.start_time
        """
        broadcasts_data = execute_query_dict(broadcasts_query, (event_unit_code,))
        broadcasts = [
            Broadcast(
                drupal_id=b['drupal_id'],
                title=b['title'],
                network=b['network'],
                start_time=b['start_time'],
                end_time=b['end_time'],
                day_part=b['day_part'],
                summary=b['summary'],
                video_url=b['video_url'],
                is_replay=b['is_replay']
            )
            for b in broadcasts_data
        ]

        event = Event(
            event_unit_code=event_data['event_unit_code'],
            event_unit_name=event_data['event_unit_name'],
            discipline=event_data['discipline'] or 'Unknown',
            event_name=event_data['event_name'] or 'Unknown',
            gender=event_data['gender'],
            start_time=event_data['start_time'],
            end_time=event_data['end_time'],
            venue=event_data['venue'],
            medal_flag=bool(event_data['medal_flag']),
            phase_name=event_data['phase_name'],
            status=event_data['status'],
            competitors=competitors,
            broadcasts=broadcasts
        )

        if event.medal_flag:
            medal_count += 1

        events.append(event)

    return ScheduleResponse(
        date=date,
        medal_events_count=medal_count,
        total_events=len(events),
        events=events
    )


@app.get("/api/tv/{date}", response_model=TVResponse)
def get_tv_schedule(date: str):
    """
    Get NBC broadcast schedule for a given date, grouped by network.
    Format: YYYY-MM-DD
    """
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Query broadcasts for the date
    query = """
        SELECT
            nb.drupal_id,
            nb.title,
            nb.short_title,
            nb.network_name,
            nb.start_time,
            nb.end_time,
            nb.day_part,
            nb.summary,
            nb.video_url,
            nb.peacock_url,
            nb.is_medal_session,
            nb.is_replay,
            nb.olympic_day
        FROM nbc_broadcasts nb
        WHERE DATE(nb.start_time) = %s
        ORDER BY nb.network_name, nb.start_time
    """

    broadcasts_data = execute_query_dict(query, (date,))

    # Group broadcasts by network
    networks = {}

    for broadcast in broadcasts_data:
        # Group null/streaming under "Peacock"
        network = broadcast['network_name'] or 'Peacock'

        if network not in networks:
            networks[network] = []

        # Get linked events for this broadcast
        events_query = """
            SELECT
                su.event_unit_code,
                su.event_unit_name,
                d.name as discipline,
                su.medal_flag
            FROM nbc_broadcast_units nbu
            JOIN schedule_units su ON nbu.unit_code = su.event_unit_code
            LEFT JOIN events e ON su.event_id = e.event_id
            LEFT JOIN disciplines d ON e.discipline_code = d.code
            WHERE nbu.broadcast_drupal_id = %s
            ORDER BY su.start_time
        """
        events_data = execute_query_dict(events_query, (broadcast['drupal_id'],))
        linked_events = [
            LinkedEvent(
                event_unit_code=e['event_unit_code'],
                event_unit_name=e['event_unit_name'],
                discipline=e['discipline'] or 'Unknown',
                medal_flag=bool(e['medal_flag'])
            )
            for e in events_data
        ]

        # Get rundown segments for this broadcast
        rundown_query = """
            SELECT header, description, segment_time
            FROM nbc_broadcast_rundown
            WHERE broadcast_drupal_id = %s
            ORDER BY segment_order
        """
        rundown_data = execute_query_dict(rundown_query, (broadcast['drupal_id'],))
        rundown = [
            RundownSegment(
                header=r['header'],
                description=r['description'],
                segment_time=r['segment_time']
            )
            for r in rundown_data
        ]

        broadcast_detail = BroadcastDetail(
            drupal_id=broadcast['drupal_id'],
            title=broadcast['title'],
            short_title=broadcast['short_title'],
            start_time=broadcast['start_time'],
            end_time=broadcast['end_time'],
            day_part=broadcast['day_part'],
            summary=broadcast['summary'],
            video_url=broadcast['video_url'],
            peacock_url=broadcast['peacock_url'],
            is_medal_session=broadcast['is_medal_session'],
            is_replay=broadcast['is_replay'],
            olympic_day=broadcast['olympic_day'],
            linked_events=linked_events,
            rundown=rundown
        )

        networks[network].append(broadcast_detail)

    return TVResponse(date=date, networks=networks)


@app.get("/api/dates", response_model=DatesResponse)
def get_dates():
    """
    Get all available dates with event counts.
    """
    query = """
        SELECT DISTINCT
            DATE(su.start_time)::text as date,
            COUNT(*) FILTER (WHERE su.medal_flag = 1) as medal_events,
            COUNT(*) as total_events,
            COUNT(DISTINCT nbu.broadcast_drupal_id) as broadcast_count
        FROM schedule_units su
        LEFT JOIN nbc_broadcast_units nbu ON su.event_unit_code = nbu.unit_code
        WHERE su.start_time IS NOT NULL
        GROUP BY DATE(su.start_time)
        ORDER BY date
    """

    dates_data = execute_query_dict(query)

    dates = [
        DateInfo(
            date=d['date'],
            total_events=d['total_events'],
            medal_events=d['medal_events'],
            broadcast_count=d['broadcast_count']
        )
        for d in dates_data
    ]

    return DatesResponse(dates=dates)


@app.get("/api/medals/{date}", response_model=ScheduleResponse)
def get_medals(date: str):
    """
    Get only medal events for a given date with broadcast info.
    Format: YYYY-MM-DD
    """
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Query medal events for the date
    query = """
        SELECT
            su.event_unit_code,
            su.event_unit_name,
            d.name as discipline,
            e.name as event_name,
            e.gender_code as gender,
            su.start_time,
            su.end_time,
            v.name as venue,
            su.medal_flag,
            su.phase_name,
            su.status,
            su.id as schedule_unit_id
        FROM schedule_units su
        LEFT JOIN events e ON su.event_id = e.event_id
        LEFT JOIN disciplines d ON e.discipline_code = d.code
        LEFT JOIN venues v ON su.venue_code = v.code
        WHERE DATE(su.start_time) = %s
        AND su.medal_flag = 1
        ORDER BY su.start_time
    """

    events_data = execute_query_dict(query, (date,))

    if not events_data:
        return ScheduleResponse(
            date=date,
            medal_events_count=0,
            total_events=0,
            events=[]
        )

    # Build events with competitors and broadcasts
    events = []

    for event_data in events_data:
        event_unit_code = event_data['event_unit_code']

        # Get competitors for this event
        competitors_query = """
            SELECT c.code, c.name, c.noc, c.competitor_type
            FROM unit_competitors uc
            JOIN competitors c ON uc.competitor_code = c.code
            WHERE uc.event_unit_code = %s
            ORDER BY uc.start_order
        """
        competitors_data = execute_query_dict(competitors_query, (event_unit_code,))
        competitors = [
            Competitor(
                code=c['code'],
                name=c['name'],
                noc=c['noc'],
                competitor_type=c['competitor_type']
            )
            for c in competitors_data
        ]

        # Get broadcasts for this event
        broadcasts_query = """
            SELECT
                nb.drupal_id,
                nb.title,
                nb.network_name as network,
                nb.start_time,
                nb.end_time,
                nb.day_part,
                nb.summary,
                nb.video_url,
                nb.is_replay
            FROM nbc_broadcast_units nbu
            JOIN nbc_broadcasts nb ON nbu.broadcast_drupal_id = nb.drupal_id
            WHERE nbu.unit_code = %s
            ORDER BY nb.start_time
        """
        broadcasts_data = execute_query_dict(broadcasts_query, (event_unit_code,))
        broadcasts = [
            Broadcast(
                drupal_id=b['drupal_id'],
                title=b['title'],
                network=b['network'],
                start_time=b['start_time'],
                end_time=b['end_time'],
                day_part=b['day_part'],
                summary=b['summary'],
                video_url=b['video_url'],
                is_replay=b['is_replay']
            )
            for b in broadcasts_data
        ]

        event = Event(
            event_unit_code=event_data['event_unit_code'],
            event_unit_name=event_data['event_unit_name'],
            discipline=event_data['discipline'] or 'Unknown',
            event_name=event_data['event_name'] or 'Unknown',
            gender=event_data['gender'],
            start_time=event_data['start_time'],
            end_time=event_data['end_time'],
            venue=event_data['venue'],
            medal_flag=bool(event_data['medal_flag']),
            phase_name=event_data['phase_name'],
            status=event_data['status'],
            competitors=competitors,
            broadcasts=broadcasts
        )

        events.append(event)

    return ScheduleResponse(
        date=date,
        medal_events_count=len(events),
        total_events=len(events),
        events=events
    )


@app.get("/api/search")
def search_events(q: str = Query(..., min_length=1)):
    """
    Search events by discipline, event name, or country.
    """
    # Build search query with wildcards
    search_term = f"%{q}%"

    query = """
        SELECT DISTINCT
            su.event_unit_code,
            su.event_unit_name,
            d.name as discipline,
            e.name as event_name,
            e.gender_code as gender,
            su.start_time,
            su.end_time,
            v.name as venue,
            su.medal_flag,
            su.phase_name,
            su.status
        FROM schedule_units su
        LEFT JOIN events e ON su.event_id = e.event_id
        LEFT JOIN disciplines d ON e.discipline_code = d.code
        LEFT JOIN venues v ON su.venue_code = v.code
        LEFT JOIN unit_competitors uc ON su.event_unit_code = uc.event_unit_code
        LEFT JOIN competitors c ON uc.competitor_code = c.code
        WHERE d.name ILIKE %s
        OR e.name ILIKE %s
        OR c.name ILIKE %s
        OR c.noc ILIKE %s
        ORDER BY su.start_time
        LIMIT 50
    """

    events_data = execute_query_dict(query, (search_term, search_term, search_term, search_term))

    if not events_data:
        return {"results": [], "count": 0}

    # Build results with competitors and broadcasts
    results = []

    for event_data in events_data:
        event_unit_code = event_data['event_unit_code']

        # Get competitors for this event
        competitors_query = """
            SELECT c.code, c.name, c.noc, c.competitor_type
            FROM unit_competitors uc
            JOIN competitors c ON uc.competitor_code = c.code
            WHERE uc.event_unit_code = %s
            ORDER BY uc.start_order
        """
        competitors_data = execute_query_dict(competitors_query, (event_unit_code,))
        competitors = [
            Competitor(
                code=c['code'],
                name=c['name'],
                noc=c['noc'],
                competitor_type=c['competitor_type']
            )
            for c in competitors_data
        ]

        # Get broadcasts for this event
        broadcasts_query = """
            SELECT
                nb.drupal_id,
                nb.title,
                nb.network_name as network,
                nb.start_time,
                nb.end_time,
                nb.day_part,
                nb.summary,
                nb.video_url,
                nb.is_replay
            FROM nbc_broadcast_units nbu
            JOIN nbc_broadcasts nb ON nbu.broadcast_drupal_id = nb.drupal_id
            WHERE nbu.unit_code = %s
            ORDER BY nb.start_time
        """
        broadcasts_data = execute_query_dict(broadcasts_query, (event_unit_code,))
        broadcasts = [
            Broadcast(
                drupal_id=b['drupal_id'],
                title=b['title'],
                network=b['network'],
                start_time=b['start_time'],
                end_time=b['end_time'],
                day_part=b['day_part'],
                summary=b['summary'],
                video_url=b['video_url'],
                is_replay=b['is_replay']
            )
            for b in broadcasts_data
        ]

        event = Event(
            event_unit_code=event_data['event_unit_code'],
            event_unit_name=event_data['event_unit_name'],
            discipline=event_data['discipline'] or 'Unknown',
            event_name=event_data['event_name'] or 'Unknown',
            gender=event_data['gender'],
            start_time=event_data['start_time'],
            end_time=event_data['end_time'],
            venue=event_data['venue'],
            medal_flag=bool(event_data['medal_flag']),
            phase_name=event_data['phase_name'],
            status=event_data['status'],
            competitors=competitors,
            broadcasts=broadcasts
        )

        results.append(event)

    return {"results": results, "count": len(results)}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
