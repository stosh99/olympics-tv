-- Results table - flattened from competitors_json for easy querying
-- Migration 003

CREATE TABLE results (
    id SERIAL PRIMARY KEY,
    event_unit_code VARCHAR(100) NOT NULL,
    competitor_code VARCHAR(50),
    noc VARCHAR(3),
    competitor_name VARCHAR(200),
    position INT,
    mark VARCHAR(50),
    winner_loser_tie VARCHAR(1),
    medal_type VARCHAR(20),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (event_unit_code) REFERENCES schedule_units(event_unit_code),
    UNIQUE(event_unit_code, competitor_code)
);

CREATE INDEX idx_results_event_unit ON results(event_unit_code);
CREATE INDEX idx_results_noc ON results(noc);
CREATE INDEX idx_results_medal ON results(medal_type);
CREATE INDEX idx_results_detected ON results(detected_at);
CREATE INDEX idx_results_position ON results(position);
