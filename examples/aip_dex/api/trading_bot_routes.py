from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from models.database import TokenMetric, get_db, TradingBot, Position, Transaction, RevenueSnapshot, LLMDecision
from api.schemas import (
    TradingBotResponse, TradingBotSummary, PositionResponse, 
    TransactionResponse, RevenueSnapshot as RevenueSnapshotSchema,
    LLMDecisionResponse, SystemStatus, PaginatedResponse
)

router = APIRouter(prefix="/api", tags=["trading-bots"])

@router.get("/bots", response_model=List[TradingBotSummary])
async def get_bots(db: Session = Depends(get_db)):
    """Get all trading bots summary"""
    try:
        bots = db.query(TradingBot).all()
        return [
            TradingBotSummary(
                id=bot.id,
                bot_name=bot.bot_name,
                account_address=bot.account_address,
                chain=bot.chain,
                strategy_type=bot.strategy_type,
                total_assets_usd=bot.total_assets_usd,
                total_profit_usd=bot.total_profit_usd,
                total_profit_percentage=bot.total_profit_usd / bot.initial_balance_usd * 100 if bot.initial_balance_usd > 0 else 0,
                is_active=bot.is_active,
                last_activity_at=bot.last_activity_at
            )
            for bot in bots
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bots/{bot_id}", response_model=TradingBotResponse)
async def get_bot_details(bot_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific trading bot"""
    try:
        bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        return TradingBotResponse(
            id=bot.id,
            bot_name=bot.bot_name,
            account_address=bot.account_address,
            chain=bot.chain,
            initial_balance_usd=bot.initial_balance_usd,
            current_balance_usd=bot.current_balance_usd,
            total_assets_usd=bot.total_assets_usd,
            strategy_type=bot.strategy_type,
            max_position_size=bot.max_position_size,
            stop_loss_percentage=bot.stop_loss_percentage,
            take_profit_percentage=bot.take_profit_percentage,
            min_profit_threshold=bot.min_profit_threshold,
            min_trade_amount_usd=bot.min_trade_amount_usd,
            max_daily_trades=bot.max_daily_trades,
            polling_interval_hours=bot.polling_interval_hours,
            llm_confidence_threshold=bot.llm_confidence_threshold,
            is_active=bot.is_active,
            enable_stop_loss=bot.enable_stop_loss,
            enable_take_profit=bot.enable_take_profit,
            total_trades=bot.total_trades,
            profitable_trades=bot.profitable_trades,
            total_profit_usd=bot.total_profit_usd,
            max_drawdown_percentage=bot.max_drawdown_percentage,
            created_at=bot.created_at,
            updated_at=bot.updated_at,
            last_activity_at=bot.last_activity_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bots/{bot_id}/positions", response_model=List[PositionResponse])
async def get_bot_positions(bot_id: str, db: Session = Depends(get_db)):
    """Get current positions for a specific bot"""
    try:
        print(f"🔍 API: Getting positions for bot {bot_id}")
        positions = db.query(Position).filter(
            Position.bot_id == bot_id,
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

@router.get("/bots/{bot_id}/transactions", response_model=List[TransactionResponse])
async def get_bot_transactions(
    bot_id: str, 
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get transaction history for a specific bot"""
    try:
        transactions = db.query(Transaction).filter(
            Transaction.bot_id == bot_id
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

@router.get("/bots/{bot_id}/revenue", response_model=List[RevenueSnapshotSchema])
async def get_bot_revenue(
    bot_id: str,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get revenue history for a specific bot"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        snapshots = db.query(RevenueSnapshot).filter(
            RevenueSnapshot.bot_id == bot_id,
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

@router.get("/transactions/recent", response_model=List[TransactionResponse])
async def get_recent_transactions(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get recent transactions across all bots"""
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
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

@router.get("/bots/{bot_id}/llm-decisions", response_model=List[LLMDecisionResponse])
async def get_bot_llm_decisions(
    bot_id: str,
    limit: int = Query(50, ge=1, le=100),
    decision_type: Optional[str] = Query(None, description="Filter by decision type: sell_analysis, buy_analysis"),
    db: Session = Depends(get_db)
):
    """Get LLM decision history for a specific bot"""
    try:
        query = db.query(LLMDecision).filter(LLMDecision.bot_id == bot_id)
        
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

@router.get("/system/overview", response_model=SystemStatus)
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

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AIP DEX Trading Bot API",
        "timestamp": datetime.utcnow().isoformat()
    } 