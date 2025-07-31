"""
Real betting functionality for Omen markets using gnosis_predict_market_tool.
This integrates directly with the existing working blockchain interaction code.
"""
import logging
import sys
import os
from typing import Optional

# Add gnosis_predict_market_tool to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
gnosis_tool_path = os.path.join(project_root, 'gnosis_predict_market_tool')
sys.path.insert(0, gnosis_tool_path)

# Import from gnosis_predict_market_tool
from prediction_market_agent_tooling.config import APIKeys
from prediction_market_agent_tooling.gtypes import USD, OutcomeStr, private_key_type
from prediction_market_agent_tooling.markets.omen.omen import (
    omen_buy_outcome_tx,
    OmenAgentMarket,
)
from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import (
    OmenSubgraphHandler,
)
from eth_typing import HexAddress, HexStr
from web3 import Web3

from .types import BetResult

logger = logging.getLogger(__name__)

def build_omen_agent_market(market_id: str):
    """Build OmenAgentMarket from market ID using subgraph."""
    subgraph_handler = OmenSubgraphHandler()
    market_data_model = subgraph_handler.get_omen_market_by_market_id(
        HexAddress(HexStr(market_id))
    )
    if not market_data_model:
        raise ValueError(f"Market {market_id} not found")
    
    return OmenAgentMarket.from_data_model(market_data_model)

def place_omen_bet(
    market_id: str,
    amount_usd: str,
    outcome: str,
    from_private_key: str,
    safe_address: Optional[str] = None,
    auto_deposit: bool = True
) -> BetResult:
    """
    Place a bet on an Omen market using the real gnosis_predict_market_tool.
    
    Args:
        market_id: The market contract address
        amount_usd: Amount to bet in USD
        outcome: The outcome to bet on ("Yes" or "No")
        from_private_key: Private key for transactions
        safe_address: Optional safe address
        auto_deposit: Whether to auto-deposit collateral
        
    Returns:
        BetResult with success status and details
    """
    try:
        logger.info(f"Placing REAL bet on market {market_id}")
        logger.info(f"Amount: ${amount_usd}, Outcome: {outcome}")
        
        # Validate inputs
        if not from_private_key:
            return BetResult(
                success=False,
                error_message="Private key not provided"
            )
        
        if outcome not in ["Yes", "No"]:
            return BetResult(
                success=False,
                error_message=f"Invalid outcome: {outcome}. Must be 'Yes' or 'No'"
            )
        
        # Setup API keys for gnosis_predict_market_tool
        safe_address_checksum = (
            Web3.to_checksum_address(safe_address) if safe_address else None
        )
        
        # Import config to get GRAPH_API_KEY
        from ..config import Config
        
        api_keys = APIKeys(
            BET_FROM_PRIVATE_KEY=private_key_type(from_private_key),
            SAFE_ADDRESS=safe_address_checksum,
            GRAPH_API_KEY=Config.GRAPH_API_KEY,
        )
        
        # Get market details from subgraph
        logger.info("🔍 Fetching market details from subgraph...")
        market = build_omen_agent_market(market_id)
        
        # Place bet using the real gnosis_predict_market_tool function
        logger.info("🔗 Placing REAL bet using gnosis_predict_market_tool...")
        
        transaction_hash = omen_buy_outcome_tx(
            api_keys=api_keys,
            amount=USD(amount_usd),
            market=market,
            outcome=OutcomeStr(outcome),
            auto_deposit=auto_deposit,
        )
        
        logger.info(f"✅ Bet placed successfully! Transaction: {transaction_hash}")
        
        return BetResult(
            success=True,
            transaction_hash=transaction_hash,
            raw_output=f"Bet placed successfully! Amount: ${amount_usd}, Outcome: {outcome}, Tx: {transaction_hash}"
        )
        
    except Exception as e:
        logger.error(f"❌ Error placing bet: {e}")
        import traceback
        traceback.print_exc()
        return BetResult(
            success=False,
            error_message=str(e)
        )