from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, DECIMAL, CheckConstraint, UniqueConstraint, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text
from sqlalchemy_utils import database_exists, create_database
import uuid
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import time

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/aip_dex")

engine = create_engine(DATABASE_URL)
if not database_exists(engine.url):
    create_database(engine.url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def create_tables():
    """Create all database tables"""
    try:
        with engine.begin() as conn:
            Base.metadata.create_all(bind=conn)
        print("✓ Tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Table creation error: {e}")
        return False

def create_indexes():
    """Create performance indexes"""
    indexes = [
        # Token and market data indexes
        "CREATE INDEX IF NOT EXISTS idx_tokens_symbol ON tokens(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_contract_chain ON tokens(contract_address, chain)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_metrics_updated_at ON tokens(metrics_updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_pool_metrics_pool_updated ON pool_metrics(pool_id, updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_pool_metrics_history_recorded ON pool_metrics_history(pool_id, recorded_at)",
        "CREATE INDEX IF NOT EXISTS idx_llm_decisions_type_phase ON llm_decisions(decision_type, decision_phase)",
        
        # Bot Owner indexes
        "CREATE INDEX IF NOT EXISTS idx_bot_owners_email ON bot_owners(email)",
        "CREATE INDEX IF NOT EXISTS idx_bot_owners_wallet ON bot_owners(wallet_address)",
        "CREATE INDEX IF NOT EXISTS idx_bot_owners_active ON bot_owners(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_bot_owners_subscription ON bot_owners(subscription_tier)",
        
        # Trading Strategy indexes
        "CREATE INDEX IF NOT EXISTS idx_trading_strategies_owner ON trading_strategies(owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_trading_strategies_type ON trading_strategies(strategy_type)",
        "CREATE INDEX IF NOT EXISTS idx_trading_strategies_risk ON trading_strategies(risk_level)",
        "CREATE INDEX IF NOT EXISTS idx_trading_strategies_active ON trading_strategies(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_trading_strategies_public ON trading_strategies(is_public)",
        "CREATE INDEX IF NOT EXISTS idx_trading_strategies_default ON trading_strategies(is_default)",
        
        # Trading Bot indexes
        "CREATE INDEX IF NOT EXISTS idx_trading_bots_owner ON trading_bots(owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_trading_bots_strategy ON trading_bots(strategy_id)",
        "CREATE INDEX IF NOT EXISTS idx_trading_bots_account_chain ON trading_bots(account_address, chain)",
        "CREATE INDEX IF NOT EXISTS idx_trading_bots_active ON trading_bots(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_trading_bots_strategy_type ON trading_bots(strategy_type)",
        
        # Position indexes
        "CREATE INDEX IF NOT EXISTS idx_positions_bot_active ON positions(bot_id, is_active)",
        "CREATE INDEX IF NOT EXISTS idx_positions_token ON positions(token_id)",
        "CREATE INDEX IF NOT EXISTS idx_positions_bot_token ON positions(bot_id, token_id)",
        
        # Position History indexes
        "CREATE INDEX IF NOT EXISTS idx_position_history_position_recorded ON position_history(position_id, recorded_at)",
        "CREATE INDEX IF NOT EXISTS idx_position_history_bot_recorded ON position_history(bot_id, recorded_at)",
        "CREATE INDEX IF NOT EXISTS idx_position_history_token_recorded ON position_history(token_id, recorded_at)",
        "CREATE INDEX IF NOT EXISTS idx_position_history_trigger ON position_history(trigger_event)",
        "CREATE INDEX IF NOT EXISTS idx_position_history_transaction ON position_history(transaction_id)",
        
        # Transaction indexes
        "CREATE INDEX IF NOT EXISTS idx_transactions_bot_created ON transactions(bot_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_type_date ON transactions(transaction_type, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_token ON transactions(token_id)",
        
        # LLM Decision indexes
        "CREATE INDEX IF NOT EXISTS idx_llm_decisions_bot_created ON llm_decisions(bot_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_llm_decisions_executed ON llm_decisions(was_executed)",
        
        # Revenue Snapshot indexes
        "CREATE INDEX IF NOT EXISTS idx_revenue_bot_created ON revenue_snapshots(bot_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_revenue_bot_snapshot_time ON revenue_snapshots(bot_id, snapshot_time)",
        "CREATE INDEX IF NOT EXISTS idx_revenue_type ON revenue_snapshots(snapshot_type)",
        "CREATE INDEX IF NOT EXISTS idx_revenue_snapshot_time ON revenue_snapshots(snapshot_time)",
        "CREATE INDEX IF NOT EXISTS idx_revenue_calculation_method ON revenue_snapshots(calculation_method)",
        
        # Trading Config indexes
        "CREATE INDEX IF NOT EXISTS idx_trading_configs_strategy ON trading_configs(strategy_name)",
        "CREATE INDEX IF NOT EXISTS idx_trading_configs_active ON trading_configs(is_active)"
    ]
    
    success_count = 0
    # Create each index in its own transaction to avoid cascading failures
    for index_sql in indexes:
        try:
            with engine.begin() as conn:
                conn.execute(text(index_sql))
            success_count += 1
        except Exception as e:
            print(f"Index creation warning: {e}")
    
    print(f"✓ Created {success_count}/{len(indexes)} indexes successfully")
    return success_count == len(indexes)

def init_database():
    """Initialize database with all tables and indexes"""
    try:
        # Create all tables first
        if not create_tables():
            return False
        
        # Small delay to ensure tables are committed
        time.sleep(0.1)
        
        # Create indexes for performance
        create_indexes()
        
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

# Auto-initialize database on import
# Remove auto-initialization to avoid import-time errors
# Call init_database() explicitly when needed

# Tier 1: Token Base Information
class Token(Base):
    __tablename__ = "tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    symbol = Column(Text, nullable=False) # uppercase
    contract_address = Column(Text, nullable=False)
    chain = Column(Text, nullable=False)
    decimals = Column(Integer, default=18)
    image_url = Column(Text)
    logo_uri = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    metrics_updated_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint('contract_address', 'chain', name='uq_token_contract_chain'),
    )
    
    # Relationships
    base_pools = relationship("TokenPool", foreign_keys="TokenPool.base_token_id", back_populates="base_token")
    quote_pools = relationship("TokenPool", foreign_keys="TokenPool.quote_token_id", back_populates="quote_token")
    metrics = relationship("TokenMetric", back_populates="token")
    metrics_history = relationship("TokenMetricsHistory", back_populates="token")
    
    # Trading Bot relationships
    positions = relationship("Position", back_populates="token")
    position_history = relationship("PositionHistory", back_populates="token")
    transactions = relationship("Transaction", back_populates="token") 
    llm_decisions_recommended = relationship("LLMDecision", foreign_keys="LLMDecision.recommended_token_id", back_populates="recommended_token")

# Tier 2: Token Pools (Token Pairs on Different DEXs)
class TokenPool(Base):
    __tablename__ = "token_pools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"), nullable=False)
    quote_token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"), nullable=False)
    dex = Column(Text, nullable=False)  # e.g., 'uniswap-v3', 'pancakeswap'
    chain = Column(Text, nullable=False)
    pair_address = Column(Text, nullable=False)
    fee_tier = Column(Integer)  # e.g., 3000 for 0.3%
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # Additional fields from DexScreener
    pair_created_at = Column(DateTime)  # DexScreener pair creation time
    
    __table_args__ = (
        UniqueConstraint('pair_address', 'chain', 'dex', name='uq_pool_pair_chain_dex'),
    )
    
    # Relationships
    base_token = relationship("Token", foreign_keys=[base_token_id], back_populates="base_pools")
    quote_token = relationship("Token", foreign_keys=[quote_token_id], back_populates="quote_pools")
    pool_metrics = relationship("PoolMetric", back_populates="pool")
    pool_history = relationship("PoolMetricHistory", back_populates="pool")

# Tier 3: Pool Metrics (Real-time Pool Data)
class PoolMetric(Base):
    __tablename__ = "pool_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("token_pools.id"), nullable=False)
    price_usd = Column(DECIMAL(20, 10))
    price_native = Column(DECIMAL(30, 18))
    
    # Volume data from DexScreener (1h, 6h, 24h)
    volume_1h = Column(DECIMAL(20, 2))
    volume_6h = Column(DECIMAL(20, 2))  # Added 6h volume
    volume_24h = Column(DECIMAL(20, 2))
    
    # Liquidity data
    liquidity_usd = Column(DECIMAL(20, 2))
    liquidity_base = Column(DECIMAL(30, 18))
    liquidity_quote = Column(DECIMAL(30, 18))
    
    # Price changes from DexScreener (1h, 6h, 24h) - increased precision for extreme values
    price_change_1h = Column(DECIMAL(15, 4))
    price_change_6h = Column(DECIMAL(15, 4))  # Added 6h price change
    price_change_24h = Column(DECIMAL(15, 4))
    
    # Transaction data from DexScreener (1h, 6h, 24h)
    txns_1h_buys = Column(Integer, default=0)
    txns_1h_sells = Column(Integer, default=0)
    txns_6h_buys = Column(Integer, default=0)  # Added 6h transaction data
    txns_6h_sells = Column(Integer, default=0)
    txns_24h_buys = Column(Integer, default=0)
    txns_24h_sells = Column(Integer, default=0)
    
    # Market valuation
    market_cap = Column(DECIMAL(20, 2))
    fdv = Column(DECIMAL(20, 2))  # Fully Diluted Valuation
    
    # Metadata
    data_source = Column(Text)  # 'dexscreener', 'moralis', 'birdeye'
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship
    pool = relationship("TokenPool", back_populates="pool_metrics")

# Tier 4: Token Metrics (Enhanced with all data aggregator fields)
class TokenMetric(Base):
    __tablename__ = "token_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"), nullable=False)
    
    # Aggregated Price Data
    avg_price_usd = Column(DECIMAL(20, 10))
    weighted_price_usd = Column(DECIMAL(20, 10))  # Volume weighted
    total_volume_24h = Column(DECIMAL(20, 2))
    total_liquidity_usd = Column(DECIMAL(20, 2))
    market_cap = Column(DECIMAL(20, 2))
    
    # Technical Indicators
    rsi_14d = Column(Float)
    ma_7d = Column(Float)
    ma_30d = Column(Float)
    volatility_24h = Column(Float)
    
    # On-chain Metrics
    holder_count = Column(Integer)  # Total holders from Moralis
    unique_traders_24h = Column(Integer)
    
    # Moralis Analytics - Buy/Sell Volume (enhanced with 5m and 6h)
    buy_volume_5m = Column(DECIMAL(20, 2))  # Added 5m data
    buy_volume_1h = Column(DECIMAL(20, 2))
    buy_volume_6h = Column(DECIMAL(20, 2))
    buy_volume_24h = Column(DECIMAL(20, 2))
    sell_volume_5m = Column(DECIMAL(20, 2))  # Added 5m data
    sell_volume_1h = Column(DECIMAL(20, 2))
    sell_volume_6h = Column(DECIMAL(20, 2))
    sell_volume_24h = Column(DECIMAL(20, 2))
    
    # Moralis Analytics - Buy/Sell Count (enhanced with 5m and 6h)
    total_buyers_5m = Column(Integer)  # Added 5m data
    total_buyers_1h = Column(Integer)
    total_buyers_6h = Column(Integer)
    total_buyers_24h = Column(Integer)
    total_sellers_5m = Column(Integer)  # Added 5m data
    total_sellers_1h = Column(Integer)
    total_sellers_6h = Column(Integer)
    total_sellers_24h = Column(Integer)
    
    # Transaction counts (enhanced)
    total_buys_5m = Column(Integer)  # Added 5m data
    total_buys_1h = Column(Integer)
    total_buys_6h = Column(Integer)
    total_buys_24h = Column(Integer)
    total_sells_5m = Column(Integer)  # Added 5m data
    total_sells_1h = Column(Integer)
    total_sells_6h = Column(Integer)
    total_sells_24h = Column(Integer)
    
    # Unique wallets (enhanced)
    unique_wallets_5m = Column(Integer)  # Added 5m data
    unique_wallets_1h = Column(Integer)
    unique_wallets_6h = Column(Integer)
    unique_wallets_24h = Column(Integer)
    
    # Moralis Analytics - Price Changes (enhanced with 5m) - increased precision for extreme values
    price_change_5m = Column(DECIMAL(15, 4))
    price_change_1h = Column(DECIMAL(15, 4))
    price_change_6h = Column(DECIMAL(15, 4))
    price_change_24h = Column(DECIMAL(15, 4))
    
    # Moralis Holder Stats - Holder Changes (enhanced with 5m, 3d) - increased precision for extreme values
    holder_change_5m = Column(Integer)  # Added 5m data
    holder_change_5m_percent = Column(DECIMAL(15, 4))
    holder_change_1h = Column(Integer)
    holder_change_1h_percent = Column(DECIMAL(15, 4))
    holder_change_6h = Column(Integer)
    holder_change_6h_percent = Column(DECIMAL(15, 4))
    holder_change_24h = Column(Integer)
    holder_change_24h_percent = Column(DECIMAL(15, 4))
    holder_change_3d = Column(Integer)  # Added 3d data
    holder_change_3d_percent = Column(DECIMAL(15, 4))
    holder_change_7d = Column(Integer)
    holder_change_7d_percent = Column(DECIMAL(15, 4))
    holder_change_30d = Column(Integer)
    holder_change_30d_percent = Column(DECIMAL(15, 4))
    
    # Moralis Holder Stats - Holder Distribution
    whales_count = Column(Integer)  # Large holders
    sharks_count = Column(Integer)
    dolphins_count = Column(Integer)
    fish_count = Column(Integer)
    octopus_count = Column(Integer)
    crabs_count = Column(Integer)
    shrimps_count = Column(Integer)
    
    # Moralis Holder Stats - Supply Distribution (enhanced with top250, top500)
    top10_supply_percent = Column(DECIMAL(5, 2))
    top25_supply_percent = Column(DECIMAL(5, 2))
    top50_supply_percent = Column(DECIMAL(5, 2))
    top100_supply_percent = Column(DECIMAL(5, 2))
    top250_supply_percent = Column(DECIMAL(5, 2))  # Added top250
    top500_supply_percent = Column(DECIMAL(5, 2))  # Added top500
    
    # Moralis Holder Acquisition Stats
    holders_by_swap = Column(Integer)  # Added holder acquisition data
    holders_by_transfer = Column(Integer)
    holders_by_airdrop = Column(Integer)
    
    # BirdEye compatibility fields - increased precision for extreme values
    volume_change_24h = Column(DECIMAL(15, 4))  # BirdEye volume change percentage
    
    # Enhanced price and liquidity data from aggregators
    total_fdv = Column(DECIMAL(20, 2))  # Moralis fully diluted valuation
    total_liquidity_usd_moralis = Column(DECIMAL(20, 2))  # Moralis liquidity data
    usd_price_moralis = Column(DECIMAL(20, 10))  # Moralis price data
    
    # Signals
    breakout_signal = Column(Boolean, default=False)
    trend_direction = Column(Text)
    signal_strength = Column(Float)
    
    # Meta
    pools_count = Column(Integer, default=0)
    last_calculation_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        CheckConstraint("trend_direction IN ('bullish', 'bearish', 'sideways')", name='check_trend_direction'),
        CheckConstraint("signal_strength >= 0 AND signal_strength <= 1", name='check_signal_strength'),
    )
    
    # Relationship
    token = relationship("Token", back_populates="metrics")

# Historical Data for Time Series Analysis
class PoolMetricHistory(Base):
    __tablename__ = "pool_metrics_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("token_pools.id"), nullable=False)
    
    # Core price metrics
    price_usd = Column(DECIMAL(20, 10))
    price_native = Column(DECIMAL(30, 18))
    
    # Volume metrics (enhanced with 6h data)
    volume_1h = Column(DECIMAL(20, 2))
    volume_6h = Column(DECIMAL(20, 2))  # Added 6h volume
    volume_24h = Column(DECIMAL(20, 2))
    
    # Liquidity metrics
    liquidity_usd = Column(DECIMAL(20, 2))
    liquidity_base = Column(DECIMAL(30, 18))
    liquidity_quote = Column(DECIMAL(30, 18))
    
    # Price change indicators (enhanced with 6h data) - increased precision for extreme values
    price_change_1h = Column(DECIMAL(15, 4))
    price_change_6h = Column(DECIMAL(15, 4))  # Added 6h price change
    price_change_24h = Column(DECIMAL(15, 4))
    
    # Transaction activity (enhanced with 6h data)
    txns_1h_buys = Column(Integer, default=0)
    txns_1h_sells = Column(Integer, default=0)
    txns_6h_buys = Column(Integer, default=0)  # Added 6h transaction data
    txns_6h_sells = Column(Integer, default=0)
    txns_24h_buys = Column(Integer, default=0)
    txns_24h_sells = Column(Integer, default=0)
    
    # Market valuation (important for historical analysis)
    market_cap = Column(DECIMAL(20, 2))
    fdv = Column(DECIMAL(20, 2))  # Fully Diluted Valuation
    
    # Meta
    data_source = Column(Text)  # Track data source for history
    recorded_at = Column(DateTime, nullable=False)
    
    # Relationship
    pool = relationship("TokenPool", back_populates="pool_history")

class TokenMetricsHistory(Base):
    __tablename__ = "token_metrics_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"), nullable=False)
    
    # Core price and volume metrics
    weighted_price_usd = Column(DECIMAL(20, 10))  # Most important price
    total_volume_24h = Column(DECIMAL(20, 2))     # Trading activity
    total_liquidity_usd = Column(DECIMAL(20, 2))  # Market depth
    market_cap = Column(DECIMAL(20, 2))           # Market valuation
    
    # Key trend indicators - increased precision for extreme values
    price_change_24h = Column(DECIMAL(15, 4))     # Price momentum
    signal_strength = Column(Float)               # Trading signal
    trend_direction = Column(Text)                # Trend direction
    
    # Enhanced Moralis metrics for historical analysis (critical ones only)
    buy_volume_24h = Column(DECIMAL(20, 2))       # Buy pressure
    sell_volume_24h = Column(DECIMAL(20, 2))      # Sell pressure
    holder_change_24h_percent = Column(DECIMAL(15, 4))  # Holder momentum - increased precision
    
    # Additional key Moralis metrics for comprehensive historical analysis
    total_buyers_24h = Column(Integer)            # Buyer activity
    total_sellers_24h = Column(Integer)           # Seller activity
    unique_wallets_24h = Column(Integer)          # Wallet engagement
    holder_count = Column(Integer)                # Total holders
    
    # Enhanced price change tracking - increased precision for extreme values
    price_change_5m = Column(DECIMAL(15, 4))      # Short-term momentum
    price_change_1h = Column(DECIMAL(15, 4))      # Hourly momentum
    price_change_6h = Column(DECIMAL(15, 4))      # 6-hour momentum
    
    # Key holder distribution (top level only)
    top10_supply_percent = Column(DECIMAL(5, 2))  # Concentration risk
    whales_count = Column(Integer)                # Large holder count
    
    # Meta
    pools_count = Column(Integer, default=0)      # Pool coverage
    data_source = Column(Text)                    # Track data source
    recorded_at = Column(DateTime, nullable=False)
    
    # Relationship
    token = relationship("Token", back_populates="metrics_history")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Trading Bot Core Models
class BotOwner(Base):
    """机器人所有者表"""
    __tablename__ = "bot_owners"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 所有者信息
    owner_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    wallet_address = Column(String(100), unique=True, nullable=False)  # 主钱包地址
    phone = Column(String(20))
    
    # 权限和状态
    is_active = Column(Boolean, default=True)
    max_bots_allowed = Column(Integer, default=5)  # 最大允许的机器人数量
    subscription_tier = Column(String(20), default='basic')  # basic/premium/enterprise
    
    # 统计信息
    total_bots_created = Column(Integer, default=0)
    total_trading_volume_usd = Column(DECIMAL(30, 18), default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime)
    
    __table_args__ = (
        CheckConstraint("subscription_tier IN ('basic', 'premium', 'enterprise')", name='check_subscription_tier'),
        CheckConstraint("max_bots_allowed >= 1", name='check_max_bots_positive'),
    )
    
    # 关系
    trading_bots = relationship("TradingBot", back_populates="owner")
    trading_strategies = relationship("TradingStrategy", back_populates="owner")

class TradingStrategy(Base):
    """交易策略表 - 包含参数设置和策略描述"""
    __tablename__ = "trading_strategies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("bot_owners.id"), nullable=False)
    
    # 策略基本信息
    strategy_name = Column(String(100), nullable=False)
    strategy_description = Column(Text)
    strategy_type = Column(String(30), nullable=False)  # conservative/moderate/aggressive等
    risk_level = Column(String(20), nullable=False)  # low/medium/high
    
    # 数值参数设置
    max_position_size = Column(DECIMAL(5, 2), nullable=False)  # 单币最大仓位比例(%)
    stop_loss_percentage = Column(DECIMAL(5, 2), nullable=False)  # 止损百分比(%)
    take_profit_percentage = Column(DECIMAL(5, 2), nullable=False)  # 止盈百分比(%)
    min_profit_threshold = Column(DECIMAL(5, 2), nullable=False)  # 最低收益率阈值(%)
    max_daily_trades = Column(Integer, nullable=False)  # 每日最大交易次数
    llm_confidence_threshold = Column(DECIMAL(3, 2), nullable=False)  # LLM决策置信度阈值
    
    # 交易费用设置
    gas_fee_native = Column(DECIMAL(10, 6), default=0.00003)  # Gas费用(原生代币)
    trading_fee_percentage = Column(DECIMAL(5, 3), default=0.1)  # 交易手续费率(%)
    slippage_tolerance = Column(DECIMAL(5, 3), default=1.0)  # 滑点容忍度(%)
    
    # 运行控制参数
    min_trade_amount_usd = Column(DECIMAL(20, 2), default=10.0)  # 最小交易金额
    polling_interval_hours = Column(DECIMAL(5, 2), default=1.0)  # 轮询间隔(小时)
    
    # 功能开关
    enable_stop_loss = Column(Boolean, default=True)
    enable_take_profit = Column(Boolean, default=True)
    
    # 策略描述性配置
    buy_strategy_description = Column(Text)  # 买入策略描述
    sell_strategy_description = Column(Text)  # 卖出策略描述
    filter_strategy_description = Column(Text)  # 筛选策略描述
    summary_strategy_description = Column(Text)  # 总结性策略描述
    
    # 策略模板
    buy_prompt_template = Column(Text)  # 买入决策提示模板
    sell_prompt_template = Column(Text)  # 卖出决策提示模板
    filter_prompt_template = Column(Text)  # 筛选决策提示模板
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # 是否公开供其他用户使用
    is_default = Column(Boolean, default=False)  # 是否为默认策略
    
    # 使用统计
    usage_count = Column(Integer, default=0)  # 使用次数
    success_rate = Column(DECIMAL(5, 2))  # 成功率(%)
    average_profit_percentage = Column(DECIMAL(10, 4))  # 平均收益率(%)
    
    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        CheckConstraint("strategy_type IN ('conservative', 'moderate', 'aggressive', 'momentum', 'mean_reversion', 'user_defined')", name='check_strategy_type'),
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name='check_risk_level'),
        CheckConstraint("max_position_size > 0 AND max_position_size <= 100", name='check_max_position_size'),
        CheckConstraint("llm_confidence_threshold >= 0 AND llm_confidence_threshold <= 1", name='check_confidence_threshold'),
        CheckConstraint("success_rate >= 0 AND success_rate <= 100", name='check_success_rate'),
    )
    
    # 关系
    owner = relationship("BotOwner", back_populates="trading_strategies")
    trading_bots = relationship("TradingBot", back_populates="strategy")

class TradingBot(Base):
    """交易机器人配置表"""
    __tablename__ = "trading_bots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 所有者关系
    owner_id = Column(UUID(as_uuid=True), ForeignKey("bot_owners.id"), nullable=True)  # 可选，启动后可以设置
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("trading_strategies.id"), nullable=True)  # 可选，启动后可以设置
    
    # 基础配置
    bot_name = Column(String(100), nullable=False)
    account_address = Column(String(100), nullable=False, unique=True)
    chain = Column(String(20), nullable=False)  # 'bsc' or 'solana'
    
    # 资金配置 (USD计价，内部精度10^18)
    initial_balance_usd = Column(DECIMAL(30, 18), nullable=False)  # 初始余额
    current_balance_usd = Column(DECIMAL(30, 18), nullable=False)  # 当前可用余额
    total_assets_usd = Column(DECIMAL(30, 18), nullable=False)     # 总资产(余额+持仓)
    
    # 机器人状态
    is_active = Column(Boolean, default=True)                    # 机器人开关
    is_configured = Column(Boolean, default=False)               # 是否已配置（有owner和strategy）
    
    # 统计数据
    total_trades = Column(Integer, default=0)                    # 总交易次数
    profitable_trades = Column(Integer, default=0)               # 盈利交易次数
    total_profit_usd = Column(DECIMAL(30, 18), default=0)        # 总盈利(USD)
    max_drawdown_percentage = Column(DECIMAL(8, 4), default=0)   # 最大回撤(%)
    
    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_activity_at = Column(DateTime)
    
    __table_args__ = (
        CheckConstraint("chain IN ('bsc', 'solana')", name='check_chain'),
    )
    
    # 关系
    owner = relationship("BotOwner", back_populates="trading_bots")
    strategy = relationship("TradingStrategy", back_populates="trading_bots")
    positions = relationship("Position", back_populates="bot", cascade="all, delete-orphan")
    position_history = relationship("PositionHistory", back_populates="bot", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="bot", cascade="all, delete-orphan")
    llm_decisions = relationship("LLMDecision", back_populates="bot", cascade="all, delete-orphan")
    revenue_snapshots = relationship("RevenueSnapshot", back_populates="bot", cascade="all, delete-orphan")

class Position(Base):
    """持仓记录表"""
    __tablename__ = "positions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("trading_bots.id"), nullable=False)
    token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"), nullable=False)
    
    # 持仓信息 (数量使用内部精度10^18)
    quantity = Column(DECIMAL(40, 18), nullable=False)           # 持有数量
    average_cost_usd = Column(DECIMAL(20, 10), nullable=False)   # 平均成本(USD)
    total_cost_usd = Column(DECIMAL(30, 18), nullable=False)     # 总成本(USD)
    
    # 当前价值
    current_price_usd = Column(DECIMAL(20, 10))                  # 当前价格
    current_value_usd = Column(DECIMAL(30, 18))                  # 当前市值
    unrealized_pnl_usd = Column(DECIMAL(30, 18))                 # 未实现盈亏
    unrealized_pnl_percentage = Column(DECIMAL(10, 4))           # 未实现盈亏百分比
    
    # 风险控制
    stop_loss_price = Column(DECIMAL(20, 10))                    # 止损价格
    take_profit_price = Column(DECIMAL(20, 10))                  # 止盈价格
    
    # 状态
    is_active = Column(Boolean, default=True)                    # 是否活跃持仓
    
    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime)                                 # 平仓时间
    
    __table_args__ = (
        UniqueConstraint('bot_id', 'token_id', name='uq_bot_token_position'),
        CheckConstraint("quantity >= 0", name='check_quantity_positive'),
        CheckConstraint("(quantity = 0 AND average_cost_usd = 0) OR (quantity > 0 AND average_cost_usd > 0)", name='check_cost_quantity_consistency'),
    )
    
    # 关系
    bot = relationship("TradingBot", back_populates="positions")
    token = relationship("Token", back_populates="positions")
    transactions = relationship("Transaction", back_populates="position")
    history = relationship("PositionHistory", back_populates="position", cascade="all, delete-orphan")

class PositionHistory(Base):
    """持仓历史记录表 - 记录持仓状态的时间序列变化"""
    __tablename__ = "position_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("trading_bots.id"), nullable=False)
    token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"), nullable=False)
    
    # 持仓状态快照 (数量使用内部精度10^18)
    quantity = Column(DECIMAL(40, 18), nullable=False)           # 当时持有数量
    average_cost_usd = Column(DECIMAL(20, 10), nullable=False)   # 当时平均成本(USD)
    total_cost_usd = Column(DECIMAL(30, 18), nullable=False)     # 当时总成本(USD)
    
    # 价格和价值快照
    token_price_usd = Column(DECIMAL(20, 10), nullable=False)    # 当时代币价格
    position_value_usd = Column(DECIMAL(30, 18), nullable=False) # 当时持仓市值
    unrealized_pnl_usd = Column(DECIMAL(30, 18), nullable=False) # 当时未实现盈亏
    unrealized_pnl_percentage = Column(DECIMAL(10, 4), nullable=False) # 当时未实现盈亏百分比
    
    # 风险控制价格 (可能为空)
    stop_loss_price = Column(DECIMAL(20, 10))                    # 当时止损价格
    take_profit_price = Column(DECIMAL(20, 10))                  # 当时止盈价格
    
    # 市场状态快照
    market_cap_at_snapshot = Column(DECIMAL(20, 2))              # 当时市值
    volume_24h_at_snapshot = Column(DECIMAL(20, 2))              # 当时24h交易量
    
    # 触发原因和元数据
    trigger_event = Column(String(30), nullable=False)           # 触发记录的事件
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"))  # 关联交易(如果由交易触发)
    
    # 账户状态快照
    bot_balance_usd = Column(DECIMAL(30, 18))                    # 当时机器人可用余额
    bot_total_assets_usd = Column(DECIMAL(30, 18))               # 当时机器人总资产
    
    # 时间戳
    recorded_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        CheckConstraint("trigger_event IN ('trade_buy', 'trade_sell', 'price_update', 'stop_loss', 'take_profit', 'manual', 'periodic')", name='check_trigger_event'),
        CheckConstraint("quantity >= 0", name='check_history_quantity_positive'),
        CheckConstraint("(quantity = 0 AND average_cost_usd = 0) OR (quantity > 0 AND average_cost_usd > 0)", name='check_history_cost_quantity_consistency'),
        CheckConstraint("token_price_usd > 0", name='check_history_price_positive'),
    )
    
    # 关系
    position = relationship("Position", back_populates="history")
    bot = relationship("TradingBot", back_populates="position_history")
    token = relationship("Token", back_populates="position_history")
    trigger_transaction = relationship("Transaction", foreign_keys=[transaction_id])

class Transaction(Base):
    """交易记录表"""
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("trading_bots.id"), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id"))
    token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"), nullable=False)
    llm_decision_id = Column(UUID(as_uuid=True), ForeignKey("llm_decisions.id"))
    
    # 交易基本信息
    transaction_type = Column(String(10), nullable=False)        # 'buy' or 'sell'
    status = Column(String(20), default='pending')               # pending/executed/failed/cancelled
    
    # 交易数量和价格 (使用内部精度10^18)
    amount_usd = Column(DECIMAL(30, 18))                         # 交易金额(USD)，买入时使用
    token_amount = Column(DECIMAL(40, 18))                       # 代币数量，卖出时使用
    price_usd = Column(DECIMAL(20, 10), nullable=False)          # 执行价格
    
    # 交易成本
    gas_cost_usd = Column(DECIMAL(20, 10), nullable=False)       # Gas费用
    trading_fee_usd = Column(DECIMAL(20, 10), nullable=False)    # 交易手续费
    total_cost_usd = Column(DECIMAL(20, 10), nullable=False)     # 总交易成本
    
    # 收益计算 (仅卖出交易)
    realized_pnl_usd = Column(DECIMAL(30, 18))                   # 已实现盈亏
    realized_pnl_percentage = Column(DECIMAL(10, 4))             # 已实现盈亏百分比
    
    # 执行前后状态
    balance_before_usd = Column(DECIMAL(30, 18))                 # 交易前余额
    balance_after_usd = Column(DECIMAL(30, 18))                  # 交易后余额
    position_before = Column(DECIMAL(40, 18))                    # 交易前持仓数量
    position_after = Column(DECIMAL(40, 18))                     # 交易后持仓数量
    avg_cost_before = Column(DECIMAL(20, 10))                    # 交易前平均成本
    avg_cost_after = Column(DECIMAL(20, 10))                     # 交易后平均成本
    
    # 市场条件
    market_cap_at_trade = Column(DECIMAL(20, 2))                 # 交易时市值
    volume_24h_at_trade = Column(DECIMAL(20, 2))                 # 交易时24h交易量
    
    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    executed_at = Column(DateTime)
    
    __table_args__ = (
        CheckConstraint("transaction_type IN ('buy', 'sell')", name='check_transaction_type'),
        CheckConstraint("status IN ('pending', 'executed', 'failed', 'cancelled')", name='check_status'),
        CheckConstraint("price_usd > 0", name='check_price_positive'),
        CheckConstraint("total_cost_usd >= 0", name='check_cost_positive'),
    )
    
    # 关系
    bot = relationship("TradingBot", back_populates="transactions")
    position = relationship("Position", back_populates="transactions")
    token = relationship("Token", back_populates="transactions")
    llm_decision = relationship("LLMDecision", back_populates="transaction")

class LLMDecision(Base):
    """LLM决策记录表"""
    __tablename__ = "llm_decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("trading_bots.id"), nullable=False)
    
    # 决策类型
    decision_type = Column(String(20), nullable=False)           # 'sell_analysis', 'buy_analysis'
    decision_phase = Column(String(20), nullable=False)          # 'phase_1_sell', 'phase_2_buy'
    
    # 决策输入数据
    input_data = Column(JSON)                                    # 输入给LLM的数据
    prompt_template = Column(Text)                               # 使用的提示模板
    
    # LLM响应
    llm_response = Column(Text)                                  # LLM原始响应
    reasoning = Column(Text)                                     # 决策推理过程
    confidence_score = Column(DECIMAL(3, 2))                     # 置信度分数
    
    # 决策结果
    recommended_action = Column(String(50))                      # 推荐动作
    recommended_token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"))  # 推荐代币(买入时)
    recommended_amount = Column(DECIMAL(30, 18))                 # 推荐金额/数量
    recommended_percentage = Column(DECIMAL(5, 2))               # 推荐卖出百分比
    
    # 预期收益分析
    expected_return_percentage = Column(DECIMAL(10, 4))          # 预期收益率
    risk_assessment = Column(String(20))                         # 'low', 'medium', 'high'
    
    # 市场分析结果
    market_sentiment = Column(String(20))                        # 'bullish', 'bearish', 'neutral'
    technical_indicators = Column(JSON)                          # 技术指标分析结果
    fundamental_analysis = Column(JSON)                          # 基本面分析结果
    
    # 执行结果
    was_executed = Column(Boolean, default=False)                # 是否被执行
    execution_reason = Column(Text)                              # 执行/不执行原因
    
    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    execution_time = Column(DateTime)                            # 决策执行时间
    
    __table_args__ = (
        CheckConstraint("decision_type IN ('sell_analysis', 'buy_analysis')", name='check_decision_type'),
        CheckConstraint("decision_phase IN ('phase_1_sell', 'phase_2_buy')", name='check_decision_phase'),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name='check_confidence_score'),
        CheckConstraint("risk_assessment IN ('low', 'medium', 'high')", name='check_risk_assessment'),
        CheckConstraint("market_sentiment IN ('bullish', 'bearish', 'neutral')", name='check_market_sentiment'),
    )
    
    # 关系
    bot = relationship("TradingBot", back_populates="llm_decisions")
    recommended_token = relationship("Token", back_populates="llm_decisions_recommended")
    transaction = relationship("Transaction", back_populates="llm_decision", uselist=False)

class RevenueSnapshot(Base):
    """收益快照表 - 用于生成收益曲线"""
    __tablename__ = "revenue_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("trading_bots.id"), nullable=False)
    
    # 资产快照
    total_assets_usd = Column(DECIMAL(30, 18), nullable=False)   # 总资产
    available_balance_usd = Column(DECIMAL(30, 18), nullable=False)  # 可用余额
    total_positions_value_usd = Column(DECIMAL(30, 18), nullable=False)  # 持仓总价值
    
    # 收益数据 (基于PositionHistory + Transaction计算)
    total_unrealized_pnl_usd = Column(DECIMAL(30, 18), nullable=False)  # 未实现盈亏总额 (汇总所有unrealized_pnl_usd)
    total_realized_pnl_usd = Column(DECIMAL(30, 18), nullable=False)    # 已实现盈亏总额 (来自Transaction)
    total_profit_usd = Column(DECIMAL(30, 18), nullable=False)   # 累计盈利 (unrealized + realized)
    total_profit_percentage = Column(DECIMAL(10, 4), nullable=False)  # 累计收益率
    daily_profit_usd = Column(DECIMAL(30, 18))                   # 当日盈利
    daily_profit_percentage = Column(DECIMAL(10, 4))             # 当日收益率
    
    # 交易统计
    total_trades = Column(Integer, default=0)                    # 总交易次数
    profitable_trades = Column(Integer, default=0)               # 盈利交易次数
    win_rate = Column(DECIMAL(5, 2))                            # 胜率
    average_profit_per_trade = Column(DECIMAL(20, 10))           # 平均每笔交易盈利
    
    # 风险指标
    max_drawdown_percentage = Column(DECIMAL(8, 4))              # 最大回撤
    current_drawdown_percentage = Column(DECIMAL(8, 4))          # 当前回撤
    volatility = Column(DECIMAL(8, 4))                          # 波动率
    sharpe_ratio = Column(DECIMAL(8, 4))                        # 夏普比率
    
    # 持仓统计 (基于PositionHistory汇总计算)
    active_positions_count = Column(Integer, default=0)          # 活跃持仓数量
    total_position_cost_usd = Column(DECIMAL(30, 18))            # 持仓总成本 (汇总所有total_cost_usd)
    largest_position_value_usd = Column(DECIMAL(30, 18))         # 最大单个持仓价值
    largest_position_percentage = Column(DECIMAL(5, 2))          # 最大持仓比例
    position_concentration_risk = Column(DECIMAL(5, 2))          # 持仓集中度风险
    
    # 数据来源追踪
    position_history_count = Column(Integer, default=0)          # 基础持仓历史记录数量
    calculation_method = Column(String(10), default='v1.0')      # 计算方法版本
    data_completeness = Column(DECIMAL(5, 2), default=100.0)     # 数据完整性百分比
    
    # 快照类型和时间
    snapshot_type = Column(String(20), default='hourly')         # hourly/daily/manual/triggered
    snapshot_time = Column(DateTime, nullable=False)             # 快照时间点 (与PositionHistory的recorded_at对应)
    
    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        CheckConstraint("snapshot_type IN ('hourly', 'daily', 'manual', 'triggered')", name='check_snapshot_type'),
        CheckConstraint("calculation_method IN ('v1.0', 'v1.1', 'v2.0')", name='check_calculation_method'),
        CheckConstraint("data_completeness >= 0 AND data_completeness <= 100", name='check_data_completeness'),
        CheckConstraint("win_rate >= 0 AND win_rate <= 100", name='check_win_rate'),
        CheckConstraint("position_concentration_risk >= 0 AND position_concentration_risk <= 100", name='check_concentration_risk'),
    )
    
    # 关系
    bot = relationship("TradingBot", back_populates="revenue_snapshots")

class TradingConfig(Base):
    """交易配置模板表 - 预定义策略参数"""
    __tablename__ = "trading_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 策略信息
    strategy_name = Column(String(50), nullable=False, unique=True)
    strategy_description = Column(Text)
    risk_level = Column(String(20), nullable=False)              # low/medium/high
    
    # 默认参数
    default_max_position_size = Column(DECIMAL(5, 2), nullable=False)
    default_stop_loss_percentage = Column(DECIMAL(5, 2), nullable=False)
    default_take_profit_percentage = Column(DECIMAL(5, 2), nullable=False)
    default_min_profit_threshold = Column(DECIMAL(5, 2), nullable=False)
    default_max_daily_trades = Column(Integer, nullable=False)
    default_confidence_threshold = Column(DECIMAL(3, 2), nullable=False)
    
    # 提示模板
    sell_prompt_template = Column(Text)                          # 卖出决策提示模板
    buy_prompt_template = Column(Text)                           # 买入决策提示模板
    
    # 状态
    is_active = Column(Boolean, default=True)
    
    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name='check_risk_level'),
    )