"""
AWS App Runner compatible logging utility for tracking market operations.
Replaces file-based logging with stdout/stderr and structured logging for AWS App Runner.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

class AwsAppRunnerLogger:
    """
    AWS App Runner compatible logger for market operations that uses stdout/stderr instead of files.
    All logs are structured JSON for better observability in AWS App Runner.
    """
    
    def __init__(self):
        # Setup structured logging for AWS App Runner
        self.setup_loggers()
        # In-memory storage for recent logs (limited to prevent memory issues)
        self.recent_logs: List[Dict] = []
        self.max_logs = 1000  # Keep only last 1000 log entries
    
    def setup_loggers(self):
        """Setup structured loggers for AWS App Runner environment."""
        
        # Market operations logger - outputs to stdout
        self.market_logger = logging.getLogger('aws_app_runner_market_operations')
        self.market_logger.setLevel(logging.INFO)
        self.market_logger.handlers.clear()
        
        # Console handler for stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - MARKET - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.market_logger.addHandler(console_handler)
        
        # Error logger - outputs to stderr
        self.error_logger = logging.getLogger('aws_app_runner_market_errors')
        self.error_logger.setLevel(logging.ERROR)
        self.error_logger.handlers.clear()
        
        error_handler = logging.StreamHandler(sys.stderr)
        error_formatter = logging.Formatter(
            '%(asctime)s - MARKET_ERROR - %(levelname)s - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        self.error_logger.addHandler(error_handler)
    
    def _add_to_memory(self, log_entry: Dict):
        """Add log entry to in-memory storage with size limit."""
        self.recent_logs.append(log_entry)
        if len(self.recent_logs) > self.max_logs:
            self.recent_logs = self.recent_logs[-self.max_logs:]
    
    def _create_log_entry(self, operation: str, application_id: str, data: Dict = None) -> Dict:
        """Create a structured log entry."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "application_id": application_id,
            "data": data or {},
            "environment": "aws_app_runner"
        }
    
    def log_market_request(self, application_id: str, request_data: Dict):
        """Log incoming market creation request."""
        log_entry = self._create_log_entry("market_request", application_id, request_data)
        self._add_to_memory(log_entry)
        
        message = f"Market creation request for application {application_id}"
        self.market_logger.info(f"{message} | {json.dumps(log_entry)}")
    
    def log_duplicate_check(self, application_id: str, existing_market: Optional[Dict]):
        """Log duplicate market check result."""
        data = {"has_existing_market": existing_market is not None}
        if existing_market:
            data["existing_market_id"] = existing_market.get("market_id")
        
        log_entry = self._create_log_entry("duplicate_check", application_id, data)
        self._add_to_memory(log_entry) 
        
        message = f"Duplicate check for application {application_id}: {'found' if existing_market else 'none'}"
        self.market_logger.info(f"{message} | {json.dumps(log_entry)}")
    
    def log_market_creation_start(self, application_id: str, application_details: Dict):
        """Log start of market creation process."""
        log_entry = self._create_log_entry("creation_start", application_id, application_details)
        self._add_to_memory(log_entry)
        
        message = f"Starting market creation for {application_details.get('project_name', 'unknown')}"
        self.market_logger.info(f"{message} | {json.dumps(log_entry)}")
    
    def log_market_creation_success(self, application_id: str, market_info: Dict, raw_output: str):
        """Log successful market creation."""
        data = {
            "market_info": market_info,
            "raw_output_length": len(raw_output),
            "success": True
        }
        log_entry = self._create_log_entry("creation_success", application_id, data)
        self._add_to_memory(log_entry)
        
        message = f"Market created successfully: {market_info.get('market_id', 'unknown')}"
        self.market_logger.info(f"{message} | {json.dumps(log_entry)}")
    
    def log_market_creation_failure(self, application_id: str, error_message: str, application_details: Dict):
        """Log failed market creation."""
        data = {
            "error_message": error_message,
            "application_details": application_details,
            "success": False
        }
        log_entry = self._create_log_entry("creation_failure", application_id, data)
        self._add_to_memory(log_entry)
        
        message = f"Market creation failed for {application_id}: {error_message}"
        self.error_logger.error(f"{message} | {json.dumps(log_entry)}")
    
    def log_database_operation(self, operation: str, application_id: str, success: bool, data: Dict):
        """Log database operations."""
        log_data = {
            "database_operation": operation,
            "success": success,
            "data_keys": list(data.keys()) if data else []
        }
        log_entry = self._create_log_entry("database", application_id, log_data)
        self._add_to_memory(log_entry)
        
        message = f"Database {operation} for {application_id}: {'success' if success else 'failed'}"
        logger = self.market_logger if success else self.error_logger
        level = "info" if success else "error"
        getattr(logger, level)(f"{message} | {json.dumps(log_entry)}")
    
    def log_error(self, error_type: str, error_message: str, application_id: str = None, **kwargs):
        """Log general errors."""
        data = {
            "error_type": error_type,
            "error_message": error_message,
            **kwargs
        }
        log_entry = self._create_log_entry("error", application_id or "unknown", data)
        self._add_to_memory(log_entry)
        
        message = f"Error ({error_type}): {error_message}"
        self.error_logger.error(f"{message} | {json.dumps(log_entry)}")
    
    def get_market_logs(self, application_id: str) -> List[Dict]:
        """Get logs for a specific application/market."""
        return [
            log for log in self.recent_logs 
            if log.get("application_id") == application_id
        ]
    
    def get_recent_logs(self, hours: int = 24) -> List[Dict]:
        """Get recent logs within specified hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            log for log in self.recent_logs
            if datetime.fromisoformat(log["timestamp"]) > cutoff_time
        ]
    
    def get_logs_by_operation(self, operation: str) -> List[Dict]:
        """Get logs by operation type."""
        return [
            log for log in self.recent_logs
            if log.get("operation") == operation
        ]

# Create global logger instance for AWS App Runner
market_logger = AwsAppRunnerLogger()