"""
Async blockchain endpoints that return immediately with task IDs.
These replace the blocking synchronous blockchain operations.
"""
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from .blockchain_task_queue import blockchain_task_queue, TaskType, TaskStatus
from .supabase_client import get_application_details, check_existing_market, create_market_record
from .config import Config
import logging

logger = logging.getLogger(__name__)

# Response models for async operations
class AsyncTaskResponse(BaseModel):
    """Standard response for async blockchain operations"""
    status: str = "accepted"
    message: str
    task_id: str
    estimated_completion_time: str
    status_endpoint: str

class TaskStatusResponse(BaseModel):
    """Response for task status queries"""
    task_id: str
    task_type: str
    status: str
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int
    max_retries: int
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None

class MarketCreationAsyncRequest(BaseModel):
    application_id: str = Field(..., 
        description="The UUID of the application in Supafund.",
        examples=["a1b2c3d4-e5f6-7890-1234-567890abcdef"]
    )

class BetAsyncRequest(BaseModel):
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
    safe_address: Optional[str] = Field(None, 
        description="Optional safe address to use for the bet."
    )
    auto_deposit: bool = Field(True, 
        description="Whether to automatically deposit collateral token."
    )

class SubmitAnswerAsyncRequest(BaseModel):
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
    safe_address: Optional[str] = Field(None, 
        description="Optional safe address to use for the transaction."
    )

class FinalizeResolutionAsyncRequest(BaseModel):
    market_id: str = Field(..., 
        description="The market ID to finalize resolution for.",
        examples=["0x86376012a5185f484ec33429cadfa00a8052d9d4"]
    )
    from_private_key: str = Field(..., 
        description="The private key to use for the transaction."
    )
    safe_address: Optional[str] = Field(None, 
        description="Optional safe address to use for the transaction."
    )

class ResearchAndSubmitAsyncRequest(BaseModel):
    market_id: str = Field(..., description="Market ID to research")
    application_id: str = Field(..., description="Application ID associated with the market")
    funding_program_name: str = Field(..., description="Name of the funding program")
    funding_program_twitter: Optional[str] = Field(None, description="Twitter URL of the funding program")

# Async endpoint handlers

async def handle_create_market_async(request: MarketCreationAsyncRequest) -> AsyncTaskResponse:
    """
    Async market creation - returns immediately with task ID.
    """
    application_id = request.application_id
    logger.info(f"🔄 Async market creation request for application_id: {application_id}")
    
    # 1. Check if market already exists (synchronous check)
    existing_market = check_existing_market(application_id)
    if existing_market:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "already_exists",
                "message": "Market already exists for this application",
                "existing_market": existing_market
            }
        )
    
    # 2. Get application details (synchronous)
    application_details = get_application_details(application_id)
    if not application_details:
        raise HTTPException(
            status_code=404,
            detail=f"Application with id {application_id} not found."
        )
    
    # 3. Submit task to async queue
    task_id = await blockchain_task_queue.submit_task(
        task_type=TaskType.CREATE_MARKET,
        payload={
            "application_id": application_id,
            "application_details": application_details
        },
        max_retries=3
    )
    
    return AsyncTaskResponse(
        message=f"Market creation task submitted for application {application_id}",
        task_id=task_id,
        estimated_completion_time="2-5 minutes",
        status_endpoint=f"/task-status/{task_id}"
    )

async def handle_bet_async(request: BetAsyncRequest) -> AsyncTaskResponse:
    """
    Async bet placement - returns immediately with task ID.
    """
    logger.info(f"🔄 Async bet request for market {request.market_id}")
    
    # Submit task to async queue
    task_id = await blockchain_task_queue.submit_task(
        task_type=TaskType.PLACE_BET,
        payload={
            "market_id": request.market_id,
            "amount_usd": request.amount_usd,
            "outcome": request.outcome,
            "from_private_key": request.from_private_key,
            "safe_address": request.safe_address,
            "auto_deposit": request.auto_deposit
        },
        max_retries=3
    )
    
    return AsyncTaskResponse(
        message=f"Bet placement task submitted for market {request.market_id}",
        task_id=task_id,
        estimated_completion_time="1-3 minutes",
        status_endpoint=f"/task-status/{task_id}"
    )

async def handle_submit_answer_async(request: SubmitAnswerAsyncRequest) -> AsyncTaskResponse:
    """
    Async answer submission - returns immediately with task ID.
    """
    logger.info(f"🔄 Async answer submission for market {request.market_id}")
    
    # Submit task to async queue
    task_id = await blockchain_task_queue.submit_task(
        task_type=TaskType.SUBMIT_ANSWER,
        payload={
            "market_id": request.market_id,
            "outcome": request.outcome,
            "confidence": request.confidence,
            "reasoning": request.reasoning,
            "from_private_key": request.from_private_key,
            "bond_amount_xdai": request.bond_amount_xdai,
            "safe_address": request.safe_address
        },
        max_retries=3
    )
    
    return AsyncTaskResponse(
        message=f"Answer submission task created for market {request.market_id}",
        task_id=task_id,
        estimated_completion_time="1-2 minutes",
        status_endpoint=f"/task-status/{task_id}"
    )

async def handle_finalize_resolution_async(request: FinalizeResolutionAsyncRequest) -> AsyncTaskResponse:
    """
    Async resolution finalization - returns immediately with task ID.
    """
    logger.info(f"🔄 Async resolution finalization for market {request.market_id}")
    
    # Submit task to async queue
    task_id = await blockchain_task_queue.submit_task(
        task_type=TaskType.FINALIZE_RESOLUTION,
        payload={
            "market_id": request.market_id,
            "from_private_key": request.from_private_key,
            "safe_address": request.safe_address
        },
        max_retries=2  # Fewer retries for finalization
    )
    
    return AsyncTaskResponse(
        message=f"Resolution finalization task created for market {request.market_id}",
        task_id=task_id,
        estimated_completion_time="1-2 minutes",
        status_endpoint=f"/task-status/{task_id}"
    )

async def handle_research_and_submit_async(request: ResearchAndSubmitAsyncRequest) -> AsyncTaskResponse:
    """
    Async research and submit - returns immediately with task ID.
    """
    logger.info(f"🔄 Async research and submit for market {request.market_id}")
    
    # Submit task to async queue
    task_id = await blockchain_task_queue.submit_task(
        task_type=TaskType.RESEARCH_AND_SUBMIT,
        payload={
            "market_id": request.market_id,
            "application_id": request.application_id,
            "funding_program_name": request.funding_program_name,
            "funding_program_twitter": request.funding_program_twitter
        },
        max_retries=2
    )
    
    return AsyncTaskResponse(
        message=f"Research and submission task created for market {request.market_id}",
        task_id=task_id,
        estimated_completion_time="3-5 minutes",
        status_endpoint=f"/task-status/{task_id}"
    )

async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    Get current status of a blockchain task.
    """
    task = await blockchain_task_queue.get_task_status(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    # Calculate progress information
    progress = {}
    if task.status == TaskStatus.PROCESSING:
        # Estimate progress based on task type and elapsed time
        if task.started_at:
            elapsed = (datetime.now(task.started_at.tzinfo) - task.started_at).total_seconds()
            if task.task_type == TaskType.CREATE_MARKET:
                progress["estimated_progress"] = min(90, elapsed / 180 * 100)  # 3 min max
            elif task.task_type == TaskType.PLACE_BET:
                progress["estimated_progress"] = min(90, elapsed / 120 * 100)  # 2 min max
            else:
                progress["estimated_progress"] = min(90, elapsed / 90 * 100)   # 1.5 min max
            progress["estimated_progress"] = round(progress["estimated_progress"], 1)
    
    return TaskStatusResponse(
        task_id=task.task_id,
        task_type=task.task_type.value,
        status=task.status.value,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        error_message=task.error_message,
        result=task.result,
        progress=progress if progress else None
    )

async def get_recent_tasks(hours: int = 24, status: Optional[str] = None) -> List[TaskStatusResponse]:
    """
    Get recent blockchain tasks with optional status filter.
    """
    if status:
        try:
            status_enum = TaskStatus(status)
            tasks = await blockchain_task_queue.get_tasks_by_status(status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid statuses: {[s.value for s in TaskStatus]}"
            )
    else:
        tasks = await blockchain_task_queue.get_recent_tasks(hours)
    
    # Sort by created_at descending (newest first)
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    
    # Convert to response format
    return [
        TaskStatusResponse(
            task_id=task.task_id,
            task_type=task.task_type.value,
            status=task.status.value,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            error_message=task.error_message,
            result=task.result
        )
        for task in tasks
    ]