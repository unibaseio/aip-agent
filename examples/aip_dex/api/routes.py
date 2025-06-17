from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from models.database import get_db, Token, TokenPool, PoolMetric
from services.token_service import TokenService
from api.schemas import (
    TokenCreate, TokenResponse, TokenSearchRequest, TokenSearchResponse,
    TokenPoolCreate, TokenPoolResponse, PoolMetricResponse,
    EnhancedSignalResponse, SignalResponse, PoolAnalysisRequest, PoolAnalysisResponse,
    ChatRequest, ChatResponse, ErrorResponse
)

router = APIRouter()
token_service = TokenService()

# ===== TOKEN ENDPOINTS =====

@router.get("/tokens", response_model=List[TokenResponse])
async def get_tokens(
    limit: int = Query(50, ge=1, le=100),
    chain: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all tracked tokens with optional filtering"""
    query = db.query(Token)
    
    if chain:
        query = query.filter(Token.chain == chain)
    
    tokens = query.limit(limit).all()
    
    # Add pools count for each token
    result = []
    for token in tokens:
        pools = await token_service.get_token_pools(db, str(token.id))
        token_dict = {
            "id": str(token.id),
            "name": token.name,
            "symbol": token.symbol,
            "contract_address": token.contract_address,
            "chain": token.chain,
            "decimals": token.decimals,
            "image_url": token.image_url,
            "created_at": token.created_at,
            "updated_at": token.updated_at,
            "pools_count": len(pools)
        }
        result.append(TokenResponse(**token_dict))
    
    return result

@router.post("/tokens/search", response_model=TokenSearchResponse)
async def search_tokens(
    request: TokenSearchRequest,
    db: Session = Depends(get_db)
):
    """Search tokens by symbol, name, or contract address"""
    try:
        tokens = await token_service.search_tokens(
            db, request.query, request.chain, request.limit
        )
        
        # Convert to response format
        token_responses = []
        for token in tokens:
            pools = await token_service.get_token_pools(db, str(token.id))
            token_dict = {
                "id": str(token.id),
                "name": token.name,
                "symbol": token.symbol,
                "contract_address": token.contract_address,
                "chain": token.chain,
                "decimals": token.decimals,
                "image_url": token.image_url,
                "created_at": token.created_at,
                "updated_at": token.updated_at,
                "pools_count": len(pools)
            }
            token_responses.append(TokenResponse(**token_dict))
        
        return TokenSearchResponse(
            tokens=token_responses,
            total=len(token_responses)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tokens", response_model=TokenResponse)
async def create_token(token_data: TokenCreate, db: Session = Depends(get_db)):
    """Add a new token"""
    try:
        # Use unified method to add token
        result = await token_service.get_or_create_token(
            db=db,
            symbol=token_data.symbol,
            contract_address=token_data.contract_address,
            chain=token_data.chain,
            name=token_data.name,
            decimals=token_data.decimals,
            image_url=token_data.image_url
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
            "decimals": token.decimals,
            "image_url": token.image_url,
            "created_at": token.created_at,
            "updated_at": token.updated_at,
        }
        
        return TokenResponse(**token_dict)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== POOL ENDPOINTS =====

@router.get("/tokens/{token_id}/pools", response_model=List[TokenPoolResponse])
async def get_token_pools(
    token_id: str,
    dex: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get all pools for a token"""
    try:
        pools = await token_service.get_token_pools(db, token_id, dex, active_only)
        return [TokenPoolResponse(
            id=str(pool.id),
            base_token_id=str(pool.base_token_id),
            quote_token_id=str(pool.quote_token_id),
            dex=pool.dex,
            chain=pool.chain,
            pair_address=pool.pair_address,
            pool_version=pool.pool_version,
            fee_tier=pool.fee_tier,
            is_active=pool.is_active,
            created_at=pool.created_at
        ) for pool in pools]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pools", response_model=TokenPoolResponse)
async def create_pool(pool_data: TokenPoolCreate, db: Session = Depends(get_db)):
    """Create a new token pool"""
    try:
        pool = await token_service.create_or_update_pool(db, {
            'base_token_id': pool_data.base_token_id,
            'quote_token_id': pool_data.quote_token_id,
            'dex': pool_data.dex,
            'chain': pool_data.chain,
            'pair_address': pool_data.pair_address,
            'pool_version': pool_data.pool_version,
            'fee_tier': pool_data.fee_tier
        })
        
        return TokenPoolResponse(
            id=str(pool.id),
            base_token_id=str(pool.base_token_id),
            quote_token_id=str(pool.quote_token_id),
            dex=pool.dex,
            chain=pool.chain,
            pair_address=pool.pair_address,
            pool_version=pool.pool_version,
            fee_tier=pool.fee_tier,
            is_active=pool.is_active,
            created_at=pool.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pools/{pool_id}/metrics", response_model=PoolMetricResponse)
async def get_pool_metrics(pool_id: str, db: Session = Depends(get_db)):
    """Get latest metrics for a specific pool"""
    try:
        pool = db.query(TokenPool).filter(TokenPool.id == pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        # Update pool metrics
        metric = await token_service.update_pool_metrics(db, pool)
        if not metric:
            raise HTTPException(status_code=500, detail="Unable to fetch pool metrics")
        
        return PoolMetricResponse(
            id=str(metric.id),
            pool_id=str(metric.pool_id),
            price_usd=metric.price_usd,
            price_native=metric.price_native,
            volume_1h=metric.volume_1h,
            volume_24h=metric.volume_24h,
            liquidity_usd=metric.liquidity_usd,
            liquidity_base=metric.liquidity_base,
            liquidity_quote=metric.liquidity_quote,
            price_change_1h=metric.price_change_1h,
            price_change_24h=metric.price_change_24h,
            txns_1h_buys=metric.txns_1h_buys,
            txns_1h_sells=metric.txns_1h_sells,
            txns_24h_buys=metric.txns_24h_buys,
            txns_24h_sells=metric.txns_24h_sells,
            market_cap=metric.market_cap,
            fdv=metric.fdv,
            data_source=metric.data_source,
            updated_at=metric.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== SIGNAL ENDPOINTS =====

@router.get("/tokens/{token_id}/signal", response_model=EnhancedSignalResponse)
async def get_enhanced_token_signal(
    token_id: str,
    include_pools: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get enhanced trading signal for a specific token with optional pool analysis"""
    try:
        signal_data = await token_service.get_enhanced_token_signal(db, token_id, include_pools)
        
        if "error" in signal_data:
            raise HTTPException(status_code=404, detail=signal_data["error"])
        
        # Get token info
        token = db.query(Token).filter(Token.id == token_id).first()
        
        return {
            "token": {
                "id": str(token.id),
                "name": token.name,
                "symbol": token.symbol,
                "contract_address": token.contract_address,
                "chain": token.chain,
                "decimals": token.decimals,
                "image_url": token.image_url,
                "created_at": token.created_at,
                "updated_at": token.updated_at,
                "pools_count": signal_data["token_metrics"]["pools_count"]
            },
            "signal": signal_data["signal"],
            "reason": signal_data["reason"],
            "confidence": signal_data["confidence"],
            "token_metrics": signal_data["token_metrics"],
            "pool_data": signal_data.get("pool_analysis", []),
            "market_analysis": {
                "trend_strength": signal_data["confidence"],
                "risk_level": "high" if signal_data["confidence"] > 0.7 else "medium" if signal_data["confidence"] > 0.4 else "low"
            },
            "updated_at": signal_data["updated_at"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tokens/{token_id}/signal/simple", response_model=SignalResponse)
async def get_simple_token_signal(token_id: str, db: Session = Depends(get_db)):
    """Get simple trading signal for backward compatibility"""
    try:
        signal_data = await token_service.get_enhanced_token_signal(db, token_id, False)
        
        if "error" in signal_data:
            raise HTTPException(status_code=404, detail=signal_data["error"])
        
        # Convert to simple format
        metrics = signal_data["token_metrics"]
        return SignalResponse(
            token=signal_data["token"],
            signal=signal_data["signal"],
            reason=signal_data["reason"],
            confidence=signal_data["confidence"],
            metrics={
                "price": metrics["weighted_price_usd"],
                "volume_24h": metrics["total_volume_24h"],
                "liquidity_usd": metrics["total_liquidity_usd"],
                "market_cap": metrics["market_cap"],
                "rsi_14d": metrics["rsi_14d"],
                "ma_7d": metrics["ma_7d"],
                "ma_30d": metrics["ma_30d"],
                "pools_count": metrics["pools_count"],
                "trend_direction": metrics["trend_direction"]
            },
            updated_at=signal_data["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pools/analyze", response_model=PoolAnalysisResponse)
async def analyze_pools(request: PoolAnalysisRequest, db: Session = Depends(get_db)):
    """Analyze pools for a token across different DEXs"""
    try:
        # Find token
        token = db.query(Token).filter(Token.symbol == request.token_symbol.upper()).first()
        if not token:
            raise HTTPException(status_code=404, detail=f"Token {request.token_symbol} not found")
        
        # Get pools (filtered by DEX if specified)
        pools = await token_service.get_token_pools(db, str(token.id))
        if request.dex_ids:
            pools = [p for p in pools if p.dex in request.dex_ids]
        
        # Get latest metrics for each pool
        pool_metrics = []
        for pool in pools:
            metric = await token_service.update_pool_metrics(db, pool)
            if metric:
                pool_metrics.append(PoolMetricResponse(
                    id=str(metric.id),
                    pool_id=str(metric.pool_id),
                    price_usd=metric.price_usd,
                    price_native=metric.price_native,
                    volume_1h=metric.volume_1h,
                    volume_24h=metric.volume_24h,
                    liquidity_usd=metric.liquidity_usd,
                    liquidity_base=metric.liquidity_base,
                    liquidity_quote=metric.liquidity_quote,
                    price_change_1h=metric.price_change_1h,
                    price_change_24h=metric.price_change_24h,
                    txns_1h_buys=metric.txns_1h_buys,
                    txns_1h_sells=metric.txns_1h_sells,
                    txns_24h_buys=metric.txns_24h_buys,
                    txns_24h_sells=metric.txns_24h_sells,
                    market_cap=metric.market_cap,
                    fdv=metric.fdv,
                    data_source=metric.data_source,
                    updated_at=metric.updated_at
                ))
        
        # Find best pool (highest liquidity)
        best_pool = None
        if pool_metrics:
            best_metric = max(pool_metrics, key=lambda x: float(x.liquidity_usd or 0))
            best_pool_obj = next(p for p in pools if str(p.id) == best_metric.pool_id)
            best_pool = {
                "dex": best_pool_obj.dex,
                "price_usd": float(best_metric.price_usd or 0),
                "liquidity_usd": float(best_metric.liquidity_usd or 0),
                "volume_24h": float(best_metric.volume_24h or 0),
                "pair_address": best_pool_obj.pair_address
            }
        
        # Calculate arbitrage opportunities if requested
        arbitrage_opportunities = []
        if request.include_arbitrage and len(pool_metrics) > 1:
            prices = [(float(m.price_usd or 0), m.pool_id) for m in pool_metrics if m.price_usd]
            if len(prices) >= 2:
                prices.sort()
                min_price, min_pool = prices[0]
                max_price, max_pool = prices[-1]
                
                if max_price > min_price:
                    arbitrage_opportunities.append({
                        "profit_percentage": ((max_price - min_price) / min_price) * 100,
                        "buy_pool": min_pool,
                        "sell_pool": max_pool,
                        "buy_price": min_price,
                        "sell_price": max_price
                    })
        
        return PoolAnalysisResponse(
            token=request.token_symbol,
            pools=pool_metrics,
            arbitrage_opportunities=arbitrage_opportunities if request.include_arbitrage else None,
            best_pool=best_pool,
            updated_at=pool_metrics[0].updated_at if pool_metrics else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== CHAT ENDPOINTS =====

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Process chat message with enhanced multi-DEX analysis"""
    try:
        response_data = await token_service.process_chat_message(
            db, request.message, request.include_pools
        )
        
        return ChatResponse(
            response=response_data["response"],
            signal_data=response_data.get("signal_data"),
            intent=response_data.get("intent"),
            pool_analysis=response_data.get("pool_analysis")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== UTILITY ENDPOINTS =====

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "Enhanced AIP DEX Signal Aggregator",
        "architecture": "Three-Tier (Token → Pools → Metrics → Aggregated)",
        "features": ["Multi-DEX Analysis", "Pool Comparison", "Arbitrage Detection", "Enhanced Signals"]
    }

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    try:
        total_tokens = db.query(Token).count()
        total_pools = db.query(TokenPool).count()
        active_pools = db.query(TokenPool).filter(TokenPool.is_active == True).count()
        total_metrics = db.query(PoolMetric).count()
        
        return {
            "total_tokens": total_tokens,
            "total_pools": total_pools,
            "active_pools": active_pools,
            "total_metrics_records": total_metrics,
            "architecture": "three-tier"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 