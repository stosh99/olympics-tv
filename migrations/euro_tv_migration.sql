-- Euro TV Schedule Tables Migration
-- Olympics 2026 — watcholympics2026.com
-- Run after reviewing euro_tv_schema_design.md

-- ============================================
-- Table 1: euro_channels (static reference)
-- ============================================
CREATE TABLE euro_channels (
    id SERIAL PRIMARY KEY,
    channel_code VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    country_code VARCHAR(2) NOT NULL,
    region VARCHAR(20) NOT NULL,
    language VARCHAR(5) NOT NULL,
    timezone VARCHAR(30) NOT NULL,
    source VARCHAR(10) NOT NULL,
    source_channel_id VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_euro_channels_country ON euro_channels(country_code);
CREATE INDEX idx_euro_channels_region ON euro_channels(region);
CREATE INDEX idx_euro_channels_source ON euro_channels(source);

-- ============================================
-- Table 2: euro_broadcasts_raw (debug archive)
-- ============================================
CREATE TABLE euro_broadcasts_raw (
    id SERIAL PRIMARY KEY,
    channel_code VARCHAR(50) NOT NULL,
    date_queried DATE NOT NULL,
    source VARCHAR(10) NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    raw_json JSONB NOT NULL,
    UNIQUE(channel_code, date_queried, source),
    FOREIGN KEY (channel_code) REFERENCES euro_channels(channel_code)
);

CREATE INDEX idx_euro_raw_date ON euro_broadcasts_raw(date_queried);

-- ============================================
-- Table 3: euro_broadcasts (normalized, Olympic only)
-- ============================================
CREATE TABLE euro_broadcasts (
    id SERIAL PRIMARY KEY,
    broadcast_id VARCHAR(100) UNIQUE NOT NULL,
    channel_code VARCHAR(50) NOT NULL,
    title_original VARCHAR(500),
    title_english VARCHAR(500),
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_minutes INTEGER,
    is_live BOOLEAN DEFAULT FALSE,
    is_replay BOOLEAN DEFAULT FALSE,
    source_event_id VARCHAR(100),
    olympic_day INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (channel_code) REFERENCES euro_channels(channel_code)
);

CREATE INDEX idx_euro_broadcasts_channel ON euro_broadcasts(channel_code);
CREATE INDEX idx_euro_broadcasts_start ON euro_broadcasts(start_time);
CREATE INDEX idx_euro_broadcasts_date ON euro_broadcasts(CAST(timezone('UTC', start_time) AS date));

-- ============================================
-- Table 4: euro_broadcast_units (JOIN to schedule_units)
-- ============================================
CREATE TABLE euro_broadcast_units (
    id SERIAL PRIMARY KEY,
    broadcast_id VARCHAR(100) NOT NULL,
    unit_code VARCHAR(100) NOT NULL,
    match_method VARCHAR(20) NOT NULL,
    match_confidence DECIMAL(3,2),
    matched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(broadcast_id, unit_code),
    FOREIGN KEY (broadcast_id) REFERENCES euro_broadcasts(broadcast_id) ON DELETE CASCADE,
    FOREIGN KEY (unit_code) REFERENCES schedule_units(event_unit_code)
);

CREATE INDEX idx_euro_bu_broadcast ON euro_broadcast_units(broadcast_id);
CREATE INDEX idx_euro_bu_unit ON euro_broadcast_units(unit_code);
CREATE INDEX idx_euro_bu_confidence ON euro_broadcast_units(match_confidence);

-- ============================================
-- Seed data: euro_channels
-- ============================================
INSERT INTO euro_channels (channel_code, display_name, country_code, region, language, timezone, source, source_channel_id) VALUES
-- UK
('bbc1', 'BBC One', 'GB', 'uk', 'en', 'Europe/London', 'epg_pw', '76657'),
('bbc2', 'BBC Two', 'GB', 'uk', 'en', 'Europe/London', 'epg_pw', '12499'),
-- Germany
('ard', 'ARD', 'DE', 'western_europe', 'de', 'Europe/Berlin', 'epg_pw', '76674'),
('zdf', 'ZDF', 'DE', 'western_europe', 'de', 'Europe/Berlin', 'epg_pw', '76627'),
('euro1_de', 'Eurosport 1', 'DE', 'western_europe', 'de', 'Europe/Berlin', 'epg_pw', '76619'),
('euro2_de', 'Eurosport 2', 'DE', 'western_europe', 'de', 'Europe/Berlin', 'epg_pw', '76744'),
-- Italy
('rai1', 'RAI 1', 'IT', 'western_europe', 'it', 'Europe/Rome', 'epg_pw', '459199'),
('rai2', 'RAI 2', 'IT', 'western_europe', 'it', 'Europe/Rome', 'epg_pw', '459214'),
('rai3', 'RAI 3', 'IT', 'western_europe', 'it', 'Europe/Rome', 'epg_pw', '459196'),
('raisport', 'RAI Sport', 'IT', 'western_europe', 'it', 'Europe/Rome', 'epg_pw', '392165'),
-- France
('france2', 'France 2', 'FR', 'western_europe', 'fr', 'Europe/Paris', 'epg_pw', '55812'),
('france3', 'France 3', 'FR', 'western_europe', 'fr', 'Europe/Paris', 'epg_pw', '55715'),
-- Denmark (epg.pw)
('dr1', 'DR1', 'DK', 'nordic', 'da', 'Europe/Copenhagen', 'epg_pw', '438463'),
('dr2', 'DR2', 'DK', 'nordic', 'da', 'Europe/Copenhagen', 'epg_pw', '438451'),
-- Norway (Allente)
('nrk1', 'NRK1', 'NO', 'nordic', 'no', 'Europe/Oslo', 'allente', '0090'),
('nrk2', 'NRK2', 'NO', 'nordic', 'no', 'Europe/Oslo', 'allente', '0288'),
('nrk3', 'NRK3', 'NO', 'nordic', 'no', 'Europe/Oslo', 'allente', '0289'),
('euro_no', 'Eurosport Norge', 'NO', 'nordic', 'no', 'Europe/Oslo', 'allente', '530'),
('euro1_no', 'Eurosport 1 NO', 'NO', 'nordic', 'no', 'Europe/Oslo', 'allente', '531'),
-- Sweden (Allente)
('svt1', 'SVT1', 'SE', 'nordic', 'sv', 'Europe/Stockholm', 'allente', '0148'),
('svt2', 'SVT2', 'SE', 'nordic', 'sv', 'Europe/Stockholm', 'allente', '0282'),
('euro1_se', 'Eurosport 1 SE', 'SE', 'nordic', 'sv', 'Europe/Stockholm', 'allente', '1023');

-- Finland TBD — need to verify Allente.fi channel IDs for YLE TV2 and Eurosport

-- ============================================
-- Grant permissions
-- ============================================
GRANT SELECT, INSERT, UPDATE ON euro_channels TO stosh99;
GRANT SELECT, INSERT ON euro_broadcasts_raw TO stosh99;
GRANT SELECT, INSERT, UPDATE, DELETE ON euro_broadcasts TO stosh99;
GRANT SELECT, INSERT, DELETE ON euro_broadcast_units TO stosh99;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO stosh99;

-- ============================================
-- Helper view: all broadcasts (NBC + Euro) for a schedule unit
-- ============================================
CREATE OR REPLACE VIEW v_all_broadcasts AS
SELECT
    'nbc' AS source,
    nb.network_name AS channel,
    NULL AS country_code,
    nb.title,
    nb.start_time,
    nb.end_time,
    nb.is_replay,
    nbu.unit_code,
    1.00 AS match_confidence
FROM nbc_broadcast_units nbu
JOIN nbc_broadcasts nb ON nbu.broadcast_drupal_id = nb.drupal_id

UNION ALL

SELECT
    'euro' AS source,
    ec.display_name AS channel,
    ec.country_code,
    eb.title_original AS title,
    eb.start_time,
    eb.end_time,
    eb.is_replay,
    ebu.unit_code,
    ebu.match_confidence
FROM euro_broadcast_units ebu
JOIN euro_broadcasts eb ON ebu.broadcast_id = eb.broadcast_id
JOIN euro_channels ec ON eb.channel_code = ec.channel_code;

SELECT 'Euro TV tables created successfully' as status;
