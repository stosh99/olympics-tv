# Database Setup & Maintenance

## Initial Setup

### BYE Competitor Entry

The Olympics scraper encounters "BYE" entries in tournament bracket data (single-elimination formats where competitors advance without competing). To maintain referential integrity with the foreign key constraint, a placeholder BYE competitor must be created in the database.

**Run this query once during initial database setup:**

```sql
INSERT INTO competitors (code, noc, name, competitor_type)
VALUES ('BYE', 'BYE', 'Bye', 'bye')
ON CONFLICT (code) DO NOTHING;
```

**Command line:**
```bash
PGPASSWORD=olympics_tv_dev psql -h localhost -p 5432 -U stosh99 -d olympics_tv << 'EOF'
INSERT INTO competitors (code, noc, name, competitor_type)
VALUES ('BYE', 'BYE', 'Bye', 'bye')
ON CONFLICT (code) DO NOTHING;
EOF
```

**Verification:**
```bash
PGPASSWORD=olympics_tv_dev psql -h localhost -p 5432 -U stosh99 -d olympics_tv -c "SELECT * FROM competitors WHERE code = 'BYE';"
```

Expected output: One row with code='BYE', noc='BYE', name='Bye', competitor_type='bye'

### Why This Is Needed

- Olympics.com data includes tournament brackets with "BYE" entries for advancement without competition
- The `unit_competitors` table has a foreign key constraint on the `competitors.code` column
- Without a BYE competitor entry, the Olympics scraper will fail with: `ForeignKeyViolation: insert or update on table "unit_competitors" violates foreign key constraint "unit_competitors_competitor_code_fkey"`

### Note for Frontend

The BYE competitor is intentionally minimal (not a real athlete). When displaying schedule data:
- Filter out matches with competitor_code='BYE' for normal athlete listings
- Or display them as "Bye" if showing tournament advancement

## Nightly Scraper

The nightly scraper runs automatically via cron at **3:30 AM daily** and:
- Fetches Olympics.com schedule data (Feb 3 - Feb 22)
- Fetches NBC broadcast data (Feb 4 - Feb 23)
- Upserts all changes to the database

Logs are saved to: `~/.logs/olympics-tv/nightly-scrape-YYYYMMDD.log`

See `scrapers/nightly_scrape.sh` for implementation details.
