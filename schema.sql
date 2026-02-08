-- Olympics TV Schedule Database Schema
-- PostgreSQL - Designed for olympics_scraper.py

CREATE TABLE disciplines (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(50) UNIQUE NOT NULL,
    discipline_code VARCHAR(10) NOT NULL,
    name VARCHAR(200),
    gender_code VARCHAR(10),
    event_type VARCHAR(20),
    event_order INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (discipline_code) REFERENCES disciplines(code)
);

CREATE INDEX idx_events_discipline_code ON events(discipline_code);
CREATE INDEX idx_events_event_id ON events(event_id);

CREATE TABLE venues (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    long_name VARCHAR(200),
    location_code VARCHAR(20),
    location_name VARCHAR(100),
    location_long_name VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_venues_code ON venues(code);

CREATE TABLE schedule_units (
    id SERIAL PRIMARY KEY,
    event_unit_code VARCHAR(100) UNIQUE NOT NULL,
    event_id VARCHAR(50),
    event_unit_name VARCHAR(200),
    phase_code VARCHAR(20),
    phase_name VARCHAR(100),
    phase_type VARCHAR(50),
    venue_code VARCHAR(20),
    olympic_day INT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    status VARCHAR(20),
    medal_flag BOOLEAN,
    live_flag BOOLEAN,
    schedule_item_type VARCHAR(50),
    session_code VARCHAR(50),
    group_id VARCHAR(50),
    unit_num INT,
    competitors_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (event_id) REFERENCES events(event_id),
    FOREIGN KEY (venue_code) REFERENCES venues(code)
);

CREATE INDEX idx_schedule_units_event_id ON schedule_units(event_id);
CREATE INDEX idx_schedule_units_venue_code ON schedule_units(venue_code);
CREATE INDEX idx_schedule_units_start_time ON schedule_units(start_time);
CREATE INDEX idx_schedule_units_status ON schedule_units(status);
CREATE INDEX idx_schedule_units_unit_code ON schedule_units(event_unit_code);

CREATE TABLE competitors (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    noc VARCHAR(3),
    name VARCHAR(100),
    competitor_type VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitors_code ON competitors(code);
CREATE INDEX idx_competitors_noc ON competitors(noc);

CREATE TABLE unit_competitors (
    id SERIAL PRIMARY KEY,
    event_unit_code VARCHAR(100) NOT NULL,
    competitor_code VARCHAR(50) NOT NULL,
    start_order INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_unit_code, competitor_code),
    FOREIGN KEY (event_unit_code) REFERENCES schedule_units(event_unit_code),
    FOREIGN KEY (competitor_code) REFERENCES competitors(code)
);

CREATE INDEX idx_unit_competitors_unit_code ON unit_competitors(event_unit_code);
CREATE INDEX idx_unit_competitors_competitor_code ON unit_competitors(competitor_code);

CREATE TABLE sync_log (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50),
    sync_type VARCHAR(50),
    status VARCHAR(20),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    records_processed INT
);

CREATE INDEX idx_sync_log_source ON sync_log(source);

-- NBC Broadcast tables
CREATE TABLE nbc_broadcasts_raw (
    id SERIAL PRIMARY KEY,
    drupal_id VARCHAR(50) UNIQUE NOT NULL,
    date_queried DATE NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    raw_json JSONB NOT NULL
);

CREATE INDEX idx_nbc_broadcasts_raw_date ON nbc_broadcasts_raw(date_queried);

CREATE TABLE nbc_broadcasts (
    id SERIAL PRIMARY KEY,
    drupal_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255),
    short_title VARCHAR(255),
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    network_name VARCHAR(50),
    day_part VARCHAR(100),
    summary TEXT,
    video_url TEXT,
    is_medal_session BOOLEAN DEFAULT FALSE,
    olympic_day INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (drupal_id) REFERENCES nbc_broadcasts_raw(drupal_id)
);

CREATE INDEX idx_nbc_broadcasts_start_time ON nbc_broadcasts(start_time);
CREATE INDEX idx_nbc_broadcasts_network_name ON nbc_broadcasts(network_name);

CREATE TABLE nbc_broadcast_units (
    id SERIAL PRIMARY KEY,
    broadcast_drupal_id VARCHAR(50) NOT NULL,
    unit_code VARCHAR(50) NOT NULL,
    UNIQUE(broadcast_drupal_id, unit_code),
    FOREIGN KEY (broadcast_drupal_id) REFERENCES nbc_broadcasts(drupal_id) ON DELETE CASCADE,
    FOREIGN KEY (unit_code) REFERENCES schedule_units(event_unit_code)
);

CREATE INDEX idx_nbc_broadcast_units_drupal ON nbc_broadcast_units(broadcast_drupal_id);
CREATE INDEX idx_nbc_broadcast_units_code ON nbc_broadcast_units(unit_code);

-- Helper views
CREATE VIEW v_full_schedule AS
SELECT
    su.id,
    d.name AS discipline,
    d.code AS discipline_code,
    e.name AS event,
    e.event_type,
    su.phase_name,
    su.event_unit_name,
    su.start_time,
    su.end_time,
    su.medal_flag,
    su.status,
    v.name AS venue,
    v.location_name AS location
FROM schedule_units su
LEFT JOIN events e ON su.event_id = e.event_id
LEFT JOIN disciplines d ON e.discipline_code = d.code
LEFT JOIN venues v ON su.venue_code = v.code
ORDER BY su.start_time;

CREATE VIEW v_matchups AS
SELECT
    su.id AS unit_id,
    su.event_unit_code,
    d.name AS discipline,
    e.name AS event,
    su.phase_name,
    su.start_time,
    su.competitors_json
FROM schedule_units su
LEFT JOIN events e ON su.event_id = e.event_id
LEFT JOIN disciplines d ON e.discipline_code = d.code
WHERE e.event_type = 'TEAM'
ORDER BY su.start_time;
