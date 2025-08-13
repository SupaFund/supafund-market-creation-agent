# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Deployment Platform

**Current Target**: Railway - optimized for serverless deployment with subprocess architecture, dynamic port configuration, and automated environment detection.

## Project Overview

The Supafund Market Creation Agent is a FastAPI service that automatically creates prediction markets on the Omen platform for Supafund applications. It consists of two main components:

1. **Main service** (`src/`) - FastAPI application with endpoints for market creation, betting, and management
2. **External tooling** (`gnosis_predict_market_tool/`) - Gnosis prediction market agent tooling package used via subprocess calls

## Key Features

- **Duplicate Prevention**: Automatically prevents creating multiple markets for the same application
- **Market Tracking**: Complete database tracking of all market operations in `prediction_markets` table  
- **Comprehensive Logging**: Railway-compatible structured logging with stdout/stderr output and emojis for better visibility
- **Market Management**: REST API endpoints for status updates and market monitoring
- **Enhanced Titles**: Market titles include project and program descriptions in `<contextStart>...<contextEnd>` tags

## Development Commands

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Apply database migration (REQUIRED - run in Supabase SQL Editor)
# Execute: database_migrations/001_create_prediction_markets_table.sql

# Environment setup check
chmod +x setup_check.sh && ./setup_check.sh
```

### Running the Service
```bash
# Development mode with hot reload
uvicorn src.main:app --reload

# Railway-optimized startup with validation
python start_railway.py

# Manual Railway startup
uvicorn src.main:app --host 0.0.0.0 --port $PORT --workers 1
```

### External Tooling Commands (in gnosis_predict_market_tool/)
```bash
# Install dependencies for market creation scripts
poetry install

# Run linting and type checking
black .
mypy .
isort .
autoflake --remove-all-unused-imports --recursive --in-place .

# Run tests
pytest                           # Unit tests
pytest tests_integration/       # Integration tests with external APIs
pytest tests_integration_with_local_chain/  # Tests requiring local blockchain
```

### Main Service Commands (in project root)
```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test categories
pytest -m unit                  # Unit tests only
pytest -m integration          # Integration tests only
pytest -m e2e                   # End-to-end tests only

# Railway deployment commands  
git add . && git commit -m "Railway deployment" && git push origin railway-deploy

# Dependency validation
python start_railway.py  # Includes dependency checks
```

## Environment Configuration

Required environment variables in `.env`:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service role key
- `OMEN_PRIVATE_KEY` - Ethereum private key for market creation
- `GRAPH_API_KEY` - The Graph API key
- `OMEN_SCRIPT_PROJECT_PATH` - Path to gnosis_predict_market_tool directory
- `POETRY_PATH` - Path to poetry executable (optional, defaults to "poetry")
- `XAI_API_KEY` - Grok API key for market resolution research (optional)

### Railway-Specific Variables
- `PORT` - Dynamically provided by Railway
- `RAILWAY_ENVIRONMENT` - Set to "production"
- `RAILWAY_SERVICE_NAME` - Railway service identifier
- `RAILWAY_PROJECT_NAME` - Railway project identifier
- `PYTHONPATH` - Set to "."
- `PYTHONUNBUFFERED` - Set to "1"

## Architecture

### Core Service Flow
**Traditional Synchronous Flow**:
1. **Market Creation**: `/create-market` endpoint → checks for duplicates → queries Supabase → executes subprocess calls → records to database  
2. **Betting**: `/bet` endpoint receives market parameters → executes subprocess calls to betting modules  
3. **Market Management**: Various endpoints for status updates, listing, and log retrieval

**New Async Flow** (Primary):
1. **Task Submission**: `/async/*` endpoints → validate request → submit to task queue → return task_id immediately
2. **Background Processing**: Worker threads process tasks asynchronously with retry logic and status updates
3. **Status Tracking**: `/task-status/{task_id}` provides real-time progress and results

### Key Modules
- `src/main.py` - FastAPI application with all endpoints including async blockchain operations
- `src/blockchain_task_queue.py` - **Core async task system** with worker pools, retry logic, and status tracking
- `src/async_blockchain_endpoints.py` - Async endpoint handlers that return task IDs immediately
- `src/config.py` - Environment configuration management  
- `src/supabase_client.py` - Database operations for applications and market tracking
- `src/omen_subprocess_creator.py` - Market creation via subprocess calls with Railway environment detection
- `src/omen_subprocess_betting.py` - Betting functionality via subprocess calls  
- `src/omen_subprocess_resolution.py` - Resolution functionality via subprocess calls
- `src/railway_logger.py` - Railway-compatible structured logging system with emojis
- `src/blockchain/` - Direct blockchain operations modules (legacy)
- `src/market_monitor.py` - Monitor markets for resolution opportunities
- `src/resolution_researcher.py` - AI-powered market outcome research using Grok API
- `src/daily_scheduler.py` - Automated daily resolution scheduling system

### Database Schema
- `prediction_markets` table tracks all market operations
- Unique constraint on `application_id` prevents duplicates
- Foreign key relationship to `program_applications`
- Full audit trail with timestamps and metadata

### External Dependencies
The service depends on the `gnosis_predict_market_tool/` package for actual blockchain interactions. **Critical change**: Railway environment uses direct Python execution (not Poetry) due to dependency management. All required blockchain tool dependencies are included in main `requirements.txt` for Railway compatibility.

### Data Flow
1. Duplicate check in `prediction_markets` table by `application_id`
2. Supabase queries join `program_applications`, `projects`, and `funding_programs` tables
3. Enhanced market titles include project and program descriptions in `<contextStart>...<contextEnd>` tags
4. Market creation/betting commands are executed in the external tooling environment
5. Results are parsed and recorded to database with comprehensive logging
6. All operations logged to local files for monitoring and analysis

### Logging System
- **Database**: All operations tracked in `prediction_markets` table
- **Railway Logs**: 
  - Structured JSON logging to stdout/stderr with emoji indicators
  - Real-time logs visible in Railway dashboard
  - In-memory log storage for API endpoints
  - Railway-compatible log formatting and timestamps
  - Subprocess operation logging for debugging

### Market Resolution System
The service includes an automated market resolution system that:
1. **Monitors** active markets for closure and resolution opportunities
2. **Researches** outcomes using Grok API with real-time Twitter/X data
3. **Submits** resolution answers to blockchain (Realitio oracle system)
4. **Resolves** markets after dispute periods end
5. **Schedules** daily automated resolution runs at 9 AM UTC

#### Resolution Flow
1. `market_monitor.py` identifies completed but unresolved markets
2. `resolution_researcher.py` uses Grok API to determine outcomes from social media
3. `omen_subprocess_resolution.py` submits answers and handles final resolution via subprocess calls
4. `daily_scheduler.py` runs automated daily resolution checks

#### Architecture Consistency
**Subprocess Execution Strategy** (Environment-Dependent):
- **Railway/Docker**: Direct Python execution with PYTHONPATH configuration
- **Local Development**: Poetry execution for dependency isolation
- **Market Creation**: `omen_subprocess_creator.py` → subprocess calls to `gnosis_predict_market_tool`
- **Betting**: `omen_subprocess_betting.py` → subprocess calls to betting scripts  
- **Resolution**: `omen_subprocess_resolution.py` → subprocess calls to resolution scripts
- **Environment Detection**: Automatic Railway vs Docker vs local development detection

**Async Task Processing**:
- **Task Queue**: In-memory task storage with status tracking (pending → processing → completed/failed)
- **Worker Pool**: 3 concurrent workers processing blockchain operations
- **Retry Logic**: Exponential backoff with 3 retry attempts for failed tasks
- **Status Management**: Real-time task status updates accessible via REST endpoints

#### Key Commands
```bash
# Local development
uvicorn src.main:app --reload

# Railway deployment startup
python start_railway.py

# Manual resolution run
python -m src.daily_scheduler

# Health check
curl https://your-app.up.railway.app/health
```

## Railway Deployment

### Configuration Files
- `railway.toml` - Railway deployment configuration with health checks
- `nixpacks.toml` - Build optimization with Poetry and Python 3.11
- `Procfile` - Process definition for Railway
- `start_railway.py` - Railway-optimized startup script with dependency validation

### Deployment Architecture  
- **Environment Detection**: Automatic Railway environment detection (`Config.IS_RAILWAY`)
- **Dependency Management**: Railway uses main `requirements.txt` with all blockchain dependencies
- **Subprocess Strategy**: Railway/Docker use direct Python, Local development uses Poetry
- **Dynamic Configuration**: Railway-provided PORT and environment variables
- **Async Task Workers**: Automatic startup via `@app.on_event("startup")` 
- **Health Monitoring**: Comprehensive health checks with subprocess validation
- **Logging**: Emoji-enhanced structured logging for better Railway dashboard visibility

### Deployment Process
1. **Railway monitors `railway-deploy` branch**: `git push origin railway-deploy` 
2. Railway automatically detects changes and triggers Nixpacks build
3. Dependencies installed via requirements.txt (including blockchain tool dependencies)
4. Environment variables configured in Railway dashboard
5. Async task workers start automatically on application startup via `@app.on_event("startup")`
6. Health check endpoint: `/health` with full system validation
7. API documentation: `/docs` (includes new async endpoints)

### Async Blockchain Operations 🚀
**NEW**: Non-blocking blockchain endpoints to prevent frontend freezing:
- `POST /async/create-market` - Async market creation (2-5 min background)
- `POST /async/bet` - Async betting (1-3 min background)  
- `POST /async/submit-answer` - Async answer submission (1-2 min background)
- `POST /async/research-and-submit` - AI-powered research and answer submission
- `POST /async/finalize-resolution` - Final market resolution
- `GET /task-status/{task_id}` - Real-time task progress tracking
- `GET /tasks/recent` - Recent task history
- `GET /tasks/queue-status` - Queue metrics and system health

**Key Benefits:**
- ✅ Immediate response (< 1 second) with task ID
- ✅ Background processing with automatic retry (up to 3 attempts)
- ✅ Progress tracking and status updates
- ✅ Concurrent task processing (max 3 simultaneous)
- ✅ Comprehensive error handling and recovery

**Usage Pattern:**
```javascript
// 1. Submit task (immediate response)
const task = await fetch('/async/create-market', {...});
const {task_id} = await task.json();

// 2. Poll status until completion  
const status = await fetch(`/task-status/${task_id}`);
// status: pending → processing → completed/failed
```

**Railway Live URL**: `https://supafund-market-creation-agent-production.up.railway.app`

See `RAILWAY_API_GUIDE.md` for complete usage documentation, examples, and troubleshooting.