"""
Core blockchain types for market creation and betting.
Simplified version of prediction_market_agent_tooling types.
"""
from decimal import Decimal
from typing import NewType, Optional, List
from datetime import datetime
from dataclasses import dataclass
from web3 import Web3

# Basic types
PrivateKey = NewType("PrivateKey", str)
ChecksumAddress = NewType("ChecksumAddress", str) 
HexAddress = NewType("HexAddress", str)
OutcomeStr = NewType("OutcomeStr", str)
USD = NewType("USD", Decimal)

# Market outcomes for binary markets
OMEN_BINARY_OUTCOMES = ["Yes", "No"]
OMEN_TRUE_OUTCOME = "Yes"
OMEN_FALSE_OUTCOME = "No"

@dataclass
class APIKeys:
    """API keys and configuration for blockchain interactions."""
    BET_FROM_PRIVATE_KEY: Optional[PrivateKey] = None
    SAFE_ADDRESS: Optional[ChecksumAddress] = None
    GRAPH_API_KEY: Optional[str] = None

@dataclass 
class MarketCreationResult:
    """Result of market creation operation."""
    success: bool
    market_id: Optional[HexAddress] = None
    market_url: Optional[str] = None
    transaction_hash: Optional[str] = None
    error_message: Optional[str] = None
    raw_output: Optional[str] = None

@dataclass
class BetResult:
    """Result of betting operation."""
    success: bool
    transaction_hash: Optional[str] = None
    error_message: Optional[str] = None
    raw_output: Optional[str] = None

@dataclass
class ResolutionResult:
    """Result of market resolution operation."""
    success: bool
    market_id: Optional[str] = None
    outcome: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    bond_amount: Optional[float] = None
    transaction_hash: Optional[str] = None
    error_message: Optional[str] = None
    raw_output: Optional[str] = None

# Collateral token choices (simplified)
COLLATERAL_TOKEN_ADDRESSES = {
    "wxdai": "0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d",
    "sdai": "0xaf204776c7245bF4147c2612BF6e5972Ee483701",
    "usdc": "0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83"
}

# Default market fee percentage
OMEN_DEFAULT_MARKET_FEE_PERC = 0.02  # 2%

def private_key_type(key: str) -> PrivateKey:
    """Convert string to PrivateKey type with basic validation."""
    if not key or not key.startswith('0x'):
        if not key.startswith('0x'):
            key = '0x' + key
    return PrivateKey(key)

def to_checksum_address(address: str) -> ChecksumAddress:
    """Convert address to checksum format."""
    return ChecksumAddress(Web3.to_checksum_address(address))

def usd_to_decimal(amount: str | float) -> USD:
    """Convert USD amount to Decimal."""
    return USD(Decimal(str(amount)))