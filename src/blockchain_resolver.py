"""
Blockchain resolution service for submitting market outcomes to the blockchain.
"""
import logging
import subprocess
import json
from typing import Dict, Optional, Tuple
from dataclasses import asdict
from datetime import datetime, timezone

from .config import Config
from .resolution_researcher import ResolutionResult
from .market_monitor import MarketStatus

logger = logging.getLogger(__name__)

class BlockchainResolver:
    """Service to resolve markets on the blockchain using existing Omen tooling"""
    
    def __init__(self):
        self.poetry_path = Config.POETRY_PATH
        self.omen_script_path = Config.OMEN_SCRIPT_PROJECT_PATH
        self.private_key = Config.OMEN_PRIVATE_KEY
    
    def resolve_market_on_blockchain(self, market_status: MarketStatus, resolution_result: ResolutionResult) -> Tuple[bool, str]:
        """
        Submit market resolution to the blockchain
        
        Args:
            market_status: Market status information
            resolution_result: Research result with outcome
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Prepare resolution data
            resolution_data = {
                "market_id": market_status.market_id,
                "outcome": resolution_result.outcome,
                "confidence": resolution_result.confidence,
                "reasoning": resolution_result.reasoning,
                "sources": resolution_result.sources,
                "application_id": market_status.application_id,
                "funding_program": market_status.funding_program_name,
                "resolved_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Log the resolution attempt
            logger.info(f"Attempting to resolve market {market_status.market_id} with outcome: {resolution_result.outcome}")
            
            if resolution_result.outcome == "Invalid":
                return self._submit_invalid_resolution(market_status, resolution_data)
            else:
                return self._submit_outcome_resolution(market_status, resolution_result, resolution_data)
                
        except Exception as e:
            error_msg = f"Error resolving market on blockchain: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def _submit_outcome_resolution(self, market_status: MarketStatus, resolution_result: ResolutionResult, resolution_data: Dict) -> Tuple[bool, str]:
        """
        Submit a Yes/No outcome resolution to the blockchain
        
        Args:
            market_status: Market status information
            resolution_result: Research result
            resolution_data: Resolution metadata
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Create a temporary script to resolve the market with outcome
            script_content = f"""
#!/usr/bin/env python3
import sys
import os
sys.path.append('{self.omen_script_path}')

from prediction_market_agent_tooling.config import APIKeys
from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import OmenSubgraphHandler
from prediction_market_agent_tooling.markets.omen.omen_resolving import omen_submit_answer_market_tx
from prediction_market_agent_tooling.markets.data_models import Resolution
from prediction_market_agent_tooling.gtypes import xDai
import json

# Set up API keys
api_keys = APIKeys(
    BET_FROM_PRIVATE_KEY="{self.private_key}",
    GRAPH_API_KEY="{Config.GRAPH_API_KEY or ''}"
)

# Get market from subgraph
subgraph_handler = OmenSubgraphHandler()
market = subgraph_handler.get_omen_market_by_market_id("{market_status.market_id}")

if not market:
    print("ERROR: Market not found in subgraph")
    sys.exit(1)

# Create resolution object
outcome_str = "{resolution_result.outcome}"
resolution = Resolution(
    outcome=outcome_str,
    outcome_source=f"Grok API research: {{resolution_result.reasoning[:100]}}...",
    invalid=False,
    confidence=float({resolution_result.confidence})
)

# Submit answer with bond (0.01 xDai)
bond_amount = xDai(0.01)

try:
    omen_submit_answer_market_tx(
        api_keys=api_keys,
        market=market,
        resolution=resolution,
        bond=bond_amount
    )
    
    # Output success with resolution data
    result = {{
        "success": True,
        "message": "Market resolution submitted successfully",
        "market_id": "{market_status.market_id}",
        "outcome": "{resolution_result.outcome}",
        "bond_amount": 0.01,
        "resolution_data": {json.dumps(resolution_data)}
    }}
    print(json.dumps(result))
    
except Exception as e:
    result = {{
        "success": False,
        "error": str(e),
        "market_id": "{market_status.market_id}"
    }}
    print(json.dumps(result))
    sys.exit(1)
"""
            
            # Execute the resolution script
            return self._execute_resolution_script(script_content, "outcome_resolution")
            
        except Exception as e:
            error_msg = f"Error submitting outcome resolution: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def _submit_invalid_resolution(self, market_status: MarketStatus, resolution_data: Dict) -> Tuple[bool, str]:
        """
        Submit an invalid resolution to the blockchain
        
        Args:
            market_status: Market status information
            resolution_data: Resolution metadata
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Create a temporary script to resolve the market as invalid
            script_content = f"""
#!/usr/bin/env python3
import sys
import os
sys.path.append('{self.omen_script_path}')

from prediction_market_agent_tooling.config import APIKeys
from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import OmenSubgraphHandler
from prediction_market_agent_tooling.markets.omen.omen_resolving import omen_submit_invalid_answer_market_tx
from prediction_market_agent_tooling.gtypes import xDai
import json

# Set up API keys
api_keys = APIKeys(
    BET_FROM_PRIVATE_KEY="{self.private_key}",
    GRAPH_API_KEY="{Config.GRAPH_API_KEY or ''}"
)

# Get market from subgraph
subgraph_handler = OmenSubgraphHandler()
market = subgraph_handler.get_omen_market_by_market_id("{market_status.market_id}")

if not market:
    print("ERROR: Market not found in subgraph")
    sys.exit(1)

# Submit invalid answer with bond (0.01 xDai)
bond_amount = xDai(0.01)

try:
    omen_submit_invalid_answer_market_tx(
        api_keys=api_keys,
        market=market,
        bond=bond_amount
    )
    
    # Output success with resolution data
    result = {{
        "success": True,
        "message": "Market marked as invalid successfully",
        "market_id": "{market_status.market_id}",
        "outcome": "Invalid",
        "bond_amount": 0.01,
        "resolution_data": {json.dumps(resolution_data)}
    }}
    print(json.dumps(result))
    
except Exception as e:
    result = {{
        "success": False,
        "error": str(e),
        "market_id": "{market_status.market_id}"
    }}
    print(json.dumps(result))
    sys.exit(1)
"""
            
            # Execute the resolution script
            return self._execute_resolution_script(script_content, "invalid_resolution")
            
        except Exception as e:
            error_msg = f"Error submitting invalid resolution: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def _execute_resolution_script(self, script_content: str, script_name: str) -> Tuple[bool, str]:
        """
        Execute a resolution script using Poetry
        
        Args:
            script_content: Python script content to execute
            script_name: Name for the temporary script file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        import tempfile
        import os
        
        try:
            # Create temporary script file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=f'_{script_name}.py',
                delete=False,
                dir=self.omen_script_path
            ) as temp_file:
                temp_file.write(script_content)
                temp_script_path = temp_file.name
            
            try:
                # Make script executable
                os.chmod(temp_script_path, 0o755)
                
                # Execute with Poetry
                cmd = [
                    self.poetry_path,
                    "run",
                    "python",
                    temp_script_path
                ]
                
                logger.info(f"Executing resolution script: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    cwd=self.omen_script_path,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                # Parse the output
                if result.returncode == 0:
                    try:
                        output_data = json.loads(result.stdout.strip())
                        if output_data.get("success"):
                            return True, output_data.get("message", "Resolution submitted successfully")
                        else:
                            return False, output_data.get("error", "Unknown error in resolution")
                    except json.JSONDecodeError:
                        # If output is not JSON, treat as success if return code is 0
                        return True, result.stdout.strip() or "Resolution submitted successfully"
                else:
                    error_msg = f"Resolution script failed with return code {result.returncode}. "
                    error_msg += f"Stdout: {result.stdout}, Stderr: {result.stderr}"
                    return False, error_msg
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_script_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return False, "Resolution script timed out after 5 minutes"
        except Exception as e:
            return False, f"Error executing resolution script: {e}"
    
    def check_market_needs_final_resolution(self, market_id: str) -> Tuple[bool, str]:
        """
        Check if a market needs final resolution after the answer period
        
        Args:
            market_id: Market ID to check
            
        Returns:
            Tuple of (needs_resolution: bool, message: str)
        """
        try:
            # Create script to check if market needs final resolution
            script_content = f"""
#!/usr/bin/env python3
import sys
import os
sys.path.append('{self.omen_script_path}')

from prediction_market_agent_tooling.config import APIKeys
from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import OmenSubgraphHandler
import json

# Set up API keys
api_keys = APIKeys(
    BET_FROM_PRIVATE_KEY="{self.private_key}",
    GRAPH_API_KEY="{Config.GRAPH_API_KEY or ''}"
)

# Get market from subgraph
subgraph_handler = OmenSubgraphHandler()
market = subgraph_handler.get_omen_market_by_market_id("{market_id}")

if not market:
    result = {{"needs_resolution": False, "message": "Market not found"}}
else:
    # Check if market has answer but needs final resolution
    has_answer = market.question.currentAnswer is not None
    is_resolved = market.condition and market.condition.resolved
    
    result = {{
        "needs_resolution": has_answer and not is_resolved,
        "message": f"Answer: {{has_answer}}, Resolved: {{is_resolved}}",
        "market_id": "{market_id}"
    }}

print(json.dumps(result))
"""
            
            success, output = self._execute_resolution_script(script_content, "check_resolution")
            
            if success:
                try:
                    result_data = json.loads(output)
                    return result_data.get("needs_resolution", False), result_data.get("message", "")
                except json.JSONDecodeError:
                    return False, f"Could not parse check result: {output}"
            else:
                return False, f"Error checking resolution status: {output}"
                
        except Exception as e:
            return False, f"Error checking market resolution status: {e}"
    
    def finalize_market_resolution(self, market_id: str) -> Tuple[bool, str]:
        """
        Finalize a market resolution after the answer period
        
        Args:
            market_id: Market ID to finalize
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Create script to finalize market resolution
            script_content = f"""
#!/usr/bin/env python3
import sys
import os
sys.path.append('{self.omen_script_path}')

from prediction_market_agent_tooling.config import APIKeys
from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import OmenSubgraphHandler
from prediction_market_agent_tooling.markets.omen.omen_resolving import omen_resolve_market_tx
import json

# Set up API keys
api_keys = APIKeys(
    BET_FROM_PRIVATE_KEY="{self.private_key}",
    GRAPH_API_KEY="{Config.GRAPH_API_KEY or ''}"
)

# Get market from subgraph
subgraph_handler = OmenSubgraphHandler()
market = subgraph_handler.get_omen_market_by_market_id("{market_id}")

if not market:
    print("ERROR: Market not found in subgraph")
    sys.exit(1)

try:
    omen_resolve_market_tx(api_keys=api_keys, market=market)
    
    result = {{
        "success": True,
        "message": "Market finalized successfully",
        "market_id": "{market_id}"
    }}
    print(json.dumps(result))
    
except Exception as e:
    result = {{
        "success": False,
        "error": str(e),
        "market_id": "{market_id}"
    }}
    print(json.dumps(result))
    sys.exit(1)
"""
            
            return self._execute_resolution_script(script_content, "finalize_resolution")
            
        except Exception as e:
            error_msg = f"Error finalizing market resolution: {e}"
            logger.error(error_msg)
            return False, error_msg