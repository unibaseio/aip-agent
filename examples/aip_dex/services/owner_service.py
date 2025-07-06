"""
Owner and Strategy Management Service for AIP DEX Trading Bot
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from models.database import BotOwner, TradingStrategy, TradingBot
from api.schemas import BotOwnerCreate, BotOwnerUpdate, TradingStrategyCreate, TradingStrategyUpdate

class OwnerService:
    """Service for managing bot owners and trading strategies"""
    
    def __init__(self):
        pass
    
    # ===== BOT OWNER MANAGEMENT =====
    
    async def create_bot_owner(self, db: Session, owner_data: BotOwnerCreate) -> Optional[BotOwner]:
        """Create a new bot owner"""
        try:
            # Check if owner with same email or wallet already exists
            existing_owner = db.query(BotOwner).filter(
                (BotOwner.email == owner_data.email) | 
                (BotOwner.wallet_address == owner_data.wallet_address)
            ).first()
            
            if existing_owner:
                print(f"Owner with email {owner_data.email} or wallet {owner_data.wallet_address} already exists")
                return existing_owner
            
            owner = BotOwner(
                owner_name=owner_data.owner_name,
                email=owner_data.email,
                wallet_address=owner_data.wallet_address,
                phone=owner_data.phone,
                subscription_tier=owner_data.subscription_tier,
                max_bots_allowed=owner_data.max_bots_allowed
            )
            
            db.add(owner)
            db.commit()
            db.refresh(owner)
            
            print(f"✓ Created bot owner: {owner.owner_name}")
            return owner
            
        except Exception as e:
            print(f"Error creating bot owner: {e}")
            db.rollback()
            return None
    
    async def get_bot_owner(self, db: Session, owner_id: uuid.UUID) -> Optional[BotOwner]:
        """Get bot owner by ID"""
        return db.query(BotOwner).filter(BotOwner.id == owner_id).first()
    
    async def get_bot_owner_by_email(self, db: Session, email: str) -> Optional[BotOwner]:
        """Get bot owner by email"""
        return db.query(BotOwner).filter(BotOwner.email == email).first()
    
    async def get_bot_owner_by_wallet(self, db: Session, wallet_address: str) -> Optional[BotOwner]:
        """Get bot owner by wallet address"""
        return db.query(BotOwner).filter(BotOwner.wallet_address == wallet_address).first()
    
    async def update_bot_owner(self, db: Session, owner_id: uuid.UUID, update_data: BotOwnerUpdate) -> Optional[BotOwner]:
        """Update bot owner"""
        try:
            owner = await self.get_bot_owner(db, owner_id)
            if not owner:
                return None
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(owner, field, value)
            
            owner.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(owner)
            
            print(f"✓ Updated bot owner: {owner.owner_name}")
            return owner
            
        except Exception as e:
            print(f"Error updating bot owner: {e}")
            db.rollback()
            return None
    
    async def list_bot_owners(self, db: Session, skip: int = 0, limit: int = 100) -> List[BotOwner]:
        """List all bot owners"""
        return db.query(BotOwner).offset(skip).limit(limit).all()
    
    async def get_owner_bots(self, db: Session, owner_id: uuid.UUID) -> List[TradingBot]:
        """Get all bots owned by an owner"""
        return db.query(TradingBot).filter(TradingBot.owner_id == owner_id).all()
    
    # ===== TRADING STRATEGY MANAGEMENT =====
    
    async def create_trading_strategy(self, db: Session, owner_id: uuid.UUID, strategy_data: TradingStrategyCreate) -> Optional[TradingStrategy]:
        """Create a new trading strategy"""
        try:
            # Verify owner exists
            owner = await self.get_bot_owner(db, owner_id)
            if not owner:
                print(f"Owner with ID {owner_id} not found")
                return None
            
            # Check if strategy with same name already exists for this owner
            existing_strategy = db.query(TradingStrategy).filter(
                and_(
                    TradingStrategy.owner_id == owner_id,
                    TradingStrategy.strategy_name == strategy_data.strategy_name
                )
            ).first()
            
            if existing_strategy:
                print(f"Strategy with name {strategy_data.strategy_name} already exists for owner {owner_id}")
                return existing_strategy
            
            strategy = TradingStrategy(
                owner_id=owner_id,
                strategy_name=strategy_data.strategy_name,
                strategy_description=strategy_data.strategy_description,
                strategy_type=strategy_data.strategy_type,
                risk_level=strategy_data.risk_level,
                
                # 数值参数设置
                max_position_size=Decimal(str(strategy_data.max_position_size)),
                stop_loss_percentage=Decimal(str(strategy_data.stop_loss_percentage)),
                take_profit_percentage=Decimal(str(strategy_data.take_profit_percentage)),
                min_profit_threshold=Decimal(str(strategy_data.min_profit_threshold)),
                max_daily_trades=strategy_data.max_daily_trades,
                llm_confidence_threshold=Decimal(str(strategy_data.llm_confidence_threshold)),
                
                # 交易费用设置
                gas_fee_native=Decimal(str(strategy_data.gas_fee_native)),
                trading_fee_percentage=Decimal(str(strategy_data.trading_fee_percentage)),
                slippage_tolerance=Decimal(str(strategy_data.slippage_tolerance)),
                
                # 运行控制参数
                min_trade_amount_usd=Decimal(str(strategy_data.min_trade_amount_usd)),
                polling_interval_hours=Decimal(str(strategy_data.polling_interval_hours)),
                
                # 功能开关
                enable_stop_loss=strategy_data.enable_stop_loss,
                enable_take_profit=strategy_data.enable_take_profit,
                
                # 策略描述性配置
                buy_strategy_description=strategy_data.buy_strategy_description,
                sell_strategy_description=strategy_data.sell_strategy_description,
                filter_strategy_description=strategy_data.filter_strategy_description,
                summary_strategy_description=strategy_data.summary_strategy_description,
                
                # 状态
                is_public=strategy_data.is_public
            )
            
            db.add(strategy)
            db.commit()
            db.refresh(strategy)
            
            print(f"✓ Created trading strategy: {strategy.strategy_name}")
            return strategy
            
        except Exception as e:
            print(f"Error creating trading strategy: {e}")
            db.rollback()
            return None
    
    async def get_trading_strategy(self, db: Session, strategy_id: uuid.UUID) -> Optional[TradingStrategy]:
        """Get trading strategy by ID"""
        return db.query(TradingStrategy).filter(TradingStrategy.id == strategy_id).first()
    
    async def update_trading_strategy(self, db: Session, strategy_id: uuid.UUID, update_data: TradingStrategyUpdate) -> Optional[TradingStrategy]:
        """Update trading strategy"""
        try:
            strategy = await self.get_trading_strategy(db, strategy_id)
            if not strategy:
                return None
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                if isinstance(value, (int, float)) and field in [
                    'max_position_size', 'stop_loss_percentage', 'take_profit_percentage',
                    'min_profit_threshold', 'llm_confidence_threshold', 'gas_fee_native',
                    'trading_fee_percentage', 'slippage_tolerance', 'min_trade_amount_usd',
                    'polling_interval_hours'
                ]:
                    setattr(strategy, field, Decimal(str(value)))
                else:
                    setattr(strategy, field, value)
            
            strategy.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(strategy)
            
            print(f"✓ Updated trading strategy: {strategy.strategy_name}")
            return strategy
            
        except Exception as e:
            print(f"Error updating trading strategy: {e}")
            db.rollback()
            return None
    
    async def list_owner_strategies(self, db: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[TradingStrategy]:
        """List all strategies for an owner"""
        return db.query(TradingStrategy).filter(
            TradingStrategy.owner_id == owner_id
        ).offset(skip).limit(limit).all()
    
    async def list_public_strategies(self, db: Session, skip: int = 0, limit: int = 100) -> List[TradingStrategy]:
        """List all public strategies"""
        return db.query(TradingStrategy).filter(
            and_(
                TradingStrategy.is_public == True,
                TradingStrategy.is_active == True
            )
        ).offset(skip).limit(limit).all()
    
    async def get_default_strategies(self, db: Session) -> List[TradingStrategy]:
        """Get all default strategies"""
        return db.query(TradingStrategy).filter(
            TradingStrategy.is_public == True
        ).all()
    
    async def delete_trading_strategy(self, db: Session, strategy_id: uuid.UUID) -> bool:
        """Delete trading strategy (soft delete by setting is_active=False)"""
        try:
            strategy = await self.get_trading_strategy(db, strategy_id)
            if not strategy:
                return False
            
            # Check if strategy is being used by any bots
            bots_using_strategy = db.query(TradingBot).filter(
                TradingBot.strategy_id == strategy_id
            ).count()
            
            if bots_using_strategy > 0:
                print(f"Cannot delete strategy {strategy_id}: {bots_using_strategy} bots are using it")
                return False
            
            strategy.is_active = False
            strategy.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            print(f"✓ Deleted trading strategy: {strategy.strategy_name}")
            return True
            
        except Exception as e:
            print(f"Error deleting trading strategy: {e}")
            db.rollback()
            return False
    
    # ===== STRATEGY DEFAULTS =====
    
    def get_strategy_defaults(self, strategy_type: str) -> Dict[str, Any]:
        """Get default parameters for each strategy type"""
        strategies = {
            "conservative": {
                "max_position_size": 10.0,
                "stop_loss_percentage": 5.0,
                "take_profit_percentage": 15.0,
                "min_profit_threshold": 5.0,
                "max_daily_trades": 10,
                "llm_confidence_threshold": 0.8,
                "risk_level": "low",
                "buy_strategy_description": "Conservative buying strategy focusing on established tokens with strong fundamentals and low volatility. Prefer tokens with high market cap, stable volume, and positive holder growth.",
                "sell_strategy_description": "Conservative selling strategy with tight stop-loss and moderate take-profit targets. Sell when technical indicators show bearish signals or when profit targets are reached.",
                "filter_strategy_description": "Filter for tokens with market cap > $10M, volume > $100K, positive holder growth, and low volatility. Avoid tokens with extreme price movements or suspicious trading patterns.",
                "summary_strategy_description": "Conservative strategy prioritizing capital preservation over aggressive gains. Suitable for risk-averse investors seeking steady, moderate returns."
            },
            "moderate": {
                "max_position_size": 20.0,
                "stop_loss_percentage": 10.0,
                "take_profit_percentage": 25.0,
                "min_profit_threshold": 3.0,
                "max_daily_trades": 15,
                "llm_confidence_threshold": 0.7,
                "risk_level": "medium",
                "buy_strategy_description": "Moderate buying strategy balancing growth potential with risk management. Target tokens with good fundamentals, reasonable volatility, and positive momentum indicators.",
                "sell_strategy_description": "Moderate selling strategy with balanced stop-loss and take-profit levels. Sell on technical breakdowns, trend reversals, or when profit targets are achieved.",
                "filter_strategy_description": "Filter for tokens with market cap > $5M, volume > $50K, positive price momentum, and reasonable volatility. Avoid extremely volatile or illiquid tokens.",
                "summary_strategy_description": "Moderate strategy seeking balanced risk-reward ratio. Suitable for investors comfortable with moderate risk for potentially higher returns."
            },
            "aggressive": {
                "max_position_size": 40.0,
                "stop_loss_percentage": 15.0,
                "take_profit_percentage": 50.0,
                "min_profit_threshold": 1.0,
                "max_daily_trades": 25,
                "llm_confidence_threshold": 0.6,
                "risk_level": "high",
                "buy_strategy_description": "Aggressive buying strategy targeting high-growth potential tokens. Focus on tokens with strong momentum, high volume, and breakout patterns.",
                "sell_strategy_description": "Aggressive selling strategy with wider stop-loss and higher take-profit targets. Hold positions longer to capture larger moves, sell on major trend reversals.",
                "filter_strategy_description": "Filter for tokens with strong momentum, high volume, and breakout potential. Accept higher volatility and risk for potential high returns.",
                "summary_strategy_description": "Aggressive strategy prioritizing maximum growth potential over risk management. Suitable for experienced investors comfortable with high volatility and risk."
            }
        }
        
        return strategies.get(strategy_type, strategies["conservative"])
    
    async def create_default_strategies(self, db: Session, owner_id: uuid.UUID) -> List[TradingStrategy]:
        """Create default strategies for a new owner"""
        strategies = []
        default_types = ["conservative", "moderate", "aggressive"]
        
        for strategy_type in default_types:
            defaults = self.get_strategy_defaults(strategy_type)
            
            strategy_data = TradingStrategyCreate(
                strategy_name=f"Default {strategy_type.title()} Strategy",
                strategy_description=defaults["summary_strategy_description"],
                strategy_type=strategy_type,
                risk_level=defaults["risk_level"],
                max_position_size=Decimal(str(defaults["max_position_size"])),
                stop_loss_percentage=Decimal(str(defaults["stop_loss_percentage"])),
                take_profit_percentage=Decimal(str(defaults["take_profit_percentage"])),
                min_profit_threshold=Decimal(str(defaults["min_profit_threshold"])),
                max_daily_trades=defaults["max_daily_trades"],
                llm_confidence_threshold=Decimal(str(defaults["llm_confidence_threshold"])),
                buy_strategy_description=defaults["buy_strategy_description"],
                sell_strategy_description=defaults["sell_strategy_description"],
                filter_strategy_description=defaults["filter_strategy_description"],
                summary_strategy_description=defaults["summary_strategy_description"]
            )
            
            strategy = await self.create_trading_strategy(db, owner_id, strategy_data)
            if strategy:
                strategies.append(strategy)
        
        return strategies 