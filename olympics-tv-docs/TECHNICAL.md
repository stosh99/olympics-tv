# Technical Implementation Details

## Database Setup

### PostgreSQL Connection
```bash
PGPASSWORD=olympics_tv_dev psql -h localhost -p 5432 -U stosh99 -d olympics_tv
```
- **Host:** localhost (TCP, not Unix socket)
- **Port:** 5432
- **Database:** olympics_tv
- **User:** stosh99
- **Password:** olympics_tv_dev

### Database Schema (10 Tables + 2 Views)

**Core Tables:**
- `disciplines` - Sports (Curling, Figure Skating, etc.)
- `events` - Events within disciplines (Mixed Doubles, Men's Doubles, etc.)
- `venues` - Physical locations (Ice Halls, Arenas, etc.)
- `schedule_units` - Individual sessions/matchups
- `competitors` - Teams/athletes
- `unit_competitors` - Many-to-many join for matchups

**Broadcast Tables:**
- `nbc_broadcasts_raw` - Raw JSON responses from NBC API
- `nbc_broadcasts` - Parsed NBC broadcast data (title, network, times, URLs)
- `nbc_broadcast_units` - Links broadcasts to Olympic schedule units
- `nbc_broadcast_rundown` - Show segment breakdowns

**Tracking:**
- `sync_log` - Records scraping operations (date, source, status)

**Views:**
- `v_full_schedule` - Joins schedule_units with discipline/venue info
- `v_matchups` - Head-to-head event view

### Data Hierarchy
```
Discipline (Curling)
  └── Event (Mixed Doubles)
        └── Phase (Round Robin)
              └── Unit (Session 1, starts Feb 8 9:05 AM)
                    └── Competitor Teams (GBR, NOR, etc.)
```

## Data Sources

### Olympics.com API
**Endpoint:** `https://www.olympics.com/wmr-owg2026/schedules/api/ENG/schedule/lite/day/{YYYY-MM-DD}`

**Response Structure:**
```json
{
  "units": [{
    "disciplineCode": "CUR",
    "disciplineName": "Curling",
    "eventId": "...",
    "eventCode": "CURXD",
    "eventName": "Mixed Doubles",
    "eventType": "TEAM",
    "startDate": "2026-02-08T09:05:00+01:00",
    "competitors": [
      {"noc": "GBR", "code": "CURXD-GBR", "name": "Great Britain", "order": 1},
      {"noc": "NOR", "code": "CURXD-NOR", "name": "Norway", "order": 2}
    ]
  }]
}
```

**Coverage:** Feb 4-22, 2026 (19 days of Olympic events)

### NBC.com API
**Endpoint:** `https://schedules.nbcolympics.com/api/v1/schedule?timeZone=America/New_York&startDate={YYYY-MM-DD}&inPattern=true`

**Networks Covered:**
- NBC (176 broadcasts)
- USA (327 broadcasts)
- CNBC (38 broadcasts)
- GOLD ZONE (15 broadcasts)
- Streaming/Peacock (416 broadcasts, null network)

**Total:** 992 broadcasts covering Feb 4-23, 2026

## Scrapers

### olympics_scraper.py
**Location:** `/home/stosh99/PycharmProjects/olympics-tv/scrapers/olympics_scraper.py`

**Key Methods:**
- `fetch_schedule(date_str)` - Fetches from Olympics.com API
- `save_raw_json()` - Saves raw responses to `raw_data/olympics{MMDDYYYY}.json`
- `upsert_*()` - Idempotent insert/update for each table
- `log_sync()`, `update_sync_log()` - Tracks operations
- `process_day(date_str)` - Processes single day
- `run(start_date, end_date)` - Full date range (1.5s delay between days)

**Features:**
- Uses `INSERT ON CONFLICT UPDATE` pattern (idempotent, re-runnable)
- Skips competitor code "TBD" (placeholders for future matchups)
- Logs all operations to sync_log table

### nbc_scraper.py
**Location:** `/home/stosh99/PycharmProjects/olympics-tv/scrapers/nbc_scraper.py`

**Key Methods:**
- `fetch_schedule(date_str)` - Fetches from NBC API
- `save_raw_json()` - Saves to `raw_data/nbc{MMDDYYYY}.json`
- `upsert_broadcasts_raw()` - Stores complete JSON response
- `upsert_broadcasts()` - Parses and curates fields
- `upsert_broadcast_units()` - Links broadcasts to Olympic schedule units
- `upsert_broadcast_rundown()` - Stores show segments
- `process_day(date_str)` - Processes single day
- `run(start_date, end_date)` - Full date range (1.5s delay)

**Timezone:** America/New_York (EST/EDT)
**Timestamp Handling:** Unix timestamps (seconds) → TIMESTAMPTZ
**Replay Detection:** Checks title for "Re-air", "Encore", "Replay" (case insensitive)

## Frontend Architecture

### Tech Stack
- **Framework:** Next.js 14+ with React
- **Styling:** TailwindCSS
- **Date Handling:** Native JavaScript Date
- **State Management:** React Hooks (useState, useEffect, useCallback, useMemo)

### Key Components
**schedule-grid.tsx** - Main component with:
- Multi-day horizontal scroll (19 days × 38 time slots = 92,416px width)
- Dynamic row heights based on concurrent events (56px per band)
- Vertical event stacking (bands 0-4)
- Hero banner with Olympic rings
- Sport filter pills
- Calendar date picker
- Timezone selector

### State Management
```typescript
// Date & Navigation
const [selectedDate, setSelectedDate] = useState<Date>()
const [leftmostVisibleDate, setLeftmostVisibleDate] = useState("2026-02-04")

// Data
const [tvRangeData, setTvRangeData] = useState<TvSchedule[]>()
const [schedRangeData, setScheduleRangeData] = useState<Schedule[]>()

// Filters
const [checkedSports, setCheckedSports] = useState<Set<string>>(new Set())
const [filterActive, setFilterActive] = useState(false)

// Concurrent Events
const [maxConcurrentPerDay, setMaxConcurrentPerDay] = useState<Map<string, Map<string, number>>>()

// UI
const [timezone, setTimezone] = useState("Eastern")
const [viewMode, setViewMode] = useState<"tv" | "sports">("tv")
```

### Data Processing

**tvToGridEvents()** - Converts NBC broadcasts to grid format:
- Input: Array of TvSchedule objects
- Output: Map<Network, Map<Date, GridEvent[]>>
- Calls `assignBandIndicesForDay()` for global band assignment
- Handles concurrent event stacking

**scheduleToGridEvents()** - Converts Olympic events to grid format:
- Input: Array of Schedule objects
- Output: Map<Discipline, Map<Date, GridEvent[]>>
- Calls `assignBandIndicesForDay()` for global band assignment
- Handles concurrent event stacking

**assignBandIndicesForDay(events)** - Global band assignment:
- Assigns events to bands 0-4 using greedy algorithm
- Prevents overlapping events in same band
- Called once at data load (not per-render)
- Returns events with `bandIndex` property set

**calculateMaxConcurrentPerDay(gridEvents, dates)** - Max concurrent per day:
- Returns: Map<Date, Map<NetworkOrDiscipline, number>>
- Calculates peak concurrent events for each day/network
- Used to size row heights dynamically

### Event Positioning
```typescript
// Start position from 5:00 AM grid start
const startPos = getAbsolutePosition(event.startTime)  // pixels from grid start
const endPos = getAbsolutePosition(event.endTime)

// Width = exact duration in pixels
const width = endPos - startPos

// Vertical position based on band
const top = bandIndex * 56 + 2  // 56px per band, 2px padding

// Styling
style={{
  position: "absolute",
  left: `${startPos + 2 + bandIndex * 8}px`,  // horizontal position + band offset
  width: `${Math.max(0, width - 4 - bandIndex * 16)}px`,  // exact width
  top: `${(event.bandIndex || 0) * 56 + 2}px`,  // vertical stacking
  height: "52px",  // 56px - 4px padding
  zIndex: 10 + (event.bandIndex || 0)  // proper layering
}}
```

### Grid Dimensions
- **Time Slot Width:** 128px (one 30-minute interval)
- **Row Height:** 56px per band (base unit)
- **Day Width:** 38 slots × 128px = 4,864px
- **Total Width:** 19 days × 4,864px = 92,416px (scrollable)
- **Dynamic Height:** 56px × maxConcurrent for each row

### Scroll Mechanism
- Single horizontal scrollbar in right column
- Arrow buttons scroll by full day (4,864px)
- Calendar selection scrolls to specific date
- Time header scrolls automatically with content
- Date updates at day boundary (5:00 AM, using Math.floor)

## API Endpoints

### Internal API (lib/api.ts)
- `fetchTvScheduleRange(startDate, endDate)` - Fetch NBC broadcasts
- `fetchOlympicScheduleRange(startDate, endDate)` - Fetch Olympic events
- `generateDateRange(start, end)` - Generate date array
- `formatDateParam(date)` - Format to YYYY-MM-DD (local timezone)

### External APIs
- Olympics.com: No authentication required
- NBC.com: No authentication required (public schedule API)

## Known Data Quirks

### NBC Timezone
- **Critical:** Must use `timeZone=America/New_York` (Eastern Time)
- Using Chicago timezone causes incorrect date grouping for early morning events
- Fixed in Session 19

### Replay Shows
- NBC includes both live events and replays
- Replays identified by title containing "Re-air", "Encore", or "Replay"
- Separate `is_replay` column in database

### Concurrent Events
- **Peacock:** Up to 30 concurrent (capped at 5 rows = 280px)
- **CNBC:** Up to 5 concurrent (capped at 5 rows = 280px)
- **NBC:** Up to 2 concurrent (2 rows = 112px)
- **USA, GOLD ZONE:** Max 1 each (1 row = 56px)

**Important:** Row heights recalculate at day boundaries (5:00 AM), not at 2:30 PM

## Performance Notes

### Optimization Done
- `useMemo` for expensive calculations (disciplinesWithEvents, filteredRows)
- `useCallback` for event handlers (handleScroll, scrollToDate)
- Nested Maps for O(1) data lookup
- Inline event filtering (no separate filter pass)

### Load Times
- Initial data load: Promise.all for 19 days in parallel
- Event rendering: 5000+ events across 19 days
- Grid width: 92,416px (handled by CSS Grid + scrolling)

## Build & Deployment

### Development
```bash
cd winter-olympics-tv-scheduleV0
npm install
npm run dev  # Runs on http://localhost:3000
```

### Production Build
```bash
npm run build
npm start
```

### Deployment Target
- **Server:** 66.220.29.98 (Ubuntu 24.04, 8 cores/24GB RAM)
- **Database:** Will need PostgreSQL setup + data import
- **Frontend:** Deploy via Next.js (can use PM2, systemd, etc.)

## Future Enhancements

### Phase 3: Nightly Sync
- Cron job to re-scrape NBC schedule daily
- Diff and update/insert new broadcasts
- Log changes to sync_log

### Possible Additions
- Real-time broadcast notifications
- User favorites/watchlist
- Calendar export
- Multi-sport statistics
- Prediction/betting integration
