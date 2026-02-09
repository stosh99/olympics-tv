# Olympics TV Project - Documentation Index

All documentation for the Olympics TV project. Use this guide to understand what each file contains.

## Quick Start Files
- **MEMORY.md** - START HERE! High-level project overview and current status
- **CURRENT_STATUS.md** - Production deployment status and readiness checklist

## Architecture & Implementation
- **TECHNICAL.md** - Database schema, API endpoints, scraper details, frontend architecture
- **SESSIONS.md** - Detailed notes from all development sessions (Sessions 3-24)

## Deployment & Setup Guides
- **SYSTEMD_SETUP.md** - How to set up systemd services for production
- **NGINX_SETUP.md** - How to configure Nginx as reverse proxy for production

## Project Information
- **PROJECT_INVENTORY.md** - File structure and project contents
- **api_endpoints.md** - API endpoint documentation
- **scraping_patterns.md** - Web scraping patterns and strategies

## Database & Configuration
- **DATABASE_CREDENTIALS.md** - Database connection details (LOCAL DEV)
- **POSTGRESQL_CONNECTION.md** - PostgreSQL setup instructions
- **NBC_TABLES_SETUP.md** - NBC broadcast tables schema

## Progress & Status
- **DATA_LOADING_PROGRESS.md** - Data loading completion status
- **PHASE1_PROGRESS.md** - Phase 1 completion summary
- **SESSION_SUMMARY.md** - Most recent session summary

## Obsolete/Legacy (kept for reference)
- **olympics_tv_project_state.md** - Old project state snapshot
- **CRITICAL_BLOCKER.md** - Legacy blocker notes
- **SKILL.md** - Skill/tool documentation

---

## For Another AI

**Recommended Reading Order:**
1. MEMORY.md - Get the overview
2. TECHNICAL.md - Understand the architecture
3. SESSIONS.md - Learn what was built and why
4. CURRENT_STATUS.md - See what's ready for production

**Key Info:**
- Project: Winter Olympics 2026 TV Schedule Aggregator
- Backend: FastAPI + PostgreSQL + Gunicorn + Uvicorn
- Frontend: Next.js + React + TailwindCSS
- Database: PostgreSQL (olympics_tv)
- Target VPS: 66.220.29.98
- Git Repo: https://github.com/stosh99/olympics-tv
- Production Status: FULLY VERIFIED - READY FOR VPS DEPLOYMENT

**Python Entry Point:**
- `/api/main.py` - FastAPI application (called via `gunicorn api.main:app`)

**All Files Location:**
- Project: `/home/stosh99/PycharmProjects/olympics-tv/`
- Production: `/home/olympics/olympics-tv/` (on deployment VPS)
