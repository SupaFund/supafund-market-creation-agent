"""
Global test configuration and fixtures
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from pathlib import Path
import asyncio
from typing import Dict, Any, List

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.market_monitor import MarketStatus
from src.resolution_researcher import ResolutionResult
from src.config import Config

# Test data fixtures
@pytest.fixture
def sample_market_status():
    """Sample MarketStatus for testing"""
    return MarketStatus(
        market_id="0x1234567890abcdef1234567890abcdef12345678",
        title="Will project ABC-123 receive funding from Test Program 2024?",
        closing_time=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        is_closed=True,
        is_resolved=False,
        application_id="abc-123-def-456",
        funding_program_name="Test Program 2024",
        funding_program_twitter="https://twitter.com/testprogram"
    )

@pytest.fixture
def sample_resolution_result():
    """Sample ResolutionResult for testing"""
    return ResolutionResult(
        outcome="Yes",
        confidence=0.85,
        reasoning="Found official announcement on Twitter confirming project ABC-123 received funding",
        sources=["https://twitter.com/testprogram/status/123456789"],
        twitter_handles_searched=["testprogram", "ethereum", "gitcoin"]
    )

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    mock_client = Mock()
    mock_client.table.return_value = mock_client
    mock_client.select.return_value = mock_client
    mock_client.eq.return_value = mock_client
    mock_client.insert.return_value = mock_client
    mock_client.update.return_value = mock_client
    mock_client.single.return_value = mock_client
    mock_client.execute.return_value = Mock(data=[])
    return mock_client

@pytest.fixture
def mock_graph_response():
    """Mock The Graph API response"""
    return {
        "data": {
            "fixedProductMarketMaker": {
                "id": "0x1234567890abcdef1234567890abcdef12345678",
                "title": "Will project ABC-123 receive funding?",
                "closed": True,
                "resolutionTimestamp": None,
                "condition": {
                    "resolved": False,
                    "payoutNumerators": None
                },
                "question": {
                    "currentAnswer": None,
                    "finalizationTimestamp": None
                }
            }
        }
    }

@pytest.fixture
def mock_grok_client():
    """Mock Grok/xAI client"""
    mock_client = Mock()
    
    # Mock chat creation
    mock_chat = Mock()
    mock_client.chat.create.return_value = mock_chat
    
    # Mock chat methods
    mock_chat.append = Mock()
    
    # Mock response
    mock_response = Mock()
    mock_response.content = """
OUTCOME: Yes
CONFIDENCE: 0.85
REASONING: Found official announcement confirming project received funding from the program
SOURCES: https://twitter.com/testprogram/status/123456789
"""
    mock_response.citations = [Mock(url="https://twitter.com/testprogram/status/123456789")]
    mock_chat.sample.return_value = mock_response
    
    return mock_client

@pytest.fixture
def mock_blockchain_success():
    """Mock successful blockchain operation"""
    return (True, "Transaction successful: 0xabc123def456")

@pytest.fixture
def mock_blockchain_failure():
    """Mock failed blockchain operation"""
    return (False, "Transaction failed: insufficient gas")

@pytest.fixture
def test_env_vars():
    """Test environment variables"""
    return {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_key_123",
        "OMEN_PRIVATE_KEY": "0x" + "1" * 64,
        "GRAPH_API_KEY": "test_graph_key",
        "XAI_API_KEY": "test_xai_key",
        "ADMIN_EMAIL": "admin@test.com",
        "SMTP_USERNAME": "test@gmail.com",
        "SMTP_PASSWORD": "test_password",
        "MIN_RESEARCH_CONFIDENCE": "0.7",
        "MAX_MARKETS_PER_RUN": "5",
        "RESOLUTION_DELAY_SECONDS": "1"
    }

@pytest.fixture
def temp_log_dir():
    """Temporary directory for log files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_email_server():
    """Mock SMTP server"""
    mock_server = Mock()
    mock_server.starttls.return_value = None
    mock_server.login.return_value = None
    mock_server.send_message.return_value = None
    mock_server.__enter__ = Mock(return_value=mock_server)
    mock_server.__exit__ = Mock(return_value=None)
    return mock_server

# Database fixtures
@pytest.fixture
def sample_market_records():
    """Sample market records from database"""
    return [
        {
            "id": "market-1",
            "application_id": "app-1",
            "market_id": "0x1111111111111111111111111111111111111111",
            "market_title": "Will project 1 get funding?",
            "status": "created",
            "created_at": "2024-01-01T00:00:00Z",
            "application": {
                "id": "app-1",
                "project": {"name": "Project 1", "description": "Test project 1"},
                "program": {
                    "name": "Test Program",
                    "twitter_url": "https://twitter.com/testprogram"
                }
            }
        },
        {
            "id": "market-2",
            "application_id": "app-2",
            "market_id": "0x2222222222222222222222222222222222222222",
            "market_title": "Will project 2 get funding?",
            "status": "active",
            "created_at": "2024-01-02T00:00:00Z",
            "application": {
                "id": "app-2",
                "project": {"name": "Project 2", "description": "Test project 2"},
                "program": {
                    "name": "Another Program",
                    "twitter_url": "https://twitter.com/anotherprogram"
                }
            }
        }
    ]

@pytest.fixture
def sample_application_details():
    """Sample application details from Supabase"""
    return {
        "application_id": "abc-123-def-456",
        "project_name": "Test Project",
        "project_description": "A revolutionary blockchain project",
        "program_name": "Test Funding Program",
        "program_description": "Supporting innovative blockchain projects",
        "deadline": "2024-12-31T23:59:59Z"
    }

# Async fixtures
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_mock_supabase():
    """Async mock for Supabase operations"""
    mock_client = Mock()
    
    async def mock_execute():
        return Mock(data=[])
    
    mock_client.table.return_value = mock_client
    mock_client.select.return_value = mock_client
    mock_client.eq.return_value = mock_client
    mock_client.execute = AsyncMock(return_value=Mock(data=[]))
    
    return mock_client

# Configuration fixtures
@pytest.fixture
def mock_config(test_env_vars):
    """Mock configuration with test values"""
    with patch.dict(os.environ, test_env_vars):
        # Mock the Config class attributes
        with patch.object(Config, 'SUPABASE_URL', test_env_vars['SUPABASE_URL']), \
             patch.object(Config, 'SUPABASE_KEY', test_env_vars['SUPABASE_KEY']), \
             patch.object(Config, 'OMEN_PRIVATE_KEY', test_env_vars['OMEN_PRIVATE_KEY']), \
             patch.object(Config, 'GRAPH_API_KEY', test_env_vars['GRAPH_API_KEY']), \
             patch.object(Config, 'XAI_API_KEY', test_env_vars['XAI_API_KEY']):
            yield Config

# Error simulation fixtures
@pytest.fixture
def network_error():
    """Simulate network errors"""
    import requests
    return requests.exceptions.ConnectionError("Network error")

@pytest.fixture
def api_timeout_error():
    """Simulate API timeout"""
    import requests
    return requests.exceptions.Timeout("Request timeout")

@pytest.fixture
def api_rate_limit_error():
    """Simulate API rate limiting"""
    import requests
    response = Mock()
    response.status_code = 429
    response.text = "Rate limit exceeded"
    return requests.exceptions.HTTPError("429 Client Error", response=response)

# Test utilities
class TestHelpers:
    """Helper utilities for tests"""
    
    @staticmethod
    def create_market_status(**overrides):
        """Create MarketStatus with optional overrides"""
        defaults = {
            "market_id": "0x1234567890abcdef1234567890abcdef12345678",
            "title": "Test market",
            "closing_time": datetime.now(timezone.utc),
            "is_closed": True,
            "is_resolved": False,
            "application_id": "test-app-id",
            "funding_program_name": "Test Program",
            "funding_program_twitter": "https://twitter.com/testprogram"
        }
        defaults.update(overrides)
        return MarketStatus(**defaults)
    
    @staticmethod
    def create_resolution_result(**overrides):
        """Create ResolutionResult with optional overrides"""
        defaults = {
            "outcome": "Yes",
            "confidence": 0.8,
            "reasoning": "Test reasoning",
            "sources": ["https://twitter.com/test/status/123"],
            "twitter_handles_searched": ["test"]
        }
        defaults.update(overrides)
        return ResolutionResult(**defaults)

@pytest.fixture
def test_helpers():
    """Test helper utilities"""
    return TestHelpers()

# Parametrize fixtures for edge cases
@pytest.fixture(params=[
    "Yes", "No", "Invalid"
])
def all_outcomes(request):
    """All possible resolution outcomes"""
    return request.param

@pytest.fixture(params=[
    0.0, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0
])
def confidence_levels(request):
    """Various confidence levels"""
    return request.param

@pytest.fixture(params=[
    "created", "active", "resolution_submitted", "resolved", "failed"
])
def market_statuses(request):
    """All possible market statuses"""
    return request.param