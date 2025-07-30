"""
Performance and load tests for the market resolution system
"""
import pytest
import time
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
import tempfile
import concurrent.futures
import memory_profiler
import threading
from typing import List

from src.market_monitor import MarketMonitor, MarketStatus
from src.resolution_researcher import GrokResolutionResearcher, ResolutionResult
from src.blockchain_resolver import BlockchainResolver
from src.resolution_logger import ResolutionLogger
from src.daily_scheduler import DailyResolutionScheduler


class TestMarketMonitorPerformance:
    """Performance tests for MarketMonitor"""
    
    @patch('src.market_monitor.get_supabase_client')
    @patch('src.market_monitor.TheGraphClient')
    def test_large_market_dataset_processing(self, mock_graph_client_class, mock_supabase):
        """Test processing large numbers of markets"""
        
        # Create large dataset (1000 markets)
        large_market_dataset = []
        for i in range(1000):
            market = {
                "id": f"market-{i}",
                "application_id": f"app-{i}",
                "market_id": f"0x{i:064x}",
                "market_title": f"Will project {i} receive funding?",
                "status": "active",
                "application": {
                    "id": f"app-{i}",
                    "project": {"name": f"Project {i}"},
                    "program": {"name": "Test Program", "twitter_url": "https://twitter.com/test"}
                }
            }
            large_market_dataset.append(market)
        
        # Setup mocks
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.in_.return_value = mock_client
        mock_client.execute.return_value.data = large_market_dataset
        
        mock_graph_client = mock_graph_client_class.return_value
        mock_graph_client.get_market_status.return_value = {
            "title": "Test market",
            "closed": True,
            "condition": {"resolved": False},
            "resolutionTimestamp": None
        }
        mock_graph_client.is_market_closed_and_unresolved.return_value = True
        
        # Measure performance
        monitor = MarketMonitor()
        
        start_time = time.time()
        result = monitor.check_completed_markets()
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Performance assertions
        assert len(result) > 0  # Should process some markets
        assert execution_time < 30.0  # Should complete within 30 seconds
        assert len(result) <= 1000  # Should handle large dataset
        
        # Calculate throughput
        markets_per_second = len(large_market_dataset) / execution_time
        assert markets_per_second > 10  # Should process at least 10 markets per second
    
    @patch('src.market_monitor.get_supabase_client')
    def test_database_query_performance(self, mock_supabase):
        """Test database query performance with various data sizes"""
        
        data_sizes = [10, 100, 500, 1000]
        execution_times = []
        
        for size in data_sizes:
            # Create dataset of specified size
            dataset = [
                {
                    "id": f"market-{i}",
                    "market_id": f"0x{i:064x}",
                    "application_id": f"app-{i}",
                    "status": "active"
                } for i in range(size)
            ]
            
            mock_client = mock_supabase.return_value
            mock_client.table.return_value = mock_client
            mock_client.select.return_value = mock_client
            mock_client.in_.return_value = mock_client
            mock_client.execute.return_value.data = dataset
            
            monitor = MarketMonitor()
            
            # Measure query time
            start_time = time.time()
            result = monitor.get_markets_to_monitor()
            end_time = time.time()
            
            execution_time = end_time - start_time
            execution_times.append(execution_time)
            
            assert len(result) == size
            assert execution_time < 5.0  # Should complete within 5 seconds
        
        # Verify performance scales reasonably (not exponentially)
        # Time for 1000 items should be less than 10x time for 100 items
        if len(execution_times) >= 4:
            ratio = execution_times[3] / execution_times[1]  # 1000 vs 100
            assert ratio < 10.0  # Performance should scale sub-linearly
    
    @patch('src.market_monitor.requests.post')
    def test_graph_api_concurrent_requests(self, mock_post):
        """Test concurrent Graph API requests performance"""
        
        # Setup mock response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {"fixedProductMarketMaker": {"id": "0x1234", "closed": True}}
        }
        
        client = MarketMonitor().graph_client
        
        # Test concurrent requests
        def make_request(market_id):
            return client.get_market_status(f"0x{market_id:064x}")
        
        start_time = time.time()
        
        # Make 50 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert len(results) == 50
        assert execution_time < 10.0  # Should complete within 10 seconds
        assert all(result is not None for result in results)
        
        # Verify concurrent execution was faster than sequential
        requests_per_second = 50 / execution_time
        assert requests_per_second > 5  # Should achieve decent throughput


class TestResolutionResearcherPerformance:
    """Performance tests for ResolutionResearcher"""
    
    def test_twitter_handle_extraction_performance(self):
        """Test performance of Twitter handle extraction"""
        
        # Create large list of URLs
        test_urls = [
            f"https://twitter.com/user{i}" for i in range(1000)
        ] + [
            f"https://x.com/test_user_{i}?tab=following" for i in range(1000)
        ] + [
            f"@direct_handle_{i}" for i in range(1000)
        ]
        
        researcher = GrokResolutionResearcher()
        
        start_time = time.time()
        
        all_handles = []
        for url in test_urls:
            handles = researcher.extract_twitter_handles_from_url(url)
            all_handles.extend(handles)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert len(all_handles) == 3000  # Should extract all handles
        assert execution_time < 5.0  # Should complete within 5 seconds
        
        urls_per_second = len(test_urls) / execution_time
        assert urls_per_second > 100  # Should process at least 100 URLs per second
    
    def test_response_parsing_performance(self):
        """Test performance of Grok response parsing"""
        
        researcher = GrokResolutionResearcher()
        
        # Create various response formats to test
        test_responses = []
        for i in range(100):
            response = f"""
OUTCOME: {"Yes" if i % 2 == 0 else "No"}
CONFIDENCE: {0.5 + (i % 50) / 100}
REASONING: This is test reasoning number {i} with sufficient detail to meet the minimum length requirements for validation. 
The reasoning includes multiple sentences to simulate real-world responses from the Grok API.
SOURCES: 
- https://twitter.com/test{i}/status/{i}000
- https://twitter.com/source{i}/status/{i}001
- Additional source {i} with more details
"""
            test_responses.append(response)
        
        citations = [Mock(url=f"https://twitter.com/cite{i}/{i}") for i in range(10)]
        twitter_handles = [f"handle{i}" for i in range(20)]
        
        start_time = time.time()
        
        results = []
        for response in test_responses:
            result = researcher._parse_grok_response(response, citations, twitter_handles)
            results.append(result)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert len(results) == 100
        assert execution_time < 2.0  # Should complete within 2 seconds
        assert all(isinstance(r, ResolutionResult) for r in results)
        
        responses_per_second = len(test_responses) / execution_time
        assert responses_per_second > 25  # Should parse at least 25 responses per second
    
    def test_validation_performance(self):
        """Test performance of result validation"""
        
        researcher = GrokResolutionResearcher()
        
        # Create many resolution results to validate
        test_results = []
        for i in range(1000):
            result = ResolutionResult(
                outcome=["Yes", "No", "Invalid"][i % 3],
                confidence=(i % 100) / 100.0,
                reasoning=f"Test reasoning {i} " * 10,  # Longer reasoning
                sources=[f"https://twitter.com/test{i}/status/{j}" for j in range(i % 5 + 1)],
                twitter_handles_searched=[f"handle{j}" for j in range(i % 10 + 1)]
            )
            test_results.append(result)
        
        start_time = time.time()
        
        validation_results = []
        for result in test_results:
            is_valid = researcher.validate_resolution_result(result)
            validation_results.append(is_valid)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert len(validation_results) == 1000
        assert execution_time < 1.0  # Should complete within 1 second
        
        validations_per_second = len(test_results) / execution_time
        assert validations_per_second > 500  # Should validate at least 500 results per second


class TestBlockchainResolverPerformance:
    """Performance tests for BlockchainResolver"""
    
    def test_script_generation_performance(self):
        """Test performance of resolution script generation"""
        
        resolver = BlockchainResolver()
        
        # Create test data
        market_statuses = []
        resolution_results = []
        
        for i in range(100):
            market_status = MarketStatus(
                market_id=f"0x{i:064x}",
                title=f"Will project {i} receive funding from program {i}?",
                closing_time=datetime.now(timezone.utc) - timedelta(days=i % 30),
                is_closed=True,
                is_resolved=False,
                application_id=f"app-{i}",
                funding_program_name=f"Program {i}",
                funding_program_twitter=f"https://twitter.com/program{i}"
            )
            market_statuses.append(market_status)
            
            resolution_result = ResolutionResult(
                outcome=["Yes", "No"][i % 2],
                confidence=0.5 + (i % 50) / 100,
                reasoning=f"Research result {i} with detailed explanation " * 5,
                sources=[f"https://twitter.com/source{j}/status/{i}{j}" for j in range(3)],
                twitter_handles_searched=[f"handle{j}" for j in range(5)]
            )
            resolution_results.append(resolution_result)
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, "Success")
            
            start_time = time.time()
            
            # Generate scripts for all test data
            for market_status, resolution_result in zip(market_statuses, resolution_results):
                if resolution_result.outcome == "Invalid":
                    resolver._submit_invalid_resolution(market_status, {})
                else:
                    resolver._submit_outcome_resolution(market_status, resolution_result, {})
            
            end_time = time.time()
            execution_time = end_time - start_time
        
        # Performance assertions
        assert mock_execute.call_count == 100
        assert execution_time < 5.0  # Should complete within 5 seconds
        
        scripts_per_second = 100 / execution_time
        assert scripts_per_second > 10  # Should generate at least 10 scripts per second
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.chmod')
    @patch('os.unlink')
    def test_concurrent_script_execution_performance(self, mock_unlink, mock_chmod, mock_temp_file, mock_subprocess):
        """Test performance of concurrent script executions"""
        
        resolver = BlockchainResolver()
        
        # Setup mocks
        mock_file = Mock()
        mock_file.name = "/tmp/test.py"
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = '{"success": true}'
        mock_subprocess.return_value.stderr = ""
        
        def execute_script(script_id):
            return resolver._execute_resolution_script(f"print('script {script_id}')", f"script_{script_id}")
        
        start_time = time.time()
        
        # Execute 20 scripts concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_script, i) for i in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert len(results) == 20
        assert all(result[0] is True for result in results)  # All should succeed
        assert execution_time < 10.0  # Should complete within 10 seconds
        
        scripts_per_second = 20 / execution_time
        assert scripts_per_second > 1  # Should achieve reasonable throughput


class TestResolutionLoggerPerformance:
    """Performance tests for ResolutionLogger"""
    
    def test_high_volume_logging_performance(self, temp_log_dir):
        """Test logging performance with high volume of operations"""
        
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Generate large number of log entries
        num_operations = 1000
        
        start_time = time.time()
        
        operation_ids = []
        for i in range(num_operations):
            op_id = logger.log_operation_start(
                f"operation_{i % 5}",  # 5 different operation types
                f"0x{i:064x}",
                f"app-{i}",
                {"detail": f"Operation {i} details", "data": list(range(i % 10))}
            )
            operation_ids.append(op_id)
        
        # Complete operations with various outcomes
        for i, op_id in enumerate(operation_ids):
            if i % 4 == 0:
                logger.log_operation_complete(op_id, {"result": f"success_{i}"}, i * 0.001)
            elif i % 4 == 1:
                logger.log_operation_failed(op_id, f"Error {i}", {"error_code": i % 100})
            elif i % 4 == 2:
                logger.log_operation_skipped(op_id, f"Skipped {i}")
            # Leave some in 'started' state
        
        # Generate summary
        summary = logger.generate_daily_summary()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert len(logger.current_session_logs) == num_operations
        assert execution_time < 10.0  # Should complete within 10 seconds
        assert summary["total_operations"] == num_operations
        
        operations_per_second = num_operations / execution_time
        assert operations_per_second > 50  # Should log at least 50 operations per second
    
    def test_concurrent_logging_performance(self, temp_log_dir):
        """Test concurrent logging performance"""
        
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        def log_operations(thread_id, num_ops):
            operation_ids = []
            for i in range(num_ops):
                op_id = logger.log_operation_start(
                    f"thread_{thread_id}_op_{i}",
                    f"0x{thread_id}{i:08x}",
                    f"app-{thread_id}-{i}"
                )
                operation_ids.append(op_id)
                
                # Immediately complete some operations
                if i % 2 == 0:
                    logger.log_operation_complete(op_id, {"thread": thread_id})
            
            return len(operation_ids)
        
        start_time = time.time()
        
        # Run concurrent logging from multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(log_operations, thread_id, 50) for thread_id in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        total_operations = sum(results)
        assert total_operations == 500  # 10 threads * 50 operations each
        assert len(logger.current_session_logs) == 500
        assert execution_time < 15.0  # Should complete within 15 seconds
        
        operations_per_second = total_operations / execution_time
        assert operations_per_second > 20  # Should handle concurrent logging efficiently
    
    def test_large_data_logging_performance(self, temp_log_dir):
        """Test logging performance with large data payloads"""
        
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Create large data structures
        large_details = {
            "large_list": list(range(1000)),
            "large_string": "A" * 10000,
            "nested_data": {
                f"key_{i}": {
                    "subkey": f"value_{i}",
                    "data": list(range(i % 100))
                } for i in range(100)
            }
        }
        
        start_time = time.time()
        
        # Log operations with large data
        operation_ids = []
        for i in range(50):
            op_id = logger.log_operation_start(
                f"large_data_op_{i}",
                f"0x{i:064x}",
                f"app-{i}",
                large_details
            )
            operation_ids.append(op_id)
            
            logger.log_operation_complete(op_id, large_details, 1.0)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert len(logger.current_session_logs) == 50
        assert execution_time < 20.0  # Should handle large data within reasonable time
        
        # Verify data integrity
        for entry in logger.current_session_logs:
            assert len(entry.details["large_list"]) == 1000
            assert len(entry.details["large_string"]) == 10000


class TestDailySchedulerPerformance:
    """Performance tests for DailyScheduler"""
    
    @pytest.mark.asyncio
    @patch('src.daily_scheduler.MarketMonitor')
    @patch('src.daily_scheduler.GrokResolutionResearcher')
    @patch('src.daily_scheduler.BlockchainResolver')
    @patch('src.daily_scheduler.EmailNotifier')
    async def test_large_scale_workflow_performance(self, mock_email, mock_resolver, mock_researcher, mock_monitor):
        """Test performance of workflow with large number of markets"""
        
        # Create large number of markets
        num_markets = 100
        markets = []
        for i in range(num_markets):
            market = MarketStatus(
                market_id=f"0x{i:064x}",
                title=f"Will project {i} receive funding?",
                closing_time=datetime.now(timezone.utc) - timedelta(days=1),
                is_closed=True,
                is_resolved=False,
                application_id=f"app-{i}",
                funding_program_name=f"Program {i % 10}",  # 10 different programs
                funding_program_twitter=f"https://twitter.com/program{i % 10}"
            )
            markets.append(market)
        
        # Setup mocks for performance
        mock_monitor_instance = mock_monitor.return_value
        mock_monitor_instance.check_completed_markets.return_value = markets
        mock_monitor_instance.update_market_status_in_db = Mock()
        
        # Fast research responses
        def fast_research(market_status):
            return ResolutionResult(
                outcome=["Yes", "No", "Invalid"][hash(market_status.market_id) % 3],
                confidence=0.8,
                reasoning="Fast test reasoning",
                sources=[],
                twitter_handles_searched=[]
            )
        
        mock_researcher_instance = mock_researcher.return_value
        mock_researcher_instance.research_market_resolution.side_effect = fast_research
        mock_researcher_instance.validate_resolution_result.return_value = True
        
        # Fast blockchain responses
        mock_resolver_instance = mock_resolver.return_value
        mock_resolver_instance.resolve_market_on_blockchain.return_value = (True, "Fast success")
        mock_resolver_instance.check_market_needs_final_resolution.return_value = (False, "No finalization needed")
        
        mock_email_instance = mock_email.return_value
        mock_email_instance.send_daily_report = Mock()
        
        # Configure for performance testing
        scheduler = DailyResolutionScheduler()
        scheduler.resolution_delay_seconds = 0.01  # Minimal delay
        scheduler.max_markets_per_run = num_markets  # Process all markets
        
        with patch('src.daily_scheduler.resolution_logger') as mock_logger:
            mock_logger.generate_daily_summary.return_value = {"test": "summary"}
            mock_logger.get_recent_errors.return_value = []
            
            start_time = time.time()
            
            result = await scheduler.run_daily_resolution_cycle()
            
            end_time = time.time()
            execution_time = end_time - start_time
        
        # Performance assertions
        assert isinstance(result, dict)
        assert execution_time < 60.0  # Should complete within 1 minute
        
        # Verify all markets were processed
        assert mock_researcher_instance.research_market_resolution.call_count == num_markets
        
        markets_per_second = num_markets / execution_time
        assert markets_per_second > 1  # Should process at least 1 market per second
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_workflow(self):
        """Test memory usage patterns during workflow execution"""
        
        # This test requires memory_profiler
        try:
            initial_memory = memory_profiler.memory_usage()[0]
        except:
            pytest.skip("memory_profiler not available")
        
        with patch('src.daily_scheduler.MarketMonitor') as mock_monitor, \
             patch('src.daily_scheduler.GrokResolutionResearcher') as mock_researcher, \
             patch('src.daily_scheduler.BlockchainResolver') as mock_resolver, \
             patch('src.daily_scheduler.EmailNotifier') as mock_email:
            
            # Create moderate number of markets with varying data sizes
            markets = []
            for i in range(50):
                market = MarketStatus(
                    market_id=f"0x{i:064x}",
                    title=f"Large market title {i} " * (i % 10 + 1),  # Varying title sizes
                    closing_time=datetime.now(timezone.utc),
                    is_closed=True,
                    is_resolved=False,
                    application_id=f"app-{i}",
                    funding_program_name=f"Program {i}",
                    funding_program_twitter=None
                )
                markets.append(market)
            
            mock_monitor_instance = mock_monitor.return_value
            mock_monitor_instance.check_completed_markets.return_value = markets
            
            mock_researcher_instance = mock_researcher.return_value
            mock_researcher_instance.research_market_resolution.return_value = ResolutionResult(
                outcome="Yes", confidence=0.8, reasoning="Test", sources=[], twitter_handles_searched=[]
            )
            mock_researcher_instance.validate_resolution_result.return_value = True
            
            mock_resolver_instance = mock_resolver.return_value
            mock_resolver_instance.resolve_market_on_blockchain.return_value = (True, "Success")
            
            mock_email_instance = mock_email.return_value
            mock_email_instance.send_daily_report = Mock()
            
            scheduler = DailyResolutionScheduler()
            
            with patch('src.daily_scheduler.resolution_logger') as mock_logger:
                mock_logger.generate_daily_summary.return_value = {"test": "summary"}
                mock_logger.get_recent_errors.return_value = []
                
                # Monitor memory during execution
                start_memory = memory_profiler.memory_usage()[0]
                
                result = await scheduler.run_daily_resolution_cycle()
                
                end_memory = memory_profiler.memory_usage()[0]
                memory_increase = end_memory - start_memory
        
        # Memory usage assertions
        assert isinstance(result, dict)
        assert memory_increase < 100  # Should not increase memory by more than 100MB
        
        # Verify final memory is not too much higher than initial
        final_memory = memory_profiler.memory_usage()[0]
        total_increase = final_memory - initial_memory
        assert total_increase < 200  # Total memory increase should be reasonable


@pytest.mark.parametrize("dataset_size,expected_max_time", [
    (10, 2.0),      # Small dataset should complete quickly
    (100, 10.0),    # Medium dataset should complete in reasonable time
    (500, 30.0),    # Large dataset should still complete within timeout
])
def test_scalability_performance(dataset_size, expected_max_time):
    """Parametrized test for scalability performance"""
    
    with patch('src.market_monitor.get_supabase_client') as mock_supabase, \
         patch('src.market_monitor.TheGraphClient') as mock_graph_client_class:
        
        # Create dataset of specified size
        dataset = [
            {
                "id": f"market-{i}",
                "market_id": f"0x{i:064x}",
                "application_id": f"app-{i}",
                "status": "active",
                "application": {
                    "project": {"name": f"Project {i}"},
                    "program": {"name": "Test Program", "twitter_url": "https://twitter.com/test"}
                }
            } for i in range(dataset_size)
        ]
        
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.in_.return_value = mock_client
        mock_client.execute.return_value.data = dataset
        
        mock_graph_client = mock_graph_client_class.return_value
        mock_graph_client.get_market_status.return_value = {
            "title": "Test", "closed": True, "condition": {"resolved": False}
        }
        mock_graph_client.is_market_closed_and_unresolved.return_value = True
        
        monitor = MarketMonitor()
        
        start_time = time.time()
        result = monitor.check_completed_markets()
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Performance assertions based on dataset size
        assert execution_time < expected_max_time
        assert len(result) <= dataset_size


class TestResourceUtilization:
    """Test resource utilization patterns"""
    
    def test_file_handle_management(self, temp_log_dir):
        """Test that file handles are properly managed"""
        import psutil
        import os
        
        # Get initial file descriptor count
        process = psutil.Process(os.getpid())
        initial_fds = len(process.open_files())
        
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        # Perform many logging operations that create/close files
        for i in range(100):
            op_id = logger.log_operation_start(f"test_{i}", f"0x{i:04x}", f"app_{i}")
            logger.log_operation_complete(op_id, {"test": "data"})
            
            # Force file operations
            logger.log_market_monitor_summary(i, i % 5)
            logger.log_resolution_research_result(f"0x{i:04x}", f"app_{i}", "Yes", 0.8, "test", [])
        
        # Generate summary (more file operations)
        summary = logger.generate_daily_summary()
        
        # Check file descriptor count hasn't grown excessively
        final_fds = len(process.open_files())
        fd_increase = final_fds - initial_fds
        
        assert fd_increase < 10  # Should not leak file descriptors
        assert isinstance(summary, dict)
    
    def test_thread_safety_performance(self, temp_log_dir):
        """Test thread safety under concurrent load"""
        
        logger = ResolutionLogger(log_dir=temp_log_dir)
        
        def concurrent_logging(thread_id):
            results = []
            for i in range(50):
                try:
                    op_id = logger.log_operation_start(
                        f"thread_{thread_id}_op_{i}",
                        f"0x{thread_id:02x}{i:04x}",
                        f"app_{thread_id}_{i}"
                    )
                    logger.log_operation_complete(op_id, {"thread": thread_id, "op": i})
                    results.append(True)
                except Exception as e:
                    results.append(False)
            return results
        
        # Run concurrent operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(concurrent_logging, i) for i in range(20)]
            all_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify thread safety and performance
        total_operations = sum(len(results) for results in all_results)
        successful_operations = sum(sum(results) for results in all_results)
        
        assert total_operations == 1000  # 20 threads * 50 operations
        assert successful_operations == total_operations  # All should succeed
        assert execution_time < 30.0  # Should complete within reasonable time
        
        # Verify data integrity
        assert len(logger.current_session_logs) == 1000
        
        # Check for data corruption (unique operation IDs)
        operation_ids = [entry.id for entry in logger.current_session_logs]
        assert len(set(operation_ids)) == len(operation_ids)  # All IDs should be unique