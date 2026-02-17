-- Sport and country source lookup tables for commentary pipeline
-- Migration 004

CREATE TABLE sport_sources (
    id SERIAL PRIMARY KEY,
    discipline_code VARCHAR(10) UNIQUE NOT NULL,
    discipline_name VARCHAR(100),
    governing_body_name VARCHAR(200),
    governing_body_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (discipline_code) REFERENCES disciplines(code)
);

CREATE TABLE country_sources (
    id SERIAL PRIMARY KEY,
    noc VARCHAR(3) UNIQUE NOT NULL,
    country_name VARCHAR(100),
    olympic_committee_url VARCHAR(500),
    high_interest BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_country_sources_noc ON country_sources(noc);
CREATE INDEX idx_country_sources_high_interest ON country_sources(high_interest);
