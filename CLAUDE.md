# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Supafund Market Creation Agent is a FastAPI service that automatically creates prediction markets on the Omen platform for Supafund applications. It consists of two main components:

1. **Main service** (`src/`) - FastAPI application with endpoints for market creation, betting, and management
2. **External tooling** (`gnosis_predict_market_tool/`) - Gnosis prediction market agent tooling package used via subprocess calls

## Key Features

- **Duplicate Prevention**: Automatically prevents creating multiple markets for the same application
- **Market Tracking**: Complete database tracking of all market operations in `prediction_markets` table  
- **Comprehensive Logging**: Local file logging to `logs/` directory with structured JSON data
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
# Run the FastAPI server with hot reload
uvicorn src.main:app --reload

# Run on specific port
uvicorn src.main:app --reload --port 8001
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

## Environment Configuration

Required environment variables in `.env`:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service role key
- `OMEN_PRIVATE_KEY` - Ethereum private key for market creation
- `GRAPH_API_KEY` - The Graph API key
- `OMEN_SCRIPT_PROJECT_PATH` - Path to gnosis_predict_market_tool directory
- `POETRY_PATH` - Path to poetry executable (optional, defaults to "poetry")

## Architecture

### Core Service Flow
1. **Market Creation**: `/create-market` endpoint → checks for duplicates → queries Supabase → executes `create_market_omen.py` script → records to database
2. **Betting**: `/bet` endpoint receives market parameters → executes `bet_omen.py` script
3. **Market Management**: Various endpoints for status updates, listing, and log retrieval

### Key Modules
- `src/main.py` - FastAPI application with all endpoints
- `src/config.py` - Environment configuration management
- `src/supabase_client.py` - Database operations for applications and market tracking
- `src/omen_creator.py` - Market creation via subprocess calls + output parsing
- `src/omen_betting.py` - Betting functionality via subprocess calls
- `src/market_logger.py` - Comprehensive local file logging system

### Database Schema
- `prediction_markets` table tracks all market operations
- Unique constraint on `application_id` prevents duplicates
- Foreign key relationship to `program_applications`
- Full audit trail with timestamps and metadata

### External Dependencies
The service depends on the `gnosis_predict_market_tool/` package for actual blockchain interactions. All market operations are executed via subprocess calls to Poetry-managed scripts in that directory.

### Data Flow
1. Duplicate check in `prediction_markets` table by `application_id`
2. Supabase queries join `program_applications`, `projects`, and `funding_programs` tables
3. Enhanced market titles include project and program descriptions in `<contextStart>...<contextEnd>` tags
4. Market creation/betting commands are executed in the external tooling environment
5. Results are parsed and recorded to database with comprehensive logging
6. All operations logged to local files for monitoring and analysis

### Logging System
- **Database**: All operations tracked in `prediction_markets` table
- **Local Files**: 
  - `logs/market_operations.log` - Human-readable operation logs
  - `logs/market_details.jsonl` - Structured JSON for analysis  
  - `logs/market_errors.log` - Detailed error logging