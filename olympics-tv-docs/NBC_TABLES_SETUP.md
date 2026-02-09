# NBC Broadcast Tables Setup

## Status
Tables defined but **PENDING CREATION** - need postgres superuser access

## Schema Files Updated ✓
- `/home/stosh99/PycharmProjects/olympics-tv/schema.sql`
- `/home/stosh99/PycharmProjects/olympics-tv/olympics-tv-skill/reference/schema.sql`

## Migration File Created ✓
- `/home/stosh99/PycharmProjects/olympics-tv/migrations/001_add_nbc_broadcasts.sql`

## Table Definitions

### 1. nbc_broadcasts_raw
Stores complete Drupal API responses as JSONB
- drupal_id (PK, unique)
- date_queried
- fetched_at
- raw_json (JSONB)

### 2. nbc_broadcasts
Curated broadcast metadata
- drupal_id (FK to nbc_broadcasts_raw)
- title, short_title
- start_time, end_time (TIMESTAMPTZ)
- network_name (NBC, USA, CNBC, Peacock, E!)
- day_part (Primetime, Daytime, etc.)
- summary (TEXT)
- video_url
- is_medal_session (BOOLEAN)
- olympic_day (1-17)

### 3. nbc_broadcast_units
Links broadcasts to Olympic schedule units (many-to-many)
- broadcast_drupal_id (FK)
- unit_code (FK to schedule_units.unit_code)
- UNIQUE constraint on (broadcast_drupal_id, unit_code)

## How to Create Tables

**Easiest Option: Use DBeaver**
1. Open DBeaver (you're already connected)
2. Create new SQL query
3. Copy contents of `/home/stosh99/PycharmProjects/olympics-tv/migrations/001_add_nbc_broadcasts.sql`
4. Execute query

**Command Line (requires postgres password or sudo)**
```bash
# Option 1: With postgres password
psql -h localhost -p 5433 -U postgres -d olympics_tv -f /home/stosh99/PycharmProjects/olympics-tv/migrations/001_add_nbc_broadcasts.sql

# Option 2: With sudo
sudo -u postgres psql -d olympics_tv -f /home/stosh99/PycharmProjects/olympics-tv/migrations/001_add_nbc_broadcasts.sql
```

## Permission Issue Details
- Public schema owned by postgres user
- stosh99 has INSERT/SELECT permissions (can use tables)
- stosh99 lacks CREATE permission (cannot create tables)
- Need postgres superuser to CREATE new tables

## Next Steps After Table Creation
1. Build nbc_scraper.py to fetch data from NBC JSON endpoint
2. Parse NBC data and insert into nbc_broadcasts table
3. Create junction records in nbc_broadcast_units
4. Link NBC broadcasts to Olympic schedule units
