from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
import logging

from .supabase_client import get_application_details
from .omen_creator import create_omen_market
from .omen_betting import place_bet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Supafund Market Creation Agent",
    description="An agent to create prediction markets on Omen for Supafund applications.",
    version="1.0.0"
)

class MarketCreationRequest(BaseModel):
    application_id: str = Field(..., 
        description="The UUID of the application in Supafund.",
        examples=["a1b2c3d4-e5f6-7890-1234-567890abcdef"]
    )

class BetRequest(BaseModel):
    market_id: str = Field(..., 
        description="The market ID to bet on.",
        examples=["0x86376012a5185f484ec33429cadfa00a8052d9d4"]
    )
    amount_usd: float = Field(..., 
        description="The amount to bet in USD.",
        examples=[0.01]
    )
    outcome: str = Field(..., 
        description="The outcome to bet on (e.g., 'Yes' or 'No').",
        examples=["Yes"]
    )
    from_private_key: str = Field(..., 
        description="The private key to use for the bet."
    )
    safe_address: str = Field(None, 
        description="Optional safe address to use for the bet."
    )
    auto_deposit: bool = Field(True, 
        description="Whether to automatically deposit collateral token."
    )

@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for health checks.
    """
    return {"status": "ok", "message": "Supafund Market Creation Agent is running."}


@app.post("/create-market", tags=["Market Creation"])
async def handle_create_market(request: MarketCreationRequest):
    """
    Receives a request to create a prediction market for a given application.
    """
    application_id = request.application_id
    logger.info(f"Received request to create market for application_id: {application_id}")

    # 1. Fetch application details from Supabase
    logger.info(f"Fetching details for application {application_id}...")
    application_details = get_application_details(application_id)

    if not application_details:
        logger.error(f"Application with id {application_id} not found.")
        raise HTTPException(
            status_code=404,
            detail=f"Application with id {application_id} not found.",
        )

    # 2. Trigger Omen market creation
    logger.info(f"Triggering Omen market creation for application {application_id}...")
    success, message = create_omen_market(application_details)

    if not success:
        logger.error(f"Failed to create market for application {application_id}: {message}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create market: {message}",
        )

    logger.info(f"Successfully created market for application {application_id}.")
    return {
        "status": "success",
        "message": "Market creation process initiated successfully.",
        "application_id": application_id,
        "omen_creation_output": message,
    }


@app.post("/bet", tags=["Betting"])
async def handle_bet(request: BetRequest):
    """
    Places a bet on a specified market.
    """
    market_id = request.market_id
    amount_usd = request.amount_usd
    outcome = request.outcome
    from_private_key = request.from_private_key
    safe_address = request.safe_address
    auto_deposit = request.auto_deposit
    
    logger.info(f"Received bet request for market {market_id}, amount: {amount_usd} USD, outcome: {outcome}")

    try:
        # Place the bet using the omen betting module
        success, message = place_bet(
            market_id=market_id,
            amount_usd=amount_usd,
            outcome=outcome,
            from_private_key=from_private_key,
            safe_address=safe_address,
            auto_deposit=auto_deposit
        )

        if not success:
            logger.error(f"Failed to place bet on market {market_id}: {message}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to place bet: {message}",
            )

        logger.info(f"Successfully placed bet on market {market_id}.")
        return {
            "status": "success",
            "message": "Bet placed successfully.",
            "market_id": market_id,
            "amount_usd": amount_usd,
            "outcome": outcome,
            "transaction_output": message,
        }

    except Exception as e:
        logger.error(f"Error placing bet on market {market_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error placing bet: {str(e)}",
        )

