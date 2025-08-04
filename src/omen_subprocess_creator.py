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
            
            # Prepare command arguments
            cmd_args = [
                self.poetry_path, "run", "python", "scripts/create_market_omen.py",
                "--question", question,
                "--closing-time", closing_time.isoformat(),
                "--category", "supafund",
                "--private-key", self.private_key
            ]
            
            # Add optional arguments
            if self.graph_api_key:
                cmd_args.extend(["--graph-api-key", self.graph_api_key])
            
            logger.info(f"Creating market with question: {question}")
            logger.info(f"Closing time: {closing_time.isoformat()}")
            
            # Execute the market creation command
            result = subprocess.run(
                cmd_args,
                cwd=self.omen_script_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
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
                    "closing_time": closing_time.isoformat(),
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
            # Try to parse as JSON first
            if output.startswith('{'):
                market_info.update(json.loads(output))
                return market_info
            
            # Extract market ID if present in output
            import re
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