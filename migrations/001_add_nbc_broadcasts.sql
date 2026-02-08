-- Migration: Add NBC Broadcasts Tables
-- Date: 2026-02-04
-- Description: Add tables for NBC broadcast schedule data aggregation
--
-- To run this migration:
-- sudo -u postgres psql -d olympics_tv -f migrations/001_add_nbc_broadcasts.sql

-- Raw NBC data storage (stores complete API responses)
CREATE TABLE IF NOT EXISTS nbc_broadcasts_raw (
    id SERIAL PRIMARY KEY,
    drupal_id VARCHAR(50) UNIQUE NOT NULL,
    date_queried DATE NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    raw_json JSONB NOT NULL
);

-- Curated broadcast data (parsed and enriched from raw)
CREATE TABLE IF NOT EXISTS nbc_broadcasts (
    id SERIAL PRIMARY KEY,
    drupal_id VARCHAR(50) UNIQUE NOT NULL REFERENCES nbc_broadcasts_raw(drupal_id),
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
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Links NBC broadcasts to Olympic schedule units (many-to-many)
-- Allows matching recap shows to multiple Olympic events
CREATE TABLE IF NOT EXISTS nbc_broadcast_units (
    id SERIAL PRIMARY KEY,
    broadcast_drupal_id VARCHAR(50) REFERENCES nbc_broadcasts(drupal_id) ON DELETE CASCADE,
    unit_code VARCHAR(50),
    UNIQUE(broadcast_drupal_id, unit_code)
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_nbc_broadcasts_raw_date ON nbc_broadcasts_raw(date_queried);
CREATE INDEX IF NOT EXISTS idx_nbc_broadcasts_start ON nbc_broadcasts(start_time);
CREATE INDEX IF NOT EXISTS idx_nbc_broadcasts_network ON nbc_broadcasts(network_name);
CREATE INDEX IF NOT EXISTS idx_nbc_broadcast_units_drupal ON nbc_broadcast_units(broadcast_drupal_id);
CREATE INDEX IF NOT EXISTS idx_nbc_broadcast_units_code ON nbc_broadcast_units(unit_code);

-- Grant read-only and insert permissions to stosh99
GRANT SELECT, INSERT ON nbc_broadcasts_raw TO stosh99;
GRANT SELECT, INSERT, UPDATE ON nbc_broadcasts TO stosh99;
GRANT SELECT, INSERT ON nbc_broadcast_units TO stosh99;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO stosh99;

-- Verify tables created
\dt nbc*
