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

from models.database import create_tables, create_indexes, get_db, Token
from services.token_service import TokenService
from api.schemas import (
    TokenResponse, ChatRequest, ChatResponse
)

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
        response_data = await token_service.process_chat_message(
            db, request.message, request.include_pools
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
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    ) 