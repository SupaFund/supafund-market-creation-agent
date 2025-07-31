from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel, Field
import logging
from datetime import datetime, timezone, timedelta
import asyncio

from .supabase_client import get_application_details, check_existing_market, create_market_record, get_market_by_application_id, update_market_record
from .omen_creator import create_omen_market, parse_market_output
from .omen_betting import place_bet
from .vercel_logger import market_logger
from .daily_scheduler import run_daily_resolution
from .resolution_logger import resolution_logger

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
        # Generate the question that was used for market creation
        project_name = application_details.get("project_name", "Unknown Project")
        program_name = application_details.get("program_name", "Unknown Program")
        application_id = application_details.get("application_id", "")
        
        market_question = f'Will project "{project_name}" be approved for the "{program_name}" program? [Supafund App: {application_id}]'
        
        market_info = parse_market_output(message)
        
        # Ensure we have the question in the parsed info
        if not market_info.get("market_question"):
            market_info["market_question"] = market_question
            
        # Generate title from question if not present
        if not market_info.get("market_title"):
            market_info["market_title"] = market_question[:100] + "..." if len(market_question) > 100 else market_question
        
        market_data = {
            "market_id": market_info.get("market_id", ""),
            "market_title": market_info.get("market_title", ""),
            "market_url": market_info.get("market_url", ""),
            "market_question": market_info.get("market_question", ""),
            "closing_time": market_info.get("closing_time"),
            "initial_funds_usd": market_info.get("initial_funds_usd", 0.01),
            "omen_creation_output": str(message) if hasattr(message, '__dict__') else message,
            "metadata": {
                "application_details": application_details,
                "creation_timestamp": market_info.get("creation_timestamp"),
                "transaction_hash": market_info.get("transaction_hash")
            }
        }
        
        # Log successful market creation
        market_logger.log_market_creation_success(application_id, market_info, str(message) if hasattr(message, '__dict__') else message)
        
        # Create market record in database
        record_created = create_market_record(application_id, market_data)
        market_logger.log_database_operation("create_record", application_id, record_created, market_data)
        
        if not record_created:
            logger.warning(f"Failed to create market record for application {application_id}, but market was created successfully")
        
    except Exception as e:
        logger.error(f"Failed to parse market output or create record: {e}")
        market_logger.log_error("parsing", f"Failed to parse market output: {e}", application_id, raw_output=str(message) if hasattr(message, '__dict__') else message)
        # Still return success since the market was created, just couldn't parse/record it

    logger.info(f"Successfully created market for application {application_id}.")
    return {
        "status": "success",
        "message": "Market creation process completed successfully.",
        "application_id": application_id,
        "market_info": market_info if 'market_info' in locals() else None,
        "omen_creation_output": str(message) if hasattr(message, '__dict__') else message,
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

        # Update market record in database with betting information
        try:
            from datetime import datetime, timezone
            
            # Get current market record to preserve existing metadata
            existing_market = None
            from .supabase_client import get_supabase_client
            supabase = get_supabase_client()
            try:
                market_response = supabase.table("prediction_markets").select("*").eq("market_id", market_id).execute()
                if market_response.data:
                    existing_market = market_response.data[0]
            except Exception as e:
                logger.warning(f"Could not retrieve existing market record: {e}")
            
            # Prepare betting metadata
            bet_info = {
                "amount_usd": amount_usd,
                "outcome": outcome,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transaction_output": message
            }
            
            # Update market metadata with betting info
            if existing_market:
                current_metadata = existing_market.get("metadata", {})
                bets_list = current_metadata.get("bets", [])
                bets_list.append(bet_info)
                current_metadata["bets"] = bets_list
                current_metadata["last_bet_timestamp"] = bet_info["timestamp"]
                
                # Update the market record
                update_result = supabase.table("prediction_markets").update({
                    "metadata": current_metadata,
                    "status": "active"  # Mark as active when bets are placed
                }).eq("market_id", market_id).execute()
                
                if update_result.data:
                    logger.info(f"Successfully updated market record with betting info for market {market_id}")
                else:
                    logger.warning(f"Failed to update market record for bet on market {market_id}")
            else:
                logger.warning(f"Could not find market record for market {market_id} to update with betting info")
                
        except Exception as e:
            logger.error(f"Error updating market record with betting info: {e}")
            # Don't fail the entire request for database update issues

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


# New Market Resolution System Endpoints

@app.post("/run-daily-resolution", tags=["Market Resolution"])
async def trigger_daily_resolution(background_tasks: BackgroundTasks):
    """
    Manually trigger the daily market resolution cycle.
    This runs in the background to avoid request timeout.
    """
    try:
        # Run the resolution cycle in the background
        background_tasks.add_task(run_daily_resolution)
        
        return {
            "status": "started",
            "message": "Daily resolution cycle started in background",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting daily resolution: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error starting daily resolution: {str(e)}"
        )


@app.get("/resolution-status", tags=["Market Resolution"])
async def get_resolution_status():
    """
    Get the current status and recent activity of the resolution system.
    """
    try:
        # Get recent logs from resolution logger
        recent_errors = resolution_logger.get_recent_errors(hours=24)
        recent_operations = resolution_logger.get_operation_logs()
        
        # Count operations by status
        status_counts = {}
        for op in recent_operations:
            status = op.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Get markets by status from database
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        markets_by_status = {}
        for status in ["created", "active", "resolution_submitted", "resolved"]:
            result = supabase.table("prediction_markets").select("id").eq("status", status).execute()
            markets_by_status[status] = len(result.data) if result.data else 0
        
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recent_operations": {
                "total": len(recent_operations),
                "by_status": status_counts,
            },
            "recent_errors": {
                "count": len(recent_errors),
                "errors": recent_errors[:5]  # Show only first 5 errors
            },
            "markets_by_status": markets_by_status,
            "system_health": "healthy" if len(recent_errors) == 0 and status_counts.get("failed", 0) < 5 else "needs_attention"
        }
        
    except Exception as e:
        logger.error(f"Error getting resolution status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting resolution status: {str(e)}"
        )


@app.get("/resolution-logs", tags=["Market Resolution"])
async def get_resolution_logs(market_id: str = None, operation: str = None, limit: int = 100):
    """
    Get resolution operation logs, optionally filtered by market ID or operation type.
    
    Args:
        market_id: Filter logs for specific market
        operation: Filter by operation type (monitor, research, resolve, finalize)
        limit: Maximum number of logs to return
    """
    try:
        logs = resolution_logger.get_operation_logs(market_id=market_id, operation=operation)
        
        # Limit results
        if len(logs) > limit:
            logs = logs[-limit:]  # Get most recent logs
        
        return {
            "status": "success",
            "filters": {
                "market_id": market_id,
                "operation": operation,
                "limit": limit
            },
            "log_count": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Error getting resolution logs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting resolution logs: {str(e)}"
        )


@app.get("/resolution-summary", tags=["Market Resolution"])
async def get_resolution_summary():
    """
    Get a summary of resolution operations and generate daily summary.
    """
    try:
        summary = resolution_logger.generate_daily_summary()
        
        return {
            "status": "success",
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error generating resolution summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating resolution summary: {str(e)}"
        )


class ResearchMarketRequest(BaseModel):
    market_id: str = Field(..., description="Market ID to research")
    application_id: str = Field(..., description="Application ID associated with the market")
    funding_program_name: str = Field(..., description="Name of the funding program")
    funding_program_twitter: str = Field(None, description="Twitter URL of the funding program")

class SubmitAnswerRequest(BaseModel):
    market_id: str = Field(..., 
        description="The market ID to submit answer for.",
        examples=["0x86376012a5185f484ec33429cadfa00a8052d9d4"]
    )
    outcome: str = Field(..., 
        description="The outcome to submit (Yes, No, or Invalid).",
        examples=["Yes"]
    )
    confidence: float = Field(..., 
        description="Confidence level (0.0 to 1.0).",
        examples=[0.85]
    )
    reasoning: str = Field(..., 
        description="Reasoning for the outcome.",
        examples=["Based on official announcement from the project team."]
    )
    from_private_key: str = Field(..., 
        description="The private key to use for the transaction."
    )
    bond_amount_xdai: float = Field(0.01, 
        description="Bond amount in xDai (default 0.01).",
        examples=[0.01]
    )
    safe_address: str = Field(None, 
        description="Optional safe address to use for the transaction."
    )

class FinalizeResolutionRequest(BaseModel):
    market_id: str = Field(..., 
        description="The market ID to finalize resolution for.",
        examples=["0x86376012a5185f484ec33429cadfa00a8052d9d4"]
    )
    from_private_key: str = Field(..., 
        description="The private key to use for the transaction."
    )
    safe_address: str = Field(None, 
        description="Optional safe address to use for the transaction."
    )


@app.post("/research-market", tags=["Market Resolution"])
async def research_market_resolution(request: ResearchMarketRequest):
    """
    Manually trigger research for a specific market resolution.
    This can be useful for testing or manual intervention.
    """
    try:
        from .market_monitor import MarketStatus
        from .resolution_researcher import GrokResolutionResearcher
        
        # Create market status object
        market_status = MarketStatus(
            market_id=request.market_id,
            title=f"Manual research for {request.market_id}",
            closing_time=datetime.now(timezone.utc),
            is_closed=True,
            is_resolved=False,
            application_id=request.application_id,
            funding_program_name=request.funding_program_name,
            funding_program_twitter=request.funding_program_twitter
        )
        
        # Initialize researcher
        researcher = GrokResolutionResearcher()
        
        # Perform research
        result = researcher.research_market_resolution(market_status)
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to get research result from Grok API"
            )
        
        # Log the research result
        resolution_logger.log_resolution_research_result(
            request.market_id,
            request.application_id,
            result.outcome,
            result.confidence,
            result.reasoning,
            result.sources
        )
        
        return {
            "status": "success",
            "market_id": request.market_id,
            "research_result": {
                "outcome": result.outcome,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
                "sources": result.sources,
                "twitter_handles_searched": result.twitter_handles_searched
            }
        }
        
    except Exception as e:
        logger.error(f"Error researching market {request.market_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error researching market: {str(e)}"
        )


@app.post("/research-and-submit-answer", tags=["Market Resolution"])
async def research_and_submit_market_answer(request: ResearchMarketRequest):
    """
    一体化端点：使用Grok研究市场并自动提交答案到Reality.eth
    
    This endpoint combines the research and submission process:
    1. Uses Grok API with Twitter handles from funding program 
    2. Analyzes if project was accepted by funding program
    3. Automatically submits answer to Reality.eth with 0.01 xDai bond
    4. Returns both research results and blockchain submission status in JSON
    """
    try:
        from .market_monitor import MarketStatus
        from .resolution_researcher import GrokResolutionResearcher
        from .config import Config
        
        logger.info(f"Starting integrated research and submission for market {request.market_id}")
        
        # Step 1: Create market status object for research
        market_status = MarketStatus(
            market_id=request.market_id,
            title=f"Research and submit for {request.market_id}",
            closing_time=datetime.now(timezone.utc),
            is_closed=True,
            is_resolved=False,
            application_id=request.application_id,
            funding_program_name=request.funding_program_name,
            funding_program_twitter=request.funding_program_twitter
        )
        
        # Step 2: Initialize Grok researcher
        researcher = GrokResolutionResearcher()
        
        # Step 3: Perform Grok research with Twitter handles
        logger.info(f"🔍 Researching market using Grok API with funding program Twitter: {request.funding_program_twitter}")
        research_result = researcher.research_market_resolution(market_status)
        
        if not research_result:
            raise HTTPException(
                status_code=500,
                detail="Failed to get research result from Grok API"
            )
        
        logger.info(f"📊 Grok research completed: {research_result.outcome} (confidence: {research_result.confidence})")
        
        # Step 4: Log the research result
        resolution_logger.log_resolution_research_result(
            request.market_id,
            request.application_id,
            research_result.outcome,
            research_result.confidence,
            research_result.reasoning,
            research_result.sources
        )
        
        # Step 5: Convert "Invalid" to "No" for blockchain submission
        # In funding program context: no evidence of acceptance = "No" 
        blockchain_outcome = research_result.outcome
        if research_result.outcome == "Invalid":
            blockchain_outcome = "No"
            logger.info(f"🔄 Converting 'Invalid' research result to 'No' for blockchain submission")
            logger.info(f"💡 Reasoning: In funding context, lack of evidence means project was not accepted")
        
        # Step 6: Auto-submit answer to Reality.eth with default 0.01 xDai bond
        logger.info(f"🔗 Auto-submitting answer to Reality.eth: {blockchain_outcome}")
        
        # Lazy import blockchain functionality
        try:
            from .blockchain.resolution import submit_market_answer
        except ImportError as e:
            logger.error(f"Failed to import blockchain module: {e}")
            return {
                "success": False,
                "error": f"Blockchain functionality not available: {e}",
                "research_result": research_result.dict()
            }
        
        submission_result = submit_market_answer(
            market_id=request.market_id,
            outcome=blockchain_outcome,  # Use converted outcome
            confidence=research_result.confidence,
            reasoning=f"[Converted from Invalid to No] {research_result.reasoning}",
            from_private_key=Config.OMEN_PRIVATE_KEY,
            bond_amount_xdai=0.01,  # Default bond amount as requested
            safe_address=None
        )
        
        # Step 6: Prepare comprehensive JSON response
        response_data = {
            "status": "success",
            "market_id": request.market_id,
            "funding_program": request.funding_program_name,
            "funding_program_twitter": request.funding_program_twitter,
            "research_result": {
                "outcome": research_result.outcome,
                "confidence": research_result.confidence,
                "reasoning": research_result.reasoning,
                "sources": research_result.sources,
                "twitter_handles_searched": research_result.twitter_handles_searched
            },
            "blockchain_submission": {
                "success": submission_result.success,
                "bond_amount_xdai": 0.01,
                "transaction_output": submission_result.raw_output,
                "error_message": submission_result.error_message if not submission_result.success else None
            }
        }
        
        # Step 7: Update database with research and resolution results
        try:
            from .supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Get existing market record
            market_response = supabase.table("prediction_markets").select("*").eq("market_id", request.market_id).execute()
            if market_response.data:
                existing_market = market_response.data[0]
                current_metadata = existing_market.get("metadata", {})
                
                # Add research and resolution info to metadata
                resolution_info = {
                    "research_timestamp": datetime.now(timezone.utc).isoformat(),
                    "grok_research_result": {
                        "outcome": research_result.outcome,
                        "blockchain_outcome": blockchain_outcome,  # The converted outcome
                        "confidence": research_result.confidence,
                        "reasoning": research_result.reasoning,
                        "sources": research_result.sources,
                        "twitter_handles_searched": research_result.twitter_handles_searched
                    },
                    "blockchain_submission": {
                        "success": submission_result.success,
                        "bond_amount_xdai": 0.01,
                        "transaction_output": submission_result.raw_output,
                        "error_message": submission_result.error_message if not submission_result.success else None
                    }
                }
                
                current_metadata["resolution_info"] = resolution_info
                
                # Update market status based on resolution success
                new_status = "resolution_submitted" if submission_result.success else "resolution_failed"
                
                # Update the database record
                update_result = supabase.table("prediction_markets").update({
                    "status": new_status,
                    "metadata": current_metadata
                }).eq("market_id", request.market_id).execute()
                
                if update_result.data:
                    logger.info(f"Successfully updated market record with resolution info for market {request.market_id}")
                else:
                    logger.warning(f"Failed to update market record for resolution of market {request.market_id}")
            else:
                logger.warning(f"Could not find market record for market {request.market_id} to update with resolution info")
                
        except Exception as e:
            logger.error(f"Error updating database with resolution info: {e}")
            # Don't fail the entire request for database update issues
        
        # Log final status
        if submission_result.success:
            logger.info(f"✅ Integrated research and submission completed successfully for market {request.market_id}")
        else:
            logger.error(f"❌ Blockchain submission failed: {submission_result.error_message}")
            # Don't raise exception - return partial success with research results
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error in integrated research and submission for market {request.market_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in research and submission: {str(e)}"
        )


@app.post("/submit-answer", tags=["Market Resolution"])
async def submit_market_answer_endpoint(request: SubmitAnswerRequest):
    """
    Submit an answer to a prediction market (Yes/No/Invalid).
    This is the first step in market resolution - submitting an answer with a bond.
    After submission, there's a waiting period before the market can be finalized.
    """
    try:
        logger.info(f"Received answer submission request for market {request.market_id}")
        logger.info(f"Outcome: {request.outcome}, Confidence: {request.confidence}")
        
        # Submit the answer using the real blockchain resolution module
        # Lazy import blockchain functionality
        try:
            from .blockchain.resolution import submit_market_answer
        except ImportError as e:
            logger.error(f"Failed to import blockchain module: {e}")
            return {
                "success": False,
                "error": f"Blockchain functionality not available: {e}"
            }
        
        result = submit_market_answer(
            market_id=request.market_id,
            outcome=request.outcome,
            confidence=request.confidence,
            reasoning=request.reasoning,
            from_private_key=request.from_private_key,
            bond_amount_xdai=request.bond_amount_xdai,
            safe_address=request.safe_address
        )
        
        if not result.success:
            logger.error(f"Failed to submit answer for market {request.market_id}: {result.error_message}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to submit answer: {result.error_message}",
            )
        
        # Update database with answer submission info
        try:
            from .supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Get existing market record
            market_response = supabase.table("prediction_markets").select("*").eq("market_id", request.market_id).execute()
            if market_response.data:
                existing_market = market_response.data[0]
                current_metadata = existing_market.get("metadata", {})
                
                # Add answer submission info to metadata
                answer_submission_info = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "outcome": request.outcome,
                    "confidence": request.confidence,
                    "reasoning": request.reasoning,
                    "bond_amount_xdai": request.bond_amount_xdai,
                    "transaction_output": result.raw_output
                }
                
                current_metadata["answer_submission"] = answer_submission_info
                
                # Update the database record
                update_result = supabase.table("prediction_markets").update({
                    "status": "resolution_submitted",
                    "metadata": current_metadata
                }).eq("market_id", request.market_id).execute()
                
                if update_result.data:
                    logger.info(f"Successfully updated market record with answer submission for market {request.market_id}")
                else:
                    logger.warning(f"Failed to update market record for answer submission to market {request.market_id}")
            else:
                logger.warning(f"Could not find market record for market {request.market_id} to update with answer submission")
                
        except Exception as e:
            logger.error(f"Error updating database with answer submission info: {e}")
            # Don't fail the entire request for database update issues
        
        logger.info(f"Successfully submitted answer for market {request.market_id}")
        return {
            "status": "success",
            "message": "Answer submitted successfully",
            "market_id": request.market_id,
            "outcome": request.outcome,
            "confidence": request.confidence,
            "bond_amount_xdai": request.bond_amount_xdai,
            "transaction_output": result.raw_output,
        }
        
    except Exception as e:
        logger.error(f"Error submitting answer for market {request.market_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting answer: {str(e)}",
        )


@app.post("/finalize-resolution", tags=["Market Resolution"])
async def finalize_market_resolution_endpoint(request: FinalizeResolutionRequest):
    """
    Finalize a market resolution after the answer period has ended.
    This is the second step in market resolution - finalizing the market after 
    the answer has been submitted and the waiting period has passed.
    """
    try:
        logger.info(f"Received finalization request for market {request.market_id}")
        
        # Finalize the market resolution using the real blockchain resolution module
        # Lazy import blockchain functionality
        try:
            from .blockchain.resolution import resolve_market_final
        except ImportError as e:
            logger.error(f"Failed to import blockchain module: {e}")
            return {
                "success": False,
                "error": f"Blockchain functionality not available: {e}"
            }
        
        result = resolve_market_final(
            market_id=request.market_id,
            from_private_key=request.from_private_key,
            safe_address=request.safe_address
        )
        
        if not result.success:
            logger.error(f"Failed to finalize resolution for market {request.market_id}: {result.error_message}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to finalize resolution: {result.error_message}",
            )
        
        # Update database with finalization info
        try:
            from .supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Get existing market record
            market_response = supabase.table("prediction_markets").select("*").eq("market_id", request.market_id).execute()
            if market_response.data:
                existing_market = market_response.data[0]
                current_metadata = existing_market.get("metadata", {})
                
                # Add finalization info to metadata
                finalization_info = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "transaction_output": result.raw_output
                }
                
                current_metadata["finalization"] = finalization_info
                
                # Update the database record to resolved status
                update_result = supabase.table("prediction_markets").update({
                    "status": "resolved",
                    "metadata": current_metadata
                }).eq("market_id", request.market_id).execute()
                
                if update_result.data:
                    logger.info(f"Successfully updated market record with finalization for market {request.market_id}")
                else:
                    logger.warning(f"Failed to update market record for finalization of market {request.market_id}")
            else:
                logger.warning(f"Could not find market record for market {request.market_id} to update with finalization")
                
        except Exception as e:
            logger.error(f"Error updating database with finalization info: {e}")
            # Don't fail the entire request for database update issues
        
        logger.info(f"Successfully finalized resolution for market {request.market_id}")
        return {
            "status": "success",
            "message": "Market resolution finalized successfully",
            "market_id": request.market_id,
            "transaction_output": result.raw_output,
        }
        
    except Exception as e:
        logger.error(f"Error finalizing resolution for market {request.market_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error finalizing resolution: {str(e)}",
        )


@app.get("/resolution-status/{market_id}", tags=["Market Resolution"])
async def get_market_resolution_status(market_id: str, from_private_key: str = None):
    """
    Get the current resolution status of a market.
    Shows whether the market is closed, has an answer, is resolved, or needs finalization.
    """
    try:
        if not from_private_key:
            # Use default private key from config for read-only operations
            from .config import Config
            from_private_key = Config.OMEN_PRIVATE_KEY
        
        logger.info(f"Checking resolution status for market {market_id}")
        
        # Check the market resolution status using the real blockchain resolution module
        # Lazy import blockchain functionality
        try:
            from .blockchain.resolution import check_market_resolution_status
        except ImportError as e:
            logger.error(f"Failed to import blockchain module: {e}")
            return {
                "success": False,
                "error": f"Blockchain functionality not available: {e}"
            }
        
        success, message, status_info = check_market_resolution_status(
            market_id=market_id,
            from_private_key=from_private_key
        )
        
        if not success:
            logger.error(f"Failed to check resolution status for market {market_id}: {message}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to check resolution status: {message}",
            )
        
        logger.info(f"Successfully retrieved resolution status for market {market_id}")
        return {
            "status": "success",
            "message": message,
            "market_id": market_id,
            "resolution_status": status_info,
        }
        
    except Exception as e:
        logger.error(f"Error checking resolution status for market {market_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking resolution status: {str(e)}",
        )

