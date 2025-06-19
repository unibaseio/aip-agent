from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, DECIMAL, CheckConstraint, UniqueConstraint
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
        "CREATE INDEX IF NOT EXISTS idx_tokens_symbol ON tokens(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_contract_chain ON tokens(contract_address, chain)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_metrics_updated_at ON tokens(metrics_updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_pool_metrics_pool_updated ON pool_metrics(pool_id, updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_pool_metrics_history_recorded ON pool_metrics_history(pool_id, recorded_at)",
        "CREATE INDEX IF NOT EXISTS idx_token_metrics_updated ON token_metrics(token_id, updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_token_metrics_history_recorded ON token_metrics_history(token_id, recorded_at)"
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