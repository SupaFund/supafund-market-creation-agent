"""
Resolution research service using Grok API to determine market outcomes.
"""
import logging
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone
import re
import os

try:
    from xai_sdk import Client
    from xai_sdk.chat import user
    from xai_sdk.search import SearchParameters, x_source
    GROK_AVAILABLE = True
except ImportError:
    # Fallback for when xai-sdk is not available
    GROK_AVAILABLE = False
    Client = None
    user = None
    SearchParameters = None
    x_source = None

from .market_monitor import MarketStatus

logger = logging.getLogger(__name__)

@dataclass
class ResolutionResult:
    """Result of resolution research"""
    outcome: str  # "Yes", "No", or "Invalid"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    sources: List[str]
    twitter_handles_searched: List[str]

class GrokResolutionResearcher:
    """Service to research market resolutions using Grok API"""
    
    def __init__(self):
        if not GROK_AVAILABLE:
            raise ImportError("xai-sdk is not installed. Please install it with: pip install xai-sdk")
        
        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            logger.warning("XAI_API_KEY not set. Grok API functionality will use mock responses.")
            self.client = None
        else:
            self.client = Client(api_key=self.api_key)
    
    def extract_twitter_handles_from_url(self, twitter_url: str) -> List[str]:
        """
        Extract Twitter handles from URLs
        
        Args:
            twitter_url: Twitter URL or handle
            
        Returns:
            List of Twitter handles (without @)
        """
        if not twitter_url:
            return []
        
        # Handle direct handles
        if twitter_url.startswith("@"):
            return [twitter_url[1:]]
        
        # Extract from URLs
        # Match patterns like twitter.com/username or x.com/username
        pattern = r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)'
        matches = re.findall(pattern, twitter_url)
        
        return matches if matches else []
    
    def get_default_crypto_handles(self) -> List[str]:
        """Get default crypto/funding related Twitter handles to search"""
        return [
            "ethereum",
            "VitalikButerin", 
            "EthereumFoundation",
            "gitcoin",
            "protocollabs",
            "paradigm",
            "a16zcrypto",
            "coinbase",
            "binance"
        ]
    
    def research_market_resolution(self, market_status: MarketStatus) -> Optional[ResolutionResult]:
        """
        Research the resolution of a market using Grok API
        
        Args:
            market_status: Market status information
            
        Returns:
            Resolution result or None if unable to determine
        """
        try:
            # Extract Twitter handles to search
            twitter_handles = []
            
            # Add funding program's Twitter handle if available
            if market_status.funding_program_twitter:
                handles = self.extract_twitter_handles_from_url(market_status.funding_program_twitter)
                twitter_handles.extend(handles)
            
            # Add some default crypto/funding related handles if we don't have specific ones
            if not twitter_handles:
                twitter_handles = self.get_default_crypto_handles()
            
            # Limit to 10 handles as per API requirement
            twitter_handles = twitter_handles[:10]
            
            # Create the research prompt
            prompt = self._create_research_prompt(market_status)
            
            # Use real Grok API if available and configured
            if not self.client:
                logger.warning("No XAI_API_KEY configured, returning mock result")
                return self._create_mock_resolution_result(market_status, twitter_handles)
            
            # Execute Grok search with Twitter data
            chat = self.client.chat.create(
                model="grok-4",
                search_parameters=SearchParameters(
                    mode="auto",
                    sources=[x_source(included_x_handles=twitter_handles)],
                ),
            )
            
            chat.append(user(prompt))
            response = chat.sample()
            
            # Parse the response
            resolution = self._parse_grok_response(
                response.content, 
                response.citations if hasattr(response, 'citations') else [],
                twitter_handles
            )
            
            logger.info(f"Grok research completed for market {market_status.market_id}: {resolution.outcome}")
            return resolution
            
        except Exception as e:
            logger.error(f"Error researching market resolution: {e}")
            return None
    
    def _create_research_prompt(self, market_status: MarketStatus) -> str:
        """
        Create a detailed prompt for Grok to research the market resolution
        
        Args:
            market_status: Market status information
            
        Returns:
            Research prompt string
        """
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        prompt = f"""
You are analyzing a prediction market to determine its correct resolution based on real-world outcomes.

Market Details:
- Market Title: "{market_status.title}"
- Market ID: {market_status.market_id}
- Application ID: {market_status.application_id}
- Funding Program: {market_status.funding_program_name}
- Market Closing Date: {market_status.closing_time}
- Current Date: {current_date}

Task: Determine if the project mentioned in this market title has successfully received funding or achieved the milestone specified in the funding program "{market_status.funding_program_name}".

Please search for recent posts on Twitter/X about:
1. The specific funding program "{market_status.funding_program_name}"
2. Any announcements about funding recipients or successful applications
3. The specific project or application referenced by ID {market_status.application_id}
4. Any relevant updates about the funding process or results

Based on your findings, please provide:

1. OUTCOME: One of the following:
   - "Yes" if the project/application successfully received funding or achieved the milestone
   - "No" if the project/application was rejected or failed to achieve the milestone  
   - "Invalid" if there's insufficient information or the market question is ambiguous

2. CONFIDENCE: A confidence score from 0.0 to 1.0 indicating how certain you are of this outcome

3. REASONING: A detailed explanation of your decision based on the evidence found

4. SOURCES: List the key Twitter posts or announcements that informed your decision

Please be thorough in your analysis and only return "Yes" if you have clear evidence that the funding was approved or milestone was achieved. If there's any doubt or lack of clear information, lean towards "Invalid" or "No" as appropriate.

Format your response as:
OUTCOME: [Yes/No/Invalid]
CONFIDENCE: [0.0-1.0]
REASONING: [Your detailed reasoning]
SOURCES: [List of relevant sources/posts]
"""
        return prompt
    
    def _create_mock_resolution_result(self, market_status: MarketStatus, twitter_handles: List[str]) -> ResolutionResult:
        """
        Create a mock resolution result for testing/fallback purposes
        
        Args:
            market_status: Market status information
            twitter_handles: Twitter handles that would be searched
            
        Returns:
            Mock ResolutionResult
        """
        logger.info(f"Creating mock resolution result for market {market_status.market_id}")
        
        # This is a placeholder implementation - in reality you would call the Grok API
        # For testing purposes, we return "Invalid" with low confidence
        return ResolutionResult(
            outcome="Invalid",
            confidence=0.3,
            reasoning=f"Mock result: Cannot determine outcome for market '{market_status.title}' "
                     f"without access to Grok API. Would search Twitter handles: {twitter_handles}",
            sources=[f"Mock source: Would search @{handle}" for handle in twitter_handles[:3]],
            twitter_handles_searched=twitter_handles
        )
    
    def _parse_grok_response(self, response_content: str, citations: List, twitter_handles: List[str]) -> ResolutionResult:
        """
        Parse Grok's response into a structured ResolutionResult
        
        Args:
            response_content: The response text from Grok
            citations: List of citations from Grok
            twitter_handles: Twitter handles that were searched
            
        Returns:
            Parsed ResolutionResult
        """
        try:
            # Extract outcome
            outcome_match = re.search(r'OUTCOME:\s*(Yes|No|Invalid)', response_content, re.IGNORECASE)
            outcome = outcome_match.group(1).capitalize() if outcome_match else "Invalid"
            
            # Extract confidence
            confidence_match = re.search(r'CONFIDENCE:\s*([0-9.]+)', response_content)
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            
            # Extract reasoning
            reasoning_match = re.search(r'REASONING:\s*(.*?)(?=SOURCES:|$)', response_content, re.DOTALL)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "No detailed reasoning provided"
            
            # Extract sources
            sources_match = re.search(r'SOURCES:\s*(.*)', response_content, re.DOTALL)
            sources_text = sources_match.group(1).strip() if sources_match else ""
            
            # Parse sources into list
            sources = []
            if sources_text:
                # Split by lines and clean up
                source_lines = [line.strip() for line in sources_text.split('\n') if line.strip()]
                sources = [line.lstrip('- ').lstrip('* ') for line in source_lines if line.strip()]
            
            # Add citation URLs if available
            if citations:
                for citation in citations:
                    if hasattr(citation, 'url') and citation.url:
                        sources.append(citation.url)
            
            return ResolutionResult(
                outcome=outcome,
                confidence=confidence,
                reasoning=reasoning,
                sources=sources,
                twitter_handles_searched=twitter_handles
            )
            
        except Exception as e:
            logger.error(f"Error parsing Grok response: {e}")
            return ResolutionResult(
                outcome="Invalid",
                confidence=0.0,
                reasoning=f"Error parsing response: {str(e)}",
                sources=[],
                twitter_handles_searched=twitter_handles
            )
    
    def validate_resolution_result(self, result: ResolutionResult, min_confidence: float = 0.7) -> bool:
        """
        Validate if a resolution result meets confidence thresholds
        
        Args:
            result: The resolution result to validate
            min_confidence: Minimum confidence threshold
            
        Returns:
            True if the result is valid and confident enough
        """
        if not result:
            return False
            
        # Check confidence threshold
        if result.confidence < min_confidence:
            logger.warning(f"Resolution confidence {result.confidence} below threshold {min_confidence}")
            return False
        
        # Check if outcome is valid
        if result.outcome not in ["Yes", "No", "Invalid"]:
            logger.warning(f"Invalid outcome: {result.outcome}")
            return False
        
        # Check if we have some reasoning
        if not result.reasoning or len(result.reasoning.strip()) < 10:
            logger.warning("Insufficient reasoning provided")
            return False
        
        return True