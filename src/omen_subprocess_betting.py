"""
Omen betting using subprocess calls to gnosis_predict_market_tool
"""
import logging
import subprocess
import json
import os
from typing import Dict, Tuple
from .config import Config

logger = logging.getLogger(__name__)

class OmenSubprocessBetting:
    """Betting service using subprocess calls to gnosis prediction market tools"""
    
    def __init__(self):
        self.poetry_path = Config.POETRY_PATH
        self.omen_script_path = Config.OMEN_SCRIPT_PROJECT_PATH
        
        # Check if we're in a production environment (Docker)
        self.use_direct_python = os.path.exists('/app/gnosis_predict_market_tool') or os.getenv('USE_DIRECT_PYTHON', 'false').lower() == 'true'
    
    def place_bet(self, market_id: str, amount_usd: float, outcome: str, 
                  from_private_key: str, safe_address: str = None, 
                  auto_deposit: bool = True) -> Tuple[bool, str]:
        """
        Place a bet on an Omen market using subprocess calls.
        
        Args:
            market_id: The market ID to bet on
            amount_usd: Amount to bet in USD
            outcome: The outcome to bet on ("Yes" or "No")
            from_private_key: Private key for the transaction
            safe_address: Optional safe address
            auto_deposit: Whether to auto deposit collateral
            
        Returns:
            Tuple of (success: bool, result: str)
        """
        try:
            # Choose execution method based on environment
            if self.use_direct_python:
                # Production environment: use direct Python with proper PYTHONPATH
                cmd_args = [
                    "python", "scripts/bet_omen.py", "buy",
                    "--market-id", market_id,
                    "--amount-usd", str(amount_usd),
                    "--outcome", outcome.lower(),
                    "--from-private-key", from_private_key
                ]
                env = os.environ.copy()
                env['PYTHONPATH'] = f"{self.omen_script_path}:{env.get('PYTHONPATH', '')}"
                logger.info(f"Using direct Python execution in production environment")
            else:
                # Development environment: use Poetry
                cmd_args = [
                    self.poetry_path, "run", "python", "scripts/bet_omen.py", "buy",
                    "--market-id", market_id,
                    "--amount-usd", str(amount_usd),
                    "--outcome", outcome.lower(),
                    "--from-private-key", from_private_key
                ]
                env = None
                logger.info(f"Using Poetry execution in development environment")
            
            # Add optional arguments
            if safe_address:
                cmd_args.extend(["--safe-address", safe_address])
            
            if auto_deposit:
                cmd_args.append("--auto-deposit")
            
            logger.info(f"Placing bet on market {market_id}: {amount_usd} USD on {outcome}")
            
            # Execute the betting command
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
                logger.info(f"Bet placed successfully: {output}")
                
                # Parse the output
                bet_info = self._parse_bet_output(output)
                
                return True, json.dumps({
                    "success": True,
                    "bet_info": bet_info,
                    "market_id": market_id,
                    "amount_usd": amount_usd,
                    "outcome": outcome,
                    "raw_output": output
                })
            else:
                error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                logger.error(f"Bet placement failed: {error_msg}")
                return False, f"Bet placement failed: {error_msg}"
                
        except subprocess.TimeoutExpired:
            error_msg = "Bet placement timed out after 5 minutes"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during bet placement: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _parse_bet_output(self, output: str) -> Dict:
        """
        Parse the output from betting script.
        
        Args:
            output: Raw output from the script
            
        Returns:
            Dictionary with parsed betting information
        """
        bet_info = {
            "raw_output": output
        }
        
        try:
            # Try to parse as JSON first
            if output.startswith('{'):
                bet_info.update(json.loads(output))
                return bet_info
            
            # Extract transaction hash if present
            import re
            tx_hash_pattern = r'transaction[_\s]*hash[:\s]*([0-9a-fA-Fx]+)'
            tx_hash_match = re.search(tx_hash_pattern, output, re.IGNORECASE)
            if tx_hash_match:
                bet_info["transaction_hash"] = tx_hash_match.group(1)
            
            # Extract shares received if present
            shares_pattern = r'shares[_\s]*received[:\s]*([0-9.]+)'
            shares_match = re.search(shares_pattern, output, re.IGNORECASE)
            if shares_match:
                bet_info["shares_received"] = float(shares_match.group(1))
                
        except Exception as e:
            logger.warning(f"Could not parse bet output: {e}")
            
        return bet_info

# Create global instance
omen_betting = OmenSubprocessBetting()

def place_bet(market_id: str, amount_usd: float, outcome: str, 
              from_private_key: str, safe_address: str = None, 
              auto_deposit: bool = True) -> Tuple[bool, str]:
    """
    Convenience function to place a bet.
    
    Args:
        market_id: The market ID to bet on
        amount_usd: Amount to bet in USD
        outcome: The outcome to bet on
        from_private_key: Private key for the transaction
        safe_address: Optional safe address
        auto_deposit: Whether to auto deposit collateral
        
    Returns:
        Tuple of (success: bool, result: str)
    """
    return omen_betting.place_bet(market_id, amount_usd, outcome, 
                                  from_private_key, safe_address, auto_deposit)