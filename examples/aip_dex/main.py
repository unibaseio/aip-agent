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

# Load environment variables
load_dotenv()

from models.database import create_tables, create_indexes, get_db, Token, SessionLocal
from services.token_service import TokenService
from llm.token_analyzer import TokenDecisionAnalyzer
from api.schemas import (
    TokenResponse, ChatRequest, ChatResponse
)

from aip_agent.agents.custom_agent import CallbackAgent
from aip_agent.agents.full_agent import FullAgentWrapper
from membase.chain.chain import membase_id  

# Global token service instance
token_service = TokenService()
token_analyzer = TokenDecisionAnalyzer()

async def analyze_token(message: str, include_pools: bool = False):
    """Analyze a token in a message with enhanced multi-DEX analysis
    
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
        print(f"========== Analyzing token: {message}")
        response_data = await token_service.process_chat_message(
                db, message, include_pools
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
        system_prompt = os.getenv("SYSTEM_PROMPT", "You are an AI assistant specialized in DEX token analysis and trading signals. When using the analyze_token function, always return the COMPLETE results without omitting any data fields. Provide comprehensive analysis including all available metrics, technical indicators, pool information, and trading signals.")
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


async def process_chat_message(db: Session, messsage: str, conversation_id: str, include_pools: bool = False) -> str:
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

        print(f"AIP DEX token analysis: {token.symbol} on {token.chain} {include_pools}")                
        # Get comprehensive token analysis
        decision_data = await token_service.get_token_decision_data(db, str(token.id))
            
        if not decision_data:
            return f"I found {target_token_symbol} but couldn't retrieve current analysis data. The token might be new or have limited trading data."
            
        system_prompt = token_analyzer._get_system_prompt(include_pools=include_pools)
        user_message = token_analyzer._create_comprehensive_analysis_prompt(decision_data, user_intent, include_pools)

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
chat_static_path = os.path.join(os.path.dirname(__file__), "chat")
if os.path.exists(chat_static_path):
    app.mount("/static", StaticFiles(directory=chat_static_path), name="static")

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

@app.get("/api/v1/tokens", response_model=List[TokenResponse], dependencies=[Depends(validate_token)])
async def tokens_api(
    limit: int = Query(50, ge=1, le=100),
    chain: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all tracked tokens with optional filtering"""
    query = db.query(Token)
    
    if chain:
        query = query.filter(Token.chain == chain)
    
    tokens = query.limit(limit).all()
    
    # Convert to response format
    result = []
    for token in tokens:
        token_dict = {
            "name": token.name,
            "symbol": token.symbol,
            "contract_address": token.contract_address,
            "chain": token.chain,
        }
        result.append(TokenResponse(**token_dict))
    
    return result

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
            "name": token.name,
            "symbol": token.symbol,
            "contract_address": token.contract_address,
            "chain": token.chain,
        }
        
        return TokenResponse(**token_dict)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """Alternative route for the chat interface"""
    return await chat_interface()

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
            "LLM Chat Interface"
        ],
        "endpoints": {
            "chat_interface": "/",
            "api_docs": "/docs",
            "api_redoc": "/redoc",
            "health_check": "/api/v1/health",
            "tokens": "/api/v1/tokens",
            "add_token": "/api/v1/add_token",
            "chat": "/api/v1/chat"
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