#!/bin/bash
# Production startup script for Olympics TV application

set -e

echo "🚀 Starting Olympics TV Application (Production)"
echo "=================================================="

# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(cat .env | xargs)

echo "✅ Environment loaded"
echo "   Environment: $ENVIRONMENT"
echo "   Debug: $DEBUG"
echo "   Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""

# Start backend API with Gunicorn + Uvicorn
echo "📡 Starting Backend API..."
echo "   Command: gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker"
echo "   Workers: 4"
echo "   Host: 0.0.0.0:8000"
echo ""

gunicorn api.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
