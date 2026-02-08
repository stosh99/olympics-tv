# Olympics TV - Systemd Service Setup Guide

This guide explains how to set up the Olympics TV application as systemd services for production deployment on Ubuntu/Debian.

## Prerequisites

- Ubuntu 20.04+ or Debian 11+
- Application cloned to `/home/olympics/olympics-tv/`
- Virtual environment created: `venv/`
- Frontend built: `winter-olympics-tv-scheduleV0/.next/`
- PostgreSQL installed and running

## Step 1: Create Application User

```bash
# Create 'olympics' user for running the service
sudo useradd -m -s /bin/bash -d /home/olympics olympics

# Add user to necessary groups (if needed)
sudo usermod -aG www-data olympics

# Set permissions
sudo chown -R olympics:olympics /home/olympics/olympics-tv
```

## Step 2: Copy Service Files

```bash
# Copy backend service
sudo cp /home/olympics/olympics-tv/olympics-tv.service /etc/systemd/system/

# Copy frontend service
sudo cp /home/olympics/olympics-tv/olympics-tv-frontend.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload
```

## Step 3: Configure Environment

Edit the `.env` file with production values:

```bash
sudo nano /home/olympics/olympics-tv/.env
```

Required variables:
```env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://olympics_user:YOUR_PASSWORD@localhost:5432/olympics_tv
SECRET_KEY=your-generated-secret-key
NEXT_PUBLIC_API_URL=https://api.watcholympics2026.com
```

## Step 4: Enable Services

```bash
# Enable services to start on boot
sudo systemctl enable olympics-tv.service
sudo systemctl enable olympics-tv-frontend.service

# Start the services
sudo systemctl start olympics-tv.service
sudo systemctl start olympics-tv-frontend.service

# Check status
sudo systemctl status olympics-tv.service
sudo systemctl status olympics-tv-frontend.service
```

## Step 5: Verify Services

```bash
# Check if backend is running
curl http://localhost:8000/api/dates

# Check if frontend is running
curl http://localhost:3000/

# View logs
sudo journalctl -u olympics-tv.service -f
sudo journalctl -u olympics-tv-frontend.service -f
```

## Common Commands

```bash
# Start service
sudo systemctl start olympics-tv.service

# Stop service
sudo systemctl stop olympics-tv.service

# Restart service
sudo systemctl restart olympics-tv.service

# View logs (last 100 lines)
sudo journalctl -u olympics-tv.service -n 100

# Follow logs in real-time
sudo journalctl -u olympics-tv.service -f

# Check if service is enabled
sudo systemctl is-enabled olympics-tv.service

# Disable service from auto-starting
sudo systemctl disable olympics-tv.service
```

## Nginx Reverse Proxy Configuration

For production, use Nginx to reverse proxy to the backend:

```nginx
server {
    listen 80;
    server_name api.watcholympics2026.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name watcholympics2026.com www.watcholympics2026.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Service fails to start

Check the logs:
```bash
sudo journalctl -u olympics-tv.service -n 50
```

Common issues:
- `.env` file not found or missing variables
- Virtual environment not accessible
- Database connection failed
- Port already in use

### Check port usage

```bash
# See what's using port 8000
sudo lsof -i :8000

# See what's using port 3000
sudo lsof -i :3000
```

### Restart service after code update

```bash
# Update code from GitHub
cd /home/olympics/olympics-tv
git pull origin main

# Rebuild frontend if needed
cd winter-olympics-tv-scheduleV0
npm run build

# Restart services
sudo systemctl restart olympics-tv.service
sudo systemctl restart olympics-tv-frontend.service
```

## Service Monitoring

### With `systemd-exporter` (Prometheus)

```bash
sudo apt install prometheus-node-exporter

# Add custom metric to monitor Olympics TV
sudo nano /etc/prometheus/node-exporter.yaml
```

### Manual Health Check

```bash
#!/bin/bash
# health-check.sh

API_URL="http://localhost:8000/api/dates"
FRONTEND_URL="http://localhost:3000/"

echo "Checking backend..."
if curl -f $API_URL > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend is down"
    sudo systemctl restart olympics-tv.service
fi

echo "Checking frontend..."
if curl -f $FRONTEND_URL > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend is down"
    sudo systemctl restart olympics-tv-frontend.service
fi
```

## Automatic Updates

Create a cron job to pull latest code and restart services:

```bash
# Edit crontab
sudo crontab -e

# Add this line to update daily at 2 AM
0 2 * * * cd /home/olympics/olympics-tv && git pull origin main && cd winter-olympics-tv-scheduleV0 && npm run build && systemctl restart olympics-tv.service olympics-tv-frontend.service
```

## Production Checklist

- ✅ Application user created (`olympics`)
- ✅ Service files copied to `/etc/systemd/system/`
- ✅ `.env` configured with production values
- ✅ Services enabled and started
- ✅ Logs verified and accessible
- ✅ Health checks passing
- ✅ Nginx reverse proxy configured (optional)
- ✅ SSL/TLS certificates installed (for HTTPS)

## Additional Resources

- [Systemd Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/source/gunicorn.app.base.html)
- [Uvicorn Worker Class](https://www.uvicorn.org/deployment/#running-with-gunicorn)
- [Nginx Reverse Proxy](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
