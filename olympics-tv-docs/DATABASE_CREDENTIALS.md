# Olympics TV Database Credentials

## CRITICAL - Save These Immediately

**Created:** Feb 4, 2026 (Session 2)
**PostgreSQL Version:** 16.11 (snap)
**Status:** Fresh installation

### Connection Parameters
- **Host:** localhost
- **Port:** 5433
- **Connection Type:** TCP (MUST use `-h localhost -p 5433`)
- **Database:** olympics_tv
- **User:** stosh99
- **Password:** olympics_tv_dev

### Connection Examples

**As stosh99 (application user):**
```bash
PGPASSWORD=olympics_tv_dev psql -h localhost -p 5433 -U stosh99 -d olympics_tv
```

**Via DBeaver:**
- Host: localhost
- Port: 5433
- Database: olympics_tv
- Username: stosh99
- Password: olympics_tv_dev

### Postgres Superuser
- **User:** postgres
- **Password:** postgres_olympics_2026 (set during installation)
- **Full command:** `sudo -u postgres psql -h localhost -p 5433 -d olympics_tv`

## Important Notes
- Always include `-h localhost -p 5433` for TCP connections
- Do NOT try Unix sockets - they don't work with snap PostgreSQL
- Password is `olympics_tv_dev` (not postgres_olympics_2026 - that's for postgres user)

## Maintenance

### Check service status:
```bash
sudo snap services postgresql
```

### Restart service:
```bash
sudo snap restart postgresql
```

### Stop service:
```bash
sudo snap stop postgresql
```

### Start service:
```bash
sudo snap start postgresql
```
