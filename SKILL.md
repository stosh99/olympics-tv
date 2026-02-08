# Olympics TV Schedule Skill

## Overview
Build and maintain a backend system that aggregates Winter Olympics 2026 event schedules from olympics.com with US TV broadcast times from nbc.com.

**VPS:** 66.220.29.98 (Ubuntu 24.04, 8 cores/24GB RAM)

---

## Data Sources

### 1. Olympics.com (Event Data)
REST API - no auth required. See [API Reference](./reference/api_endpoints.md)

### 2. NBC.com (TV Broadcasts)
Scraping required. Two data types:
- **Single events**: maps to olympics.com schedule units
- **Recap shows**: cover multiple events, need AI parsing

---

## Project Structure
```
olympics-tv/
├── scrapers/
│   ├── olympics_scraper.py    # Fetch from olympics.com API
│   └── nbc_scraper.py         # Scrape NBC broadcast schedule
├── db/
│   ├── schema.sql             # PostgreSQL schema
│   └── migrations/
├── api/
│   └── app.py                 # FastAPI endpoints for frontend
├── jobs/
│   └── nightly_sync.py        # Cron job for NBC rescrape (Phase 2)
├── requirements.txt
└── .env
```

---

## Phase 1: Core Build

### Tasks
1. Set up PostgreSQL on VPS
2. Build olympics.com scraper (API-based)
3. Investigate NBC.com scraping approach
4. Build NBC scraper
5. Create FastAPI endpoints for frontend

### Database
See [Schema Reference](./reference/schema.sql)

**Data Hierarchy:**
```
Discipline (Curling)
  └── Event (Mixed Doubles)
        └── Phase (Round Robin)
              └── Unit (Session 1)
                    └── Matchup (GBR vs NOR)
```

---

## Phase 2: Nightly Sync

NBC broadcast schedule changes as Olympics progress. Implement nightly cron job to:
1. Re-scrape NBC schedule
2. Diff against existing data
3. Update/insert new broadcasts
4. Log changes

---

## Key Decisions
- **Timezone**: Store all times as TIMESTAMPTZ, display in user's local time
- **Competitor types**: TEAM (countries) vs ATHLETE (individuals)
- **Recap shows**: Store raw description, parse with AI agent to extract covered sports

---

## Reference Files
- [API Endpoints](./reference/api_endpoints.md) - Olympics.com API details
- [Database Schema](./reference/schema.sql) - PostgreSQL tables
- [Scraping Patterns](./reference/scraping_patterns.md) - NBC scraping notes
