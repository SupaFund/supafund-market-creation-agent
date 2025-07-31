import logging
import re
import json
from datetime import datetime, timedelta, timezone
from .config import Config
from .blockchain.market_creator import create_omen_market as blockchain_create_market
from .blockchain.types import MarketCreationResult

logging.basicConfig(level=logging.INFO)

def create_omen_market(application_details: dict) -> tuple[bool, str | MarketCreationResult]:
    """
    Creates a prediction market on Omen using direct blockchain interaction.

    Args:
        application_details: A dictionary containing details about the application,
                             including project_name, program_name, and deadline.

    Returns:
        A tuple containing a boolean success status and either an error message (str) 
        or the MarketCreationResult object for successful creation.
    """
    # --- Prepare market creation parameters ---
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
        closing_time = datetime.fromisoformat(deadline_str)
    else:
        # Default to 30 days from now if no deadline is specified
        closing_time = datetime.now(timezone.utc) + timedelta(days=30)

    # Ensure closing_time has timezone info
    if closing_time.tzinfo is None:
        closing_time = closing_time.replace(tzinfo=timezone.utc)

    # 3. Create market using direct blockchain interaction
    try:
        logging.info(f"Creating market with question: {question}")
        logging.info(f"Closing time: {closing_time}")
        
        # Use the new blockchain module
        result = blockchain_create_market(
            question=question,
            closing_time=closing_time,
            category="supafund",
            initial_funds_usd="0.01",
            from_private_key=Config.OMEN_PRIVATE_KEY,
            collateral_token="wxdai",
            auto_deposit=True
        )
        
        if result.success:
            logging.info(f"Omen market creation successful.")
            logging.info(f"Market ID: {result.market_id}")
            logging.info(f"Market URL: {result.market_url}")
            logging.info(f"Transaction Hash: {result.transaction_hash}")
            # Return the structured result object instead of text
            return True, result
        else:
            error_message = f"Market creation failed: {result.error_message}"
            logging.error(error_message)
            return False, error_message
            
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logging.error(error_message)
        return False, str(e)


def parse_market_output(output) -> dict:
    """
    Parse the output from Omen market creation to extract market information.
    
    Args:
        output: Either a MarketCreationResult object or raw output string from the market creation
        
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
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        "transaction_hash": None
    }
    
    try:
        # If output is a MarketCreationResult object, extract data directly
        if isinstance(output, MarketCreationResult):
            market_info["market_id"] = output.market_id or ""
            market_info["market_url"] = output.market_url or ""
            market_info["transaction_hash"] = output.transaction_hash or ""
            
            # Extract question from raw_output if available
            if output.raw_output and "question:" in output.raw_output.lower():
                question_match = re.search(r"question[:\s]*([^\n]+)", output.raw_output, re.IGNORECASE)
                if question_match:
                    market_info["market_question"] = question_match.group(1).strip()
            
            # Generate market title from question or use a default
            if market_info["market_question"]:
                market_info["market_title"] = market_info["market_question"][:100] + "..." if len(market_info["market_question"]) > 100 else market_info["market_question"]
            else:
                market_info["market_title"] = f"Prediction Market {market_info['market_id'][:8]}..."
            
            logging.info(f"Parsed market info from MarketCreationResult: {market_info}")
            return market_info
        
        # Fallback: Parse from string output (original logic)
        # Try to find market ID in the output
        # Common patterns for market ID extraction
        market_id_patterns = [
            r"Market ID:\s*([0-9a-fA-F]{40}|0x[0-9a-fA-F]{40})",
            r"market[_\s]id[:\s]*([0-9a-fA-F]{40}|0x[0-9a-fA-F]{40})",
            r"created[_\s]market[:\s]*([0-9a-fA-F]{40}|0x[0-9a-fA-F]{40})",
            r"address[:\s]*([0-9a-fA-F]{40}|0x[0-9a-fA-F]{40})",
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
            r"Market URL:\s*(https?://[^\s]+)",
            r"https?://[^\s]+omen[^\s]*market[^\s]*",
            r"https?://omen\.eth\.limo/[^\s]*",
            r"https?://[^\s]*omen[^\s]*"
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                market_info["market_url"] = match.group(1) if len(match.groups()) > 0 else match.group(0)
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
        
        logging.info(f"Parsed market info from string: {market_info}")
        
    except Exception as e:
        logging.error(f"Error parsing market output: {e}")
        if hasattr(output, '__dict__'):
            logging.debug(f"MarketCreationResult object: {output.__dict__}")
        else:
            logging.debug(f"Raw output: {output}")
    
    return market_info