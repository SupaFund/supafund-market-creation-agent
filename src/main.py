from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
import logging
from datetime import datetime, timezone, timedelta

from .supabase_client import get_application_details, check_existing_market, create_market_record, get_market_by_application_id, update_market_record
from .omen_creator import create_omen_market, parse_market_output
from .omen_betting import place_bet
from .market_logger import market_logger

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

class MarketStatusUpdate(BaseModel):
    status: str = Field(..., 
        description="New market status",
        examples=["active", "closed", "resolved"]
    )
    metadata: dict = Field(default_factory=dict, 
        description="Additional metadata for the status update"
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
    
    # Log the incoming request
    market_logger.log_market_request(application_id, {"application_id": application_id})

    # 1. Check if market already exists
    logger.info(f"Checking for existing market for application {application_id}...")
    existing_market = check_existing_market(application_id)
    market_logger.log_duplicate_check(application_id, existing_market)
    
    if existing_market:
        logger.info(f"Market already exists for application {application_id}")
        return {
            "status": "already_exists",
            "message": "Market already exists for this application",
            "application_id": application_id,
            "existing_market": {
                "market_id": existing_market.get("market_id"),
                "market_url": existing_market.get("market_url"),
                "created_at": existing_market.get("created_at"),
                "status": existing_market.get("status")
            }
        }

    # 2. Fetch application details from Supabase
    logger.info(f"Fetching details for application {application_id}...")
    application_details = get_application_details(application_id)

    if not application_details:
        logger.error(f"Application with id {application_id} not found.")
        raise HTTPException(
            status_code=404,
            detail=f"Application with id {application_id} not found.",
        )

    # 3. Trigger Omen market creation
    logger.info(f"Triggering Omen market creation for application {application_id}...")
    market_logger.log_market_creation_start(application_id, application_details)
    
    success, message = create_omen_market(application_details)

    if not success:
        logger.error(f"Failed to create market for application {application_id}: {message}")
        market_logger.log_market_creation_failure(application_id, str(message), application_details)
        
        # Create a failed record in the database to track the attempt
        try:
            market_data = {
                "market_id": f"FAILED_{application_id}",
                "market_title": f"FAILED: {application_details.get('project_name', 'Unknown')}",
                "market_question": f"Failed to create market for {application_details.get('project_name', 'Unknown')}",
                "omen_creation_output": str(message),
                "metadata": {"error": str(message), "application_details": application_details}
            }
            record_created = create_market_record(application_id, market_data)
            market_logger.log_database_operation("create_failed_record", application_id, record_created, market_data)
        except Exception as record_error:
            logger.error(f"Failed to create failure record: {record_error}")
            market_logger.log_error("database", f"Failed to create failure record: {record_error}", application_id)
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create market: {message}",
        )

    # 4. Parse market information and create database record
    logger.info(f"Parsing market creation output...")
    try:
        market_info = parse_market_output(message)
        market_data = {
            "market_id": market_info.get("market_id", ""),
            "market_title": market_info.get("market_title", ""),
            "market_url": market_info.get("market_url", ""),
            "market_question": market_info.get("market_question", ""),
            "closing_time": market_info.get("closing_time"),
            "initial_funds_usd": market_info.get("initial_funds_usd", 0.01),
            "omen_creation_output": message,
            "metadata": {
                "application_details": application_details,
                "creation_timestamp": market_info.get("creation_timestamp")
            }
        }
        
        # Log successful market creation
        market_logger.log_market_creation_success(application_id, market_info, message)
        
        # Create market record in database
        record_created = create_market_record(application_id, market_data)
        market_logger.log_database_operation("create_record", application_id, record_created, market_data)
        
        if not record_created:
            logger.warning(f"Failed to create market record for application {application_id}, but market was created successfully")
        
    except Exception as e:
        logger.error(f"Failed to parse market output or create record: {e}")
        market_logger.log_error("parsing", f"Failed to parse market output: {e}", application_id, raw_output=message)
        # Still return success since the market was created, just couldn't parse/record it

    logger.info(f"Successfully created market for application {application_id}.")
    return {
        "status": "success",
        "message": "Market creation process completed successfully.",
        "application_id": application_id,
        "market_info": market_info if 'market_info' in locals() else None,
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


@app.get("/market-status/{application_id}", tags=["Market Management"])
async def get_market_status(application_id: str):
    """
    Get the current status of a market by application ID.
    """
    try:
        market = get_market_by_application_id(application_id)
        
        if not market:
            raise HTTPException(
                status_code=404,
                detail=f"No market found for application {application_id}"
            )
        
        return {
            "status": "success",
            "application_id": application_id,
            "market": market
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market status for {application_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving market status: {str(e)}"
        )


@app.put("/market-status/{application_id}", tags=["Market Management"])
async def update_market_status(application_id: str, update_request: MarketStatusUpdate):
    """
    Update the status of a market by application ID.
    """
    try:
        # Check if market exists
        existing_market = get_market_by_application_id(application_id)
        
        if not existing_market:
            raise HTTPException(
                status_code=404,
                detail=f"No market found for application {application_id}"
            )
        
        # Update the market record
        update_data = {
            "status": update_request.status,
            "metadata": {
                **existing_market.get("metadata", {}),
                **update_request.metadata,
                "status_updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        success = update_market_record(application_id, update_data)
        market_logger.log_database_operation("update_status", application_id, success, update_data)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update market status"
            )
        
        return {
            "status": "success",
            "message": "Market status updated successfully",
            "application_id": application_id,
            "new_status": update_request.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating market status for {application_id}: {e}")
        market_logger.log_error("status_update", f"Failed to update status: {e}", application_id)
        raise HTTPException(
            status_code=500,
            detail=f"Error updating market status: {str(e)}"
        )


@app.get("/markets", tags=["Market Management"])
async def list_markets(status: str = None, limit: int = 100):
    """
    List all markets, optionally filtered by status.
    """
    try:
        from .supabase_client import get_all_markets
        
        markets = get_all_markets(status=status, limit=limit)
        
        return {
            "status": "success",
            "count": len(markets),
            "markets": markets,
            "filter": {"status": status, "limit": limit}
        }
        
    except Exception as e:
        logger.error(f"Error listing markets: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing markets: {str(e)}"
        )


@app.get("/market-logs/{application_id}", tags=["Market Management"])
async def get_market_logs(application_id: str):
    """
    Get detailed logs for a specific market/application.
    """
    try:
        logs = market_logger.get_market_logs(application_id)
        
        return {
            "status": "success",
            "application_id": application_id,
            "log_count": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Error getting market logs for {application_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving market logs: {str(e)}"
        )


@app.get("/recent-logs", tags=["Market Management"])
async def get_recent_logs(hours: int = 24):
    """
    Get recent market operation logs within specified hours.
    """
    try:
        logs = market_logger.get_recent_logs(hours=hours)
        
        return {
            "status": "success",
            "hours": hours,
            "log_count": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Error getting recent logs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving recent logs: {str(e)}"
        )

