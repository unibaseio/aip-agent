from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal
import uuid

# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            uuid.UUID: str
        }
    )

# Token related schemas
class TokenResponse(BaseModel):
    name: str
    symbol: str
    contract_address: str
    chain: str
    
    model_config = ConfigDict(from_attributes=True)

# Chat related schemas
class ChatRequest(BaseModel):
    message: str
    include_pools: Optional[bool] = False
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str

# Bot Owner Schemas
class BotOwnerCreate(BaseModel):
    """创建机器人所有者的请求模型"""
    owner_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., description="邮箱地址")
    wallet_address: str = Field(..., min_length=20, max_length=100, description="主钱包地址")
    phone: Optional[str] = Field(None, max_length=20)
    subscription_tier: Literal["basic", "premium", "enterprise"] = Field("basic")
    max_bots_allowed: int = Field(5, ge=1, le=100)

class BotOwnerUpdate(BaseModel):
    """更新机器人所有者的请求模型"""
    owner_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    subscription_tier: Optional[Literal["basic", "premium", "enterprise"]] = None
    max_bots_allowed: Optional[int] = Field(None, ge=1, le=100)
    is_active: Optional[bool] = None

class BotOwnerResponse(BaseSchema):
    """机器人所有者详情响应模型"""
    id: uuid.UUID
    owner_name: str
    email: str
    wallet_address: str
    phone: Optional[str]
    is_active: bool
    max_bots_allowed: int
    subscription_tier: str
    total_bots_created: int
    total_trading_volume_usd: Decimal
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]

# Trading Strategy Schemas
class TradingStrategyCreate(BaseModel):
    """创建交易策略的请求模型"""
    strategy_name: str = Field(..., min_length=1, max_length=100)
    strategy_description: Optional[str] = None
    strategy_type: Literal["conservative", "moderate", "aggressive", "momentum", "mean_reversion", "user_defined"]
    risk_level: Literal["low", "medium", "high"]
    
    # 数值参数设置
    max_position_size: Decimal = Field(..., ge=1, le=100, description="单币最大仓位比例(%)")
    stop_loss_percentage: Decimal = Field(..., ge=0, le=50, description="止损百分比(%)")
    take_profit_percentage: Decimal = Field(..., ge=1, le=200, description="止盈百分比(%)")
    min_profit_threshold: Decimal = Field(..., ge=0, le=50, description="最低收益率阈值(%)")
    max_daily_trades: int = Field(..., ge=1, le=100, description="每日最大交易次数")
    llm_confidence_threshold: Decimal = Field(..., ge=0, le=1, description="LLM决策置信度阈值")
    
    # 交易费用设置
    gas_fee_native: Optional[Decimal] = Field(0.00003, ge=0)
    trading_fee_percentage: Optional[Decimal] = Field(0.1, ge=0, le=10)
    slippage_tolerance: Optional[Decimal] = Field(1.0, ge=0, le=50)
    
    # 运行控制参数
    min_trade_amount_usd: Optional[Decimal] = Field(10.0, ge=1)
    polling_interval_hours: Optional[Decimal] = Field(1.0, ge=0.1, le=24)
    
    # 功能开关
    enable_stop_loss: Optional[bool] = True
    enable_take_profit: Optional[bool] = True
    
    # 策略描述性配置
    buy_strategy_description: Optional[str] = None
    sell_strategy_description: Optional[str] = None
    filter_strategy_description: Optional[str] = None
    summary_strategy_description: Optional[str] = None
    
    # 状态
    is_public: Optional[bool] = False

class TradingStrategyUpdate(BaseModel):
    """更新交易策略的请求模型"""
    strategy_name: Optional[str] = Field(None, min_length=1, max_length=100)
    strategy_description: Optional[str] = None
    strategy_type: Optional[Literal["conservative", "moderate", "aggressive", "momentum", "mean_reversion", "user_defined"]] = None
    risk_level: Optional[Literal["low", "medium", "high"]] = None
    
    # 数值参数设置
    max_position_size: Optional[Decimal] = Field(None, ge=1, le=100)
    stop_loss_percentage: Optional[Decimal] = Field(None, ge=0, le=50)
    take_profit_percentage: Optional[Decimal] = Field(None, ge=1, le=200)
    min_profit_threshold: Optional[Decimal] = Field(None, ge=0, le=50)
    max_daily_trades: Optional[int] = Field(None, ge=1, le=100)
    llm_confidence_threshold: Optional[Decimal] = Field(None, ge=0, le=1)
    
    # 交易费用设置
    gas_fee_native: Optional[Decimal] = Field(None, ge=0)
    trading_fee_percentage: Optional[Decimal] = Field(None, ge=0, le=10)
    slippage_tolerance: Optional[Decimal] = Field(None, ge=0, le=50)
    
    # 运行控制参数
    min_trade_amount_usd: Optional[Decimal] = Field(None, ge=1)
    polling_interval_hours: Optional[Decimal] = Field(None, ge=0.1, le=24)
    
    # 功能开关
    enable_stop_loss: Optional[bool] = None
    enable_take_profit: Optional[bool] = None
    
    # 策略描述性配置
    buy_strategy_description: Optional[str] = None
    sell_strategy_description: Optional[str] = None
    filter_strategy_description: Optional[str] = None
    summary_strategy_description: Optional[str] = None
    
    # 状态
    is_public: Optional[bool] = None

class TradingStrategyResponse(BaseSchema):
    """交易策略详情响应模型"""
    id: uuid.UUID
    owner_id: uuid.UUID
    
    # 策略基本信息
    strategy_name: str
    strategy_description: Optional[str]
    strategy_type: str
    risk_level: str
    
    # 数值参数设置
    max_position_size: Decimal
    stop_loss_percentage: Decimal
    take_profit_percentage: Decimal
    min_profit_threshold: Decimal
    max_daily_trades: int
    llm_confidence_threshold: Decimal
    
    # 交易费用设置
    gas_fee_native: Decimal
    trading_fee_percentage: Decimal
    slippage_tolerance: Decimal
    
    # 运行控制参数
    min_trade_amount_usd: Decimal
    polling_interval_hours: Decimal
    
    # 功能开关
    enable_stop_loss: bool
    enable_take_profit: bool
    
    # 策略描述性配置
    buy_strategy_description: Optional[str]
    sell_strategy_description: Optional[str]
    filter_strategy_description: Optional[str]
    summary_strategy_description: Optional[str]
    
    # 状态
    is_public: bool
    
    # 使用统计
    usage_count: int
    success_rate: Optional[Decimal]
    average_profit_percentage: Optional[Decimal]
    
    # 时间戳
    created_at: datetime
    updated_at: datetime

# Trading Bot Configuration Schemas
class TradingBotCreate(BaseModel):
    """创建交易机器人的请求模型"""
    bot_name: str = Field(..., min_length=1, max_length=100)
    account_address: str = Field(..., min_length=20, max_length=100)
    chain: Literal["bsc", "solana"]
    initial_balance_usd: Decimal = Field(..., gt=0, description="初始余额，最小1000")
    
    # 所有者信息（可选，启动后可以设置）
    owner_id: Optional[uuid.UUID] = Field(None, description="机器人所有者ID")
    strategy_id: Optional[uuid.UUID] = Field(None, description="关联的策略ID")
    
    @field_validator('initial_balance_usd')
    @classmethod
    def validate_initial_balance(cls, v):
        if v < 1000:
            raise ValueError('Initial balance must be at least 1000 USD')
        return v

class TradingBotUpdate(BaseModel):
    """更新交易机器人的请求模型"""
    bot_name: Optional[str] = Field(None, min_length=1, max_length=100)
    strategy_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None

class TradingBotSummary(BaseSchema):
    """交易机器人摘要响应模型"""
    id: uuid.UUID
    bot_name: str
    account_address: str
    chain: str
    strategy_type: str
    total_assets_usd: Decimal
    total_profit_usd: Decimal
    total_profit_percentage: Decimal
    is_active: bool
    last_activity_at: Optional[datetime]
    owner_name: Optional[str] = None

class TradingBotResponse(BaseSchema):
    """交易机器人详情响应模型"""
    id: uuid.UUID
    owner_id: Optional[uuid.UUID]
    strategy_id: Optional[uuid.UUID]
    
    # 基础信息
    bot_name: str
    account_address: str
    chain: str
    strategy_type: str
    
    # Financial status
    initial_balance_usd: Decimal
    current_balance_usd: Decimal
    total_assets_usd: Decimal
    
    # Status
    is_active: bool
    is_configured: bool
    
    # Statistics
    total_trades: int
    profitable_trades: int
    total_profit_usd: Decimal
    max_drawdown_percentage: Decimal
    
    # Strategy parameters (from associated strategy)
    max_position_size: Optional[Decimal] = None
    stop_loss_percentage: Optional[Decimal] = None
    take_profit_percentage: Optional[Decimal] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_activity_at: Optional[datetime]
    
    # 关联信息
    owner: Optional[BotOwnerResponse] = None
    strategy: Optional[TradingStrategyResponse] = None

# Position Schemas
class PositionResponse(BaseSchema):
    """持仓响应模型"""
    id: uuid.UUID
    token_symbol: str
    token_name: str
    quantity: Decimal
    average_cost_usd: Decimal
    total_cost_usd: Decimal
    current_price_usd: Optional[Decimal]
    current_value_usd: Optional[Decimal]
    unrealized_pnl_usd: Optional[Decimal]
    unrealized_pnl_percentage: Optional[Decimal]
    stop_loss_price: Optional[Decimal]
    take_profit_price: Optional[Decimal]
    is_active: bool
    created_at: datetime
    updated_at: datetime

# Transaction Schemas
class TransactionCreate(BaseModel):
    """创建交易的请求模型"""
    transaction_type: Literal["buy", "sell"]
    token_id: uuid.UUID
    amount_usd: Optional[Decimal] = Field(None, gt=0, description="买入时的USD金额")
    token_amount: Optional[Decimal] = Field(None, gt=0, description="卖出时的代币数量")
    
    @field_validator('amount_usd', 'token_amount', mode='before')
    @classmethod
    def validate_amounts(cls, v, info):
        transaction_type = info.data.get('transaction_type')
        if transaction_type == 'buy' and info.field_name == 'amount_usd' and not v:
            raise ValueError('amount_usd is required for buy transactions')
        if transaction_type == 'sell' and info.field_name == 'token_amount' and not v:
            raise ValueError('token_amount is required for sell transactions')
        return v

class TransactionResponse(BaseSchema):
    """交易响应模型"""
    id: uuid.UUID
    transaction_type: str
    status: str
    token_symbol: str
    token_name: str
    bot_name: Optional[str] = None  # Added for display purposes
    amount_usd: Optional[Decimal]
    token_amount: Optional[Decimal]
    price_usd: Decimal
    gas_cost_usd: Decimal
    trading_fee_usd: Decimal
    total_cost_usd: Decimal
    realized_pnl_usd: Optional[Decimal]
    realized_pnl_percentage: Optional[Decimal]
    balance_before_usd: Optional[Decimal]
    balance_after_usd: Optional[Decimal]
    position_before: Optional[Decimal]
    position_after: Optional[Decimal]
    market_cap_at_trade: Optional[Decimal]
    volume_24h_at_trade: Optional[Decimal]
    created_at: datetime
    executed_at: Optional[datetime]

# LLM Decision Schemas
class LLMDecisionResponse(BaseSchema):
    """LLM决策响应模型"""
    id: uuid.UUID
    decision_type: str
    decision_phase: str
    llm_response: str
    reasoning: str
    confidence_score: Optional[Decimal]
    recommended_action: Optional[str]
    recommended_token_symbol: Optional[str]
    recommended_amount: Optional[Decimal]
    recommended_percentage: Optional[Decimal]
    expected_return_percentage: Optional[Decimal]
    risk_assessment: Optional[str]
    market_sentiment: Optional[str]
    was_executed: bool
    execution_reason: Optional[str]
    created_at: datetime
    execution_time: Optional[datetime]

# Revenue Schemas
class RevenueSnapshot(BaseSchema):
    """收益快照响应模型"""
    id: uuid.UUID
    total_assets_usd: Decimal
    available_balance_usd: Decimal
    total_positions_value_usd: Decimal
    total_profit_usd: Decimal
    total_profit_percentage: Decimal
    daily_profit_usd: Optional[Decimal]
    daily_profit_percentage: Optional[Decimal]
    total_trades: int
    profitable_trades: int
    win_rate: Optional[Decimal]
    average_profit_per_trade: Optional[Decimal]
    max_drawdown_percentage: Optional[Decimal]
    current_drawdown_percentage: Optional[Decimal]
    active_positions_count: int
    snapshot_type: str
    created_at: datetime

class RevenueSnapshotSchema(BaseSchema):
    """收益快照响应模型（别名）"""
    id: uuid.UUID
    total_assets_usd: Decimal
    available_balance_usd: Decimal
    total_positions_value_usd: Decimal
    total_profit_usd: Decimal
    total_profit_percentage: Decimal
    daily_profit_usd: Optional[Decimal]
    daily_profit_percentage: Optional[Decimal]
    total_trades: int
    profitable_trades: int
    win_rate: Optional[Decimal]
    average_profit_per_trade: Optional[Decimal]
    max_drawdown_percentage: Optional[Decimal]
    current_drawdown_percentage: Optional[Decimal]
    active_positions_count: int
    snapshot_type: str
    created_at: datetime

class RevenueMetrics(BaseModel):
    """收益指标响应模型"""
    total_profit_usd: Decimal
    total_profit_percentage: Decimal
    win_rate: Decimal
    total_trades: int
    profitable_trades: int
    average_profit_per_trade: Decimal
    max_drawdown_percentage: Decimal
    sharpe_ratio: Optional[Decimal]
    volatility: Optional[Decimal]

# Token Market Data Schemas (用于交易决策)
class TokenMarketData(BaseModel):
    """代币市场数据模型"""
    symbol: str
    name: str
    current_price_usd: Decimal
    market_cap: Optional[Decimal]
    volume_24h: Optional[Decimal]
    price_change_24h: Optional[Decimal]
    price_change_1h: Optional[Decimal]
    liquidity_usd: Optional[Decimal]
    holder_count: Optional[int]
    
    # Technical indicators
    rsi_14d: Optional[float]
    ma_7d: Optional[float]
    ma_30d: Optional[float]
    volatility_24h: Optional[float]
    
    # Trading signals
    trend_direction: Optional[str]
    signal_strength: Optional[float]
    breakout_signal: Optional[bool]

# Trading Decision Schemas
class SellDecisionRequest(BaseModel):
    """卖出决策请求模型"""
    positions: List[PositionResponse]
    market_data: Dict[str, TokenMarketData]
    bot_config: TradingBotResponse

class BuyDecisionRequest(BaseModel):
    """买入决策请求模型"""
    available_balance_usd: Decimal
    token_candidates: List[TokenMarketData]
    bot_config: TradingBotResponse

class TradingDecisionResponse(BaseModel):
    """交易决策响应模型"""
    decision_type: Literal["sell", "buy", "hold"]
    token_symbol: Optional[str] = None
    amount_usd: Optional[Decimal] = None
    token_amount: Optional[Decimal] = None
    sell_percentage: Optional[Decimal] = None
    confidence_score: Decimal = Field(..., ge=0, le=1)
    reasoning: str
    risk_assessment: Literal["low", "medium", "high"]
    expected_return_percentage: Optional[Decimal] = None
    market_sentiment: Literal["bullish", "bearish", "neutral"]

# Portfolio Analysis Schemas
class PortfolioSummary(BaseModel):
    """投资组合摘要"""
    total_value_usd: Decimal
    available_balance_usd: Decimal
    total_positions_value_usd: Decimal
    total_unrealized_pnl_usd: Decimal
    total_unrealized_pnl_percentage: Decimal
    active_positions_count: int
    largest_position_percentage: Decimal
    positions: List[PositionResponse]

# System Status Schemas
class SystemStatus(BaseModel):
    """系统状态模型"""
    total_bots: int
    active_bots: int
    total_trades_24h: int
    total_volume_24h_usd: Decimal
    today_profit_usd: Decimal
    total_assets_usd: Decimal
    system_uptime: str
    database_status: str
    api_status: str

# API Response Wrappers
class ApiResponse(BaseModel):
    """通用API响应包装器"""
    success: bool
    message: str
    data: Optional[Any] = None
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            uuid.UUID: str
        }
    )

class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

# Error Schemas
class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: Dict[str, Any]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "BOT_NOT_FOUND",
                    "message": "Bot not found",
                    "details": {"bot_id": "bot_001"}
                }
            }
        }
    )