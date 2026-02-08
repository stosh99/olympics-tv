-- Olympics TV Schedule Database Schema
-- PostgreSQL

-- ===================
-- DISCIPLINES & EVENTS
-- ===================

CREATE TABLE disciplines (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    discipline_id INT REFERENCES disciplines(id),
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    event_type VARCHAR(10), -- TEAM or INDV
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_discipline ON events(discipline_id);

-- ===================
-- VENUES
-- ===================

CREATE TABLE venues (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    short_desc VARCHAR(100),
    long_desc VARCHAR(200),
    location_code VARCHAR(20),
    location_desc VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===================
-- SCHEDULE UNITS
-- ===================

CREATE TABLE schedule_units (
    id SERIAL PRIMARY KEY,
    event_id INT REFERENCES events(id),
    venue_id INT REFERENCES venues(id),
    unit_code VARCHAR(50) UNIQUE,
    phase_name VARCHAR(100),
    phase_type VARCHAR(50),
    unit_name VARCHAR(200),
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    olympic_day INT,
    medal_flag BOOLEAN DEFAULT FALSE,
    status VARCHAR(20),
    status_desc VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_schedule_units_event ON schedule_units(event_id);
CREATE INDEX idx_schedule_units_start ON schedule_units(start_date);
CREATE INDEX idx_schedule_units_status ON schedule_units(status);

-- ===================
-- COMPETITORS
-- ===================

CREATE TABLE competitors (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    noc VARCHAR(3),  -- country code (USA, GBR, etc.)
    competitor_type VARCHAR(10), -- TEAM or ATHLETE
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitors_noc ON competitors(noc);
CREATE INDEX idx_competitors_type ON competitors(competitor_type);

-- ===================
-- UNIT-COMPETITOR JUNCTION (Matchups)
-- ===================

CREATE TABLE unit_competitors (
    id SERIAL PRIMARY KEY,
    schedule_unit_id INT REFERENCES schedule_units(id) ON DELETE CASCADE,
    competitor_id INT REFERENCES competitors(id),
    position INT,  -- 1 or 2 for head-to-head, lane/order for races
    result VARCHAR(50),  -- W/L, score, time, DNF, etc.
    UNIQUE(schedule_unit_id, competitor_id)
);

CREATE INDEX idx_unit_competitors_unit ON unit_competitors(schedule_unit_id);
CREATE INDEX idx_unit_competitors_competitor ON unit_competitors(competitor_id);

-- ===================
-- NBC BROADCASTS
-- ===================

CREATE TABLE broadcasts (
    id SERIAL PRIMARY KEY,
    schedule_unit_id INT REFERENCES schedule_units(id) NULL, -- null for recap shows
    network VARCHAR(50) NOT NULL,  -- NBC, USA, CNBC, Peacock, E!
    air_start TIMESTAMPTZ NOT NULL,
    air_end TIMESTAMPTZ,
    is_live BOOLEAN DEFAULT FALSE,
    is_recap BOOLEAN DEFAULT FALSE,
    description TEXT,  -- raw description for recap shows
    parsed_sports TEXT[],  -- AI-extracted sports from recap description
    source_url TEXT,  -- NBC page URL for reference
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_broadcasts_unit ON broadcasts(schedule_unit_id);
CREATE INDEX idx_broadcasts_network ON broadcasts(network);
CREATE INDEX idx_broadcasts_air_start ON broadcasts(air_start);
CREATE INDEX idx_broadcasts_is_live ON broadcasts(is_live);

-- ===================
-- SYNC LOG (Phase 2)
-- ===================

CREATE TABLE sync_log (
    id SERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL,  -- 'olympics' or 'nbc'
    sync_type VARCHAR(20) NOT NULL,  -- 'full' or 'incremental'
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    records_processed INT DEFAULT 0,
    records_inserted INT DEFAULT 0,
    records_updated INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',  -- running, success, failed
    error_message TEXT
);

-- ===================
-- HELPER VIEWS
-- ===================

-- Full schedule with discipline and venue info
CREATE VIEW v_full_schedule AS
SELECT 
    su.id,
    d.name AS discipline,
    d.code AS discipline_code,
    e.name AS event,
    e.event_type,
    su.phase_name,
    su.unit_name,
    su.start_date,
    su.end_date,
    su.medal_flag,
    su.status,
    v.short_desc AS venue,
    v.location_desc AS location
FROM schedule_units su
JOIN events e ON su.event_id = e.id
JOIN disciplines d ON e.discipline_id = d.id
LEFT JOIN venues v ON su.venue_id = v.id
ORDER BY su.start_date;

-- Matchups view for head-to-head events
CREATE VIEW v_matchups AS
SELECT 
    su.id AS unit_id,
    d.name AS discipline,
    e.name AS event,
    su.phase_name,
    su.start_date,
    c1.name AS competitor_1,
    c1.noc AS noc_1,
    uc1.result AS result_1,
    c2.name AS competitor_2,
    c2.noc AS noc_2,
    uc2.result AS result_2
FROM schedule_units su
JOIN events e ON su.event_id = e.id
JOIN disciplines d ON e.discipline_id = d.id
LEFT JOIN unit_competitors uc1 ON su.id = uc1.schedule_unit_id AND uc1.position = 1
LEFT JOIN competitors c1 ON uc1.competitor_id = c1.id
LEFT JOIN unit_competitors uc2 ON su.id = uc2.schedule_unit_id AND uc2.position = 2
LEFT JOIN competitors c2 ON uc2.competitor_id = c2.id
WHERE e.event_type = 'TEAM'
ORDER BY su.start_date;

-- ===================
-- NBC BROADCASTS
-- ===================

-- Raw NBC data storage (complete API responses from Drupal backend)
CREATE TABLE nbc_broadcasts_raw (
    id SERIAL PRIMARY KEY,
    drupal_id VARCHAR(50) UNIQUE NOT NULL,
    date_queried DATE NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    raw_json JSONB NOT NULL
);

-- Curated broadcast data (parsed and enriched from raw)
CREATE TABLE nbc_broadcasts (
    id SERIAL PRIMARY KEY,
    drupal_id VARCHAR(50) UNIQUE NOT NULL REFERENCES nbc_broadcasts_raw(drupal_id),
    title VARCHAR(255),
    short_title VARCHAR(255),
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    network_name VARCHAR(50),  -- NBC, USA, CNBC, Peacock, E!
    day_part VARCHAR(100),     -- Primetime, Daytime, Late Night, etc.
    summary TEXT,              -- Broadcast description
    video_url TEXT,            -- Link to video on nbcolympics.com
    is_medal_session BOOLEAN DEFAULT FALSE,  -- Medal ceremony flag
    olympic_day INTEGER,       -- Day of Olympics (1-17)
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Links NBC broadcasts to Olympic schedule units (many-to-many)
-- Allows matching single-event broadcasts and recap shows to Olympic events
CREATE TABLE nbc_broadcast_units (
    id SERIAL PRIMARY KEY,
    broadcast_drupal_id VARCHAR(50) REFERENCES nbc_broadcasts(drupal_id) ON DELETE CASCADE,
    unit_code VARCHAR(50),  -- References schedule_units.unit_code
    UNIQUE(broadcast_drupal_id, unit_code)
);

CREATE INDEX idx_nbc_broadcasts_raw_date ON nbc_broadcasts_raw(date_queried);
CREATE INDEX idx_nbc_broadcasts_start ON nbc_broadcasts(start_time);
CREATE INDEX idx_nbc_broadcasts_network ON nbc_broadcasts(network_name);
CREATE INDEX idx_nbc_broadcast_units_drupal ON nbc_broadcast_units(broadcast_drupal_id);
CREATE INDEX idx_nbc_broadcast_units_code ON nbc_broadcast_units(unit_code);
