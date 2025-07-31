"""
Market creation logging utility for tracking all market operations to local files.
"""
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from pathlib import Path

class MarketLogger:
    """
    Enhanced logger for market operations that writes to local files.
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup file handlers
        self.setup_loggers()
    
    def setup_loggers(self):
        """Setup different loggers for different types of operations."""
        
        # Market operations logger
        self.market_logger = logging.getLogger('market_operations')
        self.market_logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.market_logger.handlers.clear()
        
        # Market operations file handler
        market_handler = logging.FileHandler(
            self.log_dir / 'market_operations.log',
            encoding='utf-8'
        )
        market_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        market_handler.setFormatter(market_formatter)
        self.market_logger.addHandler(market_handler)
        
        # Market details JSON logger (for structured data)
        self.details_file = self.log_dir / 'market_details.jsonl'
        
        # Error logger
        self.error_logger = logging.getLogger('market_errors')
        self.error_logger.setLevel(logging.ERROR)
        self.error_logger.handlers.clear()
        
        error_handler = logging.FileHandler(
            self.log_dir / 'market_errors.log',
            encoding='utf-8'
        )
        error_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        self.error_logger.addHandler(error_handler)
    
    def log_market_request(self, application_id: str, request_data: Optional[Dict[str, Any]] = None):
        """Log incoming market creation request."""
        self.market_logger.info(f"MARKET_REQUEST - Application: {application_id}")
        
        if request_data:
            self._log_json_details({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event': 'market_request',
                'application_id': application_id,
                'request_data': request_data
            })
    
    def log_duplicate_check(self, application_id: str, existing_market: Optional[Dict[str, Any]]):
        """Log duplicate market check results."""
        if existing_market:
            self.market_logger.info(f"DUPLICATE_FOUND - Application: {application_id}, Market: {existing_market.get('market_id')}")
        else:
            self.market_logger.info(f"NO_DUPLICATE - Application: {application_id}")
        
        self._log_json_details({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event': 'duplicate_check',
            'application_id': application_id,
            'duplicate_found': existing_market is not None,
            'existing_market': existing_market
        })
    
    def log_market_creation_start(self, application_id: str, application_details: Dict[str, Any]):
        """Log start of market creation process."""
        self.market_logger.info(f"CREATION_START - Application: {application_id}, Project: {application_details.get('project_name')}")
        
        self._log_json_details({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event': 'creation_start',
            'application_id': application_id,
            'application_details': application_details
        })
    
    def log_market_creation_success(self, application_id: str, market_info: Dict[str, Any], raw_output: str):
        """Log successful market creation."""
        market_id = market_info.get('market_id', 'unknown')
        self.market_logger.info(f"CREATION_SUCCESS - Application: {application_id}, Market: {market_id}")
        
        self._log_json_details({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event': 'creation_success',
            'application_id': application_id,
            'market_info': market_info,
            'raw_output': raw_output
        })
    
    def log_market_creation_failure(self, application_id: str, error_message: str, application_details: Optional[Dict[str, Any]] = None):
        """Log failed market creation."""
        self.market_logger.error(f"CREATION_FAILED - Application: {application_id}, Error: {error_message}")
        self.error_logger.error(f"Market creation failed for {application_id}: {error_message}")
        
        self._log_json_details({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event': 'creation_failed',
            'application_id': application_id,
            'error_message': error_message,
            'application_details': application_details
        })
    
    def log_database_operation(self, operation: str, application_id: str, success: bool, details: Optional[Dict[str, Any]] = None):
        """Log database operations."""
        status = "SUCCESS" if success else "FAILED"
        self.market_logger.info(f"DB_{operation.upper()}_{status} - Application: {application_id}")
        
        self._log_json_details({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event': f'db_{operation}',
            'application_id': application_id,
            'success': success,
            'details': details
        })
    
    def log_error(self, error_type: str, message: str, application_id: Optional[str] = None, **kwargs):
        """Log general errors."""
        log_msg = f"ERROR_{error_type.upper()} - {message}"
        if application_id:
            log_msg += f" - Application: {application_id}"
        
        self.error_logger.error(log_msg)
        
        self._log_json_details({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event': 'error',
            'error_type': error_type,
            'message': message,
            'application_id': application_id,
            **kwargs
        })
    
    def _log_json_details(self, data: Dict[str, Any]):
        """Write structured data to JSON lines file."""
        try:
            with open(self.details_file, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
                f.write('\n')
        except Exception as e:
            # Fallback to regular logger if JSON logging fails
            self.error_logger.error(f"Failed to write JSON log: {e}")
    
    def get_market_logs(self, application_id: str) -> list[Dict[str, Any]]:
        """Retrieve all logs for a specific application."""
        logs = []
        
        try:
            if self.details_file.exists():
                with open(self.details_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if data.get('application_id') == application_id:
                                logs.append(data)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            self.error_logger.error(f"Failed to read logs for {application_id}: {e}")
        
        return sorted(logs, key=lambda x: x.get('timestamp', ''))
    
    def get_recent_logs(self, hours: int = 24) -> list[Dict[str, Any]]:
        """Get recent logs within specified hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        logs = []
        
        try:
            if self.details_file.exists():
                with open(self.details_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            log_time = datetime.fromisoformat(data.get('timestamp', ''))
                            if log_time >= cutoff_time:
                                logs.append(data)
                        except (json.JSONDecodeError, ValueError):
                            continue
        except Exception as e:
            self.error_logger.error(f"Failed to read recent logs: {e}")
        
        return sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)


# Global logger instance
market_logger = MarketLogger()