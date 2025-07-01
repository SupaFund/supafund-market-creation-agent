import logging
import subprocess
from datetime import datetime, timedelta

from src.config import OMEN_CREATOR_PRIVATE_KEY


def create_omen_market(application_details: dict):
    """
    Creates a prediction market on Omen using a script.
    This is a placeholder implementation.
    """
    project_name = application_details.get("projects", {}).get("name", "An unnamed project")

    # Generate a dynamic question and closing time
    question = f"Will the project '{project_name}' be approved for funding?"
    # Assuming the market closes 30 days from now. This could be tied to program end date.
    closing_time = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    category = "finance"  # Or could be derived from application data
    initial_funds_usd = "0.01"
    cl_token = "wxdai"

    command = [
        "poetry", "run", "python", "scripts/create_market_omen.py",
        "--question", question,
        "--closing-time", closing_time,
        "--category", category,
        "--initial-funds-usd", initial_funds_usd,
        "--cl-token", cl_token,
        "--from-private-key", OMEN_CREATOR_PRIVATE_KEY
    ]

    logging.info(f"Executing Omen market creation command: {' '.join(command[:-2])} --from-private-key ****")

    try:
        # In a real scenario, the script `create_market_omen.py` would exist and be executable.
        # Here we simulate its execution.
        # You would replace this with the actual subprocess call.
        #
        # result = subprocess.run(command, capture_output=True, text=True, check=True)
        # logging.info(f"Omen market creation script output: {result.stdout}")
        # market_url = result.stdout.strip() # Assuming script outputs the URL

        # Simulating a successful run for now
        market_url = f"https://omen.eth.link/#/0x...market_address_for_{project_name.replace(' ', '_')}"
        logging.info("Simulated Omen market creation successfully.")
        return {"market_url": market_url}

    except FileNotFoundError:
        logging.error("The `poetry` or `scripts/create_market_omen.py` script was not found.")
        raise
    except subprocess.CalledProcessError as e:
        logging.error(f"Omen market creation failed: {e.stderr}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred during Omen market creation: {e}")
        raise
