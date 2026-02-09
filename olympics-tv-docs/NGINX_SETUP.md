# Olympics TV - Nginx Setup Guide

Complete guide to setting up Nginx as a reverse proxy for the Olympics TV application.

## Prerequisites

- Nginx installed: `sudo apt install nginx`
- Application running on ports 8000 (API) and 3000 (Frontend)
- Domain names configured (watcholympics2026.com, api.watcholympics2026.com)
- SSL certificates obtained (via Let's Encrypt)

## Step 1: Copy Nginx Configuration

```bash
# Copy the configuration file
sudo cp /home/olympics/olympics-tv/nginx-olympics-tv.conf /etc/nginx/sites-available/olympics-tv

# Create a symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/olympics-tv /etc/nginx/sites-enabled/olympics-tv

# Disable default site (optional)
sudo rm /etc/nginx/sites-enabled/default
```

## Step 2: Obtain SSL Certificates

Using Let's Encrypt with Certbot (recommended):

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificates for both domains
sudo certbot certonly --nginx \
  -d watcholympics2026.com \
  -d www.watcholympics2026.com \
  -d api.watcholympics2026.com

# Auto-renewal (certbot installs this automatically)
sudo systemctl enable certbot.timer
```

## Step 3: Update Configuration Paths

Edit the configuration file to use your certificate paths:

```bash
sudo nano /etc/nginx/sites-available/olympics-tv
```

Verify these paths match your certificate location:
- `/etc/letsencrypt/live/watcholympics2026.com/fullchain.pem`
- `/etc/letsencrypt/live/watcholympics2026.com/privkey.pem`
- `/etc/letsencrypt/live/api.watcholympics2026.com/fullchain.pem`
- `/etc/letsencrypt/live/api.watcholympics2026.com/privkey.pem`

## Step 4: Test Configuration

```bash
# Test Nginx syntax
sudo nginx -t

# You should see:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## Step 5: Start/Reload Nginx

```bash
# Start Nginx
sudo systemctl start nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx

# Reload configuration (after making changes)
sudo systemctl reload nginx

# Restart (hard restart)
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

## Step 6: Verify Installation

```bash
# Check if Nginx is listening
sudo ss -tlnp | grep nginx

# Test HTTP to HTTPS redirect
curl -I http://watcholympics2026.com
# Should show: 301 Moved Permanently to https://

# Test API endpoint
curl -I https://api.watcholympics2026.com/api/dates
# Should show: 200 OK or appropriate API response

# Test frontend
curl -I https://watcholympics2026.com/
# Should show: 200 OK
```

## Configuration Details

### Frontend Server
- **Domain:** watcholympics2026.com, www.watcholympics2026.com
- **Root:** `/home/olympics/olympics-tv/winter-olympics-tv-scheduleV0/.next/standalone/public`
- **Port:** 443 (HTTPS)
- **Redirect:** www → non-www

### API Server
- **Domain:** api.watcholympics2026.com
- **Backend:** http://127.0.0.1:8000 (FastAPI)
- **Port:** 443 (HTTPS)
- **Rate Limiting:** 10 req/s per IP

### Security Features

✅ **SSL/TLS:**
- TLS 1.2 and 1.3
- Strong ciphers
- Session caching

✅ **Headers:**
- Strict-Transport-Security (HSTS)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- CORS headers for API

✅ **Rate Limiting:**
- General: 30 req/s, burst 20
- API: 10 req/s, burst 50

✅ **Access Control:**
- Hidden files denied
- Backup files denied
- Sensitive files blocked

## Common Commands

```bash
# View Nginx status
sudo systemctl status nginx

# View error logs
sudo tail -f /var/log/nginx/olympics-tv-error.log

# View access logs
sudo tail -f /var/log/nginx/olympics-tv-access.log

# View API logs
sudo tail -f /var/log/nginx/olympics-api-access.log

# Reload after config change
sudo nginx -t && sudo systemctl reload nginx

# View active connections
sudo ss -tlnp | grep nginx

# Monitor real-time traffic
sudo tail -f /var/log/nginx/olympics-tv-access.log | grep -v ".js" | grep -v ".css"
```

## Performance Tuning

### Enable caching headers

Static files are cached for 1 year:
```nginx
location ~* ^/_next/static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Enable gzip compression

Already configured for:
- HTML, CSS, JavaScript
- JSON responses
- Minimum 1KB to compress

### Adjust buffer sizes

Current settings in config:
```nginx
proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;
```

For higher traffic, increase:
```nginx
proxy_buffer_size 16k;
proxy_buffers 32 16k;
proxy_busy_buffers_size 32k;
```

## SSL Certificate Renewal

Certbot auto-renewal runs daily:

```bash
# Check renewal status
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew

# Force renewal
sudo certbot renew --force-renewal
```

## Troubleshooting

### Certificate Not Found

```bash
# List installed certificates
sudo certbot certificates

# Recreate certificate
sudo certbot certonly --nginx -d watcholympics2026.com
```

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :80
sudo lsof -i :443

# Kill the process (if safe)
sudo kill -9 PID
```

### Nginx Won't Start

```bash
# Check for syntax errors
sudo nginx -t

# View systemd status
sudo systemctl status nginx

# View systemd logs
sudo journalctl -u nginx -n 50
```

### API Proxy Issues

Check if backend is running:
```bash
curl http://127.0.0.1:8000/api/dates
```

Check Nginx proxy logs:
```bash
sudo tail -f /var/log/nginx/olympics-api-error.log
```

## Monitoring

### Check system resources

```bash
# CPU and memory
top -b -n 1 | grep nginx

# Open connections
netstat -an | grep ESTABLISHED | wc -l

# Connections per IP
netstat -an | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn
```

### Monitor with tools

```bash
# Install monitoring tools
sudo apt install htop vnstat nethogs

# Real-time traffic
sudo nethogs

# Traffic statistics
vnstat -h

# Process monitoring
htop -u www-data
```

## Advanced: Load Balancing

For multiple backend instances:

```nginx
upstream fastapi_backend {
    least_conn;  # Load balancing algorithm
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;  # Second instance
    server 127.0.0.1:8002;  # Third instance
}

location / {
    proxy_pass http://fastapi_backend;
    # ... other proxy settings
}
```

## Production Checklist

- ✅ Nginx installed and enabled
- ✅ Configuration copied to `/etc/nginx/sites-available/`
- ✅ Site enabled (symlinked to `sites-enabled/`)
- ✅ SSL certificates installed
- ✅ Certificate paths updated in config
- ✅ Syntax validated with `nginx -t`
- ✅ Nginx started and enabled on boot
- ✅ Frontend accessible via HTTPS
- ✅ API accessible via HTTPS
- ✅ Logs accessible and monitored
- ✅ Rate limiting enabled
- ✅ Security headers in place

## Additional Resources

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Guide](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/docs/)
- [SSL/TLS Best Practices](https://ssl-config.mozilla.org/)
- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
