"""
Unit tests for ResolutionLogger class
"""
import pytest
from unittest.mock import Mock, patch, mock_open
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import uuid

from src.resolution_logger import ResolutionLogger, ResolutionLogEntry


class TestResolutionLogEntry:
    """Tests for ResolutionLogEntry dataclass"""
    
    def test_creation(self):
        """Test creating ResolutionLogEntry"""
        entry = ResolutionLogEntry(
            id="test-id",
            timestamp="2024-01-01T00:00:00Z",
            operation="test_op",
            market_id="0x1234",
            application_id="app-123",
            status="completed",
            details={"key": "value"}
        )
        
        assert entry.id == "test-id"
        assert entry.operation == "test_op"
        assert entry.status == "completed"
        assert entry.details["key"] == "value"
        assert entry.error_message is None
        assert entry.duration_seconds is None
    
    def test_creation_with_optional_fields(self):
        """Test creating ResolutionLogEntry with optional fields"""
        entry = ResolutionLogEntry(
            id="test-id",
            timestamp="2024-01-01T00:00:00Z",
            operation="test_op",
            market_id="0x1234",
            application_id="app-123",
            status="failed",
            details={"key": "value"},
            error_message="Test error",
            duration_seconds=1.5
        )
        
        assert entry.error_message == "Test error"
        assert entry.duration_seconds == 1.5


class TestResolutionLogger:
    """Tests for ResolutionLogger class"""
    
    def test_init_default_log_dir(self):
        """Test initialization with default log directory"""
        with patch('src.resolution_logger.Config') as mock_config:
            mock_config.PROJECT_ROOT = "/test/project"
            
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                logger = ResolutionLogger()
                
                assert str(logger.log_dir) == "/test/project/logs"
                mock_mkdir.assert_called_once_with(exist_ok=True)
    
    def test_init_custom_log_dir(self, temp_log_dir):
        """Test initialization with custom log directory"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        assert str(logger.log_dir) == temp_log_dir
        assert len(logger.current_session_logs) == 0
    
    def test_log_operation_start(self, temp_log_dir):
        """Test logging operation start"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        operation_id = logger.log_operation_start(
            "test_operation",
            "0x1234",
            "app-123",
            {"detail": "test"}
        )
        
        assert isinstance(operation_id, str)
        assert len(logger.current_session_logs) == 1
        
        entry = logger.current_session_logs[0]
        assert entry.id == operation_id
        assert entry.operation == "test_operation"
        assert entry.market_id == "0x1234"
        assert entry.application_id == "app-123"
        assert entry.status == "started"
        assert entry.details["detail"] == "test"
    
    def test_log_operation_complete(self, temp_log_dir):
        """Test logging operation completion"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        operation_id = logger.log_operation_start("test_op", "0x1234", "app-123")
        logger.log_operation_complete(operation_id, {"result": "success"}, 1.5)
        
        entry = logger.current_session_logs[0]
        assert entry.status == "completed"
        assert entry.details["result"] == "success"
        assert entry.duration_seconds == 1.5
    
    def test_log_operation_failed(self, temp_log_dir):
        """Test logging operation failure"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        operation_id = logger.log_operation_start("test_op", "0x1234", "app-123")
        logger.log_operation_failed(operation_id, "Test error", {"error_code": 500}, 2.0)
        
        entry = logger.current_session_logs[0]
        assert entry.status == "failed"
        assert entry.error_message == "Test error"
        assert entry.details["error_code"] == 500
        assert entry.duration_seconds == 2.0
    
    def test_log_operation_skipped(self, temp_log_dir):
        """Test logging operation skipped"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        operation_id = logger.log_operation_start("test_op", "0x1234", "app-123")
        logger.log_operation_skipped(operation_id, "Low confidence", {"confidence": 0.3})
        
        entry = logger.current_session_logs[0]
        assert entry.status == "skipped"
        assert entry.details["skip_reason"] == "Low confidence"
        assert entry.details["confidence"] == 0.3
    
    def test_log_market_monitor_summary(self, temp_log_dir):
        """Test logging market monitor summary"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        with patch.object(logger, '_write_to_jsonl') as mock_write:
            logger.log_market_monitor_summary(50, 5, {"extra": "data"})
            
            mock_write.assert_called_once()
            call_args = mock_write.call_args[0]
            summary_data = call_args[1]
            
            assert summary_data["operation"] == "monitor_summary"
            assert summary_data["total_markets_checked"] == 50
            assert summary_data["completed_markets_found"] == 5
            assert summary_data["details"]["extra"] == "data"
    
    def test_log_resolution_research_result(self, temp_log_dir):
        """Test logging resolution research result"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        with patch.object(logger, '_write_to_jsonl') as mock_write:
            logger.log_resolution_research_result(
                "0x1234",
                "app-123",
                "Yes",
                0.85,
                "Strong evidence found",
                ["source1", "source2"]
            )
            
            mock_write.assert_called_once()
            call_args = mock_write.call_args[0]
            result_data = call_args[1]
            
            assert result_data["operation"] == "research_result"
            assert result_data["market_id"] == "0x1234"
            assert result_data["outcome"] == "Yes"
            assert result_data["confidence"] == 0.85
            assert len(result_data["sources"]) == 2
    
    def test_log_blockchain_resolution(self, temp_log_dir):
        """Test logging blockchain resolution"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        with patch.object(logger, '_write_to_jsonl') as mock_write:
            logger.log_blockchain_resolution(
                "0x1234",
                "app-123",
                "Yes",
                True,
                {"tx_hash": "0xabc123"}
            )
            
            mock_write.assert_called_once()
            call_args = mock_write.call_args[0]
            result_data = call_args[1]
            
            assert result_data["operation"] == "blockchain_resolution"
            assert result_data["market_id"] == "0x1234"
            assert result_data["outcome"] == "Yes"
            assert result_data["success"] is True
            assert result_data["transaction_details"]["tx_hash"] == "0xabc123"
    
    def test_generate_daily_summary(self, temp_log_dir):
        """Test generating daily summary"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Add some test operations
        op1_id = logger.log_operation_start("monitor", "0x1111", "app-1")
        logger.log_operation_complete(op1_id, {}, 1.0)
        
        op2_id = logger.log_operation_start("research", "0x2222", "app-2")
        logger.log_operation_failed(op2_id, "API error", {}, 0.5)
        
        op3_id = logger.log_operation_start("resolve", "0x3333", "app-3")
        logger.log_operation_skipped(op3_id, "Low confidence")
        
        with patch.object(logger, '_write_to_jsonl') as mock_write:
            summary = logger.generate_daily_summary()
        
        assert summary["total_operations"] == 3
        assert summary["operation_counts"]["monitor"]["completed"] == 1
        assert summary["operation_counts"]["research"]["failed"] == 1
        assert summary["operation_counts"]["resolve"]["skipped"] == 1
        assert summary["status_counts"]["completed"] == 1
        assert summary["status_counts"]["failed"] == 1
        assert summary["status_counts"]["skipped"] == 1
        assert summary["success_rate_percent"] == 33.33  # 1/3 * 100
        assert summary["unique_markets_processed"] == 3
        assert summary["unique_applications_processed"] == 3
        assert len(summary["errors"]) == 1
        
        mock_write.assert_called_once()
    
    def test_get_recent_errors(self, temp_log_dir):
        """Test getting recent errors"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Add operations with errors
        op1_id = logger.log_operation_start("test1", "0x1111", "app-1")
        logger.log_operation_failed(op1_id, "Error 1", {"code": 1})
        
        op2_id = logger.log_operation_start("test2", "0x2222", "app-2")
        logger.log_operation_complete(op2_id, {})
        
        op3_id = logger.log_operation_start("test3", "0x3333", "app-3")
        logger.log_operation_failed(op3_id, "Error 2", {"code": 2})
        
        errors = logger.get_recent_errors()
        
        assert len(errors) == 2
        assert errors[0]["error_message"] == "Error 1"
        assert errors[1]["error_message"] == "Error 2"
        assert errors[0]["market_id"] == "0x1111"
        assert errors[1]["market_id"] == "0x3333"
    
    def test_get_operation_logs_no_filter(self, temp_log_dir):
        """Test getting operation logs without filter"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        op1_id = logger.log_operation_start("monitor", "0x1111", "app-1")
        op2_id = logger.log_operation_start("research", "0x2222", "app-2")
        
        logs = logger.get_operation_logs()
        
        assert len(logs) == 2
        assert logs[0]["operation"] == "monitor"
        assert logs[1]["operation"] == "research"
    
    def test_get_operation_logs_with_market_filter(self, temp_log_dir):
        """Test getting operation logs filtered by market ID"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        op1_id = logger.log_operation_start("monitor", "0x1111", "app-1")
        op2_id = logger.log_operation_start("research", "0x2222", "app-2")
        
        logs = logger.get_operation_logs(market_id="0x1111")
        
        assert len(logs) == 1
        assert logs[0]["market_id"] == "0x1111"
    
    def test_get_operation_logs_with_operation_filter(self, temp_log_dir):
        """Test getting operation logs filtered by operation type"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        op1_id = logger.log_operation_start("monitor", "0x1111", "app-1")
        op2_id = logger.log_operation_start("research", "0x2222", "app-2")
        
        logs = logger.get_operation_logs(operation="research")
        
        assert len(logs) == 1
        assert logs[0]["operation"] == "research"
    
    def test_write_to_jsonl_success(self, temp_log_dir):
        """Test successful writing to JSONL file"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        test_file = logger.log_dir / "test.jsonl"
        test_data = {"test": "data", "number": 123}
        
        logger._write_to_jsonl(test_file, test_data)
        
        # Read back the file
        with open(test_file, 'r') as f:
            content = f.read().strip()
            loaded_data = json.loads(content)
        
        assert loaded_data == test_data
    
    def test_write_to_jsonl_error(self, temp_log_dir):
        """Test error handling in writing to JSONL file"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Try to write to a directory that doesn't exist
        invalid_file = Path("/invalid/path/test.jsonl")
        test_data = {"test": "data"}
        
        # Should not raise exception
        logger._write_to_jsonl(invalid_file, test_data)
    
    def test_clear_session_logs(self, temp_log_dir):
        """Test clearing session logs"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Add some logs
        logger.log_operation_start("test", "0x1234", "app-123")
        assert len(logger.current_session_logs) == 1
        
        # Clear logs
        logger.clear_session_logs()
        
        assert len(logger.current_session_logs) == 0
    
    def test_operations_logger_setup(self, temp_log_dir):
        """Test that operations logger is properly set up"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        assert logger.operations_logger.name == "resolution_operations"
        assert len(logger.operations_logger.handlers) > 0
    
    def test_errors_logger_setup(self, temp_log_dir):
        """Test that errors logger is properly set up"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        assert logger.errors_logger.name == "resolution_errors"
        assert len(logger.errors_logger.handlers) > 0


class TestResolutionLoggerEdgeCases:
    """Edge case tests for ResolutionLogger"""
    
    def test_log_operation_complete_nonexistent_id(self, temp_log_dir):
        """Test completing operation with non-existent ID"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Should not raise exception
        logger.log_operation_complete("nonexistent-id", {"test": "data"}, 1.0)
        
        # Should not have any logs
        assert len(logger.current_session_logs) == 0
    
    def test_log_operation_failed_nonexistent_id(self, temp_log_dir):
        """Test failing operation with non-existent ID"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Should not raise exception
        logger.log_operation_failed("nonexistent-id", "Error message")
        
        # Should not have any logs
        assert len(logger.current_session_logs) == 0
    
    def test_generate_daily_summary_empty_logs(self, temp_log_dir):
        """Test generating summary with no logs"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        with patch.object(logger, '_write_to_jsonl') as mock_write:
            summary = logger.generate_daily_summary()
        
        assert summary["total_operations"] == 0
        assert summary["success_rate_percent"] == 0
        assert summary["unique_markets_processed"] == 0
        assert len(summary["errors"]) == 0
        
        mock_write.assert_called_once()
    
    def test_multiple_operations_same_market(self, temp_log_dir):
        """Test multiple operations on the same market"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Add multiple operations for same market
        op1_id = logger.log_operation_start("monitor", "0x1234", "app-123")
        logger.log_operation_complete(op1_id, {})
        
        op2_id = logger.log_operation_start("research", "0x1234", "app-123")
        logger.log_operation_complete(op2_id, {})
        
        summary = logger.generate_daily_summary()
        
        assert summary["total_operations"] == 2
        assert summary["unique_markets_processed"] == 1  # Same market
        assert summary["unique_applications_processed"] == 1  # Same application


@pytest.mark.parametrize("operation_type,expected_count", [
    ("monitor", 1),
    ("research", 2),
    ("resolve", 1),
    ("finalize", 1),
])
def test_operation_counting(operation_type, expected_count, temp_log_dir):
    """Parametrized test for operation counting"""
    logger = ResolutionLogger(log_dir=temp_log_dir)
    
    # Add various operations
    operations = [
        ("monitor", "0x1111", "app-1"),
        ("research", "0x2222", "app-2"),
        ("research", "0x3333", "app-3"),
        ("resolve", "0x4444", "app-4"),
        ("finalize", "0x5555", "app-5"),
    ]
    
    for op_type, market_id, app_id in operations:
        op_id = logger.log_operation_start(op_type, market_id, app_id)
        logger.log_operation_complete(op_id, {})
    
    logs = logger.get_operation_logs(operation=operation_type)
    assert len(logs) == expected_count


@pytest.mark.parametrize("status,expected_in_errors", [
    ("completed", False),
    ("failed", True),
    ("skipped", False),
    ("started", False),
])
def test_error_detection(status, expected_in_errors, temp_log_dir):
    """Parametrized test for error detection"""
    logger = ResolutionLogger(log_dir=temp_log_dir)
    
    op_id = logger.log_operation_start("test", "0x1234", "app-123")
    
    if status == "completed":
        logger.log_operation_complete(op_id, {})
    elif status == "failed":
        logger.log_operation_failed(op_id, "Test error")
    elif status == "skipped":
        logger.log_operation_skipped(op_id, "Test reason")
    # "started" status remains unchanged
    
    errors = logger.get_recent_errors()
    
    if expected_in_errors:
        assert len(errors) == 1
        assert errors[0]["operation"] == "test"
    else:
        assert len(errors) == 0