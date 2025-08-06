"""
Railway-compatible logging utility for tracking market operations.
Uses stdout/stderr and structured logging optimized for Railway platform.
"""
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List

class RailwayLogger:
    """
    Railway-compatible logger for market operations that uses stdout/stderr instead of files.
    All logs are structured JSON for better observability in Railway logs.
    """
    
    def __init__(self):
        # Setup structured logging for Railway
        self.setup_loggers()
        # In-memory storage for recent logs (limited to prevent memory issues)
        self.recent_logs: List[Dict] = []
        self.max_logs = 1000  # Keep only last 1000 log entries
    
    def setup_loggers(self):
        """Setup structured loggers for Railway environment."""
        
        # Market operations logger - outputs to stdout
        self.market_logger = logging.getLogger('railway_market_operations')
        self.market_logger.setLevel(logging.INFO)
        self.market_logger.handlers.clear()
        
        # Console handler for stdout - Railway captures this automatically
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - MARKET - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.market_logger.addHandler(console_handler)
        
        # Error logger - outputs to stderr - Railway captures this as error logs
        self.error_logger = logging.getLogger('railway_market_errors')
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
        """Create a structured log entry for Railway."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "application_id": application_id,
            "data": data or {},
            "environment": "railway",
            "platform": "railway_deployment"
        }
    
    def log_market_request(self, application_id: str, request_data: Dict):
        """Log incoming market creation request."""
        log_entry = self._create_log_entry("market_request", application_id, request_data)
        self._add_to_memory(log_entry)
        
        message = f"🚂 Railway - Market creation request for application {application_id}"
        self.market_logger.info(f"{message} | {json.dumps(log_entry)}")
    
    def log_duplicate_check(self, application_id: str, existing_market: Optional[Dict]):
        """Log duplicate market check result."""
        data = {"has_existing_market": existing_market is not None}
        if existing_market:
            data["existing_market_id"] = existing_market.get("market_id")
        
        log_entry = self._create_log_entry("duplicate_check", application_id, data)
        self._add_to_memory(log_entry) 
        
        status_emoji = "⚠️" if existing_market else "✅"
        message = f"{status_emoji} Duplicate check for application {application_id}: {'found' if existing_market else 'none'}"
        self.market_logger.info(f"{message} | {json.dumps(log_entry)}")
    
    def log_market_creation_start(self, application_id: str, application_details: Dict):
        """Log start of market creation process."""
        log_entry = self._create_log_entry("creation_start", application_id, application_details)
        self._add_to_memory(log_entry)
        
        message = f"🏗️ Starting market creation for {application_details.get('project_name', 'unknown')}"
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
        
        message = f"🎉 Market created successfully: {market_info.get('market_id', 'unknown')}"
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
        
        message = f"❌ Market creation failed for {application_id}: {error_message}"
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
        
        status_emoji = "✅" if success else "❌"
        message = f"{status_emoji} Database {operation} for {application_id}: {'success' if success else 'failed'}"
        logger = self.market_logger if success else self.error_logger
        level = "info" if success else "error"
        getattr(logger, level)(f"{message} | {json.dumps(log_entry)}")
    
    def log_subprocess_call(self, operation: str, command: str, application_id: str = None, success: bool = True, output: str = ""):
        """Log subprocess operations (Railway-specific addition)."""
        data = {
            "command": command,
            "success": success,
            "output_length": len(output),
            "railway_subprocess": True
        }
        log_entry = self._create_log_entry("subprocess", application_id or "system", data)
        self._add_to_memory(log_entry)
        
        status_emoji = "🔧" if success else "⚠️"
        message = f"{status_emoji} Railway subprocess {operation}: {command[:100]}{'...' if len(command) > 100 else ''}"
        logger = self.market_logger if success else self.error_logger
        level = "info" if success else "error"
        getattr(logger, level)(f"{message} | {json.dumps(log_entry)}")
    
    def log_error(self, error_type: str, error_message: str, application_id: str = None, **kwargs):
        """Log general errors."""
        data = {
            "error_type": error_type,
            "error_message": error_message,
            "railway_error": True,
            **kwargs
        }
        log_entry = self._create_log_entry("error", application_id or "unknown", data)
        self._add_to_memory(log_entry)
        
        message = f"🚨 Railway Error ({error_type}): {error_message}"
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
    
    def log_railway_startup(self, port: str, host: str, service_name: str = "unknown"):
        """Railway-specific startup logging."""
        data = {
            "port": port,
            "host": host,
            "service_name": service_name,
            "railway_startup": True
        }
        log_entry = self._create_log_entry("railway_startup", "system", data)
        self._add_to_memory(log_entry)
        
        message = f"🚂 Railway startup: {service_name} on {host}:{port}"
        self.market_logger.info(f"{message} | {json.dumps(log_entry)}")

# Create global logger instance for Railway
market_logger = RailwayLogger()