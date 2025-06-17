from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal

# Token related schemas
class TokenCreate(BaseModel):
    symbol: str
    name: str
    contract_address: str
    chain: str
    decimals: Optional[int] = 18
    image_url: Optional[str] = None

class TokenResponse(BaseModel):
    name: str
    symbol: str
    contract_address: str
    chain: str
    decimals: int
    image_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    pools_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# Pool related schemas
class TokenPoolCreate(BaseModel):
    base_token_id: str
    quote_token_id: str
    dex: str
    chain: str
    pair_address: str
    pool_version: Optional[str] = None
    fee_tier: Optional[int] = None

class TokenPoolResponse(BaseModel):
    id: str
    base_token_id: str
    quote_token_id: str
    dex: str
    chain: str
    pair_address: str
    pool_version: Optional[str]
    fee_tier: Optional[int]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Pool metrics schemas
class PoolMetricResponse(BaseModel):
    id: str
    pool_id: str
    price_usd: Optional[Decimal]
    price_native: Optional[Decimal]
    volume_1h: Optional[Decimal]
    volume_24h: Optional[Decimal]
    liquidity_usd: Optional[Decimal]
    liquidity_base: Optional[Decimal]
    liquidity_quote: Optional[Decimal]
    price_change_1h: Optional[Decimal]
    price_change_24h: Optional[Decimal]
    txns_1h_buys: int
    txns_1h_sells: int
    txns_24h_buys: int
    txns_24h_sells: int
    market_cap: Optional[Decimal]
    fdv: Optional[Decimal]
    data_source: Optional[str]
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Token metrics schemas (aggregated)
class TokenMetricResponse(BaseModel):
    id: str
    token_id: str
    # Aggregated price data
    avg_price_usd: Optional[Decimal]
    weighted_price_usd: Optional[Decimal]
    total_volume_24h: Optional[Decimal]
    total_liquidity_usd: Optional[Decimal]
    market_cap: Optional[Decimal]
    
    # Technical indicators
    rsi_14d: Optional[float]
    ma_7d: Optional[float]
    ma_30d: Optional[float]
    volatility_24h: Optional[float]
    
    # On-chain metrics
    holder_count: Optional[int]
    unique_traders_24h: Optional[int]
    
    # Signals
    breakout_signal: bool
    trend_direction: Optional[str]
    signal_strength: Optional[float]
    
    # Meta
    pools_count: int
    last_calculation_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Enhanced signal response with pool-level data
class EnhancedSignalResponse(BaseModel):
    token: TokenResponse
    signal: str
    reason: str
    confidence: float
    
    # Aggregated metrics
    token_metrics: TokenMetricResponse
    
    # Pool-level breakdown
    pool_data: List[Dict[str, Any]]
    
    # Market analysis
    market_analysis: Dict[str, Any]
    
    updated_at: str

# Simple signal response for backward compatibility
class SignalResponse(BaseModel):
    token: str
    signal: str
    reason: str
    confidence: Optional[float] = 0.5
    metrics: Dict[str, Any]
    updated_at: str

# Chat related schemas
class ChatRequest(BaseModel):
    message: str
    include_pools: Optional[bool] = False  # Include pool-level data in response

class ChatResponse(BaseModel):
    response: str
    signal_data: Optional[Dict[str, Any]] = None
    intent: Optional[Dict[str, Any]] = None
    pool_analysis: Optional[List[Dict[str, Any]]] = None

# Pool analysis for specific DEX comparison
class PoolAnalysisRequest(BaseModel):
    token_symbol: str
    dex_ids: Optional[List[str]] = None  # Compare specific DEXs
    include_arbitrage: Optional[bool] = False

class PoolAnalysisResponse(BaseModel):
    token: str
    pools: List[PoolMetricResponse]
    arbitrage_opportunities: Optional[List[Dict[str, Any]]] = None
    best_pool: Optional[Dict[str, Any]] = None
    updated_at: datetime

# Aggregation helpers
class TokenSearchRequest(BaseModel):
    query: str  # symbol, name, or contract address
    chain: Optional[str] = None
    limit: Optional[int] = 10

class TokenSearchResponse(BaseModel):
    tokens: List[TokenResponse]
    total: int

# Error schemas
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None 