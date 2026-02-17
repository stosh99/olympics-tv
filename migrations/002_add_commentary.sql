-- Commentary table for AI-generated event commentary
-- Migration 002

CREATE TABLE commentary (
    id SERIAL PRIMARY KEY,
    event_unit_code VARCHAR(100),
    commentary_type VARCHAR(20) NOT NULL CHECK (commentary_type IN ('pre_event', 'post_event', 'general', 'city')),
    commentary_date TIMESTAMPTZ NOT NULL,
    content TEXT,
    proofed_content TEXT,
    sources JSONB,
    raw_scrape_data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'scraping', 'analyzing', 'writing', 'proofed', 'published', 'failed')),
    error_message TEXT,
    llm_model VARCHAR(100),
    prompt_version VARCHAR(50),
    publish_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (event_unit_code) REFERENCES schedule_units(event_unit_code)
);

-- event_unit_code is nullable for 'general' and 'city' types
CREATE INDEX idx_commentary_event_unit ON commentary(event_unit_code);
CREATE INDEX idx_commentary_type ON commentary(commentary_type);
CREATE INDEX idx_commentary_status ON commentary(status);
CREATE INDEX idx_commentary_date ON commentary(commentary_date);
CREATE INDEX idx_commentary_publish_date ON commentary(publish_date);
