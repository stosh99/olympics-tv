#!/usr/bin/env python3
"""
Migration script to create NBC broadcast tables
This script needs to run as postgres (superuser) to create new tables
"""

import subprocess
import sys

# SQL migration commands
migration_sql = """
-- Raw NBC data storage (complete API responses from Drupal backend)
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
CREATE TABLE IF NOT EXISTS nbc_broadcast_units (
    id SERIAL PRIMARY KEY,
    broadcast_drupal_id VARCHAR(50) REFERENCES nbc_broadcasts(drupal_id) ON DELETE CASCADE,
    unit_code VARCHAR(50),
    UNIQUE(broadcast_drupal_id, unit_code)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_nbc_broadcasts_raw_date ON nbc_broadcasts_raw(date_queried);
CREATE INDEX IF NOT EXISTS idx_nbc_broadcasts_start ON nbc_broadcasts(start_time);
CREATE INDEX IF NOT EXISTS idx_nbc_broadcasts_network ON nbc_broadcasts(network_name);
CREATE INDEX IF NOT EXISTS idx_nbc_broadcast_units_drupal ON nbc_broadcast_units(broadcast_drupal_id);
CREATE INDEX IF NOT EXISTS idx_nbc_broadcast_units_code ON nbc_broadcast_units(unit_code);

-- Grant permissions to stosh99
GRANT SELECT, INSERT ON nbc_broadcasts_raw TO stosh99;
GRANT SELECT, INSERT, UPDATE ON nbc_broadcasts TO stosh99;
GRANT SELECT, INSERT ON nbc_broadcast_units TO stosh99;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO stosh99;

SELECT 'NBC broadcast tables created successfully' as status;
"""

def execute_migration():
    """Execute the migration SQL"""
    try:
        # Use snap run postgresql.psql with postgres user via Unix socket
        cmd = [
            'snap', 'run', 'postgresql.psql',
            '-U', 'postgres',
            '-d', 'olympics_tv',
            '-h', '/tmp',  # Unix socket
            '-c', migration_sql
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            print("❌ Migration failed:")
            print(result.stderr)
            return False

        print("✓ Migration completed successfully!")
        print(result.stdout)
        return True

    except Exception as e:
        print(f"❌ Error executing migration: {e}")
        return False

if __name__ == '__main__':
    print("Starting NBC broadcast tables migration...")
    print("This script requires postgres (superuser) access.\n")

    success = execute_migration()
    sys.exit(0 if success else 1)
