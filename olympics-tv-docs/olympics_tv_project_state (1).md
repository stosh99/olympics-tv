# Olympics TV Project - State Save (Feb 4, 2026)

## PROJECT OVERVIEW
Winter Olympics 2026 TV Schedule Website
VPS: 66.220.29.98 (Ubuntu 24.04, 8 cores/24GB RAM)
Project dir: ~/PycharmProjects/olympics-tv
SSH: serveroptima/Qkl1ksvW

## DATABASE
- PostgreSQL 16 on port **5432** (fresh install, was 5433 before)
- Connection: `postgresql://stosh99:olympics_tv_dev@127.0.0.1:5432/olympics_tv`
- Master login: postgres / olympics_tv_dev
- TCP localhost connection (confirmed in DBeaver)

### Tables (11):
- disciplines, events, venues, schedule_units, competitors, unit_competitors, sync_log
- nbc_broadcasts_raw, nbc_broadcasts, nbc_broadcast_units, nbc_broadcast_rundown

### Views (4):
- v_full_schedule, v_matchups, v_nbc_schedule, v_schedule_with_broadcasts

## DATA LOADED
- **Olympics.com**: Feb 4-22 schedule data loaded via olympics_scraper.py
- **NBC**: 628 broadcasts loaded via nbc_scraper.py
  - Networks: NBC, USA, CNBC, Peacock, Gold Zone
- **1,172 linked events** between Olympics.com and NBC (via unit codes)
- Raw JSON files saved in ~/PycharmProjects/olympics-tv/raw_data/
  - Olympics: olympics{MMDDYYYY}.json
  - NBC: nbc{MMDDYYYY}.json

## API (RUNNING)
- FastAPI at http://localhost:8000
- Files: ~/PycharmProjects/olympics-tv/api/ (main.py, database.py, models.py)
- Endpoints:
  - GET /api/dates - all dates with counts
  - GET /api/schedule/{date} - Olympic events + broadcasts for a date
  - GET /api/tv/{date} - NBC broadcasts grouped by network
  - GET /api/medals/{date} - medal events only
  - GET /api/search?q= - search events
  - GET /health - health check
- CORS enabled, all origins allowed

## FRONTEND - NEXT STEP
- User built a UI in v0 (Vercel) - React component
- URL: https://v0.app/chat/winter-olympics-tv-schedule-qTohoiCPdCM
- Could not access from web_fetch (client-side rendered, private)
- **User needs to copy/paste the v0 code** into the conversation
- Once received, review the code and adapt it to connect to the FastAPI endpoints
- Deploy to VPS via Claude Code

## SKILL PACKAGE
- Located at ~/PycharmProjects/olympics-tv/olympics-tv-skill/
- Contains: SKILL.md, schema.sql, api_endpoints.md, scraping_patterns.md
- Needs update with NBC API details and new schema

## DATA SOURCE APIS

### Olympics.com
- Endpoint: https://www.olympics.com/wmr-owg2026/schedules/api/ENG/schedule/lite/day/{YYYY-MM-DD}
- Headers: User-Agent, Referer required
- No auth

### NBC Olympics
- Endpoint: https://schedules.nbcolympics.com/api/v1/schedule?timeZone=America/Chicago&startDate={YYYY-MM-DD}&inPattern=true
- No auth required
- Key fields: network.name, units[].code (links to Olympics.com), rundown.items[], dayPart
- Unit codes link to Olympics.com via event_unit_code = id

## KEY DECISIONS MADE
- Store raw NBC JSON in nbc_broadcasts_raw + curated fields in nbc_broadcasts
- NBC unit codes join to schedule_units.event_unit_code
- is_replay determined by title containing "Re-air", "Encore", or "Replay"
- Null network = Peacock streaming
- Gold Zone is a separate "network" (Peacock whip-around stream)

## TRANSCRIPT
Full conversation transcript at: /mnt/transcripts/2026-02-05-04-29-17-nbc-olympics-api-analysis.txt
