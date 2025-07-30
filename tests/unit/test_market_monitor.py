"""
Unit tests for MarketMonitor class
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import requests

from src.market_monitor import MarketMonitor, TheGraphClient, MarketStatus


class TestTheGraphClient:
    """Tests for TheGraphClient"""
    
    def test_init(self):
        """Test TheGraphClient initialization"""
        with patch('src.market_monitor.Config') as mock_config:
            mock_config.GRAPH_API_KEY = "test_key"
            client = TheGraphClient()
            assert client.api_key == "test_key"
            assert client.omen_subgraph_url == "https://api.thegraph.com/subgraphs/name/omen-pm/omen-xdai"
    
    @patch('src.market_monitor.requests.post')
    def test_get_market_status_success(self, mock_post, mock_graph_response):
        """Test successful market status retrieval"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_graph_response
        
        client = TheGraphClient()
        result = client.get_market_status("0x1234")
        
        assert result is not None
        assert result["id"] == "0x1234567890abcdef1234567890abcdef12345678"
        assert result["title"] == "Will project ABC-123 receive funding?"
        assert result["closed"] is True
        
        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "query" in call_args[1]["json"]
        assert "variables" in call_args[1]["json"]
        assert call_args[1]["json"]["variables"]["marketId"] == "0x1234"
    
    @patch('src.market_monitor.requests.post')
    def test_get_market_status_with_api_key(self, mock_post, mock_graph_response):
        """Test market status retrieval with API key"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_graph_response
        
        with patch('src.market_monitor.Config') as mock_config:
            mock_config.GRAPH_API_KEY = "test_api_key"
            client = TheGraphClient()
            client.get_market_status("0x1234")
        
        # Check that Authorization header was added
        call_args = mock_post.call_args
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_api_key"
    
    @patch('src.market_monitor.requests.post')
    def test_get_market_status_network_error(self, mock_post):
        """Test network error handling"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        client = TheGraphClient()
        result = client.get_market_status("0x1234")
        
        assert result is None
    
    @patch('src.market_monitor.requests.post')
    def test_get_market_status_graphql_errors(self, mock_post):
        """Test GraphQL error handling"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "errors": [{"message": "Field 'invalid' doesn't exist"}]
        }
        
        client = TheGraphClient()
        result = client.get_market_status("0x1234")
        
        assert result is None
    
    @patch('src.market_monitor.requests.post')
    def test_get_market_status_http_error(self, mock_post):
        """Test HTTP error handling"""
        mock_post.return_value.status_code = 500
        
        client = TheGraphClient()
        result = client.get_market_status("0x1234")
        
        assert result is None
    
    @patch('src.market_monitor.requests.post')
    def test_get_market_status_timeout(self, mock_post):
        """Test timeout handling"""
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        client = TheGraphClient()
        result = client.get_market_status("0x1234")
        
        assert result is None
    
    def test_is_market_closed_and_unresolved_true(self):
        """Test market that is closed but unresolved"""
        client = TheGraphClient()
        market_data = {
            "closed": True,
            "condition": {"resolved": False},
            "resolutionTimestamp": None
        }
        
        result = client.is_market_closed_and_unresolved(market_data)
        assert result is True
    
    def test_is_market_closed_and_unresolved_false_not_closed(self):
        """Test market that is not closed"""
        client = TheGraphClient()
        market_data = {
            "closed": False,
            "condition": {"resolved": False},
            "resolutionTimestamp": None
        }
        
        result = client.is_market_closed_and_unresolved(market_data)
        assert result is False
    
    def test_is_market_closed_and_unresolved_false_resolved(self):
        """Test market that is closed and resolved"""
        client = TheGraphClient()
        market_data = {
            "closed": True,
            "condition": {"resolved": True},
            "resolutionTimestamp": "1640995200"
        }
        
        result = client.is_market_closed_and_unresolved(market_data)
        assert result is False
    
    def test_is_market_closed_and_unresolved_empty_data(self):
        """Test with empty market data"""
        client = TheGraphClient()
        result = client.is_market_closed_and_unresolved(None)
        assert result is False
        
        result = client.is_market_closed_and_unresolved({})
        assert result is False


class TestMarketMonitor:
    """Tests for MarketMonitor class"""
    
    @patch('src.market_monitor.get_supabase_client')
    @patch('src.market_monitor.TheGraphClient')
    def test_init(self, mock_graph_client, mock_supabase):
        """Test MarketMonitor initialization"""
        monitor = MarketMonitor()
        assert monitor.graph_client is not None
        assert monitor.supabase is not None
    
    @patch('src.market_monitor.get_supabase_client')
    def test_get_markets_to_monitor_success(self, mock_supabase, sample_market_records):
        """Test successful retrieval of markets to monitor"""
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.in_.return_value = mock_client
        mock_client.execute.return_value.data = sample_market_records
        
        monitor = MarketMonitor()
        result = monitor.get_markets_to_monitor()
        
        assert len(result) == 2
        assert result[0]["market_id"] == "0x1111111111111111111111111111111111111111"
        assert result[1]["market_id"] == "0x2222222222222222222222222222222222222222"
    
    @patch('src.market_monitor.get_supabase_client')
    def test_get_markets_to_monitor_error(self, mock_supabase):
        """Test error handling in get_markets_to_monitor"""
        mock_client = mock_supabase.return_value
        mock_client.table.side_effect = Exception("Database error")
        
        monitor = MarketMonitor()
        result = monitor.get_markets_to_monitor()
        
        assert result == []
    
    @patch('src.market_monitor.get_supabase_client')
    @patch('src.market_monitor.TheGraphClient')
    def test_check_completed_markets_success(self, mock_graph_client_class, mock_supabase, sample_market_records):
        """Test successful checking of completed markets"""
        # Setup Supabase mock
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.in_.return_value = mock_client
        mock_client.execute.return_value.data = sample_market_records
        
        # Setup Graph client mock
        mock_graph_client = mock_graph_client_class.return_value
        mock_graph_data = {
            "title": "Will project app-1 get funding?",
            "lastActiveDay": "1640995200",
            "closed": True,
            "condition": {"resolved": False},
            "resolutionTimestamp": None
        }
        mock_graph_client.get_market_status.return_value = mock_graph_data
        mock_graph_client.is_market_closed_and_unresolved.return_value = True
        
        monitor = MarketMonitor()
        result = monitor.check_completed_markets()
        
        assert len(result) == 2  # Both markets should be identified as completed
        assert isinstance(result[0], MarketStatus)
        assert result[0].market_id == "0x1111111111111111111111111111111111111111"
        assert result[0].application_id == "app-1"
        assert result[0].is_closed is True
        assert result[0].is_resolved is False
    
    @patch('src.market_monitor.get_supabase_client')
    @patch('src.market_monitor.TheGraphClient')
    def test_check_completed_markets_no_graph_data(self, mock_graph_client_class, mock_supabase, sample_market_records):
        """Test handling when The Graph returns no data"""
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.in_.return_value = mock_client
        mock_client.execute.return_value.data = sample_market_records
        
        mock_graph_client = mock_graph_client_class.return_value
        mock_graph_client.get_market_status.return_value = None
        
        monitor = MarketMonitor()
        result = monitor.check_completed_markets()
        
        assert len(result) == 0
    
    @patch('src.market_monitor.get_supabase_client')
    @patch('src.market_monitor.TheGraphClient')
    def test_check_completed_markets_skip_failed_markets(self, mock_graph_client_class, mock_supabase):
        """Test skipping markets with FAILED_ prefix"""
        failed_market_record = {
            "id": "market-failed",
            "application_id": "app-failed",
            "market_id": "FAILED_some-app-id",
            "market_title": "Failed market",
            "status": "failed"
        }
        
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.in_.return_value = mock_client
        mock_client.execute.return_value.data = [failed_market_record]
        
        mock_graph_client = mock_graph_client_class.return_value
        
        monitor = MarketMonitor()
        result = monitor.check_completed_markets()
        
        assert len(result) == 0
        # Graph client should not be called for failed markets
        mock_graph_client.get_market_status.assert_not_called()
    
    @patch('src.market_monitor.get_supabase_client')
    @patch('src.market_monitor.TheGraphClient')
    def test_check_completed_markets_application_id_not_in_title(self, mock_graph_client_class, mock_supabase, sample_market_records):
        """Test filtering markets where application ID is not in title"""
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.in_.return_value = mock_client
        mock_client.execute.return_value.data = sample_market_records
        
        mock_graph_client = mock_graph_client_class.return_value
        mock_graph_data = {
            "title": "Will some other project get funding?",  # Doesn't contain app-1
            "lastActiveDay": "1640995200"
        }
        mock_graph_client.get_market_status.return_value = mock_graph_data
        mock_graph_client.is_market_closed_and_unresolved.return_value = True
        
        monitor = MarketMonitor()
        result = monitor.check_completed_markets()
        
        assert len(result) == 0  # Should be filtered out
    
    def test_parse_timestamp_valid(self):
        """Test parsing valid timestamp"""
        monitor = MarketMonitor()
        result = monitor._parse_timestamp("1640995200")
        
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
    
    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp"""
        monitor = MarketMonitor()
        
        assert monitor._parse_timestamp(None) is None
        assert monitor._parse_timestamp("") is None
        assert monitor._parse_timestamp("invalid") is None
        assert monitor._parse_timestamp("abc") is None
    
    @patch('src.market_monitor.get_supabase_client')
    def test_update_market_status_in_db_success(self, mock_supabase):
        """Test successful market status update"""
        mock_client = mock_supabase.return_value
        mock_client.table.return_value = mock_client
        mock_client.update.return_value = mock_client
        mock_client.eq.return_value = mock_client
        mock_client.execute.return_value.data = [{"id": "updated"}]
        
        monitor = MarketMonitor()
        monitor.update_market_status_in_db("0x1234", "resolved", {"key": "value"})
        
        # Verify the update was called correctly
        mock_client.update.assert_called_once()
        update_data = mock_client.update.call_args[0][0]
        assert update_data["status"] == "resolved"
        assert update_data["metadata"] == {"key": "value"}
        assert "updated_at" in update_data
    
    @patch('src.market_monitor.get_supabase_client')
    def test_update_market_status_in_db_error(self, mock_supabase):
        """Test error handling in market status update"""
        mock_client = mock_supabase.return_value
        mock_client.table.side_effect = Exception("Database error")
        
        monitor = MarketMonitor()
        # Should not raise exception
        monitor.update_market_status_in_db("0x1234", "resolved")


@pytest.mark.parametrize("market_data,expected", [
    ({"closed": True, "condition": {"resolved": False}, "resolutionTimestamp": None}, True),
    ({"closed": False, "condition": {"resolved": False}, "resolutionTimestamp": None}, False),
    ({"closed": True, "condition": {"resolved": True}, "resolutionTimestamp": "123"}, False),
    ({"closed": True, "condition": {"resolved": False}, "resolutionTimestamp": "123"}, False),
    ({}, False),
    (None, False),
])
def test_is_market_closed_and_unresolved_parametrized(market_data, expected):
    """Parametrized test for market closed/unresolved detection"""
    client = TheGraphClient()
    result = client.is_market_closed_and_unresolved(market_data)
    assert result == expected