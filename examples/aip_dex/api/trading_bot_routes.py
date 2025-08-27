from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from models.database import TokenMetric, get_db, TradingBot, Position, Transaction, RevenueSnapshot, LLMDecision, BotOwner, TradingStrategy
from services.owner_service import OwnerService
from api.schemas import (
    TradingBotResponse, TradingBotSummary, PositionResponse, 
    TransactionResponse, RevenueSnapshot as RevenueSnapshotSchema,
    LLMDecisionResponse, SystemStatus, PaginatedResponse,
    TradingBotCreate, TradingBotUpdate, ApiResponse
)
from services.trading_service import TradingService
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security
import os

# Token validation dependency
security = HTTPBearer()

def validate_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validate bearer token"""
    expected_token = os.getenv("DEX_BEARER_TOKEN", "aip-dex-default-token-2025")
    if credentials.credentials != expected_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials

router = APIRouter(prefix="/api/v1", tags=["trading-bots"])
trading_service = TradingService()
owner_service = OwnerService()

@router.get("/bots/overview", response_model=SystemStatus)
async def get_system_overview(db: Session = Depends(get_db)):
    """Get system overview statistics"""
    try:
        # Get basic bot statistics
        total_bots = db.query(TradingBot).count()
        active_bots = db.query(TradingBot).filter(TradingBot.is_active == True).count()
        
        # Get 24h transaction statistics
        start_time = datetime.utcnow() - timedelta(hours=24)
        total_trades_24h = db.query(Transaction).filter(
            Transaction.created_at >= start_time
        ).count()
        
        # Calculate total volume in last 24h
        recent_transactions = db.query(Transaction).filter(
            Transaction.created_at >= start_time,
            Transaction.status == 'executed'
        ).all()
        
        total_volume_24h = sum(
            float(tx.amount_usd or 0) for tx in recent_transactions
        )
        
        # Ensure total_volume_24h is not None
        if total_volume_24h is None:
            total_volume_24h = 0.0
        
        # Calculate today's profit (from today's transactions)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_transactions = db.query(Transaction).filter(
            Transaction.created_at >= today_start,
            Transaction.status == 'executed'
        ).all()
        
        today_profit = sum(
            float(tx.realized_pnl_usd or 0) for tx in today_transactions
        )
        
        # Ensure today_profit is not None
        if today_profit is None:
            today_profit = 0.0
        
        # Calculate total assets across all bots
        total_assets = sum(
            float(bot.total_assets_usd or 0) for bot in db.query(TradingBot).all()
        )
        
        # Ensure total_assets is not None
        if total_assets is None:
            total_assets = 0.0
        
        # Calculate system uptime (simplified)
        system_uptime = "24h"  # This would be calculated from actual startup time
        
        return SystemStatus(
            total_bots=total_bots,
            active_bots=active_bots,
            total_trades_24h=total_trades_24h,
            total_volume_24h_usd=Decimal(str(total_volume_24h)),
            today_profit_usd=Decimal(str(today_profit)),
            total_assets_usd=Decimal(str(total_assets)),
            system_uptime=system_uptime,
            database_status="connected",
            api_status="healthy"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bots/create", response_model=ApiResponse)
async def create_bot_frontend(bot_data: TradingBotCreate, db: Session = Depends(get_db)):
    """Create a new trading bot for frontend interface"""
    try:
        # Note: Multiple bots can now use the same account_address
        # No need to check for duplicates since unique constraint was removed
        
        # Convert and validate owner exists if provided
        owner_uuid = None
        if bot_data.owner_id:
            try:
                owner_uuid = uuid.UUID(bot_data.owner_id)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=f"Invalid owner UUID format: {str(ve)}")
            
            owner = db.query(BotOwner).filter(BotOwner.id == owner_uuid).first()
            if not owner:
                raise HTTPException(status_code=404, detail="Owner not found")
        
        # Convert and validate strategy exists if provided
        strategy_uuid = None
        if bot_data.strategy_id:
            try:
                strategy_uuid = uuid.UUID(bot_data.strategy_id)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=f"Invalid strategy UUID format: {str(ve)}")
            
            strategy = db.query(TradingStrategy).filter(TradingStrategy.id == strategy_uuid).first()
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Create new bot
        new_bot = TradingBot(
            id=uuid.uuid4(),
            bot_name=bot_data.bot_name,
            account_address=bot_data.account_address,
            chain=bot_data.chain,
            initial_balance_usd=bot_data.initial_balance_usd,
            current_balance_usd=bot_data.initial_balance_usd,
            total_assets_usd=bot_data.initial_balance_usd,
            owner_id=owner_uuid,
            strategy_id=strategy_uuid,
            is_active=False,  # Default to inactive
            is_configured=bool(owner_uuid and strategy_uuid),
            total_trades=0,
            profitable_trades=0,
            total_profit_usd=0,
            max_drawdown_percentage=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_bot)
        db.commit()
        db.refresh(new_bot)
        
        return ApiResponse(
            success=True,
            message="Bot created successfully",
            data={"bot_id": str(new_bot.id)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # Handle database errors
        if "duplicate key value violates unique constraint" in str(e):
            # Handle other potential unique constraint violations
            raise HTTPException(
                status_code=409, 
                detail=f"Duplicate data detected: {str(e)}"
            )
        raise HTTPException(status_code=500, detail=f"Failed to create bot: {str(e)}")

@router.get("/bots/owner/{owner_id}", response_model=List[TradingBotSummary])
async def get_bots_by_owner(owner_id: str, db: Session = Depends(get_db)):
    """Get all bots owned by a specific owner"""
    try:
        # Convert string ID to UUID
        try:
            owner_uuid = uuid.UUID(owner_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(ve)}")
        
        bots = db.query(TradingBot).filter(TradingBot.owner_id == owner_uuid).all()
        
        bot_summaries = []
        for bot in bots:
            # Handle strategy type
            strategy_type = "Not configured"
            if bot.strategy:
                strategy_type = bot.strategy.strategy_type
            
            # Calculate profit percentage
            total_profit_percentage = Decimal('0')
            if bot.initial_balance_usd and bot.initial_balance_usd > 0 and bot.total_profit_usd:
                total_profit_percentage = (bot.total_profit_usd / bot.initial_balance_usd) * 100
            
            # Determine status based on is_active and is_configured
            if bot.is_active and bot.is_configured:
                status = 'running'
            elif bot.is_configured:
                status = 'configured'
            else:
                status = 'inactive'
            
            bot_summaries.append(TradingBotSummary(
                id=bot.id,
                bot_name=bot.bot_name,
                account_address=bot.account_address,
                chain=bot.chain,
                strategy_type=strategy_type,
                total_assets_usd=bot.total_assets_usd or Decimal('0'),
                total_profit_usd=bot.total_profit_usd or Decimal('0'),
                total_profit_percentage=total_profit_percentage,
                is_active=bot.is_active,
                is_configured=bot.is_configured,
                status=status,
                last_activity_at=bot.last_activity_at
            ))
        
        return bot_summaries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bots for owner: {str(e)}")

@router.get("/transactions/recent", response_model=List[TransactionResponse])
async def get_recent_transactions(
    hours: int = Query(2400, ge=1, le=16800),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get recent transactions across all bots"""
    try:
        # Use timezone-aware datetime for proper comparison
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        # Convert to naive datetime to match database format
        start_time = start_time.replace(tzinfo=None)
        
        transactions = db.query(Transaction).filter(
            Transaction.created_at >= start_time
        ).order_by(Transaction.created_at.desc()).limit(limit).all()
        
        result = []
        for tx in transactions:
            token = tx.token
            bot = tx.bot
            result.append(TransactionResponse(
                id=tx.id,
                transaction_type=tx.transaction_type,
                status=tx.status,
                token_symbol=token.symbol,
                token_name=token.name,
                amount_usd=tx.amount_usd,
                token_amount=tx.token_amount,
                price_usd=tx.price_usd,
                gas_cost_usd=tx.gas_cost_usd,
                trading_fee_usd=tx.trading_fee_usd,
                total_cost_usd=tx.total_cost_usd,
                realized_pnl_usd=tx.realized_pnl_usd,
                realized_pnl_percentage=tx.realized_pnl_percentage,
                balance_before_usd=tx.balance_before_usd,
                balance_after_usd=tx.balance_after_usd,
                position_before=tx.position_before,
                position_after=tx.position_after,
                market_cap_at_trade=tx.market_cap_at_trade,
                volume_24h_at_trade=tx.volume_24h_at_trade,
                created_at=tx.created_at,
                executed_at=tx.executed_at,
                # Add bot name for display
                bot_name=bot.bot_name
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bots", response_model=List[TradingBotSummary])
async def get_bots(db: Session = Depends(get_db)):
    """Get all trading bots summary"""
    try:
        bots = db.query(TradingBot).all()
        bot_summaries = []
        
        for bot in bots:
            # Handle strategy type
            strategy_type = "Not configured"
            if bot.strategy:
                strategy_type = bot.strategy.strategy_type
            
            # Calculate profit percentage safely
            total_profit_percentage = Decimal('0')
            if bot.initial_balance_usd and bot.initial_balance_usd > 0 and bot.total_profit_usd:
                total_profit_percentage = (bot.total_profit_usd / bot.initial_balance_usd) * 100
            
            # Determine status based on is_active and is_configured
            if bot.is_active and bot.is_configured:
                status = 'running'
            elif bot.is_configured:
                status = 'configured'
            else:
                status = 'inactive'
            
            bot_summaries.append(TradingBotSummary(
                id=bot.id,
                bot_name=bot.bot_name,
                account_address=bot.account_address,
                chain=bot.chain,
                strategy_type=strategy_type,
                total_assets_usd=bot.total_assets_usd or Decimal('0'),
                total_profit_usd=bot.total_profit_usd or Decimal('0'),
                total_profit_percentage=total_profit_percentage,
                is_active=bot.is_active,
                is_configured=bot.is_configured,
                status=status,
                last_activity_at=bot.last_activity_at,
                owner_name=bot.owner.owner_name if bot.owner else None
            ))
        
        return bot_summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bots/details/{bot_id}", response_model=TradingBotResponse)
async def get_bot_details(bot_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific trading bot"""
    try:
        # Convert string ID to UUID
        try:
            bot_uuid = uuid.UUID(bot_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(ve)}")
        
        bot = db.query(TradingBot).filter(TradingBot.id == bot_uuid).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        return TradingBotResponse(
            id=bot.id,
            owner_id=bot.owner_id,
            strategy_id=bot.strategy_id,
            bot_name=bot.bot_name,
            account_address=bot.account_address,
            chain=bot.chain,
            initial_balance_usd=bot.initial_balance_usd,
            current_balance_usd=bot.current_balance_usd,
            total_assets_usd=bot.total_assets_usd,
            strategy_type=bot.strategy.strategy_type if bot.strategy else "Not configured",
            is_active=bot.is_active,
            is_configured=bot.is_configured,
            total_trades=bot.total_trades,
            profitable_trades=bot.profitable_trades,
            total_profit_usd=bot.total_profit_usd,
            max_drawdown_percentage=bot.max_drawdown_percentage,
            max_position_size=bot.strategy.max_position_size if bot.strategy else None,
            stop_loss_percentage=bot.strategy.stop_loss_percentage if bot.strategy else None,
            take_profit_percentage=bot.strategy.take_profit_percentage if bot.strategy else None,
            created_at=bot.created_at,
            updated_at=bot.updated_at,
            last_activity_at=bot.last_activity_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bots/positions/{bot_id}", response_model=List[PositionResponse])
async def get_bot_positions(bot_id: str, db: Session = Depends(get_db)):
    """Get current positions for a specific bot"""
    try:
        # Convert string ID to UUID
        try:
            bot_uuid = uuid.UUID(bot_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(ve)}")
        
        print(f"🔍 API: Getting positions for bot {bot_id}")
        positions = db.query(Position).filter(
            Position.bot_id == bot_uuid,
            Position.is_active == True
        ).all()
        
        print(f"📊 API: Found {len(positions)} active positions")
        
        result = []
        for pos in positions:
            # Get token info
            token = pos.token

            # get token metric
            token_metric = db.query(TokenMetric).filter(TokenMetric.token_id == token.id).first()

            result.append(PositionResponse(
                id=pos.id,
                token_symbol=token.symbol,
                token_name=token.name,
                quantity=pos.quantity,
                average_cost_usd=pos.average_cost_usd,
                total_cost_usd=pos.total_cost_usd,
                current_price_usd=token_metric.weighted_price_usd,
                current_value_usd=pos.current_value_usd,
                unrealized_pnl_usd=pos.unrealized_pnl_usd,
                unrealized_pnl_percentage=pos.unrealized_pnl_percentage,
                stop_loss_price=pos.stop_loss_price,
                take_profit_price=pos.take_profit_price,
                is_active=pos.is_active,
                created_at=pos.created_at,
                updated_at=pos.updated_at
            ))
        
        print(f"✅ API: Returning {len(result)} positions")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bots/transactions/{bot_id}", response_model=List[TransactionResponse])
async def get_bot_transactions(
    bot_id: str, 
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get transaction history for a specific bot"""
    try:
        # Convert string ID to UUID
        try:
            bot_uuid = uuid.UUID(bot_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(ve)}")
        
        transactions = db.query(Transaction).filter(
            Transaction.bot_id == bot_uuid
        ).order_by(Transaction.created_at.desc()).limit(limit).all()
        
        result = []
        for tx in transactions:
            token = tx.token
            result.append(TransactionResponse(
                id=tx.id,
                transaction_type=tx.transaction_type,
                status=tx.status,
                token_symbol=token.symbol,
                token_name=token.name,
                amount_usd=tx.amount_usd,
                token_amount=tx.token_amount,
                price_usd=tx.price_usd,
                gas_cost_usd=tx.gas_cost_usd,
                trading_fee_usd=tx.trading_fee_usd,
                total_cost_usd=tx.total_cost_usd,
                realized_pnl_usd=tx.realized_pnl_usd,
                realized_pnl_percentage=tx.realized_pnl_percentage,
                balance_before_usd=tx.balance_before_usd,
                balance_after_usd=tx.balance_after_usd,
                position_before=tx.position_before,
                position_after=tx.position_after,
                market_cap_at_trade=tx.market_cap_at_trade,
                volume_24h_at_trade=tx.volume_24h_at_trade,
                created_at=tx.created_at,
                executed_at=tx.executed_at
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bots/revenue/{bot_id}", response_model=List[RevenueSnapshotSchema])
async def get_bot_revenue(
    bot_id: str,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get revenue history for a specific bot"""
    try:
        # Convert string ID to UUID
        try:
            bot_uuid = uuid.UUID(bot_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(ve)}")
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        snapshots = db.query(RevenueSnapshot).filter(
            RevenueSnapshot.bot_id == bot_uuid,
            RevenueSnapshot.snapshot_time >= start_date
        ).order_by(RevenueSnapshot.snapshot_time.asc()).all()
        
        result = []
        for snapshot in snapshots:
            result.append(RevenueSnapshotSchema(
                id=snapshot.id,
                total_assets_usd=snapshot.total_assets_usd,
                available_balance_usd=snapshot.available_balance_usd,
                total_positions_value_usd=snapshot.total_positions_value_usd,
                total_profit_usd=snapshot.total_profit_usd,
                total_profit_percentage=snapshot.total_profit_percentage,
                daily_profit_usd=snapshot.daily_profit_usd,
                daily_profit_percentage=snapshot.daily_profit_percentage,
                total_trades=snapshot.total_trades,
                profitable_trades=snapshot.profitable_trades,
                win_rate=snapshot.win_rate,
                average_profit_per_trade=snapshot.average_profit_per_trade,
                max_drawdown_percentage=snapshot.max_drawdown_percentage,
                current_drawdown_percentage=snapshot.current_drawdown_percentage,
                active_positions_count=snapshot.active_positions_count,
                snapshot_type=snapshot.snapshot_type,
                created_at=snapshot.created_at
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bots/llm-decisions/{bot_id}", response_model=List[LLMDecisionResponse])
async def get_bot_llm_decisions(
    bot_id: str,
    limit: int = Query(50, ge=1, le=100),
    decision_type: Optional[str] = Query(None, description="Filter by decision type: sell_analysis, buy_analysis"),
    db: Session = Depends(get_db)
):
    """Get LLM decision history for a specific bot"""
    try:
        # Convert string ID to UUID
        try:
            bot_uuid = uuid.UUID(bot_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(ve)}")
        
        query = db.query(LLMDecision).filter(LLMDecision.bot_id == bot_uuid)
        
        if decision_type:
            query = query.filter(LLMDecision.decision_type == decision_type)
        
        decisions = query.order_by(LLMDecision.created_at.desc()).limit(limit).all()
        
        result = []
        for decision in decisions:
            # Get recommended token symbol if exists
            recommended_token_symbol = None
            if decision.recommended_token_id and decision.recommended_token:
                recommended_token_symbol = decision.recommended_token.symbol
            
            result.append(LLMDecisionResponse(
                id=decision.id,
                decision_type=decision.decision_type,
                decision_phase=decision.decision_phase,
                llm_response=decision.llm_response,
                reasoning=decision.reasoning,
                confidence_score=decision.confidence_score,
                recommended_action=decision.recommended_action,
                recommended_token_symbol=recommended_token_symbol,
                recommended_amount=decision.recommended_amount,
                recommended_percentage=decision.recommended_percentage,
                expected_return_percentage=decision.expected_return_percentage,
                risk_assessment=decision.risk_assessment,
                market_sentiment=decision.market_sentiment,
                was_executed=decision.was_executed,
                execution_reason=decision.execution_reason,
                created_at=decision.created_at,
                execution_time=decision.execution_time
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AIP DEX Trading Bot API",
        "timestamp": datetime.utcnow().isoformat()
    }

# ===== BOT MANAGEMENT ENDPOINTS =====

@router.post("/bots", response_model=ApiResponse)
async def create_bot(bot_data: TradingBotCreate, db: Session = Depends(get_db)):
    """Create a new trading bot"""
    try:
        # Note: Multiple bots can now use the same account_address
        # No need to check for duplicates since unique constraint was removed
        
        # Validate owner exists if provided
        if bot_data.owner_id:
            owner = db.query(BotOwner).filter(BotOwner.id == bot_data.owner_id).first()
            if not owner:
                raise HTTPException(status_code=404, detail="Owner not found")
        
        # Validate strategy exists if provided
        if bot_data.strategy_id:
            strategy = db.query(TradingStrategy).filter(TradingStrategy.id == bot_data.strategy_id).first()
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Create new bot
        new_bot = TradingBot(
            id=uuid.uuid4(),
            bot_name=bot_data.bot_name,
            account_address=bot_data.account_address,
            chain=bot_data.chain,
            initial_balance_usd=bot_data.initial_balance_usd,
            current_balance_usd=bot_data.initial_balance_usd,
            total_assets_usd=bot_data.initial_balance_usd,
            owner_id=bot_data.owner_id,
            strategy_id=bot_data.strategy_id,
            is_active=False,  # Default to inactive
            is_configured=bool(bot_data.owner_id and bot_data.strategy_id),
            total_trades=0,
            profitable_trades=0,
            total_profit_usd=0,
            max_drawdown_percentage=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_bot)
        db.commit()
        db.refresh(new_bot)
        
        return ApiResponse(
            success=True,
            message="Bot created successfully",
            data={"bot_id": str(new_bot.id)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # Handle database errors
        if "duplicate key value violates unique constraint" in str(e):
            # Handle other potential unique constraint violations
            raise HTTPException(
                status_code=409, 
                detail=f"Duplicate data detected: {str(e)}"
            )
        raise HTTPException(status_code=500, detail=f"Failed to create bot: {str(e)}")


@router.put("/bots/status/{bot_id}", response_model=ApiResponse)
async def update_bot_status(bot_id: str, status_data: dict, db: Session = Depends(get_db)):
    """Update bot status (active/inactive)"""
    try:
        # Convert string ID to UUID
        try:
            bot_uuid = uuid.UUID(bot_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(ve)}")
        
        # Find the bot
        bot = db.query(TradingBot).filter(TradingBot.id == bot_uuid).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Validate status data
        if "is_active" not in status_data:
            raise HTTPException(status_code=400, detail="is_active field is required")
        
        is_active = status_data["is_active"]
        if not isinstance(is_active, bool):
            raise HTTPException(status_code=400, detail="is_active must be a boolean")
        
        # Check if bot is configured before activating
        if is_active and not bot.is_configured:
            raise HTTPException(status_code=400, detail="Bot must be configured (have owner and strategy) before activation")
        
        # Update status
        bot.is_active = is_active
        bot.updated_at = datetime.utcnow()
        
        db.commit()
        
        status_text = "activated" if is_active else "deactivated"
        return ApiResponse(
            success=True,
            message=f"Bot {status_text} successfully",
            data={"bot_id": str(bot.id), "is_active": is_active}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update bot status: {str(e)}")


@router.post("/bots/configure/{bot_id}", dependencies=[Depends(validate_token)])
async def configure_bot(
    bot_id: str,
    request: dict,
    db: Session = Depends(get_db)
):
    """Configure bot with owner and strategy"""
    try:
        owner_id = request.get("owner_id")
        strategy_id = request.get("strategy_id")
        
        if not owner_id or not strategy_id:
            raise HTTPException(status_code=400, detail="Missing owner_id or strategy_id")
        
        # Convert string IDs to UUID objects
        try:
            bot_uuid = uuid.UUID(bot_id)
            owner_uuid = uuid.UUID(owner_id)
            strategy_uuid = uuid.UUID(strategy_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(ve)}")
        
        # Use trading service to configure bot
        configured_bot = await trading_service.configure_bot(db, bot_uuid, owner_uuid, strategy_uuid)
        
        if not configured_bot:
            raise HTTPException(status_code=500, detail="Failed to configure bot")
        
        return {
            "success": True,
            "message": "Bot configured successfully",
            "bot_id": str(bot_id),
            "owner_id": str(owner_id),
            "strategy_id": str(strategy_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/bots/update/{bot_id}", response_model=ApiResponse)
async def update_bot(bot_id: str, bot_data: TradingBotUpdate, db: Session = Depends(get_db)):
    """Update an existing trading bot"""
    try:
        # Convert string ID to UUID
        try:
            bot_uuid = uuid.UUID(bot_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(ve)}")
        
        # Find the bot
        bot = db.query(TradingBot).filter(TradingBot.id == bot_uuid).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Validate strategy exists if provided
        if bot_data.strategy_id:
            try:
                strategy_uuid = uuid.UUID(bot_data.strategy_id)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=f"Invalid strategy UUID format: {str(ve)}")
            
            strategy = db.query(TradingStrategy).filter(TradingStrategy.id == strategy_uuid).first()
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Update bot fields
        if bot_data.bot_name is not None:
            bot.bot_name = bot_data.bot_name
        if bot_data.strategy_id is not None:
            bot.strategy_id = strategy_uuid
            # Update is_configured status
            bot.is_configured = bool(bot.owner_id and strategy_uuid)
        if bot_data.is_active is not None:
            bot.is_active = bot_data.is_active
        
        bot.updated_at = datetime.utcnow()
        
        db.commit()
        
        return ApiResponse(
            success=True,
            message="Bot updated successfully",
            data={"bot_id": str(bot.id)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update bot: {str(e)}")
