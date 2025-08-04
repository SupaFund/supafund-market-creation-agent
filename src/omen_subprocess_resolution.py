"""
Omen market resolution using subprocess calls to gnosis_predict_market_tool
"""
import logging
import subprocess
import json
import os
import tempfile
from typing import Dict, Tuple, Optional
from .config import Config

logger = logging.getLogger(__name__)

class OmenSubprocessResolution:
    """Market resolution service using subprocess calls to gnosis prediction market tools"""
    
    def __init__(self):
        self.poetry_path = Config.POETRY_PATH
        self.omen_script_path = Config.OMEN_SCRIPT_PROJECT_PATH
        self.graph_api_key = Config.GRAPH_API_KEY
        
        # Check if we're in a production environment (Docker)
        self.use_direct_python = os.path.exists('/app/gnosis_predict_market_tool') or os.getenv('USE_DIRECT_PYTHON', 'false').lower() == 'true'
    
    def submit_market_answer(self, market_id: str, outcome: str, confidence: float, 
                           reasoning: str, from_private_key: str, 
                           bond_amount_xdai: float = 0.01, 
                           safe_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Submit an answer to a market using subprocess calls.
        
        Args:
            market_id: The market ID to submit answer for
            outcome: The outcome to submit ("Yes", "No", or "Invalid")
            confidence: Confidence level (0.0 to 1.0)
            reasoning: Reasoning for the outcome
            from_private_key: Private key for the transaction
            bond_amount_xdai: Bond amount in xDai
            safe_address: Optional safe address
            
        Returns:
            Tuple of (success: bool, result: str)
        """
        try:
            # Create a temporary Python script for answer submission
            # Escape values to prevent injection and formatting issues
            safe_address_escaped = safe_address.replace('"', '\\"') if safe_address else ""
            from_private_key_escaped = from_private_key.replace('"', '\\"')
            outcome_escaped = outcome.replace('"', '\\"')
            reasoning_escaped = reasoning.replace('"', '\\"').replace('\n', '\\n')[:100]
            
            script_content = f'''#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.insert(0, os.getcwd())

try:
    from prediction_market_agent_tooling.config import APIKeys
    from prediction_market_agent_tooling.gtypes import private_key_type, xDai
    from prediction_market_agent_tooling.markets.data_models import Resolution
    from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import OmenSubgraphHandler
    from prediction_market_agent_tooling.markets.omen.omen_resolving import (
        omen_submit_answer_market_tx,
        omen_submit_invalid_answer_market_tx,
    )
    from eth_typing import HexAddress, HexStr
    from web3 import Web3

    def main():
        try:
            # Setup API keys
            safe_address_checksum = Web3.to_checksum_address("{safe_address_escaped}") if "{safe_address_escaped}" else None
            
            api_keys = APIKeys(
                BET_FROM_PRIVATE_KEY=private_key_type("{from_private_key_escaped}"),
                SAFE_ADDRESS=safe_address_checksum,
                GRAPH_API_KEY="{self.graph_api_key}",
            )
            
            # Get market from subgraph
            subgraph_handler = OmenSubgraphHandler()
            market = subgraph_handler.get_omen_market_by_market_id(
                HexAddress(HexStr("{market_id}"))
            )
            
            if not market:
                raise ValueError("Market {market_id} not found")
            
            # Check if market is closed
            if market.is_open:
                raise ValueError(f"Market is still open. Closes at: {{market.close_time.isoformat()}}")
            
            # Create bond amount
            bond = xDai({bond_amount_xdai})
            
            # Submit answer
            if "{outcome_escaped}" == "Invalid":
                omen_submit_invalid_answer_market_tx(
                    api_keys=api_keys,
                    market=market,
                    bond=bond,
                )
            else:
                resolution = Resolution(
                    outcome="{outcome_escaped}",
                    outcome_source="Subprocess submission: {reasoning_escaped}...",
                    invalid=False,
                    confidence={confidence}
                )
                
                omen_submit_answer_market_tx(
                    api_keys=api_keys,
                    market=market,
                    resolution=resolution,
                    bond=bond,
                )
            
            # Return success result
            result = {{
                "success": True,
                "market_id": "{market_id}",
                "outcome": "{outcome_escaped}",
                "confidence": {confidence},
                "bond_amount_xdai": {bond_amount_xdai},
                "message": "Answer submitted successfully"
            }}
            
            print(json.dumps(result))
            
        except Exception as e:
            error_result = {{
                "success": False,
                "error": str(e),
                "market_id": "{market_id}"
            }}
            print(json.dumps(error_result))
            sys.exit(1)

    if __name__ == "__main__":
        main()
        
except ImportError as e:
    error_result = {{
        "success": False,
        "error": f"Import error: {{str(e)}}",
        "market_id": "{market_id}"
    }}
    print(json.dumps(error_result))
    sys.exit(1)
except Exception as e:
    error_result = {{
        "success": False,
        "error": f"Unexpected error: {{str(e)}}",
        "market_id": "{market_id}"
    }}
    print(json.dumps(error_result))
    sys.exit(1)
'''
            
            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(script_content)
                temp_script_path = temp_file.name
            
            try:
                # Choose execution method based on environment
                if self.use_direct_python:
                    # Production environment: use direct Python with proper PYTHONPATH
                    cmd_args = ["python", temp_script_path]
                    env = os.environ.copy()
                    env['PYTHONPATH'] = f"{self.omen_script_path}:{env.get('PYTHONPATH', '')}"
                    logger.info(f"Using direct Python execution in production environment")
                else:
                    # Development environment: use Poetry
                    cmd_args = [self.poetry_path, "run", "python", temp_script_path]
                    env = None
                    logger.info(f"Using Poetry execution in development environment")
                
                logger.info(f"Submitting answer for market {market_id}: {outcome}")
                
                result = subprocess.run(
                    cmd_args,
                    cwd=self.omen_script_path,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes timeout
                    env=env
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    logger.info(f"Answer submission successful: {output}")
                    return True, output
                else:
                    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                    logger.error(f"Answer submission failed: {error_msg}")
                    return False, f"Answer submission failed: {error_msg}"
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_script_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            error_msg = "Answer submission timed out after 5 minutes"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during answer submission: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def finalize_market_resolution(self, market_id: str, from_private_key: str, 
                                 safe_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Finalize market resolution using subprocess calls.
        
        Args:
            market_id: The market ID to finalize
            from_private_key: Private key for the transaction
            safe_address: Optional safe address
            
        Returns:
            Tuple of (success: bool, result: str)
        """
        try:
            # Create a temporary Python script for market finalization
            script_content = f'''
#!/usr/bin/env python3
import sys
import os
import json

# Add the project root to Python path
sys.path.insert(0, os.getcwd())

from prediction_market_agent_tooling.config import APIKeys
from prediction_market_agent_tooling.gtypes import private_key_type
from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import OmenSubgraphHandler
from prediction_market_agent_tooling.markets.omen.omen_resolving import omen_resolve_market_tx
from eth_typing import HexAddress, HexStr
from web3 import Web3

def main():
    try:
        # Setup API keys
        safe_address_checksum = Web3.to_checksum_address("{safe_address}") if "{safe_address}" else None
        
        api_keys = APIKeys(
            BET_FROM_PRIVATE_KEY=private_key_type("{from_private_key}"),
            SAFE_ADDRESS=safe_address_checksum,
            GRAPH_API_KEY="{self.graph_api_key}",
        )
        
        # Get market from subgraph
        subgraph_handler = OmenSubgraphHandler()
        market = subgraph_handler.get_omen_market_by_market_id(
            HexAddress(HexStr("{market_id}"))
        )
        
        if not market:
            raise ValueError(f"Market {market_id} not found")
        
        # Check if market has an answer
        if market.question.currentAnswer is None:
            raise ValueError("Market does not have an answer yet. Submit an answer first.")
        
        # Check if already resolved
        if market.condition and hasattr(market.condition, 'resolved') and market.condition.resolved:
            raise ValueError("Market is already resolved.")
        
        # Finalize market resolution
        omen_resolve_market_tx(
            api_keys=api_keys,
            market=market,
        )
        
        # Return success result
        result = {{
            "success": True,
            "market_id": "{market_id}",
            "message": "Market resolution finalized successfully"
        }}
        
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {{
            "success": False,
            "error": str(e),
            "market_id": "{market_id}"
        }}
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
            
            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(script_content)
                temp_script_path = temp_file.name
            
            try:
                # Choose execution method based on environment
                if self.use_direct_python:
                    # Production environment: use direct Python with proper PYTHONPATH
                    cmd_args = ["python", temp_script_path]
                    env = os.environ.copy()
                    env['PYTHONPATH'] = f"{self.omen_script_path}:{env.get('PYTHONPATH', '')}"
                    logger.info(f"Using direct Python execution in production environment")
                else:
                    # Development environment: use Poetry
                    cmd_args = [self.poetry_path, "run", "python", temp_script_path]
                    env = None
                    logger.info(f"Using Poetry execution in development environment")
                
                logger.info(f"Finalizing resolution for market {market_id}")
                
                result = subprocess.run(
                    cmd_args,
                    cwd=self.omen_script_path,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes timeout
                    env=env
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    logger.info(f"Market finalization successful: {output}")
                    return True, output
                else:
                    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                    logger.error(f"Market finalization failed: {error_msg}")
                    return False, f"Market finalization failed: {error_msg}"
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_script_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            error_msg = "Market finalization timed out after 5 minutes"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during market finalization: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def check_market_resolution_status(self, market_id: str, from_private_key: str) -> Tuple[bool, str, dict]:
        """
        Check market resolution status using subprocess calls.
        
        Args:
            market_id: The market ID to check
            from_private_key: Private key for authentication
            
        Returns:
            Tuple of (success: bool, message: str, status_info: dict)
        """
        try:
            # Create a temporary Python script for status checking
            script_content = f'''
#!/usr/bin/env python3
import sys
import os
import json

# Add the project root to Python path
sys.path.insert(0, os.getcwd())

from prediction_market_agent_tooling.config import APIKeys
from prediction_market_agent_tooling.gtypes import private_key_type
from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import OmenSubgraphHandler
from eth_typing import HexAddress, HexStr

def main():
    try:
        # Setup API keys
        api_keys = APIKeys(
            BET_FROM_PRIVATE_KEY=private_key_type("{from_private_key}"),
            GRAPH_API_KEY="{self.graph_api_key}",
        )
        
        # Get market from subgraph
        subgraph_handler = OmenSubgraphHandler()
        market = subgraph_handler.get_omen_market_by_market_id(
            HexAddress(HexStr("{market_id}"))
        )
        
        if not market:
            raise ValueError(f"Market {market_id} not found")
        
        # Handle currentAnswer type
        current_answer_hex = None
        if market.question.currentAnswer is not None:
            if isinstance(market.question.currentAnswer, str):
                current_answer_hex = market.question.currentAnswer
            else:
                current_answer_hex = market.question.currentAnswer.hex()
        
        # Check market status
        status_info = {{
            "market_id": "{market_id}",
            "is_closed": not market.is_open,
            "closing_time": market.close_time.isoformat() if market.close_time else None,
            "has_answer": market.question.currentAnswer is not None,
            "current_answer": current_answer_hex,
            "is_resolved": market.condition and hasattr(market.condition, 'resolved') and market.condition.resolved,
            "needs_finalization": market.question.currentAnswer is not None and not (market.condition and hasattr(market.condition, 'resolved') and market.condition.resolved),
        }}
        
        result = {{
            "success": True,
            "message": "Market status retrieved successfully",
            "status_info": status_info
        }}
        
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {{
            "success": False,
            "error": str(e),
            "market_id": "{market_id}"
        }}
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
            
            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(script_content)
                temp_script_path = temp_file.name
            
            try:
                # Choose execution method based on environment
                if self.use_direct_python:
                    # Production environment: use direct Python with proper PYTHONPATH
                    cmd_args = ["python", temp_script_path]
                    env = os.environ.copy()
                    env['PYTHONPATH'] = f"{self.omen_script_path}:{env.get('PYTHONPATH', '')}"
                    logger.info(f"Using direct Python execution in production environment")
                else:
                    # Development environment: use Poetry
                    cmd_args = [self.poetry_path, "run", "python", temp_script_path]
                    env = None
                    logger.info(f"Using Poetry execution in development environment")
                
                logger.info(f"Checking resolution status for market {market_id}")
                
                result = subprocess.run(
                    cmd_args,
                    cwd=self.omen_script_path,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minutes timeout for status check
                    env=env
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    logger.info(f"Status check successful: {output}")
                    
                    # Parse the JSON output
                    try:
                        result_data = json.loads(output)
                        return True, result_data.get("message", "Status retrieved"), result_data.get("status_info", {})
                    except json.JSONDecodeError:
                        return True, "Status retrieved (parsing issue)", {"raw_output": output}
                else:
                    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                    logger.error(f"Status check failed: {error_msg}")
                    return False, f"Status check failed: {error_msg}", {}
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_script_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            error_msg = "Status check timed out after 2 minutes"
            logger.error(error_msg)
            return False, error_msg, {}
        except Exception as e:
            error_msg = f"Unexpected error during status check: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}

# Create global instance
omen_resolution = OmenSubprocessResolution()

def submit_market_answer_subprocess(market_id: str, outcome: str, confidence: float, 
                                  reasoning: str, from_private_key: str, 
                                  bond_amount_xdai: float = 0.01, 
                                  safe_address: Optional[str] = None) -> Tuple[bool, str]:
    """Convenience function to submit market answer."""
    return omen_resolution.submit_market_answer(
        market_id, outcome, confidence, reasoning, from_private_key, 
        bond_amount_xdai, safe_address
    )

def finalize_market_resolution_subprocess(market_id: str, from_private_key: str, 
                                        safe_address: Optional[str] = None) -> Tuple[bool, str]:
    """Convenience function to finalize market resolution."""
    return omen_resolution.finalize_market_resolution(market_id, from_private_key, safe_address)

def check_market_resolution_status_subprocess(market_id: str, from_private_key: str) -> Tuple[bool, str, dict]:
    """Convenience function to check market resolution status."""
    return omen_resolution.check_market_resolution_status(market_id, from_private_key)