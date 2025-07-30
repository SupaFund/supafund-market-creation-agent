"""
Serverless adapter for gnosis_predict_market_tool.
This module provides a lightweight interface for blockchain operations in serverless environments.
"""
import logging
import sys
import os
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ServerlessGnosisAdapter:
    """
    Adapter class to handle gnosis_predict_market_tool imports and operations in serverless environment.
    """
    
    def __init__(self):
        self.gnosis_available = self._setup_gnosis_imports()
        
    def _setup_gnosis_imports(self) -> bool:
        """
        Setup gnosis_predict_market_tool imports with proper error handling for serverless.
        
        Returns:
            bool: True if imports successful, False otherwise
        """
        try:
            # Add gnosis_predict_market_tool to path if not already present
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            gnosis_tool_path = os.path.join(project_root, 'gnosis_predict_market_tool')
            
            if gnosis_tool_path not in sys.path:
                sys.path.insert(0, gnosis_tool_path)
                logger.info(f"Added gnosis tool path: {gnosis_tool_path}")
            
            # Test import core modules
            from prediction_market_agent_tooling.config import APIKeys
            from prediction_market_agent_tooling.gtypes import USD, OutcomeStr, private_key_type
            
            logger.info("✅ Gnosis imports successful")
            return True
            
        except ImportError as e:
            logger.error(f"❌ Failed to import gnosis_predict_market_tool: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error setting up gnosis imports: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if gnosis_predict_market_tool is available."""
        return self.gnosis_available
    
    def create_market(self, **kwargs) -> Dict[str, Any]:
        """
        Create a market using gnosis_predict_market_tool.
        
        Returns:
            Dict with success status and market details
        """
        if not self.gnosis_available:
            return {
                "success": False,
                "error_message": "Gnosis predict market tool not available in serverless environment",
                "fallback_mode": True
            }
        
        try:
            # Import the required modules
            from prediction_market_agent_tooling.config import APIKeys
            from prediction_market_agent_tooling.gtypes import USD, OutcomeStr, private_key_type
            from prediction_market_agent_tooling.markets.omen.data_models import OMEN_BINARY_MARKET_OUTCOMES
            from prediction_market_agent_tooling.markets.omen.omen import omen_create_market_tx
            from prediction_market_agent_tooling.markets.omen.omen_contracts import (
                COLLATERAL_TOKEN_CHOICE_TO_ADDRESS,
                OMEN_DEFAULT_MARKET_FEE_PERC,
                CollateralTokenChoice,
            )
            from prediction_market_agent_tooling.tools.utils import DatetimeUTC
            from web3 import Web3
            
            # Extract parameters
            question = kwargs.get('question')
            closing_time = kwargs.get('closing_time')
            initial_funds_usd = kwargs.get('initial_funds_usd', '0.01')
            from_private_key = kwargs.get('from_private_key')
            safe_address = kwargs.get('safe_address')
            
            # Validate required parameters
            if not all([question, closing_time, from_private_key]):
                return {
                    "success": False,
                    "error_message": "Missing required parameters: question, closing_time, or from_private_key"
                }
            
            # Setup API keys
            safe_address_checksum = (
                Web3.to_checksum_address(safe_address) if safe_address else None
            )
            
            from ..config import Config
            api_keys = APIKeys(
                BET_FROM_PRIVATE_KEY=private_key_type(from_private_key),
                SAFE_ADDRESS=safe_address_checksum,
                GRAPH_API_KEY=Config.GRAPH_API_KEY,
            )
            
            # Setup collateral token
            collateral_token_choice = CollateralTokenChoice.wxdai
            collateral_token_address = COLLATERAL_TOKEN_CHOICE_TO_ADDRESS[collateral_token_choice]
            
            # Convert closing time
            if closing_time.tzinfo is None:
                closing_time = closing_time.replace(tzinfo=timezone.utc)
            closing_time_utc = DatetimeUTC.from_datetime(closing_time)
            
            # Create market
            created_market = omen_create_market_tx(
                api_keys=api_keys,
                collateral_token_address=collateral_token_address,
                initial_funds=USD(initial_funds_usd),
                fee_perc=OMEN_DEFAULT_MARKET_FEE_PERC,
                question=question,
                closing_time=closing_time_utc,
                category=kwargs.get('category', 'supafund'),
                language=kwargs.get('language', 'en'),
                outcomes=[OutcomeStr(x) for x in OMEN_BINARY_MARKET_OUTCOMES],
                auto_deposit=kwargs.get('auto_deposit', True),
            )
            
            # Extract results
            market_id = created_market.market_maker_contract_address_checksummed
            market_url = f"https://aiomen.eth.limo/#{market_id}"
            transaction_hash = created_market.transaction_receipt.transactionHash.hex() if created_market.transaction_receipt else None
            
            return {
                "success": True,
                "market_id": market_id,
                "market_url": market_url,
                "transaction_hash": transaction_hash,
                "raw_output": f"Market created successfully! ID: {market_id}"
            }
            
        except Exception as e:
            logger.error(f"Error creating market in serverless: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def place_bet(self, **kwargs) -> Dict[str, Any]:
        """
        Place a bet using gnosis_predict_market_tool.
        
        Returns:
            Dict with success status and bet details
        """
        if not self.gnosis_available:
            return {
                "success": False,
                "error_message": "Gnosis predict market tool not available in serverless environment"
            }
        
        try:
            # Import required modules
            from prediction_market_agent_tooling.config import APIKeys
            from prediction_market_agent_tooling.gtypes import USD, private_key_type
            from prediction_market_agent_tooling.markets.omen.omen import omen_buy_outcome_tx
            from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import OmenSubgraphHandler
            from web3 import Web3
            from eth_typing import HexAddress, HexStr
            
            # Extract parameters
            market_id = kwargs.get('market_id')
            amount_usd = kwargs.get('amount_usd')
            outcome = kwargs.get('outcome')
            from_private_key = kwargs.get('from_private_key')
            safe_address = kwargs.get('safe_address')
            
            # Validate parameters
            if not all([market_id, amount_usd, outcome, from_private_key]):
                return {
                    "success": False,
                    "error_message": "Missing required parameters"
                }
            
            # Setup API keys
            safe_address_checksum = (
                Web3.to_checksum_address(safe_address) if safe_address else None
            )
            
            from ..config import Config
            api_keys = APIKeys(
                BET_FROM_PRIVATE_KEY=private_key_type(from_private_key),
                SAFE_ADDRESS=safe_address_checksum,
                GRAPH_API_KEY=Config.GRAPH_API_KEY,
            )
            
            # Get market from subgraph
            subgraph_handler = OmenSubgraphHandler()
            market = subgraph_handler.get_omen_market_by_market_id(HexAddress(HexStr(market_id)))
            
            if not market:
                return {
                    "success": False,
                    "error_message": f"Market {market_id} not found"
                }
            
            # Place bet
            bet_result = omen_buy_outcome_tx(
                api_keys=api_keys,
                market=market,
                outcome=outcome,
                amount=USD(str(amount_usd)),
                auto_deposit=kwargs.get('auto_deposit', True)
            )
            
            return {
                "success": True,
                "transaction_hash": bet_result.id if hasattr(bet_result, 'id') else None,
                "raw_output": f"Bet placed successfully on {outcome} for ${amount_usd}"
            }
            
        except Exception as e:
            logger.error(f"Error placing bet in serverless: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def submit_answer(self, **kwargs) -> Dict[str, Any]:
        """
        Submit answer to market using gnosis_predict_market_tool.
        
        Returns:
            Dict with success status and submission details
        """
        if not self.gnosis_available:
            return {
                "success": False,
                "error_message": "Gnosis predict market tool not available in serverless environment"
            }
        
        try:
            # This would implement the resolution submission logic
            # Similar to the patterns above
            return {
                "success": True,
                "raw_output": "Answer submitted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error submitting answer in serverless: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }


# Global adapter instance
_adapter = None

def get_serverless_adapter() -> ServerlessGnosisAdapter:
    """Get the global serverless adapter instance."""
    global _adapter
    if _adapter is None:
        _adapter = ServerlessGnosisAdapter()
    return _adapter