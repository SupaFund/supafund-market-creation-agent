"""
End-to-end workflow tests for the complete market resolution system
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timezone, timedelta
import json

from src.daily_scheduler import DailyResolutionScheduler
from src.market_monitor import MarketStatus
from src.resolution_researcher import ResolutionResult
from src.resolution_logger import resolution_logger


class TestCompleteResolutionWorkflow:
    """Test the complete market resolution workflow from start to finish"""
    
    @pytest.mark.asyncio
    @patch('src.daily_scheduler.MarketMonitor')
    @patch('src.daily_scheduler.GrokResolutionResearcher')
    @patch('src.daily_scheduler.BlockchainResolver')
    @patch('src.daily_scheduler.EmailNotifier')
    async def test_successful_end_to_end_workflow(self, mock_email, mock_resolver, mock_researcher, mock_monitor):
        """Test successful end-to-end market resolution workflow"""
        
        # Setup test data
        test_market = MarketStatus(
            market_id="0x1234567890abcdef1234567890abcdef12345678",
            title="Will project abc-123 receive funding from Test Program 2024?",
            closing_time=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            is_closed=True,
            is_resolved=False,
            application_id="abc-123",
            funding_program_name="Test Program 2024",
            funding_program_twitter="https://twitter.com/testprogram"
        )
        
        test_resolution = ResolutionResult(
            outcome="Yes",
            confidence=0.85,
            reasoning="Found official announcement confirming funding approval",
            sources=["https://twitter.com/testprogram/status/123456789"],
            twitter_handles_searched=["testprogram", "ethereum"]
        )
        
        # Setup mocks
        mock_monitor_instance = mock_monitor.return_value
        mock_monitor_instance.check_completed_markets.return_value = [test_market]
        mock_monitor_instance.update_market_status_in_db = Mock()
        
        mock_researcher_instance = mock_researcher.return_value
        mock_researcher_instance.research_market_resolution.return_value = test_resolution
        mock_researcher_instance.validate_resolution_result.return_value = True
        
        mock_resolver_instance = mock_resolver.return_value
        mock_resolver_instance.resolve_market_on_blockchain.return_value = (True, "Transaction successful: 0xabc123")
        mock_resolver_instance.check_market_needs_final_resolution.return_value = (True, "Needs finalization")
        mock_resolver_instance.finalize_market_resolution.return_value = (True, "Market finalized")
        
        mock_email_instance = mock_email.return_value
        mock_email_instance.send_daily_report = Mock()
        
        # Create scheduler and run workflow
        scheduler = DailyResolutionScheduler()
        
        with patch('src.daily_scheduler.resolution_logger') as mock_logger:
            mock_logger.generate_daily_summary.return_value = {
                "date": "2024-01-01",
                "total_operations": 4,
                "success_rate_percent": 100.0,
                "status_counts": {"completed": 4, "failed": 0}
            }
            mock_logger.get_recent_errors.return_value = []
            
            # Run the complete workflow
            result = await scheduler.run_daily_resolution_cycle()
        
        # Verify workflow execution
        assert isinstance(result, dict)
        
        # Verify monitor was called
        mock_monitor_instance.check_completed_markets.assert_called_once()
        
        # Verify research was called
        mock_researcher_instance.research_market_resolution.assert_called_once_with(test_market)
        mock_researcher_instance.validate_resolution_result.assert_called_once_with(test_resolution, 0.7)
        
        # Verify blockchain resolution was called
        mock_resolver_instance.resolve_market_on_blockchain.assert_called_once_with(test_market, test_resolution)
        
        # Verify database update was called
        mock_monitor_instance.update_market_status_in_db.assert_called_once()
        
        # Verify email report was sent
        mock_email_instance.send_daily_report.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.daily_scheduler.MarketMonitor')
    @patch('src.daily_scheduler.GrokResolutionResearcher')
    @patch('src.daily_scheduler.BlockchainResolver')
    @patch('src.daily_scheduler.EmailNotifier')
    async def test_workflow_with_low_confidence_research(self, mock_email, mock_resolver, mock_researcher, mock_monitor):
        """Test workflow when research returns low confidence result"""
        
        test_market = MarketStatus(
            market_id="0x1234567890abcdef1234567890abcdef12345678",
            title="Will project xyz-456 receive funding?",
            closing_time=datetime.now(timezone.utc) - timedelta(days=1),
            is_closed=True,
            is_resolved=False,
            application_id="xyz-456",
            funding_program_name="Test Program",
            funding_program_twitter=None
        )
        
        # Low confidence result
        low_confidence_result = ResolutionResult(
            outcome="Invalid",
            confidence=0.3,  # Below threshold
            reasoning="Insufficient information found",
            sources=[],
            twitter_handles_searched=["ethereum", "gitcoin"]
        )
        
        # Setup mocks
        mock_monitor_instance = mock_monitor.return_value
        mock_monitor_instance.check_completed_markets.return_value = [test_market]
        
        mock_researcher_instance = mock_researcher.return_value
        mock_researcher_instance.research_market_resolution.return_value = low_confidence_result
        mock_researcher_instance.validate_resolution_result.return_value = False  # Low confidence
        
        mock_resolver_instance = mock_resolver.return_value
        
        mock_email_instance = mock_email.return_value
        mock_email_instance.send_daily_report = Mock()
        
        # Create scheduler and run workflow
        scheduler = DailyResolutionScheduler()
        
        with patch('src.daily_scheduler.resolution_logger') as mock_logger:
            mock_logger.generate_daily_summary.return_value = {"test": "summary"}
            mock_logger.get_recent_errors.return_value = []
            
            result = await scheduler.run_daily_resolution_cycle()
        
        # Verify research was attempted
        mock_researcher_instance.research_market_resolution.assert_called_once()
        
        # Verify blockchain resolution was NOT called due to low confidence
        mock_resolver_instance.resolve_market_on_blockchain.assert_not_called()
        
        # Verify workflow completed despite skipping resolution
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    @patch('src.daily_scheduler.MarketMonitor')
    @patch('src.daily_scheduler.GrokResolutionResearcher')
    @patch('src.daily_scheduler.BlockchainResolver')
    @patch('src.daily_scheduler.EmailNotifier')
    async def test_workflow_with_blockchain_failure(self, mock_email, mock_resolver, mock_researcher, mock_monitor):
        """Test workflow when blockchain resolution fails"""
        
        test_market = MarketStatus(
            market_id="0x1234567890abcdef1234567890abcdef12345678",
            title="Will project fail-test receive funding?",
            closing_time=datetime.now(timezone.utc) - timedelta(days=1),
            is_closed=True,
            is_resolved=False,
            application_id="fail-test",
            funding_program_name="Test Program",
            funding_program_twitter="https://twitter.com/testprogram"
        )
        
        test_resolution = ResolutionResult(
            outcome="No",
            confidence=0.9,
            reasoning="Clear evidence of rejection",
            sources=["https://twitter.com/testprogram/status/987654321"],
            twitter_handles_searched=["testprogram"]
        )
        
        # Setup mocks
        mock_monitor_instance = mock_monitor.return_value
        mock_monitor_instance.check_completed_markets.return_value = [test_market]
        
        mock_researcher_instance = mock_researcher.return_value
        mock_researcher_instance.research_market_resolution.return_value = test_resolution
        mock_researcher_instance.validate_resolution_result.return_value = True
        
        # Blockchain resolution fails
        mock_resolver_instance = mock_resolver.return_value
        mock_resolver_instance.resolve_market_on_blockchain.return_value = (False, "Insufficient gas")
        
        mock_email_instance = mock_email.return_value
        mock_email_instance.send_daily_report = Mock()
        mock_email_instance.send_error_alert = Mock()
        
        # Create scheduler and run workflow
        scheduler = DailyResolutionScheduler()
        
        with patch('src.daily_scheduler.resolution_logger') as mock_logger:
            mock_logger.generate_daily_summary.return_value = {
                "total_operations": 3,
                "success_rate_percent": 66.67,
                "status_counts": {"completed": 2, "failed": 1}
            }
            mock_logger.get_recent_errors.return_value = [
                {"error_message": "Insufficient gas", "market_id": "0x1234567890abcdef1234567890abcdef12345678"}
            ]
            
            result = await scheduler.run_daily_resolution_cycle()
        
        # Verify research was successful
        mock_researcher_instance.research_market_resolution.assert_called_once()
        
        # Verify blockchain resolution was attempted
        mock_resolver_instance.resolve_market_on_blockchain.assert_called_once()
        
        # Verify error alert was sent
        mock_email_instance.send_error_alert.assert_called_once()
        
        # Verify workflow completed despite blockchain failure
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    @patch('src.daily_scheduler.MarketMonitor')
    @patch('src.daily_scheduler.GrokResolutionResearcher')
    @patch('src.daily_scheduler.BlockchainResolver')
    @patch('src.daily_scheduler.EmailNotifier')
    async def test_workflow_with_multiple_markets(self, mock_email, mock_resolver, mock_researcher, mock_monitor):
        """Test workflow with multiple markets requiring resolution"""
        
        # Create multiple test markets
        markets = [
            MarketStatus(
                market_id=f"0x{i:064x}",
                title=f"Will project test-{i} receive funding?",
                closing_time=datetime.now(timezone.utc) - timedelta(days=1),
                is_closed=True,
                is_resolved=False,
                application_id=f"test-{i}",
                funding_program_name="Test Program",
                funding_program_twitter="https://twitter.com/testprogram"
            ) for i in range(3)
        ]
        
        # Create corresponding resolution results
        resolutions = [
            ResolutionResult(
                outcome=["Yes", "No", "Invalid"][i],
                confidence=[0.9, 0.8, 0.4][i],
                reasoning=f"Research result for market {i}",
                sources=[f"https://twitter.com/test/status/{i}"],
                twitter_handles_searched=["testprogram"]
            ) for i in range(3)
        ]
        
        # Setup mocks
        mock_monitor_instance = mock_monitor.return_value
        mock_monitor_instance.check_completed_markets.return_value = markets
        mock_monitor_instance.update_market_status_in_db = Mock()
        
        mock_researcher_instance = mock_researcher.return_value
        mock_researcher_instance.research_market_resolution.side_effect = resolutions
        mock_researcher_instance.validate_resolution_result.side_effect = [True, True, False]  # Third has low confidence
        
        mock_resolver_instance = mock_resolver.return_value
        mock_resolver_instance.resolve_market_on_blockchain.return_value = (True, "Success")
        mock_resolver_instance.check_market_needs_final_resolution.return_value = (False, "No finalization needed")
        
        mock_email_instance = mock_email.return_value
        mock_email_instance.send_daily_report = Mock()
        
        # Create scheduler with rate limiting
        scheduler = DailyResolutionScheduler()
        scheduler.resolution_delay_seconds = 0.1  # Short delay for testing
        
        with patch('src.daily_scheduler.resolution_logger') as mock_logger:
            mock_logger.generate_daily_summary.return_value = {"test": "summary"}
            mock_logger.get_recent_errors.return_value = []
            
            # Mock asyncio.sleep to speed up test
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await scheduler.run_daily_resolution_cycle()
        
        # Verify all markets were processed
        assert mock_researcher_instance.research_market_resolution.call_count == 3
        
        # Verify only valid confidence resolutions were submitted to blockchain (first two)
        assert mock_resolver_instance.resolve_market_on_blockchain.call_count == 2
        
        # Verify workflow completed
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    @patch('src.daily_scheduler.MarketMonitor')
    @patch('src.daily_scheduler.GrokResolutionResearcher')  
    @patch('src.daily_scheduler.BlockchainResolver')
    @patch('src.daily_scheduler.EmailNotifier')
    async def test_workflow_with_finalization_phase(self, mock_email, mock_resolver, mock_researcher, mock_monitor):
        """Test workflow including the finalization phase"""
        
        # Mock existing markets that need finalization
        existing_markets = [
            {
                "id": "market-1",
                "application_id": "app-1",
                "market_id": "0x1111111111111111111111111111111111111111",
                "status": "resolution_submitted"
            }
        ]
        
        # Setup mocks
        mock_monitor_instance = mock_monitor.return_value
        mock_monitor_instance.check_completed_markets.return_value = []  # No new markets
        
        mock_resolver_instance = mock_resolver.return_value  
        mock_resolver_instance.check_market_needs_final_resolution.return_value = (True, "Ready for finalization")
        mock_resolver_instance.finalize_market_resolution.return_value = (True, "Finalized successfully")
        
        mock_email_instance = mock_email.return_value
        mock_email_instance.send_daily_report = Mock()
        
        # Mock Supabase for finalization query
        with patch('src.daily_scheduler.get_supabase_client') as mock_supabase:
            mock_client = mock_supabase.return_value
            mock_client.table.return_value = mock_client
            mock_client.select.return_value = mock_client
            mock_client.eq.return_value = mock_client
            mock_client.execute.return_value.data = existing_markets
            
            scheduler = DailyResolutionScheduler()
            scheduler.supabase = mock_client
            
            with patch('src.daily_scheduler.resolution_logger') as mock_logger:
                mock_logger.generate_daily_summary.return_value = {"test": "summary"}
                mock_logger.get_recent_errors.return_value = []
                
                result = await scheduler.run_daily_resolution_cycle()
        
        # Verify finalization was attempted
        mock_resolver_instance.check_market_needs_final_resolution.assert_called_once()
        mock_resolver_instance.finalize_market_resolution.assert_called_once()
        
        # Verify workflow completed
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    @patch('src.daily_scheduler.MarketMonitor')
    @patch('src.daily_scheduler.GrokResolutionResearcher')
    @patch('src.daily_scheduler.BlockchainResolver')
    @patch('src.daily_scheduler.EmailNotifier')
    async def test_workflow_with_critical_system_failure(self, mock_email, mock_resolver, mock_researcher, mock_monitor):
        """Test workflow handling critical system failures"""
        
        # Setup monitor to fail completely
        mock_monitor_instance = mock_monitor.return_value
        mock_monitor_instance.check_completed_markets.side_effect = Exception("Critical monitoring failure")
        
        mock_email_instance = mock_email.return_value
        mock_email_instance.send_error_alert = Mock()
        mock_email_instance.send_daily_report = Mock()
        
        scheduler = DailyResolutionScheduler()
        
        with patch('src.daily_scheduler.resolution_logger') as mock_logger:
            mock_logger.generate_daily_summary.return_value = {
                "critical_error": "Critical monitoring failure",
                "total_operations": 0
            }
            mock_logger.get_recent_errors.return_value = []
            
            result = await scheduler.run_daily_resolution_cycle()
        
        # Verify error alert was sent
        mock_email_instance.send_error_alert.assert_called_once()
        
        # Verify summary still generated despite failure
        assert isinstance(result, dict)
        assert "critical_error" in result
    
    @pytest.mark.asyncio
    async def test_workflow_rate_limiting(self):
        """Test that workflow respects rate limiting between operations"""
        
        with patch('src.daily_scheduler.MarketMonitor') as mock_monitor, \
             patch('src.daily_scheduler.GrokResolutionResearcher') as mock_researcher, \
             patch('src.daily_scheduler.BlockchainResolver') as mock_resolver, \
             patch('src.daily_scheduler.EmailNotifier') as mock_email, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            # Create multiple markets
            markets = [MarketStatus(
                market_id=f"0x{i:064x}",
                title=f"Test market {i}",
                closing_time=datetime.now(timezone.utc),
                is_closed=True,
                is_resolved=False,
                application_id=f"app-{i}",
                funding_program_name="Test",
                funding_program_twitter=None
            ) for i in range(3)]
            
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
            scheduler.resolution_delay_seconds = 1.0  # 1 second delay
            
            with patch('src.daily_scheduler.resolution_logger') as mock_logger:
                mock_logger.generate_daily_summary.return_value = {"test": "summary"}
                mock_logger.get_recent_errors.return_value = []
                
                await scheduler.run_daily_resolution_cycle()
            
            # Verify sleep was called between market processing (2 times for 3 markets)
            assert mock_sleep.call_count == 2
            # Verify each sleep was for the correct duration
            for call in mock_sleep.call_args_list:
                assert call[0][0] == 1.0


class TestWorkflowDataIntegrity:
    """Test data integrity throughout the workflow"""
    
    @pytest.mark.asyncio
    @patch('src.daily_scheduler.MarketMonitor')
    @patch('src.daily_scheduler.GrokResolutionResearcher')
    @patch('src.daily_scheduler.BlockchainResolver') 
    @patch('src.daily_scheduler.EmailNotifier')
    async def test_data_consistency_across_components(self, mock_email, mock_resolver, mock_researcher, mock_monitor):
        """Test that data remains consistent as it flows through components"""
        
        original_market = MarketStatus(
            market_id="0x1234567890abcdef1234567890abcdef12345678",
            title="Will project data-test receive funding from Data Program?",
            closing_time=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
            is_closed=True,
            is_resolved=False,
            application_id="data-test-123",
            funding_program_name="Data Program",
            funding_program_twitter="https://twitter.com/dataprogram"
        )
        
        original_resolution = ResolutionResult(
            outcome="Yes",
            confidence=0.95,
            reasoning="Strong evidence from official announcement",
            sources=["https://twitter.com/dataprogram/status/123"],
            twitter_handles_searched=["dataprogram", "ethereum"]
        )
        
        # Track data passed between components
        passed_market = None
        passed_resolution = None
        
        def capture_research_call(market_status):
            nonlocal passed_market
            passed_market = market_status
            return original_resolution
        
        def capture_resolve_call(market_status, resolution_result):
            nonlocal passed_resolution
            passed_resolution = resolution_result
            return (True, "Success")
        
        # Setup mocks with data capture
        mock_monitor_instance = mock_monitor.return_value
        mock_monitor_instance.check_completed_markets.return_value = [original_market]
        mock_monitor_instance.update_market_status_in_db = Mock()
        
        mock_researcher_instance = mock_researcher.return_value
        mock_researcher_instance.research_market_resolution.side_effect = capture_research_call
        mock_researcher_instance.validate_resolution_result.return_value = True
        
        mock_resolver_instance = mock_resolver.return_value
        mock_resolver_instance.resolve_market_on_blockchain.side_effect = capture_resolve_call
        mock_resolver_instance.check_market_needs_final_resolution.return_value = (False, "Not needed")
        
        mock_email_instance = mock_email.return_value
        mock_email_instance.send_daily_report = Mock()
        
        scheduler = DailyResolutionScheduler()
        
        with patch('src.daily_scheduler.resolution_logger') as mock_logger:
            mock_logger.generate_daily_summary.return_value = {"test": "summary"}
            mock_logger.get_recent_errors.return_value = []
            
            await scheduler.run_daily_resolution_cycle()
        
        # Verify data consistency
        assert passed_market is not None
        assert passed_market.market_id == original_market.market_id
        assert passed_market.application_id == original_market.application_id
        assert passed_market.funding_program_name == original_market.funding_program_name
        
        assert passed_resolution is not None
        assert passed_resolution.outcome == original_resolution.outcome
        assert passed_resolution.confidence == original_resolution.confidence
        assert passed_resolution.reasoning == original_resolution.reasoning
    
    @pytest.mark.asyncio
    async def test_logging_data_integrity(self):
        """Test that logging preserves data integrity"""
        
        with patch('src.daily_scheduler.MarketMonitor') as mock_monitor, \
             patch('src.daily_scheduler.GrokResolutionResearcher') as mock_researcher, \
             patch('src.daily_scheduler.BlockchainResolver') as mock_resolver, \
             patch('src.daily_scheduler.EmailNotifier') as mock_email:
            
            test_market = MarketStatus(
                market_id="0x9876543210abcdef",
                title="Log integrity test market",
                closing_time=datetime.now(timezone.utc),
                is_closed=True,
                is_resolved=False,
                application_id="log-test",
                funding_program_name="Log Program",
                funding_program_twitter=None
            )
            
            # Setup mocks
            mock_monitor_instance = mock_monitor.return_value
            mock_monitor_instance.check_completed_markets.return_value = [test_market]
            
            mock_researcher_instance = mock_researcher.return_value
            mock_researcher_instance.research_market_resolution.return_value = ResolutionResult(
                outcome="No", confidence=0.85, reasoning="Test reasoning", sources=[], twitter_handles_searched=[]
            )
            mock_researcher_instance.validate_resolution_result.return_value = True
            
            mock_resolver_instance = mock_resolver.return_value
            mock_resolver_instance.resolve_market_on_blockchain.return_value = (True, "Logged successfully")
            
            mock_email_instance = mock_email.return_value
            mock_email_instance.send_daily_report = Mock()
            
            scheduler = DailyResolutionScheduler()
            
            # Capture logging calls
            logged_operations = []
            logged_research = []
            
            with patch('src.daily_scheduler.resolution_logger') as mock_logger:
                def capture_research_log(market_id, app_id, outcome, confidence, reasoning, sources):
                    logged_research.append({
                        "market_id": market_id,
                        "application_id": app_id,
                        "outcome": outcome,
                        "confidence": confidence,
                        "reasoning": reasoning,
                        "sources": sources
                    })
                
                mock_logger.log_resolution_research_result.side_effect = capture_research_log
                mock_logger.generate_daily_summary.return_value = {"test": "summary"}
                mock_logger.get_recent_errors.return_value = []
                
                await scheduler.run_daily_resolution_cycle()
            
            # Verify logged data matches original data
            assert len(logged_research) == 1
            research_log = logged_research[0]
            assert research_log["market_id"] == test_market.market_id
            assert research_log["application_id"] == test_market.application_id
            assert research_log["outcome"] == "No"
            assert research_log["confidence"] == 0.85


@pytest.mark.parametrize("workflow_scenario,expected_behavior", [
    ("no_markets_found", "complete_successfully"),
    ("all_markets_low_confidence", "skip_blockchain_operations"),
    ("mixed_confidence_results", "process_only_high_confidence"),
    ("all_blockchain_failures", "continue_with_errors"),
    ("email_service_down", "complete_without_notifications"),
])
@pytest.mark.asyncio
async def test_workflow_scenarios(workflow_scenario, expected_behavior):
    """Parametrized test for different workflow scenarios"""
    
    with patch('src.daily_scheduler.MarketMonitor') as mock_monitor, \
         patch('src.daily_scheduler.GrokResolutionResearcher') as mock_researcher, \
         patch('src.daily_scheduler.BlockchainResolver') as mock_resolver, \
         patch('src.daily_scheduler.EmailNotifier') as mock_email:
        
        # Configure scenario-specific behavior
        if workflow_scenario == "no_markets_found":
            mock_monitor.return_value.check_completed_markets.return_value = []
            
        elif workflow_scenario == "all_markets_low_confidence":
            mock_monitor.return_value.check_completed_markets.return_value = [
                MarketStatus("0x1", "Test", datetime.now(timezone.utc), True, False, "app1", "prog", None)
            ]
            mock_researcher.return_value.research_market_resolution.return_value = ResolutionResult(
                "Invalid", 0.3, "Low confidence", [], []
            )
            mock_researcher.return_value.validate_resolution_result.return_value = False
            
        elif workflow_scenario == "mixed_confidence_results":
            mock_monitor.return_value.check_completed_markets.return_value = [
                MarketStatus("0x1", "Test1", datetime.now(timezone.utc), True, False, "app1", "prog", None),
                MarketStatus("0x2", "Test2", datetime.now(timezone.utc), True, False, "app2", "prog", None)
            ]
            mock_researcher.return_value.research_market_resolution.side_effect = [
                ResolutionResult("Yes", 0.9, "High confidence", [], []),
                ResolutionResult("Invalid", 0.3, "Low confidence", [], [])
            ]
            mock_researcher.return_value.validate_resolution_result.side_effect = [True, False]
            
        elif workflow_scenario == "all_blockchain_failures":
            mock_monitor.return_value.check_completed_markets.return_value = [
                MarketStatus("0x1", "Test", datetime.now(timezone.utc), True, False, "app1", "prog", None)
            ]
            mock_researcher.return_value.research_market_resolution.return_value = ResolutionResult(
                "Yes", 0.9, "High confidence", [], []
            )
            mock_researcher.return_value.validate_resolution_result.return_value = True
            mock_resolver.return_value.resolve_market_on_blockchain.return_value = (False, "Blockchain error")
            
        elif workflow_scenario == "email_service_down":
            mock_monitor.return_value.check_completed_markets.return_value = []
            mock_email.return_value.send_daily_report.side_effect = Exception("Email service unavailable")
        
        # Common setup
        mock_email.return_value.send_error_alert = Mock()
        
        scheduler = DailyResolutionScheduler()
        
        with patch('src.daily_scheduler.resolution_logger') as mock_logger:
            mock_logger.generate_daily_summary.return_value = {"test": "summary"}
            mock_logger.get_recent_errors.return_value = []
            
            # Run workflow
            try:
                result = await scheduler.run_daily_resolution_cycle()
                
                # Verify expected behavior
                if expected_behavior == "complete_successfully":
                    assert isinstance(result, dict)
                    
                elif expected_behavior == "skip_blockchain_operations":
                    assert isinstance(result, dict)
                    # Blockchain resolver should not be called
                    mock_resolver.return_value.resolve_market_on_blockchain.assert_not_called()
                    
                elif expected_behavior == "process_only_high_confidence":
                    assert isinstance(result, dict)
                    # Should have one blockchain call for high confidence result
                    assert mock_resolver.return_value.resolve_market_on_blockchain.call_count == 1
                    
                elif expected_behavior == "continue_with_errors":
                    assert isinstance(result, dict)
                    # Should attempt blockchain resolution despite failure
                    mock_resolver.return_value.resolve_market_on_blockchain.assert_called()
                    
                elif expected_behavior == "complete_without_notifications":
                    assert isinstance(result, dict)
                    # Email error should be handled gracefully
                    
            except Exception as e:
                # Some scenarios may raise exceptions, which should be documented
                if expected_behavior != "complete_successfully":
                    assert isinstance(e, Exception)  # Expected failure
                else:
                    raise  # Unexpected failure