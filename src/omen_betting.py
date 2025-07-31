import logging
from typing import Tuple
from .config import Config

logger = logging.getLogger(__name__)


def place_bet(
    market_id: str,
    amount_usd: float,
    outcome: str,
    from_private_key: str,
    safe_address: str = None,
    auto_deposit: bool = True
) -> Tuple[bool, str]:
    """
    Place a bet on an Omen market using direct blockchain interaction.
    
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
        
        # Lazy import blockchain functionality
        try:
            from .blockchain.betting import place_omen_bet
        except ImportError as e:
            logger.error(f"Failed to import blockchain betting module: {e}")
            return False, f"Blockchain betting functionality not available: {e}"
        
        # Use the blockchain module to place bet
        result = place_omen_bet(
            market_id=market_id,
            amount_usd=str(amount_usd),
            outcome=outcome,
            from_private_key=from_private_key,
            safe_address=safe_address,
            auto_deposit=auto_deposit
        )

        if result.success:
            success_msg = f"Bet placed successfully!\nTransaction Hash: {result.transaction_hash}\nMarket ID: {market_id}\nAmount: ${amount_usd}\nOutcome: {outcome}"
            logger.info(success_msg)
            return True, success_msg
        else:
            error_message = f"Failed to place bet: {result.error_message}"
            logger.error(error_message)
            return False, error_message

    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.error(error_message)
        return False, str(e)