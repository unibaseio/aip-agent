"""
Trading Service for AIP DEX Trading Bot - Clean Version
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from models.database import (
    TradingBot, Position, PositionHistory, Transaction, 
    LLMDecision, RevenueSnapshot, Token, TradingStrategy
)

class TradingService:
    """Trading service for managing trading bots and executing virtual trades"""
    
    def __init__(self):
        pass
    
    async def create_trading_bot(self, db: Session, config: Dict[str, Any]) -> Optional[TradingBot]:
        """Create a new trading bot with configuration"""
        try:
            # Validate configuration
            if not self._validate_bot_config(config):
                return None
            
            # Check if bot with same account already exists
            existing_bot = db.query(TradingBot).filter(
                TradingBot.account_address == config["account_address"]
            ).first()
            
            if existing_bot:
                print(f"Bot with account {config['account_address']} already exists")
                return existing_bot
            
            # Create bot with basic configuration
            bot = TradingBot(
                bot_name=config["bot_name"],
                account_address=config["account_address"],
                chain=config["chain"],
                
                # Financial config
                initial_balance_usd=Decimal(str(config["initial_balance_usd"])),
                current_balance_usd=Decimal(str(config["initial_balance_usd"])),
                total_assets_usd=Decimal(str(config["initial_balance_usd"])),
                
                # Basic status
                is_active=config.get("is_active", True),
                is_configured=False  # Will be set to True when strategy is assigned
            )
            
            db.add(bot)
            db.commit()
            db.refresh(bot)
            
            print(f"✓ Created trading bot: {bot.bot_name}")
            return bot
            
        except Exception as e:
            print(f"Error creating trading bot: {e}")
            db.rollback()
            return None
    
    async def configure_bot_strategy(self, db: Session, bot_id: str, strategy_id: str) -> bool:
        """Configure a bot with a strategy"""
        try:
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                print(f"Bot {bot_id} not found")
                return False
            
            strategy = db.query(TradingStrategy).filter(TradingStrategy.id == strategy_id).first()
            if not strategy:
                print(f"Strategy {strategy_id} not found")
                return False
            
            # Assign strategy to bot
            bot.strategy_id = strategy_id
            bot.is_configured = True
            bot.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            print(f"✓ Configured bot {bot.bot_name} with strategy {strategy.strategy_name}")
            return True
            
        except Exception as e:
            print(f"Error configuring bot strategy: {e}")
            db.rollback()
            return False
    
    def _validate_bot_config(self, config: Dict[str, Any]) -> bool:
        """Validate bot configuration"""
        required_fields = ["bot_name", "account_address", "chain", "initial_balance_usd"]
        
        for field in required_fields:
            if field not in config:
                print(f"Missing required field: {field}")
                return False
        
        if config["chain"] not in ["bsc", "solana"]:
            print(f"Invalid chain: {config['chain']}")
            return False
        
        # Strategy type is optional now, but validate if provided
        if "strategy_type" in config:
            valid_strategies = ["conservative", "moderate", "aggressive", "momentum", "mean_reversion"]
            if config["strategy_type"] not in valid_strategies:
                print(f"Invalid strategy type: {config['strategy_type']}")
                return False
        
        if float(config["initial_balance_usd"]) < 100:
            print("Initial balance must be at least $100")
            return False
        
        return True
    
    def _get_strategy_defaults(self, strategy_type: str) -> Dict[str, Any]:
        """Get default parameters for each strategy type"""
        strategies = {
            "conservative": {
                "max_position_size": 10.0,
                "stop_loss_percentage": 5.0,
                "take_profit_percentage": 15.0,
                "min_profit_threshold": 5.0,
                "max_daily_trades": 10,
                "llm_confidence_threshold": 0.8
            },
            "moderate": {
                "max_position_size": 20.0,
                "stop_loss_percentage": 10.0,
                "take_profit_percentage": 25.0,
                "min_profit_threshold": 3.0,
                "max_daily_trades": 15,
                "llm_confidence_threshold": 0.7
            },
            "aggressive": {
                "max_position_size": 40.0,
                "stop_loss_percentage": 15.0,
                "take_profit_percentage": 50.0,
                "min_profit_threshold": 1.0,
                "max_daily_trades": 25,
                "llm_confidence_threshold": 0.6
            }
        }
        
        return strategies.get(strategy_type, strategies["conservative"])
    
    async def get_bot_status(self, db: Session, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive bot status"""
        try:
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                return None
            
            # Get active positions
            positions = db.query(Position).filter(
                Position.bot_id == bot_id,
                Position.is_active == True
            ).all()
            
            return {
                "bot_info": {
                    "id": str(bot.id),
                    "name": bot.bot_name,
                    "account_address": bot.account_address,
                    "chain": bot.chain,
                    "strategy_type": bot.strategy.strategy_type if bot.strategy else "Not configured",
                    "is_active": bot.is_active
                },
                "financial_status": {
                    "initial_balance_usd": float(bot.initial_balance_usd),
                    "current_balance_usd": float(bot.current_balance_usd),
                    "total_assets_usd": float(bot.total_assets_usd),
                    "total_profit_usd": float(bot.total_profit_usd)
                },
                "trading_stats": {
                    "total_trades": bot.total_trades,
                    "profitable_trades": bot.profitable_trades
                },
                "positions": [
                    {
                        "token_symbol": pos.token.symbol if pos.token else "Unknown",
                        "quantity": float(pos.quantity),
                        "current_value_usd": float(pos.current_value_usd or 0)
                    } for pos in positions
                ]
            }
            
        except Exception as e:
            print(f"Error getting bot status: {e}")
            return None
    
    async def get_bot_positions(self, db: Session, bot_id: str) -> List[Dict[str, Any]]:
        """Get all active positions for a trading bot"""
        try:
            positions = db.query(Position).filter(
                Position.bot_id == bot_id,
                Position.is_active == True
            ).all()
            
            position_data = []
            for pos in positions:
                position_data.append({
                    "id": str(pos.id),
                    "token_id": str(pos.token_id),
                    "token_symbol": pos.token.symbol if pos.token else "Unknown",
                    "quantity": float(pos.quantity),
                    "average_cost_usd": float(pos.average_cost_usd),
                    "total_cost_usd": float(pos.total_cost_usd),
                    "current_price_usd": float(pos.current_price_usd or 0),
                    "current_value_usd": float(pos.current_value_usd or 0),
                    "unrealized_pnl_usd": float(pos.unrealized_pnl_usd or 0),
                    "unrealized_pnl_percentage": float(pos.unrealized_pnl_percentage or 0)
                })
            
            return position_data
            
        except Exception as e:
            print(f"Error getting bot positions: {e}")
            return []
    
    async def execute_buy_order(self, db: Session, bot_id: str, token_id: str, 
                               amount_usd: float, current_price: float) -> Optional[Transaction]:
        """Execute virtual buy order"""
        try:
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                return None
            
            # Calculate costs
            amount_usd_decimal = Decimal(str(amount_usd))
            price_decimal = Decimal(str(current_price))
            
            gas_cost_usd = Decimal("0.5")  # Simplified
            trading_fee_usd = amount_usd_decimal * (bot.trading_fee_percentage / 100)
            total_cost_usd = gas_cost_usd + trading_fee_usd
            
            # Calculate token quantity
            token_quantity = amount_usd_decimal / price_decimal

            print(f"token_quantity: {token_quantity}, price_decimal: {price_decimal}, amount_usd_decimal: {amount_usd_decimal}")
            
            # Check if sufficient balance
            total_required = amount_usd_decimal + total_cost_usd
            if bot.current_balance_usd < total_required:
                print(f"Insufficient balance: required ${total_required}, available ${bot.current_balance_usd}")
                return None
            
            # Create transaction record
            transaction = Transaction(
                bot_id=bot_id,
                token_id=token_id,
                transaction_type="buy",
                status="executed",
                amount_usd=amount_usd_decimal,
                token_amount=token_quantity,
                price_usd=price_decimal,
                gas_cost_usd=gas_cost_usd,
                trading_fee_usd=trading_fee_usd,
                total_cost_usd=total_cost_usd,
                balance_before_usd=bot.current_balance_usd,
                balance_after_usd=bot.current_balance_usd - total_required,
                executed_at=datetime.now(timezone.utc)
            )
            
            # Update bot balance
            bot.current_balance_usd -= total_required
            bot.total_trades += 1
            bot.last_activity_at = datetime.now(timezone.utc)
            
            # Create or update position
            position = await self._create_or_update_position_buy(
                db, bot_id, token_id, token_quantity, price_decimal, total_cost_usd
            )
            
            if position:
                transaction.position_id = position.id
            
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            
            print(f"✓ Executed buy order: {amount_usd} USD for {float(token_quantity)} tokens")
            return transaction
            
        except Exception as e:
            print(f"Error executing buy order: {e}")
            db.rollback()
            return None
    
    async def execute_sell_order(self, db: Session, bot_id: str, position_id: str, 
                                sell_percentage: float, current_price: float) -> Optional[Transaction]:
        """Execute virtual sell order"""
        try:
            position = db.query(Position).filter(
                Position.id == position_id,
                Position.bot_id == bot_id,
                Position.is_active == True
            ).first()
            
            if not position:
                return None
            
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                return None
            
            # Calculate sell details
            sell_quantity = position.quantity * Decimal(str(sell_percentage / 100))
            sell_amount_usd = sell_quantity * Decimal(str(current_price))
            
            # Calculate costs
            gas_cost_usd = Decimal("0.5")  # Simplified
            trading_fee_usd = sell_amount_usd * (bot.trading_fee_percentage / 100)
            total_cost_usd = gas_cost_usd + trading_fee_usd
            
            # Calculate net proceeds
            net_proceeds_usd = sell_amount_usd - total_cost_usd
            
            # Calculate realized P&L
            cost_basis = sell_quantity * position.average_cost_usd
            realized_pnl_usd = net_proceeds_usd - cost_basis
            realized_pnl_percentage = (realized_pnl_usd / cost_basis) * 100 if cost_basis > 0 else 0
            
            # Create transaction record
            transaction = Transaction(
                bot_id=bot_id,
                position_id=position_id,
                token_id=position.token_id,
                transaction_type="sell",
                status="executed",
                token_amount=sell_quantity,
                price_usd=Decimal(str(current_price)),
                gas_cost_usd=gas_cost_usd,
                trading_fee_usd=trading_fee_usd,
                total_cost_usd=total_cost_usd,
                realized_pnl_usd=realized_pnl_usd,
                realized_pnl_percentage=realized_pnl_percentage,
                balance_before_usd=bot.current_balance_usd,
                balance_after_usd=bot.current_balance_usd + net_proceeds_usd,
                executed_at=datetime.now(timezone.utc)
            )
            
            # Update position
            remaining_quantity = position.quantity - sell_quantity
            if remaining_quantity <= 0:
                # Close position completely
                position.quantity = Decimal("0")
                position.average_cost_usd = Decimal("0")
                position.total_cost_usd = Decimal("0")
                position.is_active = False
                position.closed_at = datetime.now(timezone.utc)
            else:
                # Update remaining position
                new_total_cost = position.total_cost_usd - cost_basis + total_cost_usd
                position.quantity = remaining_quantity
                position.average_cost_usd = new_total_cost / remaining_quantity
                position.total_cost_usd = new_total_cost
            
            position.updated_at = datetime.now(timezone.utc)
            
            # Update bot financials
            bot.current_balance_usd += net_proceeds_usd
            bot.total_trades += 1
            bot.total_profit_usd += realized_pnl_usd
            if realized_pnl_usd > 0:
                bot.profitable_trades += 1
            bot.last_activity_at = datetime.now(timezone.utc)
            
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            
            print(f"✓ Executed sell order: {sell_percentage}% for ${float(net_proceeds_usd)} proceeds")
            return transaction
            
        except Exception as e:
            print(f"Error executing sell order: {e}")
            db.rollback()
            return None
    
    async def _create_or_update_position_buy(self, db: Session, bot_id: str, token_id: str, 
                                           quantity: Decimal, price: Decimal, 
                                           cost: Decimal) -> Optional[Position]:
        """Create new position or update existing position for buy order"""
        try:
            # Check if position already exists
            existing_position = db.query(Position).filter(
                Position.bot_id == bot_id,
                Position.token_id == token_id,
                Position.is_active == True
            ).first()
            
            if existing_position:
                # Update existing position with new average cost
                old_quantity = existing_position.quantity
                old_cost = existing_position.total_cost_usd
                
                new_quantity = old_quantity + quantity
                new_total_cost = old_cost + cost
                new_average_cost = new_total_cost / new_quantity
                
                existing_position.quantity = new_quantity
                existing_position.average_cost_usd = new_average_cost
                existing_position.total_cost_usd = new_total_cost
                existing_position.updated_at = datetime.now(timezone.utc)

                # save to db
                
                return existing_position
            else:
                # Create new position
                position = Position(
                    bot_id=bot_id,
                    token_id=token_id,
                    quantity=quantity,
                    average_cost_usd=price,
                    total_cost_usd=cost,
                    current_price_usd=price,
                    current_value_usd=quantity * price,
                    unrealized_pnl_usd=Decimal("0"),
                    unrealized_pnl_percentage=Decimal("0")
                )
                
                db.add(position)
                db.flush()  # To get the ID
                return position
                
        except Exception as e:
            print(f"Error creating/updating position: {e}")
            return None 