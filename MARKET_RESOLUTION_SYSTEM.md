# Market Resolution System

This document describes the automated market resolution system that monitors prediction markets and resolves them based on real-world outcomes.

## Overview

The Market Resolution System automatically:
1. **Monitors** prediction markets from the database and The Graph API
2. **Identifies** completed markets that need resolution
3. **Researches** outcomes using Grok API with Twitter data
4. **Submits** resolutions to the blockchain
5. **Logs** all operations and sends daily reports to administrators

## System Architecture

### Core Components

#### 1. Market Monitor (`src/market_monitor.py`)
- **Purpose**: Detect completed but unresolved prediction markets
- **Data Sources**: 
  - Supabase database (`prediction_markets` table)
  - The Graph API (Omen subgraph)
- **Key Functions**:
  - `check_completed_markets()`: Identifies markets that are closed but not resolved
  - `get_markets_to_monitor()`: Retrieves active markets from database
  - `update_market_status_in_db()`: Updates market status after resolution

#### 2. Resolution Researcher (`src/resolution_researcher.py`)
- **Purpose**: Use Grok API to determine correct market outcomes
- **Data Sources**: Twitter/X posts via Grok API
- **Key Functions**:
  - `research_market_resolution()`: Main research function using Grok
  - `extract_twitter_handles_from_url()`: Extract handles from funding program URLs
  - `validate_resolution_result()`: Ensure research meets confidence thresholds

#### 3. Blockchain Resolver (`src/blockchain_resolver.py`)
- **Purpose**: Submit market resolutions to the blockchain
- **Integration**: Uses existing Omen tooling via subprocess calls
- **Key Functions**:
  - `resolve_market_on_blockchain()`: Submit resolution with outcome
  - `check_market_needs_final_resolution()`: Check if market needs finalization
  - `finalize_market_resolution()`: Complete the resolution process

#### 4. Resolution Logger (`src/resolution_logger.py`)
- **Purpose**: Comprehensive logging and monitoring
- **Features**:
  - Structured operation logging
  - Error tracking and alerting
  - Daily summary generation
  - Performance metrics

#### 5. Daily Scheduler (`src/daily_scheduler.py`)
- **Purpose**: Orchestrate the complete resolution workflow
- **Features**:
  - Automated daily execution
  - Email notifications to administrators
  - Error handling and recovery
  - Background processing

## Configuration

### Required Environment Variables

```bash
# Existing variables
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OMEN_PRIVATE_KEY=your_private_key
GRAPH_API_KEY=your_graph_api_key

# New for resolution system
XAI_API_KEY=your_grok_api_key

# Email notifications
ADMIN_EMAIL=admin@example.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### Optional Configuration

```bash
MIN_RESEARCH_CONFIDENCE=0.7      # Minimum confidence for auto-resolution
MAX_MARKETS_PER_RUN=10          # Max markets to process per cycle
RESOLUTION_DELAY_SECONDS=30     # Delay between market processing
```

## API Endpoints

### Market Resolution Endpoints

#### `POST /run-daily-resolution`
Manually trigger the daily resolution cycle.

**Response:**
```json
{
  "status": "started",
  "message": "Daily resolution cycle started in background",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### `GET /resolution-status`
Get current system status and health.

**Response:**
```json
{
  "status": "success",
  "recent_operations": {
    "total": 25,
    "by_status": {
      "completed": 20,
      "failed": 2,
      "skipped": 3
    }
  },
  "markets_by_status": {
    "created": 5,
    "active": 10,
    "resolution_submitted": 3,
    "resolved": 15
  },
  "system_health": "healthy"
}
```

#### `GET /resolution-logs`
Get detailed operation logs.

**Parameters:**
- `market_id` (optional): Filter by specific market
- `operation` (optional): Filter by operation type
- `limit` (optional): Maximum logs to return (default: 100)

#### `POST /research-market`
Manually research a specific market.

**Request:**
```json
{
  "market_id": "0x123...",
  "application_id": "uuid-here",
  "funding_program_name": "Program Name",
  "funding_program_twitter": "https://twitter.com/program"
}
```

## Workflow

### Daily Resolution Cycle

1. **Market Monitoring**
   - Query database for active markets
   - Check market status via The Graph API
   - Identify completed but unresolved markets

2. **Research Phase**
   - Extract funding program Twitter handles
   - Query Grok API with targeted search
   - Analyze Twitter posts for funding decisions
   - Generate resolution with confidence score

3. **Blockchain Resolution**
   - Submit answer to Reality.eth oracle
   - Wait for challenge period
   - Finalize market resolution

4. **Logging and Reporting**
   - Log all operations and results
   - Generate daily summary
   - Send email report to administrators

### Error Handling

- **API Failures**: Retry with exponential backoff
- **Low Confidence**: Skip resolution and log for manual review
- **Blockchain Errors**: Alert administrators immediately
- **System Errors**: Graceful degradation with comprehensive logging

## Grok Integration

### Search Strategy

The system uses Grok's X (Twitter) search with:
- **Funding program handles**: Direct from program metadata
- **Default crypto handles**: For programs without specific handles
- **Recent posts only**: Focus on funding announcement timeframes
- **Limited handles**: Maximum 10 handles per API constraint

### Resolution Logic

```python
# Example Grok prompt structure
f"""
Determine if project {application_id} successfully received funding 
from {funding_program_name}.

Search for:
1. Official funding announcements
2. Program recipient lists
3. Project success notifications

Return: Yes/No/Invalid with confidence 0.0-1.0
"""
```

## Database Schema Updates

The system uses the existing `prediction_markets` table with enhanced status tracking:

- `created`: Market created but not yet active
- `active`: Market is active and accepting bets
- `resolution_submitted`: Answer submitted, waiting for finalization
- `resolved`: Market fully resolved and payouts distributed

## Scheduling

### Cron Job Setup

```bash
# Run daily at 2 AM UTC
0 2 * * * cd /path/to/project && python scripts/setup_daily_schedule.py
```

### Docker/Container Setup

```bash
# Run as a scheduled container
docker run --env-file .env -d --restart=always \
  supafund-agent python scripts/setup_daily_schedule.py
```

## Monitoring and Alerts

### Email Reports

Daily reports include:
- **System Status**: Overall health and performance
- **Operation Summary**: Counts by operation type and status
- **Error Details**: Recent failures with context
- **Market Statistics**: Resolution progress and backlog

### Log Files

- `resolution_operations.log`: General operation logs
- `resolution_errors.log`: Error-specific logs
- `daily_summaries.jsonl`: Structured daily summaries
- `resolution_details.jsonl`: Detailed operation data

## Testing

### Manual Testing

Use the API endpoints to test individual components:

```bash
# Test market research
curl -X POST "http://localhost:8000/research-market" \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": "0x123...",
    "application_id": "uuid-here",
    "funding_program_name": "Test Program",
    "funding_program_twitter": "https://twitter.com/testprogram"
  }'

# Check system status
curl "http://localhost:8000/resolution-status"

# Trigger resolution cycle
curl -X POST "http://localhost:8000/run-daily-resolution"
```

### Development Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. Run the service:
   ```bash
   uvicorn src.main:app --reload
   ```

## Security Considerations

- **Private Keys**: Store securely, use environment variables only
- **API Keys**: Rotate regularly, monitor usage
- **Email Credentials**: Use app passwords, not main account passwords
- **Rate Limiting**: Respect API rate limits with delays
- **Error Logging**: Avoid logging sensitive information

## Troubleshooting

### Common Issues

1. **Grok API Errors**
   - Check XAI_API_KEY is valid
   - Verify API quota/usage limits
   - Review Twitter handle extraction logic

2. **The Graph API Failures**
   - Verify GRAPH_API_KEY is set
   - Check subgraph endpoint availability
   - Review query syntax for updates

3. **Email Delivery Issues**
   - Verify SMTP credentials
   - Check firewall/network restrictions
   - Review Gmail app password setup

4. **Blockchain Resolution Failures**
   - Ensure sufficient ETH/xDAI for gas
   - Verify private key permissions
   - Check Omen contract status

### Debug Mode

Enable debug logging by setting:
```bash
export LOG_LEVEL=DEBUG
```

This provides detailed operation tracing and API request/response logging.

## Future Enhancements

- **Multi-chain Support**: Extend to other prediction market platforms
- **Advanced Research**: Use multiple AI models for cross-validation
- **Real-time Monitoring**: WebSocket updates for live status
- **Machine Learning**: Train models on historical resolution accuracy
- **Governance Integration**: Support for DAO-based resolution validation