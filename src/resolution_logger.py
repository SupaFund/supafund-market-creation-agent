"""
Comprehensive logging system for market resolution operations.
"""
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import uuid

from .config import Config

@dataclass
class ResolutionLogEntry:
    """Structured log entry for resolution operations"""
    id: str
    timestamp: str
    operation: str  # "monitor", "research", "resolve", "finalize", "error"
    market_id: str
    application_id: str
    status: str  # "started", "completed", "failed", "skipped"
    details: Dict[str, Any]
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None

class ResolutionLogger:
    """Centralized logging system for market resolution operations"""
    
    def __init__(self, log_dir: str = None):
        self.log_dir = Path(log_dir or f"{Config.PROJECT_ROOT}/logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Set up different log files
        self.operations_log = self.log_dir / "resolution_operations.log"
        self.errors_log = self.log_dir / "resolution_errors.log"
        self.daily_summary_log = self.log_dir / "daily_summaries.jsonl"
        self.resolution_details_log = self.log_dir / "resolution_details.jsonl"
        
        # Set up loggers
        self._setup_loggers()
        
        # In-memory storage for current session
        self.current_session_logs: List[ResolutionLogEntry] = []
        self.session_start_time = datetime.now(timezone.utc)
    
    def _setup_loggers(self):
        """Set up different loggers for different purposes"""
        
        # Operations logger (general info)
        self.operations_logger = logging.getLogger("resolution_operations")
        self.operations_logger.setLevel(logging.INFO)
        
        operations_handler = logging.FileHandler(self.operations_log)
        operations_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        operations_handler.setFormatter(operations_formatter)
        self.operations_logger.addHandler(operations_handler)
        
        # Errors logger
        self.errors_logger = logging.getLogger("resolution_errors")
        self.errors_logger.setLevel(logging.ERROR)
        
        errors_handler = logging.FileHandler(self.errors_log)
        errors_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
        errors_handler.setFormatter(errors_formatter)
        self.errors_logger.addHandler(errors_handler)
    
    def log_operation_start(self, operation: str, market_id: str, application_id: str, details: Dict = None) -> str:
        """
        Log the start of an operation
        
        Args:
            operation: Operation type
            market_id: Market ID
            application_id: Application ID
            details: Additional details
            
        Returns:
            Operation ID for tracking
        """
        operation_id = str(uuid.uuid4())
        
        log_entry = ResolutionLogEntry(
            id=operation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            operation=operation,
            market_id=market_id,
            application_id=application_id,
            status="started",
            details=details or {}
        )
        
        self.current_session_logs.append(log_entry)
        
        self.operations_logger.info(
            f"[{operation_id}] Started {operation} for market {market_id} (app: {application_id})"
        )
        
        return operation_id
    
    def log_operation_complete(self, operation_id: str, details: Dict = None, duration_seconds: float = None):
        """
        Log successful completion of an operation
        
        Args:
            operation_id: Operation ID from log_operation_start
            details: Additional completion details
            duration_seconds: How long the operation took
        """
        # Find and update the log entry
        for entry in self.current_session_logs:
            if entry.id == operation_id:
                entry.status = "completed"
                entry.details.update(details or {})
                entry.duration_seconds = duration_seconds
                break
        
        self.operations_logger.info(
            f"[{operation_id}] Completed successfully in {duration_seconds:.2f}s" if duration_seconds 
            else f"[{operation_id}] Completed successfully"
        )
    
    def log_operation_failed(self, operation_id: str, error_message: str, details: Dict = None, duration_seconds: float = None):
        """
        Log failed operation
        
        Args:
            operation_id: Operation ID from log_operation_start
            error_message: Error description
            details: Additional error details
            duration_seconds: How long before failure
        """
        # Find and update the log entry
        for entry in self.current_session_logs:
            if entry.id == operation_id:
                entry.status = "failed"
                entry.error_message = error_message
                entry.details.update(details or {})
                entry.duration_seconds = duration_seconds
                break
        
        self.operations_logger.error(f"[{operation_id}] Failed: {error_message}")
        self.errors_logger.error(f"[{operation_id}] {error_message}", extra=details or {})
    
    def log_operation_skipped(self, operation_id: str, reason: str, details: Dict = None):
        """
        Log skipped operation
        
        Args:
            operation_id: Operation ID from log_operation_start
            reason: Why it was skipped
            details: Additional details
        """
        # Find and update the log entry
        for entry in self.current_session_logs:
            if entry.id == operation_id:
                entry.status = "skipped"
                entry.details.update(details or {"skip_reason": reason})
                break
        
        self.operations_logger.info(f"[{operation_id}] Skipped: {reason}")
    
    def log_market_monitor_summary(self, total_markets: int, completed_markets: int, details: Dict = None):
        """
        Log market monitoring summary
        
        Args:
            total_markets: Total markets checked
            completed_markets: Markets found completed
            details: Additional monitoring details
        """
        summary = {
            "operation": "monitor_summary",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_markets_checked": total_markets,
            "completed_markets_found": completed_markets,
            "details": details or {}
        }
        
        self.operations_logger.info(
            f"Market monitoring complete: {completed_markets}/{total_markets} markets need resolution"
        )
        
        # Write to detailed log
        self._write_to_jsonl(self.resolution_details_log, summary)
    
    def log_resolution_research_result(self, market_id: str, application_id: str, outcome: str, 
                                     confidence: float, reasoning: str, sources: List[str]):
        """
        Log resolution research results
        
        Args:
            market_id: Market ID
            application_id: Application ID
            outcome: Research outcome
            confidence: Confidence score
            reasoning: Research reasoning
            sources: Source list
        """
        result = {
            "operation": "research_result",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_id": market_id,
            "application_id": application_id,
            "outcome": outcome,
            "confidence": confidence,
            "reasoning": reasoning,
            "sources": sources
        }
        
        self.operations_logger.info(
            f"Research completed for market {market_id}: {outcome} (confidence: {confidence:.2f})"
        )
        
        # Write detailed result
        self._write_to_jsonl(self.resolution_details_log, result)
    
    def log_blockchain_resolution(self, market_id: str, application_id: str, outcome: str, 
                                success: bool, transaction_details: Dict = None):
        """
        Log blockchain resolution submission
        
        Args:
            market_id: Market ID
            application_id: Application ID
            outcome: Resolution outcome
            success: Whether submission succeeded
            transaction_details: Transaction details
        """
        result = {
            "operation": "blockchain_resolution",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_id": market_id,
            "application_id": application_id,
            "outcome": outcome,
            "success": success,
            "transaction_details": transaction_details or {}
        }
        
        status = "successful" if success else "failed"
        self.operations_logger.info(
            f"Blockchain resolution {status} for market {market_id}: {outcome}"
        )
        
        # Write detailed result
        self._write_to_jsonl(self.resolution_details_log, result)
    
    def generate_daily_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of all operations for the current session/day
        
        Returns:
            Summary dictionary
        """
        session_duration = (datetime.now(timezone.utc) - self.session_start_time).total_seconds()
        
        # Count operations by type and status
        operation_counts = {}
        status_counts = {}
        
        for entry in self.current_session_logs:
            op_type = entry.operation
            status = entry.status
            
            if op_type not in operation_counts:
                operation_counts[op_type] = {"started": 0, "completed": 0, "failed": 0, "skipped": 0}
            
            operation_counts[op_type][status] += 1
            
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
        
        # Calculate success rates
        total_operations = len(self.current_session_logs)
        success_rate = (status_counts.get("completed", 0) / total_operations * 100) if total_operations > 0 else 0
        
        # Collect error summaries
        errors = [entry for entry in self.current_session_logs if entry.status == "failed"]
        error_summary = [
            {
                "market_id": entry.market_id,
                "operation": entry.operation,
                "error": entry.error_message
            } for entry in errors
        ]
        
        summary = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "session_start": self.session_start_time.isoformat(),
            "session_duration_seconds": session_duration,
            "total_operations": total_operations,
            "operation_counts": operation_counts,
            "status_counts": status_counts,
            "success_rate_percent": round(success_rate, 2),
            "errors": error_summary,
            "unique_markets_processed": len(set(entry.market_id for entry in self.current_session_logs)),
            "unique_applications_processed": len(set(entry.application_id for entry in self.current_session_logs))
        }
        
        # Write to daily summary log
        self._write_to_jsonl(self.daily_summary_log, summary)
        
        return summary
    
    def get_recent_errors(self, hours: int = 24) -> List[Dict]:
        """
        Get recent errors from the current session
        
        Args:
            hours: Number of hours to look back (ignored for current session)
            
        Returns:
            List of recent error entries
        """
        errors = []
        for entry in self.current_session_logs:
            if entry.status == "failed":
                errors.append({
                    "timestamp": entry.timestamp,
                    "operation": entry.operation,
                    "market_id": entry.market_id,
                    "application_id": entry.application_id,
                    "error_message": entry.error_message,
                    "details": entry.details
                })
        
        return errors
    
    def get_operation_logs(self, market_id: str = None, operation: str = None) -> List[Dict]:
        """
        Get operation logs, optionally filtered
        
        Args:
            market_id: Filter by market ID
            operation: Filter by operation type
            
        Returns:
            List of matching log entries
        """
        filtered_logs = []
        
        for entry in self.current_session_logs:
            if market_id and entry.market_id != market_id:
                continue
            if operation and entry.operation != operation:
                continue
            
            filtered_logs.append(asdict(entry))
        
        return filtered_logs
    
    def _write_to_jsonl(self, file_path: Path, data: Dict):
        """
        Write data to a JSONL file
        
        Args:
            file_path: Path to JSONL file
            data: Data to write
        """
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            self.errors_logger.error(f"Failed to write to {file_path}: {e}")
    
    def clear_session_logs(self):
        """Clear the current session logs (use with caution)"""
        self.current_session_logs.clear()
        self.session_start_time = datetime.now(timezone.utc)

# Global logger instance
resolution_logger = ResolutionLogger()