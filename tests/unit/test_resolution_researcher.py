"""
Unit tests for ResolutionResearcher class
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import os

from src.resolution_researcher import GrokResolutionResearcher, ResolutionResult
from src.market_monitor import MarketStatus


class TestGrokResolutionResearcher:
    """Tests for GrokResolutionResearcher class"""
    
    @patch('src.resolution_researcher.GROK_AVAILABLE', True)
    @patch('src.resolution_researcher.Client')
    def test_init_with_api_key(self, mock_client_class):
        """Test initialization with valid API key"""
        with patch.dict(os.environ, {"XAI_API_KEY": "test_api_key"}):
            researcher = GrokResolutionResearcher()
            assert researcher.api_key == "test_api_key"
            assert researcher.client is not None
            mock_client_class.assert_called_once_with(api_key="test_api_key")
    
    @patch('src.resolution_researcher.GROK_AVAILABLE', True)
    def test_init_without_api_key(self):
        """Test initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            researcher = GrokResolutionResearcher()
            assert researcher.api_key is None
            assert researcher.client is None
    
    @patch('src.resolution_researcher.GROK_AVAILABLE', False)
    def test_init_sdk_not_available(self):
        """Test initialization when SDK is not available"""
        with pytest.raises(ImportError, match="xai-sdk is not installed"):
            GrokResolutionResearcher()
    
    def test_extract_twitter_handles_from_url_direct_handle(self):
        """Test extracting handle from direct @handle"""
        researcher = GrokResolutionResearcher()
        result = researcher.extract_twitter_handles_from_url("@testuser")
        assert result == ["testuser"]
    
    def test_extract_twitter_handles_from_url_twitter_url(self):
        """Test extracting handle from Twitter URL"""
        researcher = GrokResolutionResearcher()
        
        urls_and_expected = [
            ("https://twitter.com/testuser", ["testuser"]),
            ("https://x.com/testuser", ["testuser"]),
            ("https://twitter.com/testuser/status/123", ["testuser"]),
            ("https://x.com/testuser?tab=replies", ["testuser"]),
        ]
        
        for url, expected in urls_and_expected:
            result = researcher.extract_twitter_handles_from_url(url)
            assert result == expected
    
    def test_extract_twitter_handles_from_url_invalid(self):
        """Test extracting handles from invalid URLs"""
        researcher = GrokResolutionResearcher()
        
        invalid_urls = [
            "",
            None,
            "https://facebook.com/user",
            "not-a-url",
            "https://example.com"
        ]
        
        for url in invalid_urls:
            result = researcher.extract_twitter_handles_from_url(url)
            assert result == []
    
    def test_get_default_crypto_handles(self):
        """Test getting default crypto handles"""
        researcher = GrokResolutionResearcher()
        handles = researcher.get_default_crypto_handles()
        
        assert isinstance(handles, list)
        assert len(handles) > 0
        assert "ethereum" in handles
        assert "VitalikButerin" in handles
        assert "gitcoin" in handles
    
    @patch('src.resolution_researcher.GROK_AVAILABLE', True)
    def test_research_market_resolution_no_client(self, sample_market_status):
        """Test research when no client is available (no API key)"""
        with patch.dict(os.environ, {}, clear=True):
            researcher = GrokResolutionResearcher()
            researcher.client = None
            
            result = researcher.research_market_resolution(sample_market_status)
            
            assert result is not None
            assert result.outcome == "Invalid"
            assert result.confidence == 0.3
            assert "Mock result" in result.reasoning
    
    @patch('src.resolution_researcher.GROK_AVAILABLE', True)
    @patch('src.resolution_researcher.Client')
    def test_research_market_resolution_success(self, mock_client_class, sample_market_status):
        """Test successful market research"""
        # Setup mock client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Setup mock chat
        mock_chat = Mock()
        mock_client.chat.create.return_value = mock_chat
        
        # Setup mock response
        mock_response = Mock()
        mock_response.content = """
OUTCOME: Yes
CONFIDENCE: 0.85
REASONING: Found official announcement confirming project received funding
SOURCES: https://twitter.com/testprogram/status/123456789
"""
        mock_response.citations = [Mock(url="https://twitter.com/testprogram/status/123456789")]
        mock_chat.sample.return_value = mock_response
        
        with patch.dict(os.environ, {"XAI_API_KEY": "test_key"}):
            researcher = GrokResolutionResearcher()
            result = researcher.research_market_resolution(sample_market_status)
        
        assert result is not None
        assert result.outcome == "Yes"
        assert result.confidence == 0.85
        assert "Found official announcement" in result.reasoning
        assert len(result.sources) > 0
    
    @patch('src.resolution_researcher.GROK_AVAILABLE', True)
    @patch('src.resolution_researcher.Client')
    def test_research_market_resolution_api_error(self, mock_client_class, sample_market_status):
        """Test research with API error"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.chat.create.side_effect = Exception("API Error")
        
        with patch.dict(os.environ, {"XAI_API_KEY": "test_key"}):
            researcher = GrokResolutionResearcher()
            result = researcher.research_market_resolution(sample_market_status)
        
        assert result is None
    
    def test_create_research_prompt(self, sample_market_status):
        """Test research prompt creation"""
        researcher = GrokResolutionResearcher()
        prompt = researcher._create_research_prompt(sample_market_status)
        
        assert isinstance(prompt, str)
        assert sample_market_status.title in prompt
        assert sample_market_status.application_id in prompt
        assert sample_market_status.funding_program_name in prompt
        assert "OUTCOME:" in prompt
        assert "CONFIDENCE:" in prompt
        assert "REASONING:" in prompt
        assert "SOURCES:" in prompt
    
    def test_create_mock_resolution_result(self, sample_market_status):
        """Test mock resolution result creation"""
        researcher = GrokResolutionResearcher()
        twitter_handles = ["test1", "test2"]
        
        result = researcher._create_mock_resolution_result(sample_market_status, twitter_handles)
        
        assert isinstance(result, ResolutionResult)
        assert result.outcome == "Invalid"
        assert result.confidence == 0.3
        assert "Mock result" in result.reasoning
        assert len(result.sources) > 0
        assert result.twitter_handles_searched == twitter_handles
    
    def test_parse_grok_response_valid(self):
        """Test parsing valid Grok response"""
        researcher = GrokResolutionResearcher()
        
        response_content = """
OUTCOME: Yes
CONFIDENCE: 0.85
REASONING: Found official announcement confirming the project received funding from the program after thorough review.
SOURCES: 
- https://twitter.com/testprogram/status/123456789
- https://twitter.com/project/status/987654321
"""
        citations = [Mock(url="https://twitter.com/cite/123")]
        twitter_handles = ["testprogram", "project"]
        
        result = researcher._parse_grok_response(response_content, citations, twitter_handles)
        
        assert result.outcome == "Yes"
        assert result.confidence == 0.85
        assert "Found official announcement" in result.reasoning
        assert len(result.sources) >= 2
        assert result.twitter_handles_searched == twitter_handles
    
    def test_parse_grok_response_malformed(self):
        """Test parsing malformed Grok response"""
        researcher = GrokResolutionResearcher()
        
        response_content = "This is not a properly formatted response"
        citations = []
        twitter_handles = ["test"]
        
        result = researcher._parse_grok_response(response_content, citations, twitter_handles)
        
        assert result.outcome == "Invalid"
        assert result.confidence == 0.5
        assert result.twitter_handles_searched == twitter_handles
    
    def test_parse_grok_response_partial_data(self):
        """Test parsing response with partial data"""
        researcher = GrokResolutionResearcher()
        
        response_content = """
OUTCOME: No
CONFIDENCE: 0.7
"""
        citations = []
        twitter_handles = ["test"]
        
        result = researcher._parse_grok_response(response_content, citations, twitter_handles)
        
        assert result.outcome == "No"
        assert result.confidence == 0.7
        # Should have default reasoning when not provided
        assert len(result.reasoning) > 0
    
    def test_validate_resolution_result_valid(self):
        """Test validation of valid resolution result"""
        researcher = GrokResolutionResearcher()
        
        result = ResolutionResult(
            outcome="Yes",
            confidence=0.8,
            reasoning="Strong evidence found in multiple sources",
            sources=["https://twitter.com/test/123"],
            twitter_handles_searched=["test"]
        )
        
        assert researcher.validate_resolution_result(result) is True
    
    def test_validate_resolution_result_low_confidence(self):
        """Test validation with low confidence"""
        researcher = GrokResolutionResearcher()
        
        result = ResolutionResult(
            outcome="Yes",
            confidence=0.3,  # Below default threshold of 0.7
            reasoning="Some evidence found",
            sources=["https://twitter.com/test/123"],
            twitter_handles_searched=["test"]
        )
        
        assert researcher.validate_resolution_result(result) is False
    
    def test_validate_resolution_result_invalid_outcome(self):
        """Test validation with invalid outcome"""
        researcher = GrokResolutionResearcher()
        
        result = ResolutionResult(
            outcome="Maybe",  # Invalid outcome
            confidence=0.8,
            reasoning="Strong evidence found",
            sources=["https://twitter.com/test/123"],
            twitter_handles_searched=["test"]
        )
        
        assert researcher.validate_resolution_result(result) is False
    
    def test_validate_resolution_result_insufficient_reasoning(self):
        """Test validation with insufficient reasoning"""
        researcher = GrokResolutionResearcher()
        
        result = ResolutionResult(
            outcome="Yes",
            confidence=0.8,
            reasoning="short",  # Too short
            sources=["https://twitter.com/test/123"],
            twitter_handles_searched=["test"]
        )
        
        assert researcher.validate_resolution_result(result) is False
    
    def test_validate_resolution_result_none(self):
        """Test validation with None result"""
        researcher = GrokResolutionResearcher()
        assert researcher.validate_resolution_result(None) is False
    
    def test_validate_resolution_result_custom_threshold(self):
        """Test validation with custom confidence threshold"""
        researcher = GrokResolutionResearcher()
        
        result = ResolutionResult(
            outcome="Yes",
            confidence=0.6,
            reasoning="Moderate evidence found",
            sources=["https://twitter.com/test/123"],
            twitter_handles_searched=["test"]
        )
        
        # Should fail with default threshold (0.7)
        assert researcher.validate_resolution_result(result) is False
        
        # Should pass with lower threshold (0.5)
        assert researcher.validate_resolution_result(result, min_confidence=0.5) is True


@pytest.mark.parametrize("outcome,expected_valid", [
    ("Yes", True),
    ("No", True),
    ("Invalid", True),
    ("Maybe", False),
    ("Unknown", False),
    ("", False),
])
def test_outcome_validation(outcome, expected_valid):
    """Parametrized test for outcome validation"""
    researcher = GrokResolutionResearcher()
    
    result = ResolutionResult(
        outcome=outcome,
        confidence=0.8,
        reasoning="Test reasoning with sufficient length",
        sources=["https://twitter.com/test/123"],
        twitter_handles_searched=["test"]
    )
    
    is_valid = researcher.validate_resolution_result(result)
    assert is_valid == expected_valid


@pytest.mark.parametrize("confidence,min_threshold,expected_valid", [
    (0.8, 0.7, True),
    (0.7, 0.7, True),
    (0.69, 0.7, False),
    (0.5, 0.4, True),
    (0.0, 0.0, True),
    (1.0, 0.9, True),
])
def test_confidence_validation(confidence, min_threshold, expected_valid):
    """Parametrized test for confidence validation"""
    researcher = GrokResolutionResearcher()
    
    result = ResolutionResult(
        outcome="Yes",
        confidence=confidence,
        reasoning="Test reasoning with sufficient length",
        sources=["https://twitter.com/test/123"],
        twitter_handles_searched=["test"]
    )
    
    is_valid = researcher.validate_resolution_result(result, min_confidence=min_threshold)
    assert is_valid == expected_valid


class TestResolutionResult:
    """Tests for ResolutionResult dataclass"""
    
    def test_resolution_result_creation(self):
        """Test creating ResolutionResult"""
        result = ResolutionResult(
            outcome="Yes",
            confidence=0.8,
            reasoning="Test reasoning",
            sources=["source1", "source2"],
            twitter_handles_searched=["handle1", "handle2"]
        )
        
        assert result.outcome == "Yes"
        assert result.confidence == 0.8
        assert result.reasoning == "Test reasoning"
        assert len(result.sources) == 2
        assert len(result.twitter_handles_searched) == 2
    
    def test_resolution_result_defaults(self):
        """Test ResolutionResult with minimal parameters"""
        result = ResolutionResult(
            outcome="No",
            confidence=0.5,
            reasoning="Minimal test",
            sources=[],
            twitter_handles_searched=[]
        )
        
        assert result.outcome == "No"
        assert result.confidence == 0.5
        assert isinstance(result.sources, list)
        assert isinstance(result.twitter_handles_searched, list)