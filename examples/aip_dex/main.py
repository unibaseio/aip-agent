from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from models.database import create_tables, create_indexes
from api.routes import router
from services.token_service import TokenService

# Global token service instance
token_service = TokenService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Enhanced AIP DEX Signal Aggregator (Three-Tier Architecture)...")
    
    # Create database tables
    print("📊 Creating database tables...")
    create_tables()
    
    # Create performance indexes
    print("⚡ Creating performance indexes...")
    try:
        create_indexes()
        print("✅ Indexes created successfully")
    except Exception as e:
        print(f"⚠️ Index creation warning: {e}")
    
    print("✅ Database initialization complete")
    print("🏗️ Architecture: Token → Pools → Pool Metrics → Aggregated Token Metrics")
    print("🔥 Features: Multi-DEX Analysis | Pool Comparison | Arbitrage Detection")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    await token_service.close()
    print("✅ All connections closed.")

app = FastAPI(
    title="Enhanced AIP DEX Signal Aggregator",
    description="""
    Advanced Web3 Token Signal Aggregator with Three-Tier Architecture
    
    ## Features
    - **Multi-DEX Analysis**: Compare prices across different DEXs
    - **Pool-Level Metrics**: Granular data for each trading pool
    - **Arbitrage Detection**: Identify price differences between DEXs
    - **Enhanced Signals**: AI-powered trading signals with confidence scores
    - **LLM Chat Interface**: Natural language token analysis
    
    ## Architecture
    Three-tier data structure: Token → Pools → Pool Metrics → Aggregated Token Metrics
    
    ## Supported Data Sources
    - DEX Screener (Real-time DEX data)
    - CoinGecko (Market data)
    - Moralis (On-chain metrics)
    """,
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint with enhanced API information"""
    return {
        "message": "Welcome to Enhanced AIP DEX Signal Aggregator",
        "version": "2.0.0",
        "architecture": "Three-Tier (Token → Pools → Metrics → Aggregated)",
        "features": [
            "Multi-DEX Analysis",
            "Pool Comparison", 
            "Arbitrage Detection",
            "Enhanced AI Signals",
            "LLM Chat Interface"
        ],
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "tokens": "/api/v1/tokens",
            "token_search": "/api/v1/tokens/search",
            "pools": "/api/v1/pools",
            "pool_analysis": "/api/v1/pools/analyze",
            "enhanced_signals": "/api/v1/tokens/{token_id}/signal",
            "simple_signals": "/api/v1/tokens/{token_id}/signal/simple", 
            "chat": "/api/v1/chat",
            "stats": "/api/v1/stats",
            "health": "/api/v1/health"
        },
        "example_usage": {
            "search_token": "POST /api/v1/tokens/search",
            "get_signal": "GET /api/v1/tokens/{token_id}/signal?include_pools=true",
            "analyze_pools": "POST /api/v1/pools/analyze",
            "chat_analysis": "POST /api/v1/chat"
        }
    }

@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "api_version": "v1",
        "architecture": "three-tier",
        "data_flow": [
            "1. Token (Base Info)",
            "2. Pools (Token Pairs on DEXs)",
            "3. Pool Metrics (Real-time Data)",
            "4. Token Metrics (Aggregated)"
        ],
        "supported_chains": ["ethereum", "bsc", "polygon"],
        "supported_dexs": ["uniswap-v2", "uniswap-v3", "pancakeswap", "sushiswap"],
        "data_sources": ["dexscreener", "coingecko", "moralis"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    ) 