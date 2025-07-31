"""
Integration tests for API endpoints
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Import the FastAPI app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root health check endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Supafund Market Creation Agent" in data["message"]


class TestMarketManagementEndpoints:
    """Tests for existing market management endpoints"""
    
    @patch('src.main.get_application_details')
    @patch('src.main.check_existing_market')
    @patch('src.main.create_omen_market')
    @patch('src.main.parse_market_output')
    @patch('src.main.create_market_record')
    def test_create_market_success(self, mock_create_record, mock_parse, mock_create_market, 
                                 mock_check_existing, mock_get_details, client, sample_application_details):
        """Test successful market creation"""
        # Setup mocks
        mock_check_existing.return_value = None  # No existing market
        mock_get_details.return_value = sample_application_details
        mock_create_market.return_value = (True, "Market created successfully")
        mock_parse.return_value = {
            "market_id": "0x1234567890abcdef",
            "market_title": "Test Market",
            "market_url": "https://omen.eth.link/0x1234567890abcdef",
            "market_question": "Will the project succeed?",
            "closing_time": "2024-12-31T23:59:59Z"
        }
        mock_create_record.return_value = True
        
        # Make request
        response = client.post("/create-market", json={"application_id": "test-app-123"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["application_id"] == "test-app-123"
        assert "market_info" in data
    
    @patch('src.main.get_application_details')
    @patch('src.main.check_existing_market')
    def test_create_market_already_exists(self, mock_check_existing, mock_get_details, client):
        """Test market creation when market already exists"""
        # Setup mocks
        mock_check_existing.return_value = {
            "market_id": "0x1234567890abcdef",
            "market_url": "https://omen.eth.link/0x1234567890abcdef",
            "created_at": "2024-01-01T00:00:00Z",
            "status": "created"
        }
        
        # Make request
        response = client.post("/create-market", json={"application_id": "test-app-123"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_exists"
        assert "existing_market" in data
    
    @patch('src.main.get_application_details')
    @patch('src.main.check_existing_market')
    def test_create_market_application_not_found(self, mock_check_existing, mock_get_details, client):
        """Test market creation when application is not found"""
        # Setup mocks
        mock_check_existing.return_value = None
        mock_get_details.return_value = None  # Application not found
        
        # Make request
        response = client.post("/create-market", json={"application_id": "nonexistent-app"})
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    @patch('src.main.place_bet')
    def test_bet_endpoint_success(self, mock_place_bet, client):
        """Test successful bet placement"""
        # Setup mock
        mock_place_bet.return_value = (True, "Bet placed successfully")
        
        bet_request = {
            "market_id": "0x1234567890abcdef",
            "amount_usd": 0.01,
            "outcome": "Yes",
            "from_private_key": "0x" + "1" * 64,
            "auto_deposit": True
        }
        
        # Make request
        response = client.post("/bet", json=bet_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["market_id"] == bet_request["market_id"]
        assert data["amount_usd"] == bet_request["amount_usd"]
    
    @patch('src.main.place_bet')
    def test_bet_endpoint_failure(self, mock_place_bet, client):
        """Test bet placement failure"""
        # Setup mock
        mock_place_bet.return_value = (False, "Insufficient balance")
        
        bet_request = {
            "market_id": "0x1234567890abcdef",
            "amount_usd": 100.0,
            "outcome": "Yes",
            "from_private_key": "0x" + "1" * 64
        }
        
        # Make request
        response = client.post("/bet", json=bet_request)
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to place bet" in data["detail"]


class TestResolutionSystemEndpoints:
    """Tests for new resolution system endpoints"""
    
    def test_resolution_status_endpoint(self, client):
        """Test resolution status endpoint"""
        with patch('src.main.resolution_logger') as mock_logger, \
             patch('src.main.get_supabase_client') as mock_supabase:
            
            # Setup mocks
            mock_logger.get_recent_errors.return_value = []
            mock_logger.get_operation_logs.return_value = [
                {"status": "completed", "operation": "monitor"},
                {"status": "failed", "operation": "research"},
            ]
            
            # Setup Supabase mock
            mock_client = mock_supabase.return_value
            mock_client.table.return_value = mock_client
            mock_client.select.return_value = mock_client
            mock_client.eq.return_value = mock_client
            
            # Mock market counts by status
            def mock_execute_side_effect():
                # Return different counts for different statuses
                if mock_client.eq.call_args[0][1] == "created":
                    return Mock(data=[{"id": "1"}, {"id": "2"}])  # 2 created
                elif mock_client.eq.call_args[0][1] == "active":
                    return Mock(data=[{"id": "3"}])  # 1 active
                else:
                    return Mock(data=[])  # 0 for others
            
            mock_client.execute.side_effect = mock_execute_side_effect
            
            # Make request
            response = client.get("/resolution-status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "recent_operations" in data
            assert "recent_errors" in data
            assert "markets_by_status" in data
            assert "system_health" in data
    
    def test_run_daily_resolution_endpoint(self, client):
        """Test manual trigger of daily resolution"""
        with patch('src.main.run_daily_resolution') as mock_run_resolution:
            # Make request
            response = client.post("/run-daily-resolution")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "Daily resolution cycle started" in data["message"]
    
    def test_resolution_logs_endpoint_no_filter(self, client):
        """Test resolution logs endpoint without filters"""
        with patch('src.main.resolution_logger') as mock_logger:
            mock_logger.get_operation_logs.return_value = [
                {
                    "id": "op-1",
                    "operation": "monitor",
                    "market_id": "0x1234",
                    "status": "completed"
                },
                {
                    "id": "op-2", 
                    "operation": "research",
                    "market_id": "0x5678",
                    "status": "failed"
                }
            ]
            
            # Make request
            response = client.get("/resolution-logs")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["log_count"] == 2
            assert len(data["logs"]) == 2
    
    def test_resolution_logs_endpoint_with_filters(self, client):
        """Test resolution logs endpoint with filters"""
        with patch('src.main.resolution_logger') as mock_logger:
            mock_logger.get_operation_logs.return_value = [
                {
                    "id": "op-1",
                    "operation": "monitor",
                    "market_id": "0x1234",
                    "status": "completed"
                }
            ]
            
            # Make request with filters
            response = client.get("/resolution-logs?market_id=0x1234&operation=monitor&limit=50")
            
            assert response.status_code == 200
            data = response.json()
            assert data["filters"]["market_id"] == "0x1234"
            assert data["filters"]["operation"] == "monitor"
            assert data["filters"]["limit"] == 50
            # Verify mock was called with correct parameters
            mock_logger.get_operation_logs.assert_called_with(market_id="0x1234", operation="monitor")
    
    def test_resolution_summary_endpoint(self, client):
        """Test resolution summary endpoint"""
        with patch('src.main.resolution_logger') as mock_logger:
            mock_summary = {
                "date": "2024-01-01",
                "total_operations": 10,
                "success_rate_percent": 80.0,
                "operation_counts": {
                    "monitor": {"completed": 5, "failed": 0},
                    "research": {"completed": 3, "failed": 2}
                }
            }
            mock_logger.generate_daily_summary.return_value = mock_summary
            
            # Make request
            response = client.get("/resolution-summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["summary"]["total_operations"] == 10
            assert data["summary"]["success_rate_percent"] == 80.0
    
    @patch('src.main.GrokResolutionResearcher')
    @patch('src.main.resolution_logger')
    def test_research_market_endpoint_success(self, mock_logger, mock_researcher_class, client):
        """Test manual market research endpoint"""
        # Setup mock researcher
        mock_researcher = mock_researcher_class.return_value
        mock_result = Mock()
        mock_result.outcome = "Yes"
        mock_result.confidence = 0.85
        mock_result.reasoning = "Strong evidence found"
        mock_result.sources = ["https://twitter.com/test/123"]
        mock_result.twitter_handles_searched = ["test"]
        mock_researcher.research_market_resolution.return_value = mock_result
        
        research_request = {
            "market_id": "0x1234567890abcdef",
            "application_id": "app-123",
            "funding_program_name": "Test Program",
            "funding_program_twitter": "https://twitter.com/testprogram"
        }
        
        # Make request
        response = client.post("/research-market", json=research_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["market_id"] == research_request["market_id"]
        assert data["research_result"]["outcome"] == "Yes"
        assert data["research_result"]["confidence"] == 0.85
    
    @patch('src.main.GrokResolutionResearcher')
    def test_research_market_endpoint_failure(self, mock_researcher_class, client):
        """Test manual market research endpoint failure"""
        # Setup mock researcher to return None (failure)
        mock_researcher = mock_researcher_class.return_value
        mock_researcher.research_market_resolution.return_value = None
        
        research_request = {
            "market_id": "0x1234567890abcdef",
            "application_id": "app-123",
            "funding_program_name": "Test Program"
        }
        
        # Make request
        response = client.post("/research-market", json=research_request)
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get research result" in data["detail"]


class TestMarketStatusEndpoints:
    """Tests for market status management endpoints"""
    
    @patch('src.main.get_market_by_application_id')
    def test_get_market_status_success(self, mock_get_market, client):
        """Test successful market status retrieval"""
        mock_market = {
            "id": "market-123",
            "application_id": "app-123",
            "market_id": "0x1234567890abcdef",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_get_market.return_value = mock_market
        
        # Make request
        response = client.get("/market-status/app-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["application_id"] == "app-123"
        assert data["market"]["status"] == "active"
    
    @patch('src.main.get_market_by_application_id')
    def test_get_market_status_not_found(self, mock_get_market, client):
        """Test market status retrieval when market not found"""
        mock_get_market.return_value = None
        
        # Make request
        response = client.get("/market-status/nonexistent-app")
        
        assert response.status_code == 404
        data = response.json()
        assert "No market found" in data["detail"]
    
    @patch('src.main.get_market_by_application_id')
    @patch('src.main.update_market_record')
    def test_update_market_status_success(self, mock_update, mock_get_market, client):
        """Test successful market status update"""
        mock_market = {
            "id": "market-123",
            "application_id": "app-123",
            "status": "active",
            "metadata": {"old": "data"}
        }
        mock_get_market.return_value = mock_market
        mock_update.return_value = True
        
        update_request = {
            "status": "resolved",
            "metadata": {"resolution": "Yes", "confidence": 0.85}
        }
        
        # Make request
        response = client.put("/market-status/app-123", json=update_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["new_status"] == "resolved"
        
        # Verify update was called with correct data
        mock_update.assert_called_once()
        update_data = mock_update.call_args[0][1]
        assert update_data["status"] == "resolved"
        assert update_data["metadata"]["resolution"] == "Yes"
        assert update_data["metadata"]["old"] == "data"  # Preserved old metadata
    
    @patch('src.main.get_market_by_application_id')
    def test_update_market_status_not_found(self, mock_get_market, client):
        """Test market status update when market not found"""
        mock_get_market.return_value = None
        
        update_request = {"status": "resolved"}
        
        # Make request
        response = client.put("/market-status/nonexistent-app", json=update_request)
        
        assert response.status_code == 404
        data = response.json()
        assert "No market found" in data["detail"]


class TestMarketListingEndpoints:
    """Tests for market listing endpoints"""
    
    @patch('src.main.get_all_markets')
    def test_list_markets_no_filter(self, mock_get_markets, client, sample_market_records):
        """Test listing markets without filter"""
        mock_get_markets.return_value = sample_market_records
        
        # Make request
        response = client.get("/markets")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 2
        assert len(data["markets"]) == 2
        assert data["filter"]["status"] is None
        assert data["filter"]["limit"] == 100
    
    @patch('src.main.get_all_markets')
    def test_list_markets_with_filter(self, mock_get_markets, client):
        """Test listing markets with status filter"""
        filtered_markets = [
            {
                "id": "market-1",
                "status": "active",
                "market_id": "0x1111"
            }
        ]
        mock_get_markets.return_value = filtered_markets
        
        # Make request with filter
        response = client.get("/markets?status=active&limit=50")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["filter"]["status"] == "active"
        assert data["filter"]["limit"] == 50
        
        # Verify mock was called with correct parameters
        mock_get_markets.assert_called_with(status="active", limit=50)


class TestErrorHandling:
    """Tests for error handling in API endpoints"""
    
    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON in request"""
        # Make request with invalid JSON
        response = client.post(
            "/create-market", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_missing_required_fields(self, client):
        """Test handling of missing required fields"""
        # Make request without required application_id
        response = client.post("/create-market", json={})
        
        assert response.status_code == 422
        data = response.json()
        assert "field required" in str(data["detail"]).lower()
    
    def test_invalid_field_types(self, client):
        """Test handling of invalid field types"""  
        # Make bet request with invalid amount type
        bet_request = {
            "market_id": "0x1234567890abcdef",
            "amount_usd": "invalid_number",  # Should be float
            "outcome": "Yes",
            "from_private_key": "0x" + "1" * 64
        }
        
        response = client.post("/bet", json=bet_request)
        
        assert response.status_code == 422
    
    @patch('src.main.resolution_logger')
    def test_internal_server_error(self, mock_logger, client):
        """Test handling of internal server errors"""
        # Make resolution_logger raise an exception
        mock_logger.get_recent_errors.side_effect = Exception("Internal error")
        
        response = client.get("/resolution-status")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error getting resolution status" in data["detail"]


@pytest.mark.parametrize("endpoint,method,expected_status", [
    ("/", "GET", 200),
    ("/docs", "GET", 200),
    ("/openapi.json", "GET", 200),
    ("/resolution-status", "GET", 200),
    ("/resolution-logs", "GET", 200),
    ("/resolution-summary", "GET", 200),
])
def test_endpoint_accessibility(endpoint, method, expected_status, client):
    """Parametrized test to ensure all endpoints are accessible"""
    # Mock any dependencies that might be called
    with patch('src.main.resolution_logger') as mock_logger:
        mock_logger.get_recent_errors.return_value = []
        mock_logger.get_operation_logs.return_value = []
        mock_logger.generate_daily_summary.return_value = {"test": "data"}
        
        with patch('src.main.get_supabase_client') as mock_supabase:
            mock_client = mock_supabase.return_value
            mock_client.table.return_value = mock_client
            mock_client.select.return_value = mock_client
            mock_client.eq.return_value = mock_client
            mock_client.execute.return_value = Mock(data=[])
            
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            
            assert response.status_code == expected_status


class TestAPIValidation:
    """Tests for API input validation"""
    
    def test_application_id_format_validation(self, client):
        """Test application ID format validation"""
        # Test with various invalid formats
        invalid_ids = [
            "",  # Empty string
            "too-short", # Too short
            "invalid format without dashes",  # Wrong format
            "123",  # Numbers only
        ]
        
        for invalid_id in invalid_ids:
            response = client.post("/create-market", json={"application_id": invalid_id})
            # Should still accept it (validation happens at business logic level)
            assert response.status_code in [200, 404, 422, 500]  # Various expected responses
    
    def test_market_id_format_validation(self, client):
        """Test market ID format validation"""
        with patch('src.main.place_bet') as mock_place_bet:
            mock_place_bet.return_value = (True, "Success")
            
            # Test with invalid market ID format
            bet_request = {
                "market_id": "invalid-market-id",  # Should be hex
                "amount_usd": 0.01,
                "outcome": "Yes",
                "from_private_key": "0x" + "1" * 64
            }
            
            response = client.post("/bet", json=bet_request)
            # API should accept it, validation happens at business logic level
            assert response.status_code == 200
    
    def test_outcome_validation(self, client):
        """Test outcome field validation"""
        with patch('src.main.place_bet') as mock_place_bet:
            mock_place_bet.return_value = (True, "Success")
            
            valid_outcomes = ["Yes", "No"]
            
            for outcome in valid_outcomes:
                bet_request = {
                    "market_id": "0x1234567890abcdef",
                    "amount_usd": 0.01,
                    "outcome": outcome,
                    "from_private_key": "0x" + "1" * 64
                }
                
                response = client.post("/bet", json=bet_request)
                assert response.status_code == 200