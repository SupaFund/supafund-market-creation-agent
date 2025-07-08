import logging
from typing import Tuple
from eth_typing import HexAddress, HexStr
from web3 import Web3

from gnosis_predict_market_tool.prediction_market_agent_tooling.config import APIKeys
from gnosis_predict_market_tool.prediction_market_agent_tooling.gtypes import USD, OutcomeStr, private_key_type
from gnosis_predict_market_tool.prediction_market_agent_tooling.markets.omen.omen import (
    OmenAgentMarket,
    omen_buy_outcome_tx,
)
from gnosis_predict_market_tool.prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import (
    OmenSubgraphHandler,
)

logger = logging.getLogger(__name__)


def build_omen_agent_market(market_id: str) -> OmenAgentMarket:
    """Build an OmenAgentMarket from a market ID."""
    subgraph_handler = OmenSubgraphHandler()
    market_data_model = subgraph_handler.get_omen_market_by_market_id(
        HexAddress(HexStr(market_id))
    )
    market = OmenAgentMarket.from_data_model(market_data_model)
    return market


def place_bet(
    market_id: str,
    amount_usd: float,
    outcome: str,
    from_private_key: str,
    safe_address: str = None,
    auto_deposit: bool = True
) -> Tuple[bool, str]:
    """
    Place a bet on an Omen market.
    
    Args:
        market_id: The market ID to bet on
        amount_usd: The amount to bet in USD
        outcome: The outcome to bet on (e.g., 'Yes' or 'No')
        from_private_key: The private key to use for the bet
        safe_address: Optional safe address to use for the bet
        auto_deposit: Whether to automatically deposit collateral token
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        logger.info(f"Placing bet on market {market_id} for {amount_usd} USD on outcome {outcome}")
        
        # Convert safe_address to checksum format if provided
        safe_address_checksum = (
            Web3.to_checksum_address(safe_address) if safe_address else None
        )
        
        # Build the market object
        market = build_omen_agent_market(market_id)
        
        # Place the bet
        tx_hash = omen_buy_outcome_tx(
            api_keys=APIKeys(
                SAFE_ADDRESS=safe_address_checksum,
                BET_FROM_PRIVATE_KEY=private_key_type(from_private_key),
            ),
            amount=USD(amount_usd),
            market=market,
            outcome=OutcomeStr(outcome),
            auto_deposit=auto_deposit,
        )
        
        logger.info(f"Bet placed successfully. Transaction hash: {tx_hash}")
        return True, f"Bet placed successfully. Transaction hash: {tx_hash}"
        
    except Exception as e:
        error_message = f"Error placing bet: {str(e)}"
        logger.error(error_message)
        return False, error_message