"""
Real market creation functionality for Omen using gnosis_predict_market_tool.
This integrates directly with the existing working blockchain interaction code.
"""
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

# Add gnosis_predict_market_tool to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
gnosis_tool_path = os.path.join(project_root, 'gnosis_predict_market_tool')
sys.path.insert(0, gnosis_tool_path)

# Import from gnosis_predict_market_tool
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

from .types import MarketCreationResult

logger = logging.getLogger(__name__)

def create_omen_market(
    question: str,
    closing_time: datetime,
    category: str,
    initial_funds_usd: str,
    from_private_key: str,
    safe_address: Optional[str] = None,
    collateral_token: str = "wxdai",
    fee_perc: float = OMEN_DEFAULT_MARKET_FEE_PERC,
    language: str = "en",
    outcomes: List[str] = None,
    auto_deposit: bool = True
) -> MarketCreationResult:
    """
    Create a new prediction market on Omen using the real gnosis_predict_market_tool.
    
    Args:
        question: The market question
        closing_time: When the market closes for trading
        category: Market category  
        initial_funds_usd: Initial funding amount
        from_private_key: Private key for transactions
        safe_address: Optional safe address
        collateral_token: Collateral token choice (wxdai, sdai, usdc)
        fee_perc: Market fee percentage
        language: Question language
        outcomes: Market outcomes (defaults to Yes/No)
        auto_deposit: Whether to auto-deposit collateral
        
    Returns:
        MarketCreationResult with success status and details
    """
    try:
        if outcomes is None:
            outcomes = OMEN_BINARY_MARKET_OUTCOMES
                
        logger.info(f"Creating REAL market: {question}")
        logger.info(f"Closing time: {closing_time}")
        logger.info(f"Initial funds: ${initial_funds_usd}")
        
        # Validate inputs
        if not from_private_key:
            return MarketCreationResult(
                success=False,
                error_message="Private key not provided"
            )
        
        # Convert collateral token string to address
        try:
            if collateral_token == "wxdai":
                collateral_token_choice = CollateralTokenChoice.wxdai
            elif collateral_token == "sdai":
                collateral_token_choice = CollateralTokenChoice.sdai  
            elif collateral_token == "usdc":
                collateral_token_choice = CollateralTokenChoice.usdc
            else:
                collateral_token_choice = CollateralTokenChoice.wxdai  # default
                
            collateral_token_address = COLLATERAL_TOKEN_CHOICE_TO_ADDRESS[collateral_token_choice]
        except KeyError:
            return MarketCreationResult(
                success=False,
                error_message=f"Unsupported collateral token: {collateral_token}"
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
        
        # Convert closing time to DatetimeUTC
        if closing_time.tzinfo is None:
            closing_time = closing_time.replace(tzinfo=timezone.utc)
        closing_time_utc = DatetimeUTC.from_datetime(closing_time)
        
        # Create market using the real gnosis_predict_market_tool function
        logger.info("🔗 Creating REAL market using gnosis_predict_market_tool...")
        
        created_market = omen_create_market_tx(
            api_keys=api_keys,
            collateral_token_address=collateral_token_address,
            initial_funds=USD(initial_funds_usd),
            fee_perc=fee_perc,
            question=question,
            closing_time=closing_time_utc,
            category=category,
            language=language,
            outcomes=[OutcomeStr(x) for x in outcomes],
            auto_deposit=auto_deposit,
        )
        
        logger.info(f"✅ Market created successfully! Market: {created_market}")
        
        # Extract market information
        market_id = created_market.market_maker_contract_address_checksummed
        market_url = f"https://aiomen.eth.limo/#{market_id}"
        
        return MarketCreationResult(
            success=True,
            market_id=market_id,
            market_url=market_url,
            transaction_hash=created_market.transaction_receipt.transactionHash.hex() if created_market.transaction_receipt else None,
            raw_output=f"Market created successfully! ID: {market_id}, URL: {market_url}"
        )
        
    except Exception as e:
        logger.error(f"❌ Error creating market: {e}")
        import traceback
        traceback.print_exc()
        return MarketCreationResult(
            success=False,
            error_message=str(e)
        )