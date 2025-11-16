from fastapi import FastAPI, Depends, HTTPException, Query, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from decimal import Decimal
import uuid

# Load environment variables
load_dotenv()

from models.database import create_tables, create_indexes, get_db, Token, SessionLocal, BotOwner, TradingBot
from services.token_service import TokenService
from llm.token_analyzer import TokenDecisionAnalyzer
from api.schemas import (
    TokenResponse, ChatRequest, ChatResponse, BotOwnerCreate, TradingStrategyCreate,
    TradingStrategyUpdate,
    TokenDetailResponse, TokenPoolResponse, TokenHolderDistribution, TokenTechnicalIndicators,
    TokenTradeActivity, TokenPriceHistory
)
from api.trading_bot_routes import router as trading_bot_router
from services.owner_service import OwnerService
from services.trading_service import TradingService

from aip_agent.agents.custom_agent import CallbackAgent
from aip_agent.agents.full_agent import FullAgentWrapper
from membase.chain.chain import membase_id  

# Global service instances
token_service = TokenService()
token_analyzer = TokenDecisionAnalyzer()
owner_service = OwnerService()
trading_service = TradingService()

# cache_key is token_id;
# value is time of hour and the response of the token analysis;
cached_response = {}

async def analyze_token(message: str, include_pools: bool = False, language: str = "chinese"):
    """Analyze a token in a message with enhanced multi-DEX analysis
    
    Args:
        message: User's query message
        include_pools: Whether to include pool-level data
        language: Language for analysis output ("chinese" or "english")
    
    Examples:
        - "BTC price trends" - Analyze Bitcoin price movements and trends
        - "ETH liquidity analysis" - Check Ethereum liquidity across DEXs
        - "PEPE market cap" - Get PEPE token market capitalization
        - "ADA holder distribution" - Analyze ADA token holder statistics
        - "MATIC technical indicators" - Get technical analysis for MATIC
        - "What is the opportunity of DOGE?" - Analyze DOGE token
        - "BEEPER trading signal" - Analyze the trading signal of BEEPER token
    """
    db = SessionLocal()
    try:
        print(f"========== Analyzing token: {message} (language: {language})")
        response_data = await token_service.process_chat_message(
                db, message, include_pools, cached_response, language
        )  
        return response_data
    finally:
        db.close()

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
    
    # Initialize agent
    print("🤖 Initializing AIP Agent...")
    try:
        default_system_prompt = f"""You are an AI assistant specialized in DEX token analysis and trading signals. 

IMPORTANT LANGUAGE GUIDELINES:
- Detect the language of the user's message
- If the user writes in Chinese (中文), respond in Chinese
- If the user writes in English, respond in English
- Always match the user's language choice for consistency
- When calling analyze_token function, use the appropriate language parameter based on user's language

DIRECT OUTPUT POLICY:
- When analyze_token function is called, its output becomes the final response
- No additional processing, formatting, or explanation is needed
- Return the analyze_token results exactly as they are

CRITICAL OUTPUT REQUIREMENTS for analyze_token function:
1. Return the COMPLETE and EXACT results from analyze_token function as the FINAL OUTPUT
2. Do NOT modify, summarize, or omit any data fields
3. Do NOT add additional analysis, interpretation, or commentary
4. Do NOT wrap the results in additional formatting or explanations
5. PRESERVE all original data structure and values exactly as received
6. PRESENT the results in the user's preferred language (Chinese or English)
7. When calling analyze_token, set the language parameter to match the user's language
8. The analyze_token function output IS the final response - return it directly
9. Do NOT add any prefix, suffix, or wrapper text around the analyze_token results
10. The analyze_token function returns the complete analysis - use it as-is

The analyze_token function provides comprehensive token analysis data - return it exactly as received without any modifications or additions."""
        system_prompt = os.getenv("SYSTEM_PROMPT", default_system_prompt)
        grpc_server_url = os.getenv("GRPC_SERVER_URL", "54.169.29.193:8081")
        
        app.agent = FullAgentWrapper(
            agent_cls=CallbackAgent,
            name=membase_id,
            description=system_prompt,
            host_address=grpc_server_url,
            functions=[analyze_token]  # Add any specific functions if needed
        )
        
        await app.agent.initialize()
        print("✅ Agent initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing agent: {str(e)}")
        raise e
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    
    # Close agent resources
    if hasattr(app, 'agent') and app.agent is not None:
        print("🤖 Shutting down agent...")
        try:
            await app.agent.stop()
            print("✅ Agent stopped successfully")
        except Exception as e:
            print(f"⚠️ Error shutting down agent: {str(e)}")
    
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
    - BirdEye (Top tokens)
    - DEX Screener (Real-time DEX data)
    - Moralis (On-chain metrics)
    """,
    version="1.0.0",
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

# Include trading bot routes
app.include_router(trading_bot_router)


async def process_chat_message(db: Session, messsage: str, conversation_id: str, include_pools: bool = False, language: str = "chinese") -> str:
    """Process chat message with enhanced multi-DEX analysis
    
    This function provides comprehensive token analysis including:
    - Multi-DEX price comparison and arbitrage detection
    - Technical indicators and trend analysis
    - Holder distribution and on-chain metrics
    - Volume and liquidity analysis across timeframes
    - Trading signals with confidence scores
    
    Examples:
        - "What's the current price of BTC?" - Get real-time Bitcoin price
        - "Analyze ETH liquidity across all DEXs" - Multi-DEX liquidity comparison
        - "Show me PEPE trading signals" - Get AI-powered trading recommendations
        - "DOGE volume analysis last 24h" - Detailed volume breakdown
        - "BNB price differences between exchanges" - Arbitrage opportunity detection
        - "SHIB holder statistics" - On-chain holder distribution analysis
        - "ADA technical indicators" - RSI, moving averages, volatility analysis
        - "MATIC market sentiment" - Overall market sentiment assessment
    """
    try: 
        # Step 1: Get available token list from database
        available_tokens = token_service._get_available_tokens_list(db, limit=0)
            
        if not available_tokens:
            return f"No tokens found in the database. Please add some tokens first. Available tokens: {', '.join([t['symbol'] for t in available_tokens])}"
            
        # Step 2: Use LLM to determine which token the user is asking about
        user_message = token_analyzer.get_prompt_for_identify_target_token(messsage, available_tokens)
        system_prompt = token_analyzer.get_sys_prompt_for_identify_target_token()
        response = await app.agent.process_query(
            user_message,
            use_history=False,
            system_prompt=system_prompt,
            conversation_id=conversation_id,
            use_tool_call=False
        )

        llm_token_analysis = {"token_found": False, "token_symbol": None, "chain": None, "token_info": None, "similar_tokens": [], "user_intent": "general", "confidence": 0.0}

        import json
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            llm_token_analysis = json.loads(json_match.group())
        
        print(f"AIP DEX token analysis: {llm_token_analysis}")
        
        if not llm_token_analysis.get("token_found") or not llm_token_analysis.get("token_symbol") or llm_token_analysis.get("token_symbol") == "":
            similar_tokens = llm_token_analysis.get("similar_tokens", [])
            if similar_tokens and len(similar_tokens) > 0:
                return f"I couldn't identify a specific token from your message. Did you mean: {', '.join(similar_tokens)}?"
            else:
                available_symbols = [f"{t['symbol']}({t['name']})" if t['name'].upper() != t['symbol'].upper() else t['symbol'] for t in available_tokens if t.get('symbol')]
                return f"I couldn't identify a specific token from your message. \n\nAvailable tokens: {', '.join(available_symbols)}"

        user_intent = llm_token_analysis.get("user_intent", "general")
        target_chain = llm_token_analysis.get("intended_chain", "bsc")
        target_token_symbol = llm_token_analysis.get("token_symbol")
            
        # Step 3: Check if the identified token exists in our list
        token_exists = any(token['symbol'].upper() == target_token_symbol.upper() for token in available_tokens)
                 
        if not token_exists:
            similar_tokens = [t['symbol'] for t in available_tokens if target_token_symbol.lower() in t['symbol'].lower() or t['symbol'].lower() in target_token_symbol.lower()]
            suggestion = f" Did you mean: {', '.join(similar_tokens)}?" if similar_tokens else ""
            return f"Token {target_token_symbol} is not available in our database. {suggestion}"
            
        # Step 4: Get or create token and retrieve decision data
        token = await token_service.get_or_create_token(db, symbol=target_token_symbol, chain=target_chain)
        if not token:
            return f"Sorry, I couldn't retrieve data for token {target_token_symbol} on {target_chain}."

        # cache_key is token_id + time of hour
        time_of_hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        cache_key = f"{str(token.id)}" + language.lower()
        if cached_response.get(cache_key):
            cached_value = cached_response.get(cache_key)
            if cached_value.get("time_of_hour") == time_of_hour:
                print(f"Cached response found for token: {token.symbol or 'Unknown'} at {time_of_hour}")
                return cached_value.get("response")
            else:
                print(f"Cached response found for token: {token.symbol or 'Unknown'} at {time_of_hour} but it is expired, will update the cache")
                # remove the expired cache
                del cached_response[cache_key]

        print(f"AIP DEX token analysis: {token.symbol or 'Unknown'} on {token.chain or 'Unknown'} {include_pools}")                
        # Get comprehensive token analysis
        decision_data = await token_service.get_token_decision_data(db, str(token.id))
            
        if not decision_data:
            return f"I found {target_token_symbol} but couldn't retrieve current analysis data. The token might be new or have limited trading data."
            
        system_prompt = token_analyzer._get_system_prompt(include_pools=include_pools, language=language)
        user_message = token_analyzer._create_comprehensive_analysis_prompt(decision_data, user_intent, include_pools, language)

        # Step 5: Use LLM to analyze the decision data and generate response
        llm_analysis = await app.agent.process_query(
            user_message,
            use_history=False,
            system_prompt=system_prompt,
            conversation_id=conversation_id,
            use_tool_call=False
        )

        llm_analysis = llm_analysis.replace("```markdown", "").replace("```", "")

        print(f"AIP DEX analysis: \n\n {llm_analysis}")

        cached_response[cache_key] = {
            "time_of_hour": time_of_hour,
            "response": llm_analysis
        }

        return llm_analysis
            
    except Exception as e:
            print(f"Error processing chat message: {e}")
            return {
                "response": f"Sorry, I encountered an error while analyzing your request: {str(e)}",
                "signal_data": None,
                "intent": None,
                "pool_analysis": None,
                "available_tokens": None
            }

# Mount static files directory for CSS, JS, and other static assets
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Mount chat static files if they exist
chat_static_path = os.path.join(os.path.dirname(__file__), "chat")
if os.path.exists(chat_static_path):
    app.mount("/chat-static", StaticFiles(directory=chat_static_path), name="chat-static")

# Set bearer token from environment variable
app.bearer_token = os.getenv("DEX_BEARER_TOKEN", "aip-dex-default-token-2025")

# All routes are now defined directly in this file
security = HTTPBearer()

# Dependency for token validation
async def validate_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validate bearer token"""
    if not credentials:
        print("❌ Missing Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = credentials.credentials
    if token != app.bearer_token:
        print(f"❌ Invalid bearer token attempted: {token[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid bearer token")
    
    print("✅ Bearer token validated successfully")
    return token

# ===== TOKEN ENDPOINTS =====

@app.get("/api/v1/tokens", dependencies=[Depends(validate_token)])
async def tokens_api(
    limit: int = Query(50, ge=1, le=300),
    chain: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all tracked tokens with their latest metrics, sorted by market cap"""
    from models.database import TokenMetric
    
    # 使用子查询获取每个token的最新指标，然后按market cap排序
    from sqlalchemy import func
    
    # 子查询：获取每个token的最新指标记录
    latest_metrics_subquery = db.query(
        TokenMetric.token_id,
        func.max(TokenMetric.updated_at).label('max_updated_at')
    ).group_by(TokenMetric.token_id).subquery()
    
    # 主查询：JOIN token和最新指标，按market cap排序
    query = db.query(Token, TokenMetric).outerjoin(
        TokenMetric, Token.id == TokenMetric.token_id
    ).outerjoin(
        latest_metrics_subquery,
        (TokenMetric.token_id == latest_metrics_subquery.c.token_id) &
        (TokenMetric.updated_at == latest_metrics_subquery.c.max_updated_at)
    )
    
    if chain:
        query = query.filter(Token.chain == chain)
    
    # 按market cap降序排序，处理NULL值
    query = query.order_by(
        func.coalesce(TokenMetric.total_volume_24h, 0).desc()
    ).limit(limit)
    
    tokens_with_metrics = query.all()
    
    # 构建结果
    result = []
    for token, latest_metric in tokens_with_metrics:
        token_data = {
            "id": str(token.id),
            "name": token.name or "",
            "symbol": token.symbol or "",
            "contract_address": token.contract_address or "",
            "chain": token.chain or "",
            "image_url": token.image_url or "",
            "logo_uri": token.logo_uri or "",
            "created_at": token.created_at.isoformat() if token.created_at else None,
            "metrics_updated_at": token.metrics_updated_at.isoformat() if token.metrics_updated_at else None
        }
        
        if latest_metric:
            token_data["market_cap"] = float(latest_metric.market_cap or 0)
            token_data["price_usd"] = float(latest_metric.weighted_price_usd or latest_metric.avg_price_usd or 0)
            token_data["price_change_24h"] = float(latest_metric.price_change_24h or 0)
            token_data["total_volume_24h"] = float(latest_metric.total_volume_24h or 0)
        else:
            token_data["market_cap"] = 0
            token_data["price_usd"] = 0
            token_data["price_change_24h"] = 0
            token_data["total_volume_24h"] = 0
            
        result.append(token_data)
    
    return {"tokens": result, "total": len(result)}

@app.post("/api/v1/add_token", response_model=TokenResponse, dependencies=[Depends(validate_token)])
async def add_token_api(
    symbol: str,
    chain: str,
    db: Session = Depends(get_db)
):
    """Add a new token with symbol and chain"""
    try:
        # Use unified method to add token
        result = await token_service.get_or_create_token(
            db=db,
            symbol=symbol,
            contract_address=None,  # Will be fetched automatically
            chain=chain,
            name=None,  # Will be fetched automatically
            decimals=None,  # Will be fetched automatically
            image_url=None  # Will be fetched automatically
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=404, 
                detail=result["error"]
            )
        
        # Get the actual token from database for complete info
        token = db.query(Token).filter(Token.id == result["id"]).first()
        
        token_dict = {
            "name": token.name or "",
            "symbol": token.symbol or "",
            "contract_address": token.contract_address or "",
            "chain": token.chain or "",
        }
        
        return TokenResponse(**token_dict)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tokens/{token_id}/details", response_model=TokenDetailResponse, dependencies=[Depends(validate_token)])
async def get_token_detail(
    token_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific token"""
    try:
        # 获取token基本信息
        token = db.query(Token).filter(Token.id == token_id).first()
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
            
        # 获取token指标
        from models.database import TokenMetric, TokenPool, PoolMetric, PoolMetricHistory
        latest_metric = db.query(TokenMetric).filter(
            TokenMetric.token_id == token.id
        ).order_by(TokenMetric.updated_at.desc()).first()
        
        # 获取token交易池
        pools_data = []
        token_pools = db.query(TokenPool).filter(
            TokenPool.base_token_id == token.id,
            TokenPool.is_active == True
        ).all()
        
        for pool in token_pools:
            # 获取池子最新指标
            pool_metric = db.query(PoolMetric).filter(
                PoolMetric.pool_id == pool.id
            ).order_by(PoolMetric.updated_at.desc()).first()
            
            if pool_metric:
                # 获取quote token的symbol
                quote_symbol = "UNKNOWN"
                if pool.quote_token:
                    quote_symbol = pool.quote_token.symbol
                
                pool_data = TokenPoolResponse(
                    base_symbol=token.symbol,
                    quote_symbol=quote_symbol,
                    dex=pool.dex,
                    chain=token.chain,
                    price_usd=pool_metric.price_usd or Decimal(0),
                    price_change_24h=pool_metric.price_change_24h or Decimal(0),
                    volume_24h=pool_metric.volume_24h or Decimal(0),
                    liquidity_usd=pool_metric.liquidity_usd or Decimal(0),
                    pair_address=pool.pair_address,
                    pair_created_at=pool.pair_created_at
                )
                pools_data.append(pool_data)
        
        # 获取价格历史数据
        price_history_data = []
        price_history = db.query(PoolMetricHistory).join(
            TokenPool, PoolMetricHistory.pool_id == TokenPool.id
        ).filter(
            TokenPool.base_token_id == token.id
        ).order_by(PoolMetricHistory.recorded_at.desc()).limit(30).all()
        
        for history in price_history:
            price_data = TokenPriceHistory(
                timestamp=history.recorded_at,
                price=history.price_usd or Decimal(0)
            )
            price_history_data.append(price_data)
        
        # 构建响应
        response = TokenDetailResponse(
            id=str(token.id),
            name=token.name or "",
            symbol=token.symbol or "",
            contract_address=token.contract_address or "",
            chain=token.chain or "",
            image_url=token.image_url,
            logo_uri=token.logo_uri,
            created_at=token.created_at,
            metrics_updated_at=token.metrics_updated_at
        )
        
        # 添加价格和市场数据
        if latest_metric:
            response.price_usd = latest_metric.weighted_price_usd or latest_metric.avg_price_usd
            response.price_change_24h = latest_metric.price_change_24h
            response.market_cap = latest_metric.market_cap
            response.total_volume_24h = latest_metric.total_volume_24h
            response.total_liquidity_usd = latest_metric.total_liquidity_usd
            response.fdv = latest_metric.total_fdv
            
            # 添加技术指标
            response.technical_indicators = TokenTechnicalIndicators(
                rsi_14d=latest_metric.rsi_14d,
                ma_7d=latest_metric.ma_7d,
                ma_30d=latest_metric.ma_30d,
                volatility_24h=latest_metric.volatility_24h,
                breakout_signal=latest_metric.breakout_signal,
                trend_direction=latest_metric.trend_direction,
                signal_strength=latest_metric.signal_strength
            )
            
            # 添加持有者分析
            response.holder_distribution = TokenHolderDistribution(
                holder_count=latest_metric.holder_count or 0,
                whales_count=latest_metric.whales_count,
                sharks_count=latest_metric.sharks_count,
                holder_change_24h=latest_metric.holder_change_24h,
                holder_change_7d=latest_metric.holder_change_7d,
                holder_change_24h_percent=latest_metric.holder_change_24h_percent,
                holder_change_7d_percent=latest_metric.holder_change_7d_percent,
                top10_supply_percent=latest_metric.top10_supply_percent,
                top50_supply_percent=latest_metric.top50_supply_percent,
                top100_supply_percent=latest_metric.top100_supply_percent
            )
            
            # 添加交易活动
            response.trade_activity = TokenTradeActivity(
                buy_volume_24h=latest_metric.buy_volume_24h,
                sell_volume_24h=latest_metric.sell_volume_24h,
                total_buyers_24h=latest_metric.total_buyers_24h,
                total_sellers_24h=latest_metric.total_sellers_24h,
                total_buys_24h=latest_metric.total_buys_24h,
                total_sells_24h=latest_metric.total_sells_24h,
                unique_wallets_24h=latest_metric.unique_wallets_24h
            )
        
        # 添加交易池和价格历史
        response.pools = pools_data
        response.price_history = price_history_data
                
        return response
        
    except Exception as e:
        print(f"Error getting token details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tokens/metrics", dependencies=[Depends(validate_token)])
async def get_tokens_with_metrics(
    limit: int = Query(50, ge=1, le=100),
    chain: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all tracked tokens with their latest metrics"""
    from models.database import TokenMetric
    
    query = db.query(Token)
    
    if chain:
        query = query.filter(Token.chain == chain)
    
    tokens = query.limit(limit).all()
    
    result = []
    for token in tokens:
        # Get latest metrics for this token
        latest_metric = db.query(TokenMetric).filter(
            TokenMetric.token_id == token.id
        ).order_by(TokenMetric.updated_at.desc()).first()
        
        token_data = {
            "id": str(token.id),
            "name": token.name or "",
            "symbol": token.symbol or "",
            "contract_address": token.contract_address or "",
            "chain": token.chain or "",
            "image_url": token.image_url or "",
            "logo_uri": token.logo_uri or "",
            "created_at": token.created_at.isoformat() if token.created_at else None,
            "metrics_updated_at": token.metrics_updated_at.isoformat() if token.metrics_updated_at else None
        }
        
        if latest_metric:
            token_data["metrics"] = {
                "price_usd": float(latest_metric.weighted_price_usd or latest_metric.avg_price_usd or 0),
                "price_change_24h": float(latest_metric.price_change_24h or 0),
                "price_change_1h": float(latest_metric.price_change_1h or 0),
                "price_change_5m": float(latest_metric.price_change_5m or 0),
                "volume_24h": float(latest_metric.total_volume_24h or 0),
                "market_cap": float(latest_metric.market_cap or 0),
                "liquidity_usd": float(latest_metric.total_liquidity_usd or 0),
                "holder_count": latest_metric.holder_count or 0,
                "unique_traders_24h": latest_metric.unique_traders_24h or 0,
                "buy_volume_24h": float(latest_metric.buy_volume_24h or 0),
                "sell_volume_24h": float(latest_metric.sell_volume_24h or 0),
                "total_buyers_24h": latest_metric.total_buyers_24h or 0,
                "total_sellers_24h": latest_metric.total_sellers_24h or 0,
                "total_buys_24h": latest_metric.total_buys_24h or 0,
                "total_sells_24h": latest_metric.total_sells_24h or 0,
                "rsi_14d": latest_metric.rsi_14d,
                "ma_7d": latest_metric.ma_7d,
                "ma_30d": latest_metric.ma_30d,
                "volatility_24h": latest_metric.volatility_24h,
                "trend_direction": latest_metric.trend_direction,
                "signal_strength": latest_metric.signal_strength,
                "breakout_signal": latest_metric.breakout_signal,
                "whales_count": latest_metric.whales_count or 0,
                "sharks_count": latest_metric.sharks_count or 0,
                "dolphins_count": latest_metric.dolphins_count or 0,
                "top10_supply_percent": float(latest_metric.top10_supply_percent or 0),
                "top25_supply_percent": float(latest_metric.top25_supply_percent or 0),
                "top50_supply_percent": float(latest_metric.top50_supply_percent or 0),
                "holder_change_24h": latest_metric.holder_change_24h or 0,
                "holder_change_24h_percent": float(latest_metric.holder_change_24h_percent or 0),
                "pools_count": latest_metric.pools_count or 0,
                "updated_at": latest_metric.updated_at.isoformat() if latest_metric.updated_at else None
            }
        else:
            token_data["metrics"] = None
            
        result.append(token_data)
    
    return {"tokens": result, "total": len(result)}

# ===== CHAT ENDPOINTS =====

@app.post("/api/v1/chat", response_model=ChatResponse, dependencies=[Depends(validate_token)])
async def chat_api(request: ChatRequest, db: Session = Depends(get_db)):
    """Process chat message with enhanced multi-DEX analysis"""
    try:
        
        response_data = await process_chat_message(
            db, request.message, request.conversation_id, request.include_pools
        )
        
        return ChatResponse(
            response=response_data
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== UTILITY ENDPOINTS =====

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "Simplified AIP DEX API",
        "features": ["Token Management", "Chat Interface"]
    }

# ===== WEB INTERFACE ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the trading bot dashboard HTML page"""
    try:
        dashboard_html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
        with open(dashboard_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dashboard not found")

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface():
    """Serve the chat interface HTML page"""
    try:
        chat_html_path = os.path.join(os.path.dirname(__file__), "chat", "index.html")
        with open(chat_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Replace the API base URL to use relative paths since we're serving from the same server
        html_content = html_content.replace(
            "this.baseUrl = 'http://127.0.0.1:8000';",
            "this.baseUrl = '';"
        )
        
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat interface not found")

@app.get("/chat-page", response_class=HTMLResponse)
async def chat_page():
    """Alternative route for the chat interface"""
    return await chat_interface()

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the MetaMask login page"""
    try:
        login_html_path = os.path.join(os.path.dirname(__file__), "static", "login.html")
        with open(login_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Login page not found")

@app.get("/bot-management", response_class=HTMLResponse)
async def bot_management_page():
    """Serve the bot management page"""
    try:
        management_html_path = os.path.join(os.path.dirname(__file__), "static", "bot-management.html")
        with open(management_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Bot management page not found")

@app.get("/tokens", response_class=HTMLResponse)
async def tokens_page():
    """Serve the token analytics page"""
    try:
        tokens_html_path = os.path.join(os.path.dirname(__file__), "static", "token-list.html")
        with open(tokens_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Token analytics page not found")

@app.get("/token/{token_id}", response_class=HTMLResponse)
async def token_detail_page(token_id: str):
    """Serve the token detail page"""
    try:
        token_detail_html_path = os.path.join(os.path.dirname(__file__), "static", "token-detail.html")
        with open(token_detail_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Token detail page not found")

@app.get("/token-detail.html", response_class=HTMLResponse)
async def token_detail_html():
    """Serve the token detail HTML page directly"""
    try:
        token_detail_html_path = os.path.join(os.path.dirname(__file__), "static", "token-detail.html")
        with open(token_detail_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Token detail page not found")

# ===== META MASK AUTHENTICATION ENDPOINTS =====

@app.post("/api/v1/auth/metamask", dependencies=[Depends(validate_token)])
async def metamask_auth(
    request: dict,
    db: Session = Depends(get_db)
):
    """Authenticate user with MetaMask signature"""
    try:
        wallet_address = request.get("wallet_address")
        signature = request.get("signature")
        message = request.get("message")
        
        if not all([wallet_address, signature, message]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Verify signature (simplified for demo - in production use proper verification)
        # For now, we'll just create or get the owner
        
        # Check if owner exists
        existing_owner = db.query(BotOwner).filter(
            BotOwner.wallet_address == wallet_address
        ).first()
        
        if existing_owner:
            return {
                "owner_id": str(existing_owner.id),
                "owner_name": existing_owner.owner_name,
                "wallet_address": wallet_address,
                "message": "Existing user authenticated"
            }
        
        # Create new owner with basic subscription (1 bot limit)
        owner_data = BotOwnerCreate(
            owner_name=f"User_{wallet_address[:8]}",
            email=f"{wallet_address[:8]}@metamask.user",
            wallet_address=wallet_address,
            subscription_tier="basic",
            max_bots_allowed=1  # Basic users can only claim 1 bot
        )
        
        new_owner = await owner_service.create_bot_owner(db, owner_data)
        
        if not new_owner:
            raise HTTPException(status_code=500, detail="Failed to create owner")
        
        return {
            "owner_id": str(new_owner.id),
            "owner_name": new_owner.owner_name,
            "wallet_address": wallet_address,
            "message": "New user created and authenticated"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== BOT MANAGEMENT ENDPOINTS =====
# Bot management endpoints have been moved to api/trading_bot_routes.py







# ===== STRATEGY MANAGEMENT ENDPOINTS =====

@app.post("/api/v1/strategies", dependencies=[Depends(validate_token)])
async def create_strategy(
    request: dict,
    db: Session = Depends(get_db)
):
    """Create a new trading strategy"""
    try:
        # Accept optional strategy_id to perform update instead of create
        strategy_id = request.get("strategy_id")
        owner_id = request.get("owner_id")

        # If strategy_id present -> update
        if strategy_id:
            try:
                strategy_uuid = uuid.UUID(strategy_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid strategy_id format")

            # Validate update payload by selecting allowed fields and assigning one-by-one
            try:
                # Collect allowed field names from the Pydantic model (v2)
                allowed_fields = set(getattr(TradingStrategyUpdate, 'model_fields', {}).keys())

                # Build payload only with fields that belong to the update model
                payload = {}
                for k, v in request.items():
                    # skip control fields
                    if k in ("strategy_id", "owner_id"):
                        continue
                    if k in allowed_fields:
                        payload[k] = v

                if not payload:
                    raise HTTPException(status_code=400, detail="No updatable fields provided")

                # Instantiate model with the filtered payload
                update_data = TradingStrategyUpdate(**payload)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid update data: {e}")

            updated = await owner_service.update_trading_strategy(db, strategy_uuid, update_data)
            if not updated:
                raise HTTPException(status_code=404, detail="Strategy not found or could not be updated")

            return {
                "success": True,
                "strategy_id": str(updated.id),
                "strategy_name": updated.strategy_name,
                "message": "Strategy updated successfully"
            }

        # Otherwise create new strategy (owner_id required)
        if not owner_id:
            raise HTTPException(status_code=400, detail="Missing owner_id for strategy creation")

        try:
            owner_uuid = uuid.UUID(owner_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid owner_id format")

        # Create strategy data with default values for missing fields
        strategy_data = TradingStrategyCreate(
            strategy_name=request.get("strategy_name", "Custom Strategy"),
            strategy_description=request.get("strategy_description", "Custom strategy description"),
            strategy_type=request.get("strategy_type", "user_defined"),
            risk_level=request.get("risk_level", "medium"),
            max_position_size=Decimal(str(request.get("max_position_size", 20.0))),
            stop_loss_percentage=Decimal(str(request.get("stop_loss_percentage", 10.0))),
            take_profit_percentage=Decimal(str(request.get("take_profit_percentage", 25.0))),
            min_profit_threshold=Decimal(str(request.get("min_profit_threshold", 3.0))),
            max_daily_trades=request.get("max_daily_trades", 15),
            llm_confidence_threshold=Decimal(str(request.get("llm_confidence_threshold", 0.7))),
            gas_fee_native=Decimal(str(request.get("gas_fee_native", 0.001))),
            trading_fee_percentage=Decimal(str(request.get("trading_fee_percentage", 0.3))),
            slippage_tolerance=Decimal(str(request.get("slippage_tolerance", 2.0))),
            min_trade_amount_usd=Decimal(str(request.get("min_trade_amount_usd", 10.0))),
            polling_interval_hours=Decimal(str(request.get("polling_interval_hours", 1.0))),
            enable_stop_loss=request.get("enable_stop_loss", True),
            enable_take_profit=request.get("enable_take_profit", True),
            buy_strategy_description=request.get("buy_strategy_description", "Custom buy strategy"),
            sell_strategy_description=request.get("sell_strategy_description", "Custom sell strategy"),
            filter_strategy_description=request.get("filter_strategy_description", "Custom filter strategy"),
            summary_strategy_description=request.get("summary_strategy_description", "Custom strategy summary"),
            is_public=request.get("is_public", False)
        )

        strategy = await owner_service.create_trading_strategy(db, owner_uuid, strategy_data)

        if not strategy:
            raise HTTPException(status_code=500, detail="Failed to create strategy")

        return {
            "success": True,
            "strategy_id": str(strategy.id),
            "strategy_name": strategy.strategy_name,
            "message": "Strategy created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/strategies/owner/{owner_id}", dependencies=[Depends(validate_token)])
async def get_owner_strategies(
    owner_id: str,
    db: Session = Depends(get_db)
):
    """Get all strategies for an owner"""
    try:
        # Convert string ID to UUID
        try:
            owner_uuid = uuid.UUID(owner_id)
        except ValueError:
            # Return empty list for invalid UUID
            return []
        
        strategies = await owner_service.list_owner_strategies(db, owner_uuid)
        
        result = []
        for strategy in strategies:
            result.append({
                # 基本信息
                "id": str(strategy.id),
                "owner_id": str(strategy.owner_id),
                "strategy_name": strategy.strategy_name,
                "strategy_description": strategy.strategy_description,
                "strategy_type": strategy.strategy_type,
                "risk_level": strategy.risk_level,
                
                # 数值参数设置
                "max_position_size": float(strategy.max_position_size),
                "stop_loss_percentage": float(strategy.stop_loss_percentage),
                "take_profit_percentage": float(strategy.take_profit_percentage),
                "min_profit_threshold": float(strategy.min_profit_threshold),
                "max_daily_trades": strategy.max_daily_trades,
                "llm_confidence_threshold": float(strategy.llm_confidence_threshold),
                
                # 交易费用设置
                "gas_fee_native": float(strategy.gas_fee_native) if strategy.gas_fee_native else 0.00003,
                "trading_fee_percentage": float(strategy.trading_fee_percentage) if strategy.trading_fee_percentage else 0.1,
                "slippage_tolerance": float(strategy.slippage_tolerance) if strategy.slippage_tolerance else 1.0,
                
                # 运行控制参数
                "min_trade_amount_usd": float(strategy.min_trade_amount_usd) if strategy.min_trade_amount_usd else 10.0,
                "polling_interval_hours": float(strategy.polling_interval_hours) if strategy.polling_interval_hours else 1.0,
                
                # 功能开关
                "enable_stop_loss": strategy.enable_stop_loss,
                "enable_take_profit": strategy.enable_take_profit,
                
                # 策略描述性配置
                "buy_strategy_description": strategy.buy_strategy_description,
                "sell_strategy_description": strategy.sell_strategy_description,
                "filter_strategy_description": strategy.filter_strategy_description,
                "summary_strategy_description": strategy.summary_strategy_description,
                
                # 状态字段
                "is_active": strategy.is_active,
                "is_public": strategy.is_public,
                "is_default": strategy.is_default,
                
                # 使用统计
                "usage_count": strategy.usage_count,
                "success_rate": float(strategy.success_rate) if strategy.success_rate else None,
                "average_profit_percentage": float(strategy.average_profit_percentage) if strategy.average_profit_percentage else None,
                
                # 时间戳
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/owners", dependencies=[Depends(validate_token)])
async def create_owner(
    request: dict,
    db: Session = Depends(get_db)
):
    """Create a new bot owner"""
    try:
        owner_data = BotOwnerCreate(
            owner_name=request.get("owner_name"),
            email=request.get("email"),
            wallet_address=request.get("wallet_address"),
            phone=request.get("phone"),
            subscription_tier=request.get("subscription_tier", "basic"),
            max_bots_allowed=request.get("max_bots_allowed", 1)
        )
        
        owner = await owner_service.create_bot_owner(db, owner_data)
        
        if not owner:
            raise HTTPException(status_code=500, detail="Failed to create owner")
        
        return {
            "success": True,
            "id": str(owner.id),
            "owner_name": owner.owner_name,
            "email": owner.email,
            "wallet_address": owner.wallet_address,
            "subscription_tier": owner.subscription_tier,
            "max_bots_allowed": owner.max_bots_allowed,
            "message": "Owner created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/owners/wallet/{wallet_address}", dependencies=[Depends(validate_token)])
async def get_owner_by_wallet(
    wallet_address: str,
    db: Session = Depends(get_db)
):
    """Get owner by wallet address"""
    try:
        owner = await owner_service.get_bot_owner_by_wallet(db, wallet_address)
        
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
        
        return {
            "id": str(owner.id),
            "owner_name": owner.owner_name,
            "email": owner.email,
            "wallet_address": owner.wallet_address,
            "subscription_tier": owner.subscription_tier,
            "max_bots_allowed": owner.max_bots_allowed
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# All bots endpoint moved to api/trading_bot_routes.py

@app.get("/api/info")
async def api_info():
    """API information and available endpoints"""
    return {
        "service": "AIP DEX Signal Aggregator",
        "version": "1.0.0",
        "features": [
            "Token Management",
            "Multi-DEX Analysis", 
            "Pool-Level Metrics",
            "Arbitrage Detection",
            "LLM Chat Interface",
            "MetaMask Authentication",
            "Bot Claiming",
            "Strategy Management"
        ],
        "endpoints": {
            "chat_interface": "/",
            "login_page": "/login",
            "tokens_page": "/tokens",
            "bot_management": "/bot-management",
            "api_docs": "/docs",
            "api_redoc": "/redoc",
            "bots_overview": "/api/v1/bots/overview",
            "all_bots": "/api/v1/bots",
            "create_bot_frontend": "/api/v1/bots/create",
            "health_check": "/api/v1/health",
            "tokens_api": "/api/v1/tokens",
            "add_token": "/api/v1/add_token",
            "chat": "/api/v1/chat",
            "metamask_auth": "/api/v1/auth/metamask",
            "create_owner": "/api/v1/owners",
            "get_owner_by_wallet": "/api/v1/owners/wallet/{wallet_address}",
            "owner_bots": "/api/v1/bots/owner/{owner_id}",
            "configure_bot": "/api/v1/bots/configure/{bot_id}",
            "create_strategy": "/api/v1/strategies",
            "owner_strategies": "/api/v1/strategies/owner/{owner_id}"
        }
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=args.port,
        log_level="info"
    )