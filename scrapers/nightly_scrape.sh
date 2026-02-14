#!/bin/bash
# Crontab entry (add with: crontab -e)
# Run nightly at 3:00 AM Eastern (scrapers re-fetch all dates, upsert changes)
# 0 3 * * * /home/stosh/olympics-tv/scrapers/nightly_scrape.sh

# Olympics TV Schedule - Nightly Scraper Wrapper
# This script runs both scrapers (Olympics.com and NBC) nightly to update
# schedule data with any changes: time shifts, competitor updates, network moves, etc.

set -euo pipefail

# Production paths
PROJECT_ROOT="/home/stosh/olympics-tv"
VENV_ACTIVATE="$PROJECT_ROOT/.venv/bin/activate"
LOG_DIR="/var/log/olympics-tv"
LOG_FILE="$LOG_DIR/nightly-scrape-$(date +%Y%m%d).log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Logging helper functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# Track exit status
olympics_scraper_failed=0
nbc_scraper_failed=0

log "=========================================="
log "Starting nightly scrape"
log "=========================================="

# Activate Python virtual environment
log "Activating Python virtual environment"
if [ ! -f "$VENV_ACTIVATE" ]; then
    log_error "Virtual environment not found at $VENV_ACTIVATE"
    exit 1
fi

source "$VENV_ACTIVATE"
log "Virtual environment activated"

# Change to project root
cd "$PROJECT_ROOT" || exit 1
log "Changed directory to $PROJECT_ROOT"

# Run Olympics.com scraper
log ""
log "Running Olympics.com scraper (Feb 3 - Feb 22)..."
if python3 scrapers/olympics_scraper.py 2>&1 | tee -a "$LOG_FILE"; then
    log "Olympics.com scraper completed successfully"
else
    olympics_scraper_failed=$?
    log_error "Olympics.com scraper failed with exit code $olympics_scraper_failed"
fi

# Run NBC scraper
log ""
log "Running NBC scraper (Feb 4 - Feb 23)..."
if python3 scrapers/nbc_scraper.py 2>&1 | tee -a "$LOG_FILE"; then
    log "NBC scraper completed successfully"
else
    nbc_scraper_failed=$?
    log_error "NBC scraper failed with exit code $nbc_scraper_failed"
fi

# Summary
log ""
log "=========================================="
log "Nightly scrape completed"
log "=========================================="
log "Olympics.com scraper: $([ $olympics_scraper_failed -eq 0 ] && echo 'SUCCESS' || echo 'FAILED')"
log "NBC scraper: $([ $nbc_scraper_failed -eq 0 ] && echo 'SUCCESS' || echo 'FAILED')"
log "Log file: $LOG_FILE"

# Exit with error if any scraper failed
if [ $olympics_scraper_failed -ne 0 ] || [ $nbc_scraper_failed -ne 0 ]; then
    log_error "One or more scrapers failed"
    exit 1
fi

log "All scrapers completed successfully"
exit 0
