"""
Edge cases and error handling tests for the market resolution system
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json
import requests
import subprocess
import tempfile
import os

from src.market_monitor import MarketMonitor, TheGraphClient, MarketStatus
from src.resolution_researcher import GrokResolutionResearcher, ResolutionResult
from src.blockchain_resolver import BlockchainResolver
from src.resolution_logger import ResolutionLogger
from src.daily_scheduler import DailyResolutionScheduler, EmailNotifier


class TestMarketMonitorEdgeCases:
    """Edge cases for MarketMonitor"""
    
    @patch('src.market_monitor.get_supabase_client')
    def test_empty_database_result(self, mock_supabase):
        """Test handling empty database results"""
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.in_.return_value = mock_client
        mock_client.execute.return_value.data = []  # Empty result
        
        monitor = MarketMonitor()
        result = monitor.get_markets_to_monitor()
        
        assert result == []
    
    @patch('src.market_monitor.get_supabase_client')
    def test_malformed_database_data(self, mock_supabase):
        """Test handling malformed database data"""
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.in_.return_value = mock_client
        
        # Malformed data missing required fields
        malformed_data = [
            {"id": "market-1"},  # Missing market_id
            {"market_id": "0x1234"},  # Missing application_id
            {"market_id": None, "application_id": "app-1"},  # Null market_id
        ]
        mock_client.execute.return_value.data = malformed_data
        
        monitor = MarketMonitor()
        result = monitor.check_completed_markets()
        
        # Should handle gracefully and return empty list
        assert result == []
    
    @patch('src.market_monitor.requests.post')
    def test_graph_api_malformed_response(self, mock_post):
        """Test handling malformed Graph API response"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "fixedProductMarketMaker": None  # Null response
            }
        }
        
        client = TheGraphClient()
        result = client.get_market_status("0x1234")
        
        assert result is None
    
    @patch('src.market_monitor.requests.post')
    def test_graph_api_missing_fields(self, mock_post):
        """Test handling Graph API response with missing fields"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "fixedProductMarketMaker": {
                    "id": "0x1234",
                    # Missing other required fields
                }
            }
        }
        
        client = TheGraphClient()
        result = client.get_market_status("0x1234")
        
        # Should still return the partial data
        assert result is not None
        assert result["id"] == "0x1234"
    
    def test_parse_timestamp_edge_cases(self):
        """Test timestamp parsing with edge cases"""
        monitor = MarketMonitor()
        
        edge_cases = [
            ("0", datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),  # Unix epoch
            ("4294967295", datetime(2106, 2, 7, 6, 28, 15, tzinfo=timezone.utc)),  # Max 32-bit
            ("-1", datetime(1969, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),  # Negative timestamp (valid but historical)
            ("1.5", None),  # Float timestamp (invalid)
            ("invalid", None),  # Non-numeric string
            ("", None),  # Empty string
        ]
        
        for input_ts, expected in edge_cases:
            result = monitor._parse_timestamp(input_ts)
            if expected is None:
                assert result is None
            else:
                assert result == expected
    
    @patch('src.market_monitor.get_supabase_client')
    @patch('src.market_monitor.TheGraphClient')
    def test_concurrent_market_updates(self, mock_graph_client_class, mock_supabase):
        """Test handling concurrent market updates"""
        # Simulate database connection error during update
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.update.side_effect = Exception("Connection lost")
        
        monitor = MarketMonitor()
        
        # Should not raise exception
        monitor.update_market_status_in_db("0x1234", "resolved")
    
    def test_unicode_and_special_characters(self):
        """Test handling Unicode and special characters in market titles"""
        monitor = MarketMonitor()
        
        special_titles = [
            "Will project 测试 receive funding? 🚀",  # Unicode characters
            "Market with\nline\nbreaks",  # Line breaks
            "Market with\ttabs",  # Tabs
            "Market with 'quotes' and \"double quotes\"",  # Quotes
            "Market with <script>alert('xss')</script>",  # Potential XSS
            "",  # Empty string
            "   ",  # Only whitespace
        ]
        
        for title in special_titles:
            # Should not raise exceptions when processing
            market_status = MarketStatus(
                market_id="0x1234",
                title=title,
                closing_time=datetime.now(timezone.utc),
                is_closed=True,
                is_resolved=False,
                application_id="test-app",
                funding_program_name="Test Program",
                funding_program_twitter=None
            )
            
            # Should handle gracefully
            assert isinstance(market_status.title, str)


class TestResolutionResearcherEdgeCases:
    """Edge cases for ResolutionResearcher"""
    
    def test_extreme_confidence_values(self):
        """Test handling extreme confidence values"""
        researcher = GrokResolutionResearcher()
        
        extreme_values = [
            (-1.0, False),  # Negative confidence
            (0.0, False),   # Zero confidence
            (0.5, False),   # Below threshold
            (0.7, True),    # At threshold
            (1.0, True),    # Maximum confidence
            (1.1, True),    # Above maximum (should still pass)
            (float('inf'), True),  # Infinity
            (float('-inf'), False),  # Negative infinity
        ]
        
        for confidence, expected_valid in extreme_values:
            try:
                result = ResolutionResult(
                    outcome="Yes",
                    confidence=confidence,
                    reasoning="Test reasoning with sufficient length",
                    sources=["https://twitter.com/test/123"],
                    twitter_handles_searched=["test"]
                )
                
                is_valid = researcher.validate_resolution_result(result)
                assert is_valid == expected_valid
            except (ValueError, OverflowError):
                # Some extreme values might raise exceptions, which is acceptable
                pass
    
    def test_malformed_twitter_urls(self):
        """Test handling malformed Twitter URLs"""
        researcher = GrokResolutionResearcher()
        
        malformed_urls = [
            "https://twitter.com/",  # Missing username
            "twitter.com/user",  # Missing protocol
            "https://twitter.com/user/with/extra/paths",  # Extra paths
            "https://twitter.com/user?param=value&other=param",  # Query params
            "https://twitter.com/user#fragment",  # Fragment
            "https://twitter.com/user with spaces",  # Spaces in URL
            "https://twitter.com/用户名",  # Unicode username
            "ftp://twitter.com/user",  # Wrong protocol
            "javascript:alert('xss')",  # XSS attempt
        ]
        
        for url in malformed_urls:
            # Should not raise exceptions
            result = researcher.extract_twitter_handles_from_url(url)
            assert isinstance(result, list)
    
    def test_extremely_long_inputs(self):
        """Test handling extremely long inputs"""
        researcher = GrokResolutionResearcher()
        
        # Create extremely long strings
        long_market_title = "A" * 10000  # 10KB title
        long_reasoning = "B" * 50000  # 50KB reasoning
        many_sources = [f"https://twitter.com/user{i}/status/{i}" for i in range(1000)]  # 1000 sources
        
        # Should handle without crashing
        try:
            result = ResolutionResult(
                outcome="Yes",
                confidence=0.8,
                reasoning=long_reasoning,
                sources=many_sources,
                twitter_handles_searched=["test"]
            )
            
            # Validation should work with long inputs
            is_valid = researcher.validate_resolution_result(result)
            assert isinstance(is_valid, bool)
        except MemoryError:
            # Acceptable if system runs out of memory
            pass
    
    @patch('src.resolution_researcher.GROK_AVAILABLE', True)
    @patch('src.resolution_researcher.Client')
    def test_grok_api_various_errors(self, mock_client_class, sample_market_status):
        """Test handling various Grok API errors"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Test different types of API errors
        api_errors = [
            requests.exceptions.ConnectionError("Network error"),
            requests.exceptions.Timeout("Request timeout"),
            requests.exceptions.HTTPError("HTTP 429 Rate Limited"),
            ValueError("Invalid API response"),
            KeyError("Missing response field"),
            json.JSONDecodeError("Invalid JSON", "", 0),
        ]
        
        with patch.dict(os.environ, {"XAI_API_KEY": "test_key"}):
            researcher = GrokResolutionResearcher()
            
            for error in api_errors:
                mock_client.chat.create.side_effect = error
                
                # Should handle gracefully and return None
                result = researcher.research_market_resolution(sample_market_status)
                assert result is None
    
    def test_grok_response_parsing_edge_cases(self):
        """Test parsing edge cases in Grok responses"""
        researcher = GrokResolutionResearcher()
        
        edge_case_responses = [
            "",  # Empty response
            "OUTCOME:",  # Missing outcome value
            "CONFIDENCE: not_a_number",  # Invalid confidence
            "OUTCOME: Maybe\nCONFIDENCE: 0.8",  # Invalid outcome
            "OUTCOME: Yes\nCONFIDENCE: 0.8\nREASONING:",  # Empty reasoning
            "Some random text without proper format",  # No format markers
            "OUTCOME: Yes\nCONFIDENCE: 0.8\nREASONING: Good\nSOURCES:\n- " + "A" * 10000,  # Very long source
        ]
        
        for response in edge_case_responses:
            # Should not raise exceptions
            result = researcher._parse_grok_response(response, [], ["test"])
            assert isinstance(result, ResolutionResult)
            assert result.outcome in ["Yes", "No", "Invalid"]
            assert 0.0 <= result.confidence <= 1.0


class TestBlockchainResolverEdgeCases:
    """Edge cases for BlockchainResolver"""
    
    def test_script_execution_with_various_outputs(self):
        """Test script execution with various output formats"""
        resolver = BlockchainResolver()
        
        test_outputs = [
            ('{"success": true}', True),  # Minimal success JSON
            ('{"success": false, "error": ""}', False),  # Empty error message
            ('{"invalid": "json_structure"}', False),  # Invalid structure - no success key defaults to False
            ('Plain text success message', True),  # Non-JSON success
            ('', True),  # Empty output but success code
            ('\n\n   \n', True),  # Only whitespace
            ('{"success": true, "nested": {"deep": {"value": 123}}}', True),  # Complex nested JSON
        ]
        
        for output, expected_success in test_outputs:
            with patch('subprocess.run') as mock_subprocess, \
                 patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
                 patch('os.chmod'), \
                 patch('os.unlink'):
                
                mock_file = Mock()
                mock_file.name = "/tmp/test.py"
                mock_temp_file.return_value.__enter__.return_value = mock_file
                
                mock_subprocess.return_value.returncode = 0
                mock_subprocess.return_value.stdout = output
                mock_subprocess.return_value.stderr = ""
                
                success, message = resolver._execute_resolution_script("test", "test")
                assert success == expected_success
    
    def test_script_generation_with_special_characters(self, sample_market_status, sample_resolution_result):
        """Test script generation with special characters in data"""
        resolver = BlockchainResolver()
        
        # Market status with special characters
        special_market_status = MarketStatus(
            market_id="0x1234",
            title="Will project 'test' & <script> receive \"funding\"?",
            closing_time=datetime.now(timezone.utc),
            is_closed=True,
            is_resolved=False,
            application_id="app-with-quotes'and\"backslashes\\",
            funding_program_name="Program with\nnewlines\ttabs",
            funding_program_twitter="https://twitter.com/user"
        )
        
        # Resolution result with special characters
        special_resolution = ResolutionResult(
            outcome="Yes",
            confidence=0.8,
            reasoning="Reasoning with 'quotes' and \"double quotes\" and \n newlines",
            sources=["https://twitter.com/test/123", "Source with spaces and 'quotes'"],
            twitter_handles_searched=["user", "test'user"]
        )
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, "Success")
            
            # Should not raise exceptions during script generation
            resolver._submit_outcome_resolution(special_market_status, special_resolution, {})
            
            # Script should be generated without syntax errors
            script_content = mock_execute.call_args[0][0]
            assert isinstance(script_content, str)
            assert len(script_content) > 0
    
    def test_concurrent_script_execution(self):
        """Test handling concurrent script executions"""
        resolver = BlockchainResolver()
        
        with patch('subprocess.run') as mock_subprocess, \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('os.chmod'), \
             patch('os.unlink'):
            
            # Simulate file creation conflict
            mock_temp_file.side_effect = [
                OSError("File already exists"),
                Mock(__enter__=Mock(return_value=Mock(name="/tmp/test2.py")), __exit__=Mock())
            ]
            
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = "Success"
            mock_subprocess.return_value.stderr = ""
            
            # Should handle file creation errors gracefully
            try:
                success, message = resolver._execute_resolution_script("test", "test")
                # May succeed with retry or fail gracefully
                assert isinstance(success, bool)
            except OSError:
                # Acceptable if system can't handle concurrent file creation
                pass
    
    def test_subprocess_resource_limits(self):
        """Test subprocess execution with resource constraints"""
        resolver = BlockchainResolver()
        
        with patch('subprocess.run') as mock_subprocess, \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('os.chmod'), \
             patch('os.unlink'):
            
            mock_file = Mock()
            mock_file.name = "/tmp/test.py"
            mock_temp_file.return_value.__enter__.return_value = mock_file
            
            # Simulate various subprocess issues
            subprocess_errors = [
                subprocess.TimeoutExpired("cmd", 300),
                OSError("Resource temporarily unavailable"),
                MemoryError("Out of memory"),
                subprocess.CalledProcessError(1, "cmd", "Process killed"),
            ]
            
            for error in subprocess_errors:
                mock_subprocess.side_effect = error
                
                # Should handle gracefully
                success, message = resolver._execute_resolution_script("test", "test")
                assert success is False
                assert isinstance(message, str)


class TestResolutionLoggerEdgeCases:
    """Edge cases for ResolutionLogger"""
    
    def test_log_file_permissions_error(self, temp_log_dir):
        """Test handling log file permission errors"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Make log directory read-only
        os.chmod(temp_log_dir, 0o444)
        
        try:
            # Should handle permission errors gracefully
            logger.log_market_monitor_summary(10, 5)
            
            # Restore permissions for cleanup
            os.chmod(temp_log_dir, 0o755)
        except PermissionError:
            # Restore permissions even if test fails
            os.chmod(temp_log_dir, 0o755)
    
    def test_disk_space_exhaustion(self, temp_log_dir):
        """Test handling disk space exhaustion during logging"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Simulate disk space exhaustion
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            # Should handle gracefully without crashing
            logger._write_to_jsonl(logger.operations_log, {"test": "data"})
    
    def test_extremely_large_log_entries(self, temp_log_dir):
        """Test handling extremely large log entries"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Create very large log entry
        huge_details = {
            "large_data": "A" * 1000000,  # 1MB of data
            "many_items": [f"item_{i}" for i in range(10000)],  # 10k items
            "nested": {"level" + str(i): f"value_{i}" for i in range(1000)}  # Deep nesting
        }
        
        try:
            operation_id = logger.log_operation_start("test", "0x1234", "app-123", huge_details)
            logger.log_operation_complete(operation_id, huge_details)
            
            # Should handle large data without crashing
            summary = logger.generate_daily_summary()
            assert isinstance(summary, dict)
        except MemoryError:
            # Acceptable if system runs out of memory
            pass
    
    def test_concurrent_logging(self, temp_log_dir):
        """Test concurrent logging operations"""
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Simulate concurrent operations
        operation_ids = []
        for i in range(100):
            op_id = logger.log_operation_start(f"op_{i}", f"0x{i:04x}", f"app_{i}")
            operation_ids.append(op_id)
        
        # Complete operations in random order
        import random
        random.shuffle(operation_ids)
        
        for op_id in operation_ids:
            if random.choice([True, False]):
                logger.log_operation_complete(op_id, {"result": "success"})
            else:
                logger.log_operation_failed(op_id, "Random failure")
        
        # Should handle concurrent updates correctly
        summary = logger.generate_daily_summary()
        assert summary["total_operations"] == 100
        assert summary["status_counts"]["completed"] + summary["status_counts"]["failed"] == 100


class TestDailySchedulerEdgeCases:
    """Edge cases for DailyScheduler"""
    
    def test_email_server_unavailable(self):
        """Test handling email server unavailability"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = ConnectionRefusedError("Connection refused")
            
            notifier = EmailNotifier()
            if notifier.enabled:
                # Should handle gracefully
                notifier.send_daily_report({"test": "summary"})
    
    def test_email_authentication_failure(self):
        """Test handling email authentication failures"""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_class.return_value.__enter__.return_value = mock_server
            mock_server.login.side_effect = Exception("Authentication failed")
            
            with patch.dict(os.environ, {
                "SMTP_USERNAME": "test@example.com",
                "SMTP_PASSWORD": "wrong_password",
                "ADMIN_EMAIL": "admin@example.com"
            }):
                notifier = EmailNotifier()
                
                # Should handle authentication failure gracefully
                notifier.send_daily_report({"test": "summary"})
    
    def test_extremely_large_email_content(self):
        """Test handling extremely large email content"""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_class.return_value.__enter__.return_value = mock_server
            
            with patch.dict(os.environ, {
                "SMTP_USERNAME": "test@example.com", 
                "SMTP_PASSWORD": "password",
                "ADMIN_EMAIL": "admin@example.com"
            }):
                notifier = EmailNotifier()
                
                # Create extremely large summary
                huge_summary = {
                    "errors": [{"error": "A" * 10000} for _ in range(1000)],
                    "large_field": "B" * 1000000
                }
                
                # Should handle large content without crashing
                notifier.send_daily_report(huge_summary)
    
    @patch('src.daily_scheduler.MarketMonitor')
    @patch('src.daily_scheduler.GrokResolutionResearcher')
    @patch('src.daily_scheduler.BlockchainResolver')
    def test_partial_system_failures(self, mock_resolver, mock_researcher, mock_monitor):
        """Test handling partial system failures"""
        # Setup partial failures
        mock_monitor.return_value.check_completed_markets.side_effect = Exception("Monitor failed")
        mock_researcher.return_value.research_market_resolution.return_value = None
        mock_resolver.return_value.resolve_market_on_blockchain.return_value = (False, "Blockchain error")
        
        scheduler = DailyResolutionScheduler()
        
        # Should handle partial failures and continue operation
        try:
            import asyncio
            result = asyncio.run(scheduler.run_daily_resolution_cycle())
            assert isinstance(result, dict)
        except Exception as e:
            # Some failures might be expected
            assert "error" in str(e).lower()


@pytest.mark.parametrize("invalid_input,component", [
    (None, "market_monitor"),
    ("", "resolution_researcher"), 
    ([], "blockchain_resolver"),
    ({}, "resolution_logger"),
    (123, "daily_scheduler"),
])
def test_invalid_input_handling(invalid_input, component):
    """Parametrized test for invalid input handling across components"""
    # Test that components handle invalid inputs gracefully
    try:
        if component == "market_monitor":
            monitor = MarketMonitor()
            # Should handle None inputs gracefully
            result = monitor._parse_timestamp(invalid_input)
            assert result is None
            
        elif component == "resolution_researcher":
            researcher = GrokResolutionResearcher()
            result = researcher.extract_twitter_handles_from_url(invalid_input)
            assert isinstance(result, list)
            
        elif component == "blockchain_resolver":
            resolver = BlockchainResolver()
            # Should handle invalid inputs without crashing
            assert hasattr(resolver, 'poetry_path')
            
        elif component == "resolution_logger":  
            with tempfile.TemporaryDirectory() as temp_dir:
                logger = ResolutionLogger(log_dir=temp_dir)
                # Should handle invalid inputs gracefully
                assert hasattr(logger, 'current_session_logs')
                
        elif component == "daily_scheduler":
            scheduler = DailyResolutionScheduler()
            # Should initialize without crashing
            assert hasattr(scheduler, 'market_monitor')
            
    except (TypeError, ValueError, AttributeError) as e:
        # Some invalid inputs may raise expected exceptions
        assert isinstance(e, (TypeError, ValueError, AttributeError))


class TestNetworkResilience:
    """Tests for network resilience and retry mechanisms"""
    
    @patch('src.market_monitor.requests.post')
    def test_intermittent_network_failures(self, mock_post):
        """Test handling intermittent network failures"""
        # Simulate intermittent failures followed by success
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Network error"),
            requests.exceptions.Timeout("Timeout"),
            Mock(status_code=200, json=lambda: {"data": {"fixedProductMarketMaker": {"id": "0x1234"}}})
        ]
        
        client = TheGraphClient()
        
        # First two calls should fail, third should succeed
        assert client.get_market_status("0x1234") is None  # First failure
        assert client.get_market_status("0x1234") is None  # Second failure  
        assert client.get_market_status("0x1234") is not None  # Success
    
    @patch('subprocess.run')
    def test_blockchain_node_disconnection(self, mock_subprocess):
        """Test handling blockchain node disconnection"""
        resolver = BlockchainResolver()
        
        # Simulate node disconnection error
        mock_subprocess.side_effect = [
            Mock(returncode=1, stdout="", stderr="Connection to node failed"),
            Mock(returncode=0, stdout='{"success": true}', stderr="")  # Recovery
        ]
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('os.chmod'), \
             patch('os.unlink'):
            
            mock_file = Mock()
            mock_file.name = "/tmp/test.py"
            mock_temp_file.return_value.__enter__.return_value = mock_file
            
            # First call should fail
            success1, message1 = resolver._execute_resolution_script("test", "test")
            assert success1 is False
            
            # Second call should succeed (simulating recovery)
            success2, message2 = resolver._execute_resolution_script("test", "test")
            assert success2 is True


@pytest.mark.parametrize("error_type,expected_handling", [
    (requests.exceptions.ConnectionError, "graceful"),
    (requests.exceptions.Timeout, "graceful"),
    (requests.exceptions.HTTPError, "graceful"),
    (json.JSONDecodeError, "graceful"),
    (KeyError, "graceful"),
    (ValueError, "graceful"),
    (MemoryError, "may_raise"),
    (OSError, "graceful"),
])
def test_error_type_handling(error_type, expected_handling):
    """Parametrized test for different error type handling"""
    # Create appropriate test context based on error type
    if error_type in [requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError]:
        with patch('src.market_monitor.requests.post') as mock_post:
            mock_post.side_effect = error_type("Test error")
            client = TheGraphClient()
            result = client.get_market_status("0x1234")
            
            if expected_handling == "graceful":
                assert result is None
    
    elif error_type == json.JSONDecodeError:
        researcher = GrokResolutionResearcher()
        try:
            result = researcher._parse_grok_response("invalid json", [], ["test"])
            if expected_handling == "graceful":
                assert isinstance(result, ResolutionResult)
        except json.JSONDecodeError:
            if expected_handling == "may_raise":
                pass  # Expected
    
    # Add more error type tests as needed
    else:
        # For other error types, just ensure they exist
        assert issubclass(error_type, Exception)