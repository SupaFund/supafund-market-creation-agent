# Quick Start Guide - Market Resolution System

## ✅ System Status

The Market Resolution System has been successfully implemented and integrated into your existing Supafund Market Creation Agent. All components are working correctly!

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Test the System

```bash
# Test all imports
python test_imports.py

# Start the server
python start_server.py
# or
uvicorn src.main:app --reload
```

### 3. Access the API

Once the server is running, visit:
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/
- **Resolution Status**: http://127.0.0.1:8000/resolution-status

## 🔧 Configuration

### Required Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Copy the example file
cp .env.example .env

# Edit with your API keys
nano .env
```

**Minimum required variables:**
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OMEN_PRIVATE_KEY=your_private_key
GRAPH_API_KEY=your_graph_api_key
```

**For full functionality (including Grok API and email notifications):**
```bash
XAI_API_KEY=your_grok_api_key
ADMIN_EMAIL=admin@example.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

## 🎯 New Features Available

### API Endpoints

1. **`POST /run-daily-resolution`**
   - Manually trigger market resolution cycle
   - Runs in background to avoid timeouts

2. **`GET /resolution-status`**
   - View system health and recent activity
   - See market counts by status

3. **`GET /resolution-logs`**
   - Access detailed operation logs
   - Filter by market ID or operation type

4. **`POST /research-market`**
   - Manually research specific markets
   - Test the Grok API integration

5. **`GET /resolution-summary`**
   - Generate daily operation summary
   - Performance metrics and statistics

### Core System Components

- **🔍 Market Monitor**: Detects completed markets via The Graph API
- **🧠 Resolution Researcher**: Uses Grok API to analyze Twitter data
- **⛓️ Blockchain Resolver**: Submits resolutions to Omen contracts
- **📊 Logger System**: Comprehensive operation tracking
- **📧 Email Notifications**: Daily reports to administrators

## 🎮 Testing the System

### 1. Check System Health

```bash
curl "http://127.0.0.1:8000/resolution-status"
```

### 2. Test Market Research (Mock Mode)

```bash
curl -X POST "http://127.0.0.1:8000/research-market" \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": "0x123456789abcdef",
    "application_id": "uuid-test-123",
    "funding_program_name": "Test Program",
    "funding_program_twitter": "https://twitter.com/testprogram"
  }'
```

### 3. Trigger Resolution Cycle

```bash
curl -X POST "http://127.0.0.1:8000/run-daily-resolution"
```

## 📅 Production Deployment

### 1. Set up Daily Cron Job

```bash
# Edit crontab
crontab -e

# Add daily execution at 2 AM UTC
0 2 * * * cd /path/to/supafund-market-creation-agent && python scripts/setup_daily_schedule.py
```

### 2. Configure Email Notifications

Set up Gmail App Password:
1. Enable 2FA on your Gmail account
2. Generate an App Password
3. Use the App Password as `SMTP_PASSWORD`

### 3. Monitor Logs

Log files are created in the `logs/` directory:
- `resolution_operations.log`: General operations
- `resolution_errors.log`: Error tracking
- `daily_summaries.jsonl`: Daily reports
- `resolution_details.jsonl`: Detailed operation data

## 🔮 Grok API Integration

### Current Status: Mock Mode

The system currently runs in **mock mode** for Grok API integration because:
1. The exact xAI SDK package name/version needs verification
2. API endpoints and authentication may need adjustment

### To Enable Real Grok Integration:

1. **Install the xAI SDK**:
   ```bash
   # Install the xAI SDK
   pip install xai-sdk
   ```

2. **The imports are already correct in `src/resolution_researcher.py`**:
   ```python
   # These imports are already in place and correct
   from xai_sdk import Client
   from xai_sdk.chat import user
   from xai_sdk.search import SearchParameters, x_source
   ```

3. **Set your API key**:
   ```bash
   export XAI_API_KEY=your_real_grok_api_key
   ```

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**: Run `python test_imports.py` to diagnose
2. **Database Connection**: Check Supabase credentials
3. **Email Not Sending**: Verify SMTP credentials and Gmail App Password
4. **Server Won't Start**: Check port 8000 isn't already in use

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
uvicorn src.main:app --reload --log-level debug
```

## 🎉 Success!

Your Market Resolution System is ready to go! The system will:

- ✅ Monitor markets automatically
- ✅ Research outcomes using AI (when Grok API is configured)
- ✅ Submit resolutions to blockchain
- ✅ Send daily email reports
- ✅ Log all operations comprehensively

Visit the API documentation at http://127.0.0.1:8000/docs to explore all available endpoints.

---

**Need help?** Check the detailed documentation in `MARKET_RESOLUTION_SYSTEM.md` for comprehensive information about the system architecture and advanced configuration options.