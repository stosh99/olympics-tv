# PostgreSQL Connection Details

## CRITICAL: Host and Port Required

**SNAP PostgreSQL does NOT use Unix sockets by default on this system**

### Connection Parameters
- **Host:** localhost (REQUIRED - use `-h localhost`)
- **Port:** 5433 (REQUIRED - use `-p 5433`)
- **Database:** olympics_tv
- **TCP Connection Only** (NOT Unix socket)

### Connection Commands

**As stosh99 user:**
```bash
PGPASSWORD=dbeaver_password psql -h localhost -p 5433 -U stosh99 -d olympics_tv
```

**As postgres user (superuser):**
```bash
sudo -u postgres psql -h localhost -p 5433 -d olympics_tv
```

**From DBeaver:**
- Host: localhost
- Port: 5433
- Database: olympics_tv
- User: stosh99 (or postgres for admin)
- Password: dbeaver_password

## Password Information

- **stosh99 password:** dbeaver_password
- **postgres password:** postgres_olympics_2026 (being set in Feb 4 session)

## Why This Matters

The snap PostgreSQL installation listens on **TCP port 5433**, not on the default Unix socket paths:
- ❌ NOT at `/var/run/postgresql/.s.PGSQL.5433` (Unix socket)
- ❌ NOT at `/tmp/.s.PGSQL.5433` (Unix socket)
- ✅ ALWAYS use `-h localhost -p 5433` for TCP connection

## Common Mistakes to Avoid

- Do NOT omit `-h localhost` - psql will try Unix socket and fail
- Do NOT use port 5432 (default) - snap is on 5433
- Do NOT try to connect via Unix socket - it won't work

## PostgreSQL Service

- Installation: snap (PostgreSQL 16.11)
- Service: `snap.postgresql.postgresql`
- Start/stop: `sudo snap start/stop postgresql`
- Status: `snap services postgresql`
