"""
Async blockchain task queue system for handling long-running blockchain operations.
Prevents frontend blocking and provides status tracking with retry mechanisms.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
import logging
from concurrent.futures import ThreadPoolExecutor

from .config import Config
from .railway_logger import market_logger

logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    """Types of blockchain tasks"""
    CREATE_MARKET = "create_market"
    PLACE_BET = "place_bet"
    SUBMIT_ANSWER = "submit_answer"
    FINALIZE_RESOLUTION = "finalize_resolution"
    RESEARCH_AND_SUBMIT = "research_and_submit"

@dataclass
class BlockchainTask:
    """Blockchain task definition"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, (TaskStatus, TaskType)):
                data[key] = value.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlockchainTask':
        """Create from dictionary"""
        # Convert ISO strings back to datetime objects
        for key in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        
        data['task_type'] = TaskType(data['task_type'])
        data['status'] = TaskStatus(data['status'])
        return cls(**data)

class BlockchainTaskQueue:
    """
    Async task queue for blockchain operations.
    Handles task queuing, execution, retry logic, and status tracking.
    """
    
    def __init__(self, max_concurrent_tasks: int = 3):
        self.tasks: Dict[str, BlockchainTask] = {}
        self.queue = asyncio.Queue()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)
        self.workers_started = False
        self._lock = asyncio.Lock()
        
        logger.info(f"🔄 BlockchainTaskQueue initialized with max_concurrent_tasks={max_concurrent_tasks}")
    
    async def submit_task(self, task_type: TaskType, payload: Dict[str, Any], 
                         max_retries: int = 3) -> str:
        """
        Submit a new blockchain task to the queue.
        Returns task_id immediately for status tracking.
        """
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        task = BlockchainTask(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            payload=payload,
            created_at=now,
            updated_at=now,
            max_retries=max_retries
        )
        
        async with self._lock:
            self.tasks[task_id] = task
            await self.queue.put(task_id)
        
        # Start workers if not already started
        if not self.workers_started:
            await self.start_workers()
        
        # Log task submission
        market_logger.log_subprocess_call(
            f"queue_{task_type.value}", 
            f"Task {task_id} queued",
            payload.get("application_id"),
            True
        )
        
        logger.info(f"🔄 Task {task_id} ({task_type.value}) submitted to queue")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[BlockchainTask]:
        """Get current task status"""
        return self.tasks.get(task_id)
    
    async def get_tasks_by_status(self, status: TaskStatus) -> List[BlockchainTask]:
        """Get all tasks with specific status"""
        return [task for task in self.tasks.values() if task.status == status]
    
    async def get_recent_tasks(self, hours: int = 24) -> List[BlockchainTask]:
        """Get tasks from the last N hours"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [task for task in self.tasks.values() if task.created_at > cutoff]
    
    async def start_workers(self):
        """Start async worker tasks"""
        if self.workers_started:
            return
            
        self.workers_started = True
        
        # Start multiple worker coroutines
        for i in range(self.max_concurrent_tasks):
            asyncio.create_task(self._worker(f"worker-{i}"))
        
        logger.info(f"🚀 Started {self.max_concurrent_tasks} blockchain task workers")
    
    async def _worker(self, worker_name: str):
        """Background worker that processes tasks from the queue"""
        logger.info(f"👷 Worker {worker_name} started")
        
        while True:
            try:
                # Get task from queue (blocks until available)
                task_id = await self.queue.get()
                
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    logger.info(f"👷 Worker {worker_name} processing task {task_id} ({task.task_type.value})")
                    
                    # Process the task
                    await self._process_task(task, worker_name)
                
                # Mark queue task as done
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"👷 Worker {worker_name} error: {e}")
                await asyncio.sleep(5)  # Brief pause before continuing
    
    async def _process_task(self, task: BlockchainTask, worker_name: str):
        """Process a single blockchain task"""
        try:
            # Update task status
            await self._update_task_status(task, TaskStatus.PROCESSING)
            task.started_at = datetime.now(timezone.utc)
            
            logger.info(f"🔄 Processing {task.task_type.value} task {task.task_id}")
            
            # Execute the blockchain operation in thread pool
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._execute_blockchain_operation, task
            )
            
            if result.get("success"):
                # Task completed successfully
                task.result = result
                await self._update_task_status(task, TaskStatus.COMPLETED)
                task.completed_at = datetime.now(timezone.utc)
                
                logger.info(f"✅ Task {task.task_id} completed successfully")
                market_logger.log_subprocess_call(
                    f"completed_{task.task_type.value}",
                    f"Task {task.task_id} completed",
                    task.payload.get("application_id"),
                    True,
                    str(result)
                )
                
            else:
                # Task failed, handle retry logic
                await self._handle_task_failure(task, result.get("error", "Unknown error"))
                
        except Exception as e:
            logger.error(f"❌ Task {task.task_id} processing error: {e}")
            await self._handle_task_failure(task, str(e))
    
    async def _handle_task_failure(self, task: BlockchainTask, error_message: str):
        """Handle task failure with retry logic"""
        task.error_message = error_message
        task.retry_count += 1
        
        if task.retry_count <= task.max_retries:
            # Retry the task
            await self._update_task_status(task, TaskStatus.RETRYING)
            
            # Exponential backoff: 2^retry_count minutes
            delay_minutes = 2 ** task.retry_count
            logger.info(f"🔄 Task {task.task_id} failed, retrying in {delay_minutes} minutes (attempt {task.retry_count}/{task.max_retries})")
            
            # Schedule retry
            asyncio.create_task(self._schedule_retry(task, delay_minutes * 60))
            
            market_logger.log_error(
                f"task_retry_{task.task_type.value}",
                f"Task {task.task_id} retry {task.retry_count}: {error_message}",
                task.payload.get("application_id")
            )
        else:
            # Max retries exceeded, mark as failed
            await self._update_task_status(task, TaskStatus.FAILED)
            task.completed_at = datetime.now(timezone.utc)
            
            logger.error(f"❌ Task {task.task_id} failed permanently after {task.retry_count} retries: {error_message}")
            market_logger.log_error(
                f"task_failed_{task.task_type.value}",
                f"Task {task.task_id} failed permanently: {error_message}",
                task.payload.get("application_id")
            )
    
    async def _schedule_retry(self, task: BlockchainTask, delay_seconds: int):
        """Schedule a task retry after delay"""
        await asyncio.sleep(delay_seconds)
        
        # Re-queue the task
        async with self._lock:
            await self.queue.put(task.task_id)
        
        logger.info(f"🔄 Task {task.task_id} re-queued for retry")
    
    async def _update_task_status(self, task: BlockchainTask, status: TaskStatus):
        """Update task status and timestamp"""
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        
        # Here you could add database persistence if needed
        logger.debug(f"📊 Task {task.task_id} status updated to {status.value}")
    
    def _execute_blockchain_operation(self, task: BlockchainTask) -> Dict[str, Any]:
        """
        Execute blockchain operation synchronously in thread pool.
        This is where the actual blockchain calls happen.
        """
        try:
            if task.task_type == TaskType.CREATE_MARKET:
                return self._execute_create_market(task.payload)
            elif task.task_type == TaskType.PLACE_BET:
                return self._execute_place_bet(task.payload)
            elif task.task_type == TaskType.SUBMIT_ANSWER:
                return self._execute_submit_answer(task.payload)
            elif task.task_type == TaskType.FINALIZE_RESOLUTION:
                return self._execute_finalize_resolution(task.payload)
            elif task.task_type == TaskType.RESEARCH_AND_SUBMIT:
                return self._execute_research_and_submit(task.payload)
            else:
                return {"success": False, "error": f"Unknown task type: {task.task_type}"}
                
        except Exception as e:
            logger.error(f"Blockchain operation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_create_market(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute market creation"""
        try:
            from .omen_subprocess_creator import create_omen_market
            
            application_details = payload["application_details"]
            success, result = create_omen_market(application_details)
            
            if success:
                # Parse market output for database storage
                from .omen_subprocess_creator import parse_market_output
                market_info = parse_market_output(result)
                
                return {
                    "success": True,
                    "market_info": market_info,
                    "raw_output": str(result)
                }
            else:
                return {"success": False, "error": str(result)}
                
        except Exception as e:
            return {"success": False, "error": f"Market creation failed: {str(e)}"}
    
    def _execute_place_bet(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute bet placement"""
        try:
            from .omen_subprocess_betting import place_bet
            
            success, result = place_bet(
                market_id=payload["market_id"],
                amount_usd=payload["amount_usd"],
                outcome=payload["outcome"],
                from_private_key=payload["from_private_key"],
                safe_address=payload.get("safe_address"),
                auto_deposit=payload.get("auto_deposit", True)
            )
            
            return {
                "success": success,
                "result": result if success else None,
                "error": result if not success else None
            }
            
        except Exception as e:
            return {"success": False, "error": f"Bet placement failed: {str(e)}"}
    
    def _execute_submit_answer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute answer submission"""
        try:
            from .blockchain.resolution import submit_market_answer
            
            result = submit_market_answer(
                market_id=payload["market_id"],
                outcome=payload["outcome"],
                confidence=payload["confidence"],
                reasoning=payload["reasoning"],
                from_private_key=payload["from_private_key"],
                bond_amount_xdai=payload.get("bond_amount_xdai", 0.01),
                safe_address=payload.get("safe_address")
            )
            
            return {
                "success": result.success,
                "result": result.raw_output if result.success else None,
                "error": result.error_message if not result.success else None
            }
            
        except Exception as e:
            return {"success": False, "error": f"Answer submission failed: {str(e)}"}
    
    def _execute_finalize_resolution(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute resolution finalization"""
        try:
            from .blockchain.resolution import resolve_market_final
            
            result = resolve_market_final(
                market_id=payload["market_id"],
                from_private_key=payload["from_private_key"],
                safe_address=payload.get("safe_address")
            )
            
            return {
                "success": result.success,
                "result": result.raw_output if result.success else None,
                "error": result.error_message if not result.success else None
            }
            
        except Exception as e:
            return {"success": False, "error": f"Resolution finalization failed: {str(e)}"}
    
    def _execute_research_and_submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute research and answer submission"""
        try:
            from .market_monitor import MarketStatus
            from .resolution_researcher import GrokResolutionResearcher
            from .blockchain.resolution import submit_market_answer
            
            # Create market status for research
            market_status = MarketStatus(
                market_id=payload["market_id"],
                title=f"Research for {payload['market_id']}",
                closing_time=datetime.now(timezone.utc),
                is_closed=True,
                is_resolved=False,
                application_id=payload["application_id"],
                funding_program_name=payload["funding_program_name"],
                funding_program_twitter=payload.get("funding_program_twitter")
            )
            
            # Perform research
            researcher = GrokResolutionResearcher()
            research_result = researcher.research_market_resolution(market_status)
            
            if not research_result:
                return {"success": False, "error": "Research failed to produce results"}
            
            # Convert "Invalid" to "No" for blockchain submission
            blockchain_outcome = research_result.outcome
            if research_result.outcome == "Invalid":
                blockchain_outcome = "No"
            
            # Submit answer
            submission_result = submit_market_answer(
                market_id=payload["market_id"],
                outcome=blockchain_outcome,
                confidence=research_result.confidence,
                reasoning=research_result.reasoning,
                from_private_key=Config.OMEN_PRIVATE_KEY,
                bond_amount_xdai=0.01,
                safe_address=None
            )
            
            return {
                "success": submission_result.success,
                "research_result": {
                    "outcome": research_result.outcome,
                    "blockchain_outcome": blockchain_outcome,
                    "confidence": research_result.confidence,
                    "reasoning": research_result.reasoning,
                    "sources": research_result.sources
                },
                "submission_result": submission_result.raw_output if submission_result.success else None,
                "error": submission_result.error_message if not submission_result.success else None
            }
            
        except Exception as e:
            return {"success": False, "error": f"Research and submission failed: {str(e)}"}

# Global task queue instance
blockchain_task_queue = BlockchainTaskQueue(max_concurrent_tasks=3)