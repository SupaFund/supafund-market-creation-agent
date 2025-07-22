# Supafund Market Creation Agent

This service provides a backend agent that listens for API calls to automatically create prediction markets on the Omen platform for new applications submitted to Supafund.

## Overview

The agent is built with FastAPI and is designed to be called by the main Supafund backend. When a new application is ready, the Supafund backend sends a request to this agent with an `application_id`. The agent then fetches the application's details from a Supabase database and uses this information to construct and execute a command to create a new prediction market on Omen via a separate script repository.

The core logic is as follows:
1.  Receive a `POST` request to `/create-market` with an `application_id`.
2.  Query the Supabase database to get the project name, program name, and other details associated with the application.
3.  Automatically run `poetry install` in the Omen script project to ensure all dependencies are installed.
4.  Construct and execute the `create_market_omen.py` script with the correct parameters (question, closing time, private key, etc.).
5.  Return a success or error response.

## Prerequisites

Before running this service, ensure you have the following installed:
- Python 3.10+
- `pip` for installing packages

This service also depends on an external script repository for creating Omen markets. This repository must be managed with `poetry`.

## Setup Instructions

Follow these steps to get the agent running locally.

### 1. Clone the Repository

If you haven't already, clone this repository to your local machine.

### 2. Install Dependencies

Install the required Python packages using the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

### 3. Set Up Database

**IMPORTANT**: Before running the service, you must create the required database table to enable market tracking and duplicate prevention.

#### Apply Database Migration

1. Go to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Execute the SQL migration script located at `database_migrations/001_create_prediction_markets_table.sql`

Or copy and paste this SQL:

```sql
CREATE TABLE public.prediction_markets (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  application_id uuid NOT NULL,
  market_id text NOT NULL,
  market_title text NOT NULL,
  market_url text,
  market_question text,
  closing_time timestamp with time zone,
  initial_funds_usd numeric,
  omen_creation_output text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'created' CHECK (status = ANY (ARRAY['created'::text, 'active'::text, 'closed'::text, 'resolved'::text, 'failed'::text])),
  metadata jsonb DEFAULT '{}'::jsonb,
  
  CONSTRAINT prediction_markets_pkey PRIMARY KEY (id),
  CONSTRAINT prediction_markets_application_id_unique UNIQUE (application_id),
  CONSTRAINT prediction_markets_market_id_unique UNIQUE (market_id),
  CONSTRAINT prediction_markets_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.program_applications(id)
);

CREATE INDEX idx_prediction_markets_application_id ON public.prediction_markets (application_id);
CREATE INDEX idx_prediction_markets_market_id ON public.prediction_markets (market_id);
CREATE INDEX idx_prediction_markets_status ON public.prediction_markets (status);
CREATE INDEX idx_prediction_markets_created_at ON public.prediction_markets (created_at);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_prediction_markets_updated_at 
    BEFORE UPDATE ON public.prediction_markets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
```

### 4. Configure Environment Variables

This service requires several environment variables to function correctly. Create a file named `.env` in the root directory of this project by copying the required structure:

```
# .env

# --- Supabase Configuration ---
# Your Supabase project URL and service role key
SUPABASE_URL="YOUR_SUPABASE_URL"
SUPABASE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY"

# --- Omen Configuration ---
# The private key of the Ethereum account that will create the markets
OMEN_PRIVATE_KEY="YOUR_ETHEREUM_PRIVATE_KEY_FOR_OMEN"

# --- The Graph API Key ---
# Required for blockchain data queries
GRAPH_API_KEY="YOUR_GRAPH_API_KEY"

# --- Path to the Omen script project ---
# This should be a relative or absolute path to the directory containing
# the 'create_market_omen.py' script and its 'pyproject.toml' file.
OMEN_SCRIPT_PROJECT_PATH="path/to/your/gnosis_predict_market_tool"

# --- Path to the Poetry executable ---
# The absolute path to the poetry executable. Find this by running 'which poetry'
# in your terminal. This is crucial for ensuring the service can find poetry.
POETRY_PATH="/absolute/path/to/your/poetry/executable"
```

Fill in the values for each variable.

### 5. Verify Setup (Optional but Recommended)

Run the included setup check script to ensure your environment is correctly configured:
```bash
# First, make the script executable
chmod +x setup_check.sh

# Then, run the check
./setup_check.sh
```
Address any issues reported by the script before proceeding.

### 6. Run the Service

Start the FastAPI server using `uvicorn`:
```bash
uvicorn src.main:app --reload
```
The `--reload` flag enables hot-reloading, which is convenient for development. The server will be available at `http://127.0.0.1:8000`.

## Key Features

### 🔒 Duplicate Prevention
The system automatically prevents creating multiple markets for the same application:
- First call creates the market and stores it in the database
- Subsequent calls return the existing market information
- No wasted resources or duplicate markets

### 📊 Market Tracking
All market operations are tracked in the `prediction_markets` table:
- Market ID, URL, and metadata
- Creation status and timestamps
- Full audit trail of all operations

### 📝 Comprehensive Logging
Detailed logging to local files in the `logs/` directory:
- `market_operations.log` - Human-readable operation logs
- `market_details.jsonl` - Structured JSON data for analysis
- `market_errors.log` - Detailed error logs

### 🎯 Enhanced Market Titles
Market titles now include contextual information:
- Project description from the projects table
- Program description from the funding_programs long_description
- Format: `Will project "Name" be approved for "Program" program? [Supafund App: ID] <contextStart>Project: description; Program: description<contextEnd>`

## API Usage

### Create a Prediction Market

- **Endpoint**: `POST /create-market`
- **Description**: Creates a new prediction market on Omen for a given Supafund application. **Automatically prevents duplicates** - if a market already exists, returns the existing market information.
- **Request Body**:
  ```json
  {
    "application_id": "YOUR_SUPAFUND_APPLICATION_UUID"
  }
  ```
- **Example `curl` Request**:
  ```bash
  curl -X POST "http://127.0.0.1:8000/create-market" \
  -H "Content-Type: application/json" \
  -d '{"application_id": "9a8d4281-c8bb-478a-8277-c23222f698c9"}'
  ```

#### Responses

- **Success (200 OK)**:
  Indicates that the market creation process was successfully completed. The body will contain market information and creation output.
  ```json
  {
    "status": "success",
    "message": "Market creation process completed successfully.",
    "application_id": "9a8d4281-c8bb-478a-8277-c23222f698c9",
    "market_info": {
      "market_id": "0x1234...",
      "market_url": "https://omen.eth.limo/...",
      "market_title": "Will project...",
      "closing_time": "2024-01-01T00:00:00"
    },
    "omen_creation_output": "..."
  }
  ```
- **Market Already Exists (200 OK)**:
  A market already exists for this application. Returns existing market information instead of creating a new one.
  ```json
  {
    "status": "already_exists",
    "message": "Market already exists for this application",
    "application_id": "9a8d4281-c8bb-478a-8277-c23222f698c9",
    "existing_market": {
      "market_id": "0x1234...",
      "market_url": "https://omen.eth.limo/...",
      "created_at": "2024-01-01T00:00:00",
      "status": "created"
    }
  }
  ```
- **Not Found (404 Not Found)**:
  The provided `application_id` could not be found in the Supabase database.
  ```json
  {
    "detail": "Application with id ... not found."
  }
  ```
- **Internal Server Error (500 Internal Server Error)**:
  An error occurred during the market creation process (e.g., script execution failed). The response detail will contain the error message from the logs.
  ```json
  {
    "detail": "Failed to create market: ..."
  }
  ```

### Place a Bet

- **Endpoint**: `POST /bet`
- **Description**: Places a bet on a specified prediction market.
- **Request Body**:
  ```json
  {
    "market_id": "0x86376012a5185f484ec33429cadfa00a8052d9d4",
    "amount_usd": 0.01,
    "outcome": "Yes",
    "from_private_key": "YOUR_PRIVATE_KEY",
    "safe_address": "OPTIONAL_SAFE_ADDRESS",
    "auto_deposit": true
  }
  ```
- **Example `curl` Request**:

  ```bash
  curl -X POST "http://127.0.0.1:8000/bet" \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": "0x86376012a5185f484ec33429cadfa00a8052d9d4",
    "amount_usd": 0.01,
    "outcome": "Yes",
    "from_private_key": "your-private-key",
    "auto_deposit": true
  }'
  ```

#### Bet Responses

- **Success (200 OK)**:
  Indicates that the bet was successfully placed.

  ```json
  {
    "status": "success",
    "message": "Bet placed successfully.",
    "market_id": "0x86376012a5185f484ec33429cadfa00a8052d9d4",
    "amount_usd": 0.01,
    "outcome": "Yes",
    "transaction_output": "Bet placed successfully. Transaction hash: 0x..."
  }
  ```

- **Internal Server Error (500 Internal Server Error)**:
  An error occurred during the betting process.

  ```json
  {
    "detail": "Failed to place bet: ..."
  }
  ```

### Market Management

#### Get Market Status
- **Endpoint**: `GET /market-status/{application_id}`
- **Description**: Get the current status and details of a market by application ID.
- **Response**:
  ```json
  {
    "status": "success",
    "application_id": "9a8d4281-c8bb-478a-8277-c23222f698c9",
    "market": {
      "id": "uuid",
      "application_id": "9a8d4281-c8bb-478a-8277-c23222f698c9",
      "market_id": "0x1234...",
      "market_title": "Will project...",
      "market_url": "https://omen.eth.limo/...",
      "status": "created",
      "created_at": "2024-01-01T00:00:00",
      "metadata": {}
    }
  }
  ```

#### Update Market Status
- **Endpoint**: `PUT /market-status/{application_id}`
- **Description**: Update the status of a market (e.g., from 'created' to 'active').
- **Request Body**:
  ```json
  {
    "status": "active",
    "metadata": {
      "updated_by": "admin",
      "reason": "Market went live"
    }
  }
  ```

#### List All Markets
- **Endpoint**: `GET /markets`
- **Description**: List all markets with optional status filtering.
- **Query Parameters**:
  - `status` (optional): Filter by market status
  - `limit` (optional): Limit number of results (default: 100)

#### Get Market Logs
- **Endpoint**: `GET /market-logs/{application_id}`
- **Description**: Get detailed operation logs for a specific market.

#### Get Recent Logs
- **Endpoint**: `GET /recent-logs`
- **Description**: Get recent market operation logs.
- **Query Parameters**:
  - `hours` (optional): Number of hours to look back (default: 24)

### Health Check

- **Endpoint**: `GET /`
- **Description**: A simple endpoint to verify that the service is running.
- **Response**:

  ```json
  {
    "status": "ok",
    "message": "Supafund Market Creation Agent is running."
  }
  ```

## Logging and Monitoring

### Local File Logs

The system creates detailed logs in the `logs/` directory:

- **`market_operations.log`**: Human-readable logs of all market operations
- **`market_details.jsonl`**: Structured JSON logs for programmatic analysis
- **`market_errors.log`**: Detailed error logs with stack traces

### Database Tracking

All market operations are tracked in the `prediction_markets` table:
- Market creation attempts (successful and failed)
- Market status updates
- Full metadata and audit trail
- Automatic duplicate prevention

## Troubleshooting

### Common Issues

1. **"Table prediction_markets doesn't exist"**
   - Solution: Apply the database migration from `database_migrations/001_create_prediction_markets_table.sql`

2. **"Market already exists" but you want to recreate**
   - Check existing market: `GET /market-status/{application_id}`
   - Update status if needed: `PUT /market-status/{application_id}`

3. **Market creation fails but no error logged**
   - Check `logs/market_errors.log` for detailed error information
   - Verify environment variables are correctly set

### Log Analysis

Query structured logs programmatically:
```bash
# Find all failed market creations
grep '"event": "creation_failed"' logs/market_details.jsonl

# Count operations by type
grep -o '"event": "[^"]*"' logs/market_details.jsonl | sort | uniq -c
```