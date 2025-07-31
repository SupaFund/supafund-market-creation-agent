"""
Market monitoring service for detecting completed prediction markets.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
import requests
from dataclasses import dataclass

from .config import Config
from .supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

@dataclass
class MarketStatus:
    """Market status information from The Graph"""
    market_id: str
    title: str
    closing_time: datetime
    is_closed: bool
    is_resolved: bool
    application_id: str
    funding_program_name: str
    funding_program_twitter: Optional[str]

class TheGraphClient:
    """Client for interacting with The Graph API to get market status"""
    
    def __init__(self):
        self.api_key = Config.GRAPH_API_KEY
        self.omen_subgraph_url = "https://api.thegraph.com/subgraphs/name/omen-pm/omen-xdai"
        
    def get_market_status(self, market_id: str) -> Optional[Dict]:
        """
        Query The Graph for market status information
        
        Args:
            market_id: The market contract address
            
        Returns:
            Market status data or None if not found
        """
        query = """
        query GetMarket($marketId: String!) {
            fixedProductMarketMaker(id: $marketId) {
                id
                title
                question {
                    id
                    title
                    isPendingArbitration
                    currentAnswer
                    currentAnswerTimestamp
                    finalizationTimestamp
                    arbitrator
                }
                answerFinalizedTimestamp
                resolutionTimestamp
                creationTimestamp
                lastActiveDay
                closed
                condition {
                    id
                    resolved
                    payoutNumerators
                }
            }
        }
        """
        
        variables = {"marketId": market_id.lower()}
        
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = requests.post(
                self.omen_subgraph_url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    return None
                    
                market_data = data.get("data", {}).get("fixedProductMarketMaker")
                return market_data
            else:
                logger.error(f"Graph API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying The Graph: {e}")
            return None

    def is_market_closed_and_unresolved(self, market_data: Dict) -> bool:
        """
        Check if market is closed but not yet resolved
        
        Args:
            market_data: Market data from The Graph
            
        Returns:
            True if market is closed but unresolved
        """
        if not market_data:
            return False
            
        # Check if market is closed
        is_closed = market_data.get("closed", False)
        
        # Check if condition is resolved
        condition = market_data.get("condition", {})
        is_resolved = condition.get("resolved", False)
        
        # Check if resolution timestamp exists
        has_resolution = market_data.get("resolutionTimestamp") is not None
        
        return is_closed and not (is_resolved or has_resolution)

class MarketMonitor:
    """Main market monitoring service"""
    
    def __init__(self):
        self.graph_client = TheGraphClient()
        self.supabase = get_supabase_client()
        
    def get_markets_to_monitor(self) -> List[Dict]:
        """
        Get all active markets from database that need monitoring
        
        Returns:
            List of market records with application details
        """
        try:
            # Query prediction_markets joined with applications and funding programs
            response = self.supabase.table("prediction_markets").select(
                """
                *,
                application:program_applications (
                    id,
                    project:projects (
                        name,
                        description
                    ),
                    program:funding_programs (
                        name,
                        twitter_url,
                        long_description
                    )
                )
                """
            ).in_("status", ["created", "active"]).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error fetching markets to monitor: {e}")
            return []
    
    def check_completed_markets(self) -> List[MarketStatus]:
        """
        Check all active markets for completion status
        
        Returns:
            List of completed but unresolved markets
        """
        markets = self.get_markets_to_monitor()
        completed_markets = []
        
        logger.info(f"Checking {len(markets)} markets for completion status")
        
        for market in markets:
            try:
                market_id = market.get("market_id", "")
                if not market_id or market_id.startswith("FAILED_"):
                    continue
                    
                # Get market status from The Graph
                graph_data = self.graph_client.get_market_status(market_id)
                
                if not graph_data:
                    logger.warning(f"No data found for market {market_id}")
                    continue
                
                # Check if market is closed but unresolved
                if self.graph_client.is_market_closed_and_unresolved(graph_data):
                    # Extract application and funding program info
                    application = market.get("application", {})
                    program = application.get("program", {}) if application else {}
                    
                    # Check if market title contains application UUID
                    market_title = graph_data.get("title", "")
                    application_id = market.get("application_id", "")
                    
                    if application_id in market_title:
                        market_status = MarketStatus(
                            market_id=market_id,
                            title=market_title,
                            closing_time=self._parse_timestamp(graph_data.get("lastActiveDay")),
                            is_closed=True,
                            is_resolved=False,
                            application_id=application_id,
                            funding_program_name=program.get("name", ""),
                            funding_program_twitter=program.get("twitter_url", "")
                        )
                        completed_markets.append(market_status)
                        logger.info(f"Found completed market: {market_id}")
                
            except Exception as e:
                logger.error(f"Error checking market {market.get('market_id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Found {len(completed_markets)} completed markets")
        return completed_markets
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None
        try:
            # The Graph returns timestamps as Unix timestamps
            timestamp = int(timestamp_str)
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, TypeError):
            return None
    
    def update_market_status_in_db(self, market_id: str, new_status: str, metadata: Dict = None):
        """
        Update market status in database
        
        Args:
            market_id: Market ID to update
            new_status: New status value
            metadata: Additional metadata to store
        """
        try:
            update_data = {
                "status": new_status,
                "metadata": metadata or {},
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table("prediction_markets").update(
                update_data
            ).eq("market_id", market_id).execute()
            
            if result.data:
                logger.info(f"Updated market {market_id} status to {new_status}")
            else:
                logger.warning(f"No rows updated for market {market_id}")
                
        except Exception as e:
            logger.error(f"Error updating market status for {market_id}: {e}")