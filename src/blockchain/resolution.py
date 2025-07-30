"""
Real market resolution functionality for Omen using gnosis_predict_market_tool.
This integrates directly with the existing working blockchain resolution code.
"""
import logging
import sys
import os
from typing import Optional, Tuple
from datetime import datetime, timezone

# Add gnosis_predict_market_tool to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
gnosis_tool_path = os.path.join(project_root, 'gnosis_predict_market_tool')
sys.path.insert(0, gnosis_tool_path)

# Import from gnosis_predict_market_tool
from prediction_market_agent_tooling.config import APIKeys
from prediction_market_agent_tooling.gtypes import private_key_type, xDai
from prediction_market_agent_tooling.markets.data_models import Resolution
from prediction_market_agent_tooling.markets.omen.omen import OmenAgentMarket
from prediction_market_agent_tooling.markets.omen.omen_subgraph_handler import OmenSubgraphHandler
from prediction_market_agent_tooling.markets.omen.omen_resolving import (
    omen_submit_answer_market_tx,
    omen_submit_invalid_answer_market_tx,
    omen_resolve_market_tx,
)
from eth_typing import HexAddress, HexStr
from web3 import Web3

from .types import ResolutionResult

logger = logging.getLogger(__name__)

def submit_market_answer(
    market_id: str,
    outcome: str,
    confidence: float,
    reasoning: str,
    from_private_key: str,
    bond_amount_xdai: float = 0.01,
    safe_address: Optional[str] = None
) -> ResolutionResult:
    """
    Submit an answer to an Omen market using the real gnosis_predict_market_tool.
    
    Args:
        market_id: The market contract address
        outcome: The outcome to submit ("Yes", "No", or "Invalid")
        confidence: Confidence level (0.0 to 1.0)
        reasoning: Reasoning for the outcome
        from_private_key: Private key for transactions
        bond_amount_xdai: Bond amount in xDai (default 0.01)
        safe_address: Optional safe address
        
    Returns:
        ResolutionResult with success status and details
    """
    try:
        logger.info(f"Submitting REAL answer for market {market_id}")
        logger.info(f"Outcome: {outcome}, Confidence: {confidence}")
        
        # Validate inputs
        if not from_private_key:
            return ResolutionResult(
                success=False,
                error_message="Private key not provided"
            )
        
        if outcome not in ["Yes", "No", "Invalid"]:
            return ResolutionResult(
                success=False,
                error_message=f"Invalid outcome: {outcome}. Must be 'Yes', 'No', or 'Invalid'"
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
        market = build_omen_market_from_id(market_id)
        
        # Check if market is closed (required for answer submission)
        if market.is_open:
            error_msg = f"Market {market_id} is still open. Markets must be closed before submitting answers. Market closes at: {market.close_time.isoformat()}"
            logger.error(f"❌ {error_msg}")
            return ResolutionResult(
                success=False,
                market_id=market_id,
                error_message=error_msg
            )
        
        logger.info(f"✅ Market is closed (closed at: {market.close_time.isoformat()})")
        
        # Check if answer was already submitted (for information, not blocking)
        if market.question.currentAnswer is not None:
            # Handle both string and HexBytes types for currentAnswer
            if isinstance(market.question.currentAnswer, str):
                answer_hex = market.question.currentAnswer
            else:
                answer_hex = market.question.currentAnswer.hex()
            
            logger.info(f"ℹ️  Market {market_id} already has an answer: {answer_hex}")
            logger.info(f"🔥 Attempting to challenge existing answer with bond: {bond_amount_xdai} xDai")
            logger.info(f"⚠️  Note: Reality.eth will validate if your bond is sufficient to challenge")
        else:
            logger.info(f"📝 Submitting first answer to market {market_id}")
        
        # Create bond amount
        bond = xDai(bond_amount_xdai)
        
        # Submit answer using the real gnosis_predict_market_tool function
        logger.info("🔗 Submitting REAL answer using gnosis_predict_market_tool...")
        
        if outcome == "Invalid":
            # Submit invalid answer
            omen_submit_invalid_answer_market_tx(
                api_keys=api_keys,
                market=market,
                bond=bond,
            )
            
            logger.info(f"✅ Invalid answer submitted successfully for market {market_id}")
            
        else:
            # Submit regular answer (Yes/No)
            resolution = Resolution(
                outcome=outcome,
                outcome_source=f"Manual submission: {reasoning[:100]}...",
                invalid=False,
                confidence=confidence
            )
            
            omen_submit_answer_market_tx(
                api_keys=api_keys,
                market=market,
                resolution=resolution,
                bond=bond,
            )
            
            logger.info(f"✅ Answer '{outcome}' submitted successfully for market {market_id}")
        
        # Determine if this was a challenge or first answer
        action_type = "challenged" if market.question.currentAnswer is not None else "submitted"
        
        return ResolutionResult(
            success=True,
            market_id=market_id,
            outcome=outcome,
            confidence=confidence,
            reasoning=reasoning,
            bond_amount=bond_amount_xdai,
            raw_output=f"Answer {action_type} successfully! Outcome: {outcome}, Bond: {bond_amount_xdai} xDai"
        )
        
    except Exception as e:
        logger.error(f"❌ Error submitting answer: {e}")
        import traceback
        traceback.print_exc()
        return ResolutionResult(
            success=False,
            market_id=market_id,
            error_message=str(e)
        )

def resolve_market_final(
    market_id: str,
    from_private_key: str,
    safe_address: Optional[str] = None
) -> ResolutionResult:
    """
    Finalize market resolution after the answer period using gnosis_predict_market_tool.
    
    Args:
        market_id: The market contract address
        from_private_key: Private key for transactions
        safe_address: Optional safe address
        
    Returns:
        ResolutionResult with success status and details
    """
    try:
        logger.info(f"Finalizing REAL resolution for market {market_id}")
        
        # Validate inputs
        if not from_private_key:
            return ResolutionResult(
                success=False,
                error_message="Private key not provided"
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
        market = build_omen_market_from_id(market_id)
        
        # Check if market has an answer (required for finalization)
        if market.question.currentAnswer is None:
            error_msg = f"Market {market_id} does not have an answer yet. Submit an answer first using /submit-answer endpoint."
            logger.error(f"❌ {error_msg}")
            return ResolutionResult(
                success=False,
                market_id=market_id,
                error_message=error_msg
            )
        
        # Check if market is already resolved
        if market.condition and hasattr(market.condition, 'resolved') and market.condition.resolved:
            error_msg = f"Market {market_id} is already resolved. No need to finalize again."
            logger.error(f"❌ {error_msg}")
            return ResolutionResult(
                success=False,
                market_id=market_id,
                error_message=error_msg
            )
        
        # Handle both string and HexBytes types for currentAnswer
        if isinstance(market.question.currentAnswer, str):
            answer_hex = market.question.currentAnswer
        else:
            answer_hex = market.question.currentAnswer.hex()
        
        logger.info(f"✅ Market has answer: {answer_hex}")
        
        # Finalize market resolution using the real gnosis_predict_market_tool function
        logger.info("🔗 Finalizing REAL market resolution using gnosis_predict_market_tool...")
        
        omen_resolve_market_tx(
            api_keys=api_keys,
            market=market,
        )
        
        logger.info(f"✅ Market {market_id} resolution finalized successfully!")
        
        return ResolutionResult(
            success=True,
            market_id=market_id,
            raw_output=f"Market resolution finalized successfully!"
        )
        
    except Exception as e:
        logger.error(f"❌ Error finalizing market resolution: {e}")
        import traceback
        traceback.print_exc()
        return ResolutionResult(
            success=False,
            market_id=market_id,
            error_message=str(e)
        )

def build_omen_market_from_id(market_id: str):
    """Build OmenMarket from market ID using subgraph."""
    subgraph_handler = OmenSubgraphHandler()
    market_data_model = subgraph_handler.get_omen_market_by_market_id(
        HexAddress(HexStr(market_id))
    )
    if not market_data_model:
        raise ValueError(f"Market {market_id} not found")
    
    # Return the OmenMarket data model directly for resolution functions
    return market_data_model

def check_market_resolution_status(
    market_id: str,
    from_private_key: str
) -> Tuple[bool, str, dict]:
    """
    Check the current resolution status of a market.
    
    Args:
        market_id: The market contract address
        from_private_key: Private key for authentication
        
    Returns:
        Tuple of (success: bool, message: str, status_info: dict)
    """
    try:
        logger.info(f"Checking resolution status for market {market_id}")
        
        # Setup API keys for gnosis_predict_market_tool
        from ..config import Config
        
        api_keys = APIKeys(
            BET_FROM_PRIVATE_KEY=private_key_type(from_private_key),
            GRAPH_API_KEY=Config.GRAPH_API_KEY,
        )
        
        # Get market details from subgraph
        market = build_omen_market_from_id(market_id)
        
        # Handle currentAnswer type for status display
        current_answer_hex = None
        if market.question.currentAnswer is not None:
            if isinstance(market.question.currentAnswer, str):
                current_answer_hex = market.question.currentAnswer
            else:
                current_answer_hex = market.question.currentAnswer.hex()
        
        # Check market status
        status_info = {
            "market_id": market_id,
            "is_closed": not market.is_open,
            "closing_time": market.close_time.isoformat() if market.close_time else None,
            "has_answer": market.question.currentAnswer is not None,
            "current_answer": current_answer_hex,
            "is_resolved": market.condition and hasattr(market.condition, 'resolved') and market.condition.resolved,
            "needs_finalization": market.question.currentAnswer is not None and not (market.condition and hasattr(market.condition, 'resolved') and market.condition.resolved),
        }
        
        message = f"Market status retrieved successfully"
        logger.info(f"✅ {message}: {status_info}")
        
        return True, message, status_info
        
    except Exception as e:
        error_msg = f"Error checking market resolution status: {e}"
        logger.error(f"❌ {error_msg}")
        return False, error_msg, {}