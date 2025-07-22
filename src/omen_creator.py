import subprocess
import logging
import shlex
import os
import sys
import re
import json
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
    project_description = application_details.get("project_description", "")
    program_description = application_details.get("program_description", "")
    program_name = application_details.get("program_name")
    application_id = application_details.get("application_id")

    if not all([project_name, program_name, application_id]):
        return False, "Missing project_name, program_name, or application_id in details."

    # 1. Construct the question with metadata and descriptions
    descriptions_parts = []
    if project_description:
        descriptions_parts.append(f"Project: {project_description}")
    if program_description:
        descriptions_parts.append(f"Program: {program_description}")
    
    # Join descriptions with semicolon if any exist
    descriptions_text = "; ".join(descriptions_parts) if descriptions_parts else ""
    
    question = (
        f'Will project "{project_name}" be approved for the "{program_name}" program?'
        f' [Supafund App: {application_id}]'
        + (f' <contextStart>{descriptions_text}<contextEnd>' if descriptions_text else '')
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


def parse_market_output(output: str) -> dict:
    """
    Parse the output from Omen market creation script to extract market information.
    
    Args:
        output: Raw output string from the market creation script
        
    Returns:
        Dictionary containing extracted market information
    """
    market_info = {
        "market_id": "",
        "market_title": "",
        "market_url": "",
        "market_question": "",
        "closing_time": None,
        "initial_funds_usd": 0.01,
        "creation_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Try to find market ID in the output
        # Common patterns for market ID extraction
        market_id_patterns = [
            r"market[_\s]id[:\s]*([0-9a-fA-F]{40}|0x[0-9a-fA-F]{40})",
            r"created[_\s]market[:\s]*([0-9a-fA-F]{40}|0x[0-9a-fA-F]{40})",
            r"address[:\s]*([0-9a-fA-F]{40}|0x[0-9a-fA-F]{40})",
            r"Market ID: ([0-9a-fA-F]{40}|0x[0-9a-fA-F]{40})",
        ]
        
        for pattern in market_id_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                market_info["market_id"] = match.group(1)
                if not market_info["market_id"].startswith("0x"):
                    market_info["market_id"] = "0x" + market_info["market_id"]
                break
        
        # Try to find market URL
        url_patterns = [
            r"https?://[^\s]+omen[^\s]*market[^\s]*",
            r"https?://omen\.eth\.limo/[^\s]*",
            r"https?://[^\s]*omen[^\s]*"
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                market_info["market_url"] = match.group(0)
                break
        
        # Extract question if visible in output
        question_patterns = [
            r"question[:\s]*[\"']([^\"']+)[\"']",
            r"Will project[^?]*\?[^<]*<contextStart>[^<]*<contextEnd>",
        ]
        
        for pattern in question_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                market_info["market_question"] = match.group(1) if len(match.groups()) > 0 else match.group(0)
                break
        
        # Try to extract closing time
        time_patterns = [
            r"closing[_\s]time[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})",
            r"deadline[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})",
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                market_info["closing_time"] = match.group(1)
                break
        
        # Try to extract funding amount
        funding_patterns = [
            r"initial[_\s]funds[:\s]*\$?([0-9]+\.?[0-9]*)",
            r"funding[:\s]*\$?([0-9]+\.?[0-9]*)",
        ]
        
        for pattern in funding_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                market_info["initial_funds_usd"] = float(match.group(1))
                break
        
        # Generate market title based on available info
        if market_info["market_question"]:
            market_info["market_title"] = market_info["market_question"][:100] + "..." if len(market_info["market_question"]) > 100 else market_info["market_question"]
        
        logging.info(f"Parsed market info: {market_info}")
        
    except Exception as e:
        logging.error(f"Error parsing market output: {e}")
        logging.debug(f"Raw output: {output}")
    
    return market_info
