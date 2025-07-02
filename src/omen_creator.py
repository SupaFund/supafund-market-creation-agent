import subprocess
import logging
import shlex
import os
import sys
from datetime import datetime, timedelta, timezone
from .config import Config

logging.basicConfig(level=logging.INFO)

def create_omen_market(application_details: dict) -> tuple[bool, str]:
    """
    Creates a prediction market on Omen by executing an external script.

    Args:
        application_details: A dictionary containing details about the application,
                             including project_name, program_name, and deadline.

    Returns:
        A tuple containing a boolean success status and the output message.
    """
    poetry_executable_path = Config.POETRY_PATH
    project_path = Config.OMEN_SCRIPT_PROJECT_PATH

    # --- Step 1: Ensure dependencies are installed in the script's project ---
    try:
        logging.info(f"Ensuring dependencies are installed in '{project_path}'...")
        install_command = [
            "/bin/sh",
            poetry_executable_path,
            "install",
        ]
        install_result = subprocess.run(
            install_command,
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        logging.info(f"Dependency installation check in '{project_path}' completed.")
        # Optionally log stdout for debugging: logging.debug(f"Poetry install stdout: {install_result.stdout}")
    except subprocess.CalledProcessError as e:
        error_message = (
            f"Failed to install poetry dependencies in '{project_path}'. Exit code: {e.returncode}.\n"
            f"Stderr: {e.stderr}\n"
            f"Stdout: {e.stdout}"
        )
        logging.error(error_message)
        return False, error_message
    except FileNotFoundError as e:
        error_message = f"Subprocess error during dependency installation: Could not execute '{e.filename}'. Full error: {e}"
        logging.error(error_message)
        return False, error_message

    # --- Step 2: Prepare and run the market creation script ---
    project_name = application_details.get("project_name")
    program_name = application_details.get("program_name")
    application_id = application_details.get("application_id")

    if not all([project_name, program_name, application_id]):
        return False, "Missing project_name, program_name, or application_id in details."

    # 1. Construct the question with metadata
    question = (
        f'Will project "{project_name}" be approved for the "{program_name}" program?'
        f' [Supafund App: {application_id}]'
    )

    # 2. Determine the closing time
    deadline_str = application_details.get("deadline")
    if deadline_str:
        closing_time = datetime.fromisoformat(deadline_str).strftime("%Y-%m-%dT%H:%M:%S")
    else:
        # Default to 30 days from now if no deadline is specified
        closing_time = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")

    # 3. Construct the command
    command = [
        "/bin/sh",
        poetry_executable_path,
        "run",
        "python",
        "scripts/create_market_omen.py",
        "--question", question,
        "--closing-time", closing_time,
        "--category", "supafund",
        "--initial-funds-usd", "0.01",
        "--cl-token", "wxdai",
        "--from-private-key", Config.OMEN_PRIVATE_KEY,
    ]

    logging.info(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")

    # 4. Execute the command
    try:
        logging.info(f"Executing command in directory: {project_path}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            cwd=project_path
        )
        logging.info(f"Omen market creation successful. Output:\n{result.stdout}")
        return True, result.stdout

    except FileNotFoundError as e:
        error_message = f"Subprocess error: File not found. The system failed to execute '{e.filename}'. This could be an issue with the file itself, its path, or its interpreter's dependencies. Full error: {e}"
        logging.error(error_message)
        return False, error_message
        
    except subprocess.CalledProcessError as e:
        error_message = (
            f"Omen market creation failed with exit code {e.returncode}.\n"
            f"Stderr: {e.stderr}\n"
            f"Stdout: {e.stdout}"
        )
        logging.error(error_message)
        return False, error_message
        
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logging.error(error_message)
        return False, str(e)
