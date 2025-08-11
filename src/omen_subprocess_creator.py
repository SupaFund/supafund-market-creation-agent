"""
Omen market creation using subprocess calls to gnosis_predict_market_tool
"""
import logging
import subprocess
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Optional
from .config import Config

logger = logging.getLogger(__name__)

class OmenSubprocessCreator:
    """Market creator using subprocess calls to gnosis prediction market tools"""
    
    def __init__(self):
        self.poetry_path = Config.POETRY_PATH
        self.omen_script_path = Config.OMEN_SCRIPT_PROJECT_PATH
        self.private_key = Config.OMEN_PRIVATE_KEY
        self.graph_api_key = Config.GRAPH_API_KEY
        
        # Environment detection with precise Railway vs Docker distinction
        is_railway = Config.IS_RAILWAY
        railway_env = os.getenv('RAILWAY_ENVIRONMENT') is not None
        
        # True Docker environment: /app path exists but NOT Railway
        is_genuine_docker = (
            os.path.exists('/app/gnosis_predict_market_tool') and 
            not is_railway and 
            not railway_env
        )
        
        # Explicit override flag
        explicit_direct = os.getenv('USE_DIRECT_PYTHON', 'false').lower() == 'true'
        
        # Railway environment should use direct Python (Poetry not reliably available)
        # Docker environment should use direct Python 
        # Local development should use Poetry
        self.use_direct_python = is_railway or railway_env or is_genuine_docker or explicit_direct
        
        logger.info(f"Environment detection - Railway: {is_railway}/{railway_env}, Docker: {is_genuine_docker}, Direct Python: {self.use_direct_python}")
        logger.info(f"Execution strategy: {'Direct Python' if self.use_direct_python else 'Poetry'} ({'Railway' if is_railway or railway_env else 'Docker' if is_genuine_docker else 'Local'} environment)")
    
    def create_omen_market(self, application_details: dict) -> Tuple[bool, str]:
        """
        Creates a prediction market on Omen using subprocess calls to gnosis tools.
        
        Args:
            application_details: Dictionary containing application details
            
        Returns:
            Tuple of (success: bool, result: str)
        """
        try:
            # Extract and validate required fields
            project_name = application_details.get("project_name")
            project_description = application_details.get("project_description", "")
            program_description = application_details.get("program_description", "")
            program_name = application_details.get("program_name")
            application_id = application_details.get("application_id")
            deadline_str = application_details.get("deadline")
            
            if not all([project_name, program_name, application_id]):
                return False, "Missing required fields: project_name, program_name, or application_id"
            
            # Construct market question with context
            descriptions_parts = []
            if project_description:
                descriptions_parts.append(f"Project: {project_description}")
            if program_description:
                descriptions_parts.append(f"Program: {program_description}")
            
            descriptions_text = "; ".join(descriptions_parts) if descriptions_parts else ""
            
            question = (
                f'Will project "{project_name}" be approved for the "{program_name}" program?'
                f' [Supafund App: {application_id}]'
                + (f' <contextStart>{descriptions_text}<contextEnd>' if descriptions_text else '')
            )
            
            # Calculate closing time (default to 30 days if no deadline)
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                    # Set closing time to 1 day before deadline
                    closing_time = deadline - timedelta(days=1)
                except ValueError:
                    logger.warning(f"Invalid deadline format: {deadline_str}, using default")
                    closing_time = datetime.now(timezone.utc) + timedelta(days=30)
            else:
                closing_time = datetime.now(timezone.utc) + timedelta(days=30)
            
            # Format closing time to match script expectations (remove microseconds and timezone)
            closing_time_formatted = closing_time.strftime("%Y-%m-%dT%H:%M:%S")
            
            # Choose execution method based on environment
            if self.use_direct_python:
                # Railway/Docker environment: use direct Python with proper PYTHONPATH
                cmd_args = [
                    "python", "scripts/create_market_omen.py",
                    "--question", question,
                    "--closing-time", closing_time_formatted,
                    "--category", "supafund",
                    "--initial-funds-usd", "0.01",
                    "--from-private-key", self.private_key
                ]
                env = os.environ.copy()
                env['PYTHONPATH'] = f"{self.omen_script_path}:{env.get('PYTHONPATH', '')}"
                logger.info(f"Using direct Python execution (Railway/Docker environment)")
            else:
                # Local development environment: use Poetry
                cmd_args = [
                    self.poetry_path, "run", "python", "scripts/create_market_omen.py",
                    "--question", question,
                    "--closing-time", closing_time_formatted,
                    "--category", "supafund",
                    "--initial-funds-usd", "0.01",
                    "--from-private-key", self.private_key
                ]
                env = None
                logger.info(f"Using Poetry execution (Local development environment)")
            
            # Note: create_market_omen.py doesn't support --graph-api-key parameter
            # The Graph API key is used internally by the tooling when needed
            
            logger.info(f"Creating market with question: {question}")
            logger.info(f"Closing time: {closing_time_formatted}")
            
            # Execute the market creation command
            result = subprocess.run(
                cmd_args,
                cwd=self.omen_script_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env=env
            )
            
            if result.returncode == 0:
                # Parse the output to extract market information
                output = result.stdout.strip()
                logger.info(f"Market creation successful: {output}")
                
                # Try to extract market ID from output
                market_info = self._parse_market_output(output)
                
                return True, json.dumps({
                    "success": True,
                    "market_info": market_info,
                    "question": question,
                    "closing_time": closing_time_formatted,
                    "raw_output": output
                })
            else:
                error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                logger.error(f"Market creation failed: {error_msg}")
                return False, f"Market creation failed: {error_msg}"
                
        except subprocess.TimeoutExpired:
            error_msg = "Market creation timed out after 5 minutes"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during market creation: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _parse_market_output(self, output: str) -> Dict:
        """
        Parse the output from market creation script to extract market information.
        
        Args:
            output: Raw output from the script
            
        Returns:
            Dictionary with parsed market information
        """
        market_info = {
            "raw_output": output
        }
        
        try:
            # Look for MARKET_CREATED output from our modified script
            import re
            market_created_pattern = r'MARKET_CREATED: (.+)'
            market_created_match = re.search(market_created_pattern, output)
            if market_created_match:
                # Parse the market info dict
                market_data_str = market_created_match.group(1)
                # Convert string representation to dict (safely)
                import ast
                market_data = ast.literal_eval(market_data_str)
                market_info.update(market_data)
                logger.info(f"Successfully parsed market data: {market_data.get('market_id', 'unknown')}")
                return market_info
            
            # Fallback: try to parse as JSON first
            if output.strip().startswith('{'):
                market_info.update(json.loads(output.strip()))
                return market_info
            
            # Fallback: Extract market ID if present in output (legacy parsing)
            market_id_pattern = r'market[_\s]*id[:\s]*([0-9a-fA-Fx]+)'
            market_id_match = re.search(market_id_pattern, output, re.IGNORECASE)
            if market_id_match:
                market_info["market_id"] = market_id_match.group(1)
            
            # Extract transaction hash if present
            tx_hash_pattern = r'transaction[_\s]*hash[:\s]*([0-9a-fA-Fx]+)'
            tx_hash_match = re.search(tx_hash_pattern, output, re.IGNORECASE)
            if tx_hash_match:
                market_info["transaction_hash"] = tx_hash_match.group(1)
                
        except Exception as e:
            logger.warning(f"Could not parse market output: {e}")
            
        return market_info

# Create global instance
omen_creator = OmenSubprocessCreator()

def create_omen_market(application_details: dict) -> Tuple[bool, str]:
    """
    Convenience function to create an Omen market.
    
    Args:
        application_details: Dictionary containing application details
        
    Returns:
        Tuple of (success: bool, result: str)
    """
    return omen_creator.create_omen_market(application_details)