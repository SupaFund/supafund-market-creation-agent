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

### 3. Configure Environment Variables

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

### 4. Verify Setup (Optional but Recommended)

Run the included setup check script to ensure your environment is correctly configured:
```bash
# First, make the script executable
chmod +x setup_check.sh

# Then, run the check
./setup_check.sh
```
Address any issues reported by the script before proceeding.

### 5. Run the Service

Start the FastAPI server using `uvicorn`:
```bash
uvicorn src.main:app --reload
```
The `--reload` flag enables hot-reloading, which is convenient for development. The server will be available at `http://127.0.0.1:8000`.

## API Usage

### Create a Prediction Market

- **Endpoint**: `POST /create-market`
- **Description**: Triggers the creation of a new prediction market on Omen for a given Supafund application.
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
  Indicates that the market creation process was successfully initiated. The body will contain the output from the creation script.
  ```json
  {
    "status": "success",
    "message": "Market creation process initiated successfully.",
    "application_id": "9a8d4281-c8bb-478a-8277-c23222f698c9",
    "omen_creation_output": "..."
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