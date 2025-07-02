"""
Trading Service for AIP DEX Trading Bot

This service handles all trading-related operations including:
- Bot management and configuration
- Position management and cost calculations
- Virtual trade execution
- Revenue tracking and snapshots
- Risk management and validation
"""

from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import uuid

from models.database import (
    TradingBot, Position, PositionHistory, Transaction, 
    LLMDecision, RevenueSnapshot, Token, get_db
)
from data_aggregator.dex_screener import DexScreenerProvider

class TradingService:
    """Trading service for managing trading bots and executing virtual trades"""
    
    def __init__(self):
        self.dex_screener = DexScreenerProvider()
        self._native_token_prices = {}  # Cache for native token prices
        self._price_cache_time = {}     # Cache timestamp for price freshness
        self._gas_fee_native = 0.00003 # bnb gas fee 0.00003 bnb
        self._gas_cost_usd = 0.5
        self._trading_fee_percentage = 0.1 # 0.1% trading fee
    
    async def get_native_token_price(self, chain: str) -> Optional[Decimal]:
        """
        Get current native token price (BNB for BSC, SOL for Solana)
        
        Args:
            chain: Blockchain chain (bsc, solana)
            
        Returns:
            Native token price in USD or None if failed
        """
        try:
            # Check cache first (cache for 5 minutes)
            cache_key = f"{chain}_native_price"
            current_time = datetime.now(timezone.utc)
            
            if (cache_key in self._native_token_prices and 
                cache_key in self._price_cache_time and
                (current_time - self._price_cache_time[cache_key]).total_seconds() < 300):  # 5 minutes
                return self._native_token_prices[cache_key]
            
            # Define native token addresses and symbols
            native_tokens = {
                "bsc": {
                    "address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
                    "symbol": "WBNB"
                },
                "solana": {
                    "address": "So11111111111111111111111111111111111111112",  # Wrapped SOL
                    "symbol": "SOL"
                }
            }
            
            if chain not in native_tokens:
                print(f"Unsupported chain for native token price: {chain}")
                return None
            
            token_info = native_tokens[chain]
            
            # Try to get price from DexScreener
            try:
                result = await self.dex_screener.get_token_pools_by_address(
                    chain, token_info["address"], limit=1
                )
                
                if result and result.get("pools"):
                    pool_data = result["pools"][0]
                    price_usd = pool_data.get("price_usd", 0)
                    
                    if price_usd > 0:
                        # Cache the price
                        self._native_token_prices[cache_key] = Decimal(str(price_usd))
                        self._price_cache_time[cache_key] = current_time
                        
                        print(f"✅ Updated {chain.upper()} native token price: ${price_usd:.4f}")
                        return self._native_token_prices[cache_key]
                
            except Exception as e:
                print(f"Error fetching {chain} native token price from DexScreener: {e}")
            
            # Fallback: try to get from database if we have WBNB/SOL token
            try:
                from services.token_service import TokenService
                token_service = TokenService()
                
                native_token = await token_service.get_or_create_token(
                    db=None,  # We'll handle DB session separately
                    symbol=token_info["symbol"],
                    contract_address=token_info["address"],
                    chain=chain,
                    name=f"Wrapped {chain.upper()}"
                )
                
                if native_token:
                    # Get latest metrics from database
                    from models.database import TokenMetric
                    db = next(get_db())
                    try:
                        latest_metric = db.query(TokenMetric).filter(
                            TokenMetric.token_id == native_token.id
                        ).order_by(TokenMetric.created_at.desc()).first()
                        
                        if latest_metric and latest_metric.weighted_price_usd:
                            price_usd = float(latest_metric.weighted_price_usd)
                            
                            # Cache the price
                            self._native_token_prices[cache_key] = Decimal(str(price_usd))
                            self._price_cache_time[cache_key] = current_time
                            
                            print(f"✅ Retrieved {chain.upper()} native token price from DB: ${price_usd:.4f}")
                            return self._native_token_prices[cache_key]
                    finally:
                        db.close()
                        
            except Exception as e:
                print(f"Error getting {chain} native token price from database: {e}")
            
            # Return cached price if available (even if stale)
            if cache_key in self._native_token_prices:
                print(f"⚠️ Using cached {chain.upper()} native token price: ${self._native_token_prices[cache_key]:.4f}")
                return self._native_token_prices[cache_key]
            
            # Final fallback: use default prices
            default_prices = {
                "bsc": Decimal("300.0"),    # Default BNB price
                "solana": Decimal("100.0")  # Default SOL price
            }
            
            fallback_price = default_prices.get(chain, Decimal("100.0"))
            print(f"⚠️ Using fallback {chain.upper()} native token price: ${fallback_price:.4f}")
            return fallback_price
            
        except Exception as e:
            print(f"Error in get_native_token_price for {chain}: {e}")
            return None
    
    async def calculate_gas_cost_usd(self, chain: str) -> float:
        """
        Calculate gas cost in USD using current native token price
        
        Args:
            chain: Blockchain chain
            gas_fee_native: Gas fee in native token units (float)
            
        Returns:
            Gas cost in USD (float)
        """
        try:
            from decimal import Decimal
            native_price = await self.get_native_token_price(chain)
            if native_price:
                gas_cost_usd = float(self._gas_fee_native) * float(native_price)
                self._gas_cost_usd = gas_cost_usd
                return gas_cost_usd
            else:
                # Fallback calculation with estimated price
                estimated_prices = {
                    "bsc": 300.0,
                    "solana": 100.0
                }
                estimated_price = estimated_prices.get(chain, 100.0)
                return float(self._gas_fee_native) * estimated_price
                
        except Exception as e:
            print(f"Error calculating gas cost: {e}")
            # Return a reasonable default
            return 0.5
    
    # ===== BOT MANAGEMENT =====
    
    async def create_trading_bot(self, db: Session, config: Dict[str, Any]) -> Optional[TradingBot]:
        """Create a new trading bot with configuration"""
        try:
            # Validate configuration
            if not self._validate_bot_config(config):
                return None
            
            # Check if bot with same account already exists (account_address is unique)
            existing_bot = db.query(TradingBot).filter(
                TradingBot.account_address == config["account_address"],
                TradingBot.chain == config["chain"],
            ).first()
            
            if existing_bot:
                print(f"✅ Found existing bot with account {config['account_address']}: {existing_bot.bot_name}")
                print(f"   Chain: {existing_bot.chain}, Strategy: {existing_bot.strategy_type}")
                print(f"   Current Balance: ${float(existing_bot.current_balance_usd):,.2f}")
                self._gas_fee_native = float(existing_bot.gas_fee_native)
                self._trading_fee_percentage = float(existing_bot.trading_fee_percentage)
                return existing_bot
            
            # Create bot with strategy defaults
            strategy_params = self._get_strategy_defaults(config.get("strategy_type", "conservative"))
            
            self._gas_fee_native = float(config.get("gas_fee_native", 0.00003))
            self._trading_fee_percentage = float(config.get("trading_fee_percentage", 0.1))
            
            bot = TradingBot(
                bot_name=config["bot_name"],
                account_address=config["account_address"],
                chain=config["chain"],
                
                # Financial config
                initial_balance_usd=Decimal(str(config["initial_balance_usd"])),
                current_balance_usd=Decimal(str(config["initial_balance_usd"])),
                total_assets_usd=Decimal(str(config["initial_balance_usd"])),
                
                # Trading fees
                gas_fee_native=Decimal(str(config.get("gas_fee_native", 0.00003))),
                trading_fee_percentage=Decimal(str(config.get("trading_fee_percentage", 0.1))),
                slippage_tolerance=Decimal(str(config.get("slippage_tolerance", 1.0))),
                
                # Strategy config
                strategy_type=config["strategy_type"],
                max_position_size=Decimal(str(config.get("max_position_size", strategy_params["max_position_size"]))),
                stop_loss_percentage=Decimal(str(config.get("stop_loss_percentage", strategy_params["stop_loss_percentage"]))),
                take_profit_percentage=Decimal(str(config.get("take_profit_percentage", strategy_params["take_profit_percentage"]))),
                min_profit_threshold=Decimal(str(config.get("min_profit_threshold", strategy_params["min_profit_threshold"]))),
                
                # Runtime config
                min_trade_amount_usd=Decimal(str(config.get("min_trade_amount_usd", 10.0))),
                max_daily_trades=config.get("max_daily_trades", strategy_params["max_daily_trades"]),
                polling_interval_hours=config.get("polling_interval_hours", 1),
                llm_confidence_threshold=Decimal(str(config.get("llm_confidence_threshold", strategy_params["llm_confidence_threshold"]))),
                
                # Feature flags
                enable_stop_loss=config.get("enable_stop_loss", True),
                enable_take_profit=config.get("enable_take_profit", True),
                is_active=config.get("is_active", True)
            )
            
            db.add(bot)
            db.commit()
            db.refresh(bot)
            
            # Create initial revenue snapshot
            await self._create_revenue_snapshot(db, bot.id, "initial")
            
            print(f"✓ Created trading bot: {bot.bot_name} with ${bot.initial_balance_usd} initial balance")
            return bot
            
        except Exception as e:
            print(f"❌ Error creating trading bot: {e}")
            if "duplicate key value violates unique constraint" in str(e):
                print(f"   💡 This account address is already in use: {config.get('account_address', 'Unknown')}")
                print(f"   💡 Try using a different account address or check existing bots")
            db.rollback()
            return None
    
    def _validate_bot_config(self, config: Dict[str, Any]) -> bool:
        """Validate bot configuration"""
        required_fields = ["bot_name", "account_address", "chain", "initial_balance_usd", "strategy_type"]
        
        for field in required_fields:
            if field not in config:
                print(f"Missing required field: {field}")
                return False
        
        # Validate chain
        if config["chain"] not in ["bsc", "solana"]:
            print(f"Invalid chain: {config['chain']}")
            return False
        
        # Validate strategy type
        valid_strategies = ["conservative", "moderate", "aggressive", "momentum", "mean_reversion", "user_defined"]
        if config["strategy_type"] not in valid_strategies:
            print(f"Invalid strategy type: {config['strategy_type']}")
            return False
        
        # Validate balance
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
            },
            "momentum": {
                "max_position_size": 30.0,
                "stop_loss_percentage": 12.0,
                "take_profit_percentage": 35.0,
                "min_profit_threshold": 2.0,
                "max_daily_trades": 20,
                "llm_confidence_threshold": 0.65
            },
            "mean_reversion": {
                "max_position_size": 25.0,
                "stop_loss_percentage": 8.0,
                "take_profit_percentage": 20.0,
                "min_profit_threshold": 4.0,
                "max_daily_trades": 12,
                "llm_confidence_threshold": 0.75
            }
        }
        
        return strategies.get(strategy_type, strategies["conservative"])
    
    # ===== BOT MANAGEMENT =====
    
    async def get_bot_status(self, db: Session, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive bot status"""
        try:
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                return None
            
            # Get active positions with full details
            positions = db.query(Position).filter(
                Position.bot_id == bot_id,
                Position.is_active == True
            ).all()
            
            # Update current values for all positions
            for pos in positions:
                await self._update_position_current_value(db, pos)
            
            # Recalculate and update total_assets_usd
            total_position_value = self._calculate_total_position_value(db, bot_id)
            bot.total_assets_usd = bot.current_balance_usd + total_position_value
            db.commit()
            
            # Get recent transactions (last 24 hours)
            from datetime import datetime, timedelta, timezone
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            recent_transactions = db.query(Transaction).filter(
                Transaction.bot_id == bot_id,
                Transaction.created_at >= yesterday
            ).order_by(Transaction.created_at.desc()).limit(10).all()
            
            # Get latest revenue snapshot
            latest_revenue = db.query(RevenueSnapshot).filter(
                RevenueSnapshot.bot_id == bot_id
            ).order_by(RevenueSnapshot.created_at.desc()).first()
            
            # Calculate additional trading stats
            total_trades = bot.total_trades or 0
            profitable_trades = bot.profitable_trades or 0
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else None
            
            # Count today's trades
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = db.query(Transaction).filter(
                Transaction.bot_id == bot_id,
                Transaction.created_at >= today_start
            ).count()
            
            # Calculate max drawdown if available
            max_drawdown_percentage = None
            if hasattr(bot, 'max_drawdown_percentage'):
                max_drawdown_percentage = float(bot.max_drawdown_percentage) if bot.max_drawdown_percentage else None
            
            return {
                "bot_info": {
                    "id": str(bot.id),
                    "name": bot.bot_name,
                    "account_address": bot.account_address,
                    "chain": bot.chain,
                    "strategy_type": bot.strategy_type,
                    "is_active": bot.is_active
                },
                "financial_status": {
                    "initial_balance_usd": float(bot.initial_balance_usd),
                    "current_balance_usd": float(bot.current_balance_usd),
                    "total_assets_usd": float(bot.total_assets_usd),
                    "total_profit_usd": float(bot.total_profit_usd),
                    "max_drawdown_percentage": max_drawdown_percentage
                },
                "trading_stats": {
                    "total_trades": total_trades,
                    "profitable_trades": profitable_trades,
                    "win_rate": win_rate,
                    "today_trades": today_trades
                },
                "positions": [
                    {
                        "id": str(pos.id),
                        "token_id": str(pos.token_id),
                        "token_symbol": pos.token.symbol if pos.token else "Unknown",
                        "token_name": pos.token.name if pos.token else "Unknown",
                        "quantity": float(pos.quantity),
                        "average_cost_usd": float(pos.average_cost_usd),
                        "total_cost_usd": float(pos.total_cost_usd),
                        "current_price_usd": float(pos.current_price_usd or 0),
                        "current_value_usd": float(pos.current_value_usd or 0),
                        "unrealized_pnl_usd": float(pos.unrealized_pnl_usd or 0),
                        "unrealized_pnl_percentage": float(pos.unrealized_pnl_percentage or 0),
                        "stop_loss_price": float(pos.stop_loss_price or 0),
                        "take_profit_price": float(pos.take_profit_price or 0),
                        "created_at": pos.created_at.isoformat() if pos.created_at else None,
                        "updated_at": pos.updated_at.isoformat() if pos.updated_at else None
                    } for pos in positions
                ],
                "recent_transactions": [
                    {
                        "id": str(tx.id),
                        "type": tx.transaction_type,
                        "token_symbol": tx.token.symbol if tx.token else "Unknown",
                        "amount_usd": float(tx.amount_usd or 0),
                        "realized_pnl_usd": float(tx.realized_pnl_usd or 0),
                        "status": tx.status,
                        "created_at": tx.created_at.isoformat() if tx.created_at else None
                    } for tx in recent_transactions
                ],
                "latest_revenue": {
                    "total_profit_usd": float(latest_revenue.total_profit_usd) if latest_revenue else 0,
                    "total_profit_percentage": float(latest_revenue.total_profit_percentage) if latest_revenue else 0,
                    "snapshot_time": latest_revenue.created_at.isoformat() if latest_revenue and latest_revenue.created_at else None
                } if latest_revenue else None
            }
            
        except Exception as e:
            print(f"Error getting bot status: {e}")
            return None
    
    # ===== POSITION MANAGEMENT =====
    
    async def get_bot_positions(self, db: Session, bot_id: str) -> List[Dict[str, Any]]:
        """Get all active positions for a trading bot"""
        try:
            positions = db.query(Position).filter(
                Position.bot_id == bot_id,
                Position.is_active == True
            ).all()
            position_data = []
            for pos in positions:
                await self._update_position_current_value(db, pos)
                position_data.append({
                    "id": str(pos.id),
                    "token_id": str(pos.token_id),
                    "token_symbol": pos.token.symbol if pos.token else "Unknown",
                    "token_name": pos.token.name if pos.token else "Unknown",
                    "quantity": float(pos.quantity),
                    "average_cost_usd": float(pos.average_cost_usd),
                    "total_cost_usd": float(pos.total_cost_usd),
                    "current_price_usd": float(pos.current_price_usd or 0),
                    "current_value_usd": float(pos.current_value_usd or 0),
                    "unrealized_pnl_usd": float(pos.unrealized_pnl_usd or 0),
                    "unrealized_pnl_percentage": float(pos.unrealized_pnl_percentage or 0),
                    "stop_loss_price": float(pos.stop_loss_price or 0),
                    "take_profit_price": float(pos.take_profit_price or 0),
                    "created_at": pos.created_at.isoformat(),
                    "updated_at": pos.updated_at.isoformat()
                })
            return position_data
        except Exception as e:
            print(f"Error getting bot positions: {e}")
            return []
    
    async def _update_position_current_value(self, db: Session, position: Position) -> bool:
        """Update position current value based on latest token price"""
        try:
            from models.database import TokenMetric
            token_metric = db.query(TokenMetric).filter(
                TokenMetric.token_id == position.token_id
            ).first()
            if not token_metric or not token_metric.weighted_price_usd:
                return False
            current_price = token_metric.weighted_price_usd
            current_value = position.quantity * current_price
            cost_basis = position.quantity * position.average_cost_usd

            trading_fee_usd = current_value * (Decimal(str(self._trading_fee_percentage)) / Decimal('100'))
            total_sell_cost_usd = Decimal(str(self._gas_cost_usd)) + trading_fee_usd
            unrealized_pnl = current_value - cost_basis - total_sell_cost_usd
            
            # Handle precision issues with very small values
            if abs(unrealized_pnl) < Decimal("0.000000000000001"):
                unrealized_pnl = Decimal("0")
            
            # Calculate percentage, handling very small cost basis
            if cost_basis > Decimal("0.000000000000001"):
                unrealized_pnl_percentage = (unrealized_pnl / cost_basis) * 100
            else:
                unrealized_pnl_percentage = Decimal("0")
            
            # Handle unrealistic P&L percentages
            if abs(unrealized_pnl_percentage) > 10000:
                print(f"⚠️  Warning: Unrealistic P&L percentage detected: {unrealized_pnl_percentage:.2f}%")
                print(f"   Position: {position.token.symbol if position.token else 'Unknown'}")
                print(f"   Cost basis: ${cost_basis:.2f}")
                print(f"   Current value: ${current_value:.2f}")
                print(f"   Sell costs: ${total_sell_cost_usd:.2f} (gas: ${self._gas_cost_usd or 0:.2f}, fee: ${self._trading_fee_percentage:.2f}%)")
                print(f"   Unrealized P&L: ${unrealized_pnl:.2f}")
                if position.total_cost_usd > Decimal("0.000000000000001"):
                    unrealized_pnl_percentage = (unrealized_pnl / position.total_cost_usd) * 100
                    print(f"   Recalculated using total_cost_usd: {unrealized_pnl_percentage:.2f}%")
                else:
                    unrealized_pnl_percentage = Decimal("0")
            position.current_price_usd = current_price
            position.current_value_usd = current_value
            position.unrealized_pnl_usd = unrealized_pnl
            position.unrealized_pnl_percentage = unrealized_pnl_percentage
            position.updated_at = datetime.now(timezone.utc)
            # Don't commit here - let the calling method handle the transaction
            db.flush()  # Flush to ensure changes are applied
            return True
        except Exception as e:
            print(f"Error updating position current value: {e}")
            # Don't rollback here - let the calling method handle rollback
            return False
    
    async def calculate_position_expected_return(self, db: Session, position: Position, sell_percentage: float, current_price: float) -> Dict[str, Any]:
        """Calculate expected return for selling a percentage of position"""
        try:
            from decimal import Decimal
            current_price_decimal = Decimal(str(current_price))
            sell_quantity = position.quantity * Decimal(str(sell_percentage / 100))
            sell_amount_usd = sell_quantity * current_price_decimal
            
            trading_fee_usd = sell_amount_usd * (Decimal(str(self._trading_fee_percentage)) / Decimal('100'))
            total_cost_usd = Decimal(str(self._gas_cost_usd)) + trading_fee_usd
            net_proceeds_usd = sell_amount_usd - total_cost_usd
            cost_basis = sell_quantity * position.average_cost_usd

            #print(f"current_price: {current_price}")  
            #print(f"quantity: {position.quantity}")  
            #print(f"sell_percentage: {sell_percentage}")  
            #print(f"sell_quantity: {sell_quantity}")  
            #print(f"average_cost_usd: {position.average_cost_usd}")  
            #print(f"cost_basis: {cost_basis}")  
            #print(f"net_proceeds_usd: {net_proceeds_usd}")  

            gross_profit_usd = sell_amount_usd - cost_basis
            net_profit_usd = net_proceeds_usd - cost_basis
            
            # Handle precision issues with very small values
            if abs(gross_profit_usd) < Decimal("0.000000000000001"):
                gross_profit_usd = Decimal("0")
            if abs(net_profit_usd) < Decimal("0.000000000000001"):
                net_profit_usd = Decimal("0")
            
            # Calculate return rates, handling very small cost basis
            if cost_basis > Decimal("0.000000000000001"):
                gross_return_rate = (gross_profit_usd / cost_basis) * 100
                net_return_rate = (net_profit_usd / cost_basis) * 100
            else:
                gross_return_rate = Decimal("0")
                net_return_rate = Decimal("0")
            remaining_quantity = position.quantity - sell_quantity
            
            # Handle precision issues - if remaining quantity is very small, treat as zero
            if remaining_quantity <= Decimal("0.000000000000001"):
                remaining_quantity = Decimal("0")
            
            return {
                "sell_percentage": sell_percentage,
                "sell_quantity": float(sell_quantity),
                "sell_amount_usd": float(sell_amount_usd),
                "trading_costs": {
                    "gas_cost_usd": float(self._gas_cost_usd),
                    "trading_fee_usd": float(trading_fee_usd),
                    "total_cost_usd": float(total_cost_usd)
                },
                "financial_impact": {
                    "net_proceeds_usd": float(net_proceeds_usd),
                    "cost_basis": float(cost_basis),
                    "gross_profit_usd": float(gross_profit_usd),
                    "net_profit_usd": float(net_profit_usd),
                    "gross_return_rate": float(gross_return_rate),
                    "net_return_rate": float(net_return_rate)
                },
                "remaining_position": {
                    "quantity": float(remaining_quantity),
                    "total_cost_impact": float(total_cost_usd)
                }
            }
        except Exception as e:
            print(f"Error calculating expected return: {e}")
            return {"error": str(e)}
    
    # ===== VIRTUAL TRADING EXECUTION =====
    
    async def execute_buy_order(self, db: Session, bot_id: str, token_id: str, amount_usd: float, current_price: float, llm_decision_id: Optional[str] = None) -> Optional[Transaction]:
        """Execute virtual buy order"""
        try:
    
            amount_usd_decimal = Decimal(str(amount_usd))
            price_decimal = Decimal(str(current_price))
            trading_fee_usd = amount_usd_decimal * (Decimal(str(self._trading_fee_percentage)) / Decimal('100'))
            total_cost_usd = Decimal(str(self._gas_cost_usd)) + trading_fee_usd
            token_quantity = amount_usd_decimal / price_decimal
            total_required = amount_usd_decimal + total_cost_usd
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot or bot.current_balance_usd < total_required:
                print(f"Insufficient balance: required ${total_required}, available ${bot.current_balance_usd if bot else 0}")
                return None
            transaction = Transaction(
                bot_id=bot_id,
                token_id=token_id,
                llm_decision_id=llm_decision_id,
                transaction_type="buy",
                status="executed",
                amount_usd=amount_usd_decimal,
                token_amount=token_quantity,
                price_usd=price_decimal,
                gas_cost_usd=Decimal(str(self._gas_cost_usd or 0)),
                trading_fee_usd=trading_fee_usd,
                total_cost_usd=total_cost_usd,
                balance_before_usd=bot.current_balance_usd,
                balance_after_usd=bot.current_balance_usd - total_required,
                executed_at=datetime.now(timezone.utc)
            )
            bot.current_balance_usd -= total_required
            bot.total_trades += 1
            bot.last_activity_at = datetime.now(timezone.utc)
            position = await self._create_or_update_position_buy(
                db, bot_id, token_id, token_quantity, price_decimal, total_cost_usd
            )
            if position:
                print(f"🔗 Linking position {position.id} to transaction")
                transaction.position_id = position.id
                transaction.position_before = Decimal("0") if not position else position.quantity - token_quantity
                transaction.position_after = position.quantity
                transaction.avg_cost_before = Decimal("0")
                transaction.avg_cost_after = position.average_cost_usd
            else:
                print(f"❌ Failed to create/update position for token {token_id}")
            bot.total_assets_usd = bot.current_balance_usd + self._calculate_total_position_value(db, bot_id)
            db.add(transaction)
            
            # Create position history within the same transaction
            if position:
                await self._create_position_history(db, position, "trade_buy", transaction.id)
            
            # Commit everything together
            db.commit()
            db.refresh(transaction)
            db.refresh(bot)
            if position:
                db.refresh(position)
            
            print(f"✓ Executed buy order: {amount_usd} USD for {float(token_quantity)} tokens at ${current_price}")
            
            # Verify position was created/updated
            if position:
                print(f"✅ Position verified: ID={position.id}, Quantity={position.quantity}, Active={position.is_active}")
            else:
                print(f"❌ No position created/updated")
            
            return transaction
        except Exception as e:
            print(f"Error executing buy order: {e}")
            db.rollback()
            return None
    
    async def execute_sell_order(self, db: Session, bot_id: str, position_id: str, sell_percentage: float, current_price: float, llm_decision_id: Optional[str] = None) -> Optional[Transaction]:
        """Execute virtual sell order"""
        try:
            from decimal import Decimal
            
            position = db.query(Position).filter(
                Position.id == position_id,
                Position.bot_id == bot_id,
                Position.is_active == True
            ).first()
            if not position:
                return None
            
            # Convert all inputs to Decimal for precise calculations
            sell_percentage_decimal = Decimal(str(sell_percentage))
            current_price_decimal = Decimal(str(current_price))
            
            # Calculate sell quantity using Decimal arithmetic
            sell_quantity = position.quantity * (sell_percentage_decimal / Decimal('100'))
            sell_amount_usd = sell_quantity * current_price_decimal
            trading_fee_usd = sell_amount_usd * (Decimal(str(self._trading_fee_percentage)) / Decimal('100'))
            total_cost_usd = Decimal(str(self._gas_cost_usd)) + trading_fee_usd
            net_proceeds_usd = sell_amount_usd - total_cost_usd
            cost_basis = sell_quantity * position.average_cost_usd
            net_profit_usd = net_proceeds_usd - cost_basis
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                return None

            # Calculate remaining quantity and handle precision issues
            remaining_quantity = position.quantity - sell_quantity
            
            # Handle floating point precision issues - if remaining quantity is very small, treat as zero
            if remaining_quantity <= Decimal("0.000000000000001"):  # Very small threshold
                print(f"⚠️  Warning: Remaining quantity is very small ({remaining_quantity}), treating as zero")
                position.quantity = Decimal("0")
                position.average_cost_usd = Decimal("0")
                position.total_cost_usd = Decimal("0")
                position.is_active = False
            else:
                position.quantity = remaining_quantity
                position.total_cost_usd -= cost_basis

            transaction = Transaction(
                bot_id=bot_id,
                token_id=position.token_id,
                llm_decision_id=llm_decision_id,
                transaction_type="sell",
                status="executed",
                amount_usd=sell_amount_usd,
                token_amount=sell_quantity,
                price_usd=current_price_decimal,
                gas_cost_usd=Decimal(str(self._gas_cost_usd or 0)),
                trading_fee_usd=trading_fee_usd,
                total_cost_usd=total_cost_usd,
                realized_pnl_usd=net_profit_usd,
                balance_before_usd=bot.current_balance_usd - net_proceeds_usd,
                balance_after_usd=bot.current_balance_usd,
                executed_at=datetime.now(timezone.utc)
            )

            # Update bot total assets, depends on positions
            bot.current_balance_usd += net_proceeds_usd
            bot.total_trades += 1
            bot.last_activity_at = datetime.now(timezone.utc)
            bot.total_profit_usd += net_profit_usd
            if net_profit_usd > 0:
                bot.profitable_trades += 1
            bot.total_assets_usd = bot.current_balance_usd + self._calculate_total_position_value(db, bot_id)
            bot.max_drawdown_percentage = max(bot.max_drawdown_percentage or 0, abs(bot.total_assets_usd - bot.initial_balance_usd) / bot.initial_balance_usd)
            
            # Add transaction to database
            db.add(transaction)
            
            # Create position history within the same transaction
            await self._create_position_history(db, position, "trade_sell", transaction.id)
            
            # Commit everything together
            db.commit()
            db.refresh(transaction)
            db.refresh(position)
            db.refresh(bot)
            
            print(f"✓ Executed sell order: {sell_percentage}% of position at ${current_price}")
            return transaction
        except Exception as e:
            print(f"Error executing sell order: {e}")
            db.rollback()
            return None
    
    def _validate_buy_order(self, bot: TradingBot, amount_usd: float, 
                           current_price: float) -> Dict[str, Any]:
        """Validate buy order parameters"""
        # Check minimum trade amount
        if amount_usd < float(bot.min_trade_amount_usd):
            return {"valid": False, "reason": f"Amount below minimum ${bot.min_trade_amount_usd}"}
        
        # Check daily trade limit
        # This should be enhanced to check actual daily trades
        
        # Check if price is reasonable
        if current_price <= 0:
            return {"valid": False, "reason": "Invalid price"}
        
        return {"valid": True}
    
    async def _create_or_update_position_buy(self, db: Session, bot_id: str, token_id: str, 
                                           quantity: Decimal, price: Decimal, 
                                           total_cost: Decimal) -> Optional[Position]:
        """Create new position or update existing position for buy order"""
        try:
            print(f"🔍 Checking for existing position: bot_id={bot_id}, token_id={token_id}")
            # Check if position already exists
            existing_position = db.query(Position).filter(
                Position.bot_id == bot_id,
                Position.token_id == token_id,
                Position.is_active == True
            ).first()
            
            if existing_position:
                print(f"📝 Updating existing position: {existing_position.id}")
                # Update existing position with new average cost
                old_quantity = existing_position.quantity
                old_total_cost = existing_position.total_cost_usd
                old_avg_cost = existing_position.average_cost_usd
                
                # Calculate new values
                new_quantity = old_quantity + quantity
                
                # For average cost calculation, we need to separate the token cost from trading costs
                # The total_cost includes both token purchase cost and trading fees
                # We need to calculate the effective price per token including trading costs
                # But we should use the actual token price for average cost calculation, not include trading fees
                effective_price_per_token = price  # Use the actual token price, not total_cost/quantity
                
                # Calculate new average cost using weighted average
                # Formula: (old_quantity * old_avg_cost + new_quantity * effective_price_per_token) / total_quantity
                new_average_cost = (old_quantity * old_avg_cost + quantity * effective_price_per_token) / new_quantity
                
                # Ensure average cost is positive and handle precision issues
                if new_average_cost <= 0:
                    print(f"⚠️  Warning: Calculated negative average cost in buy: {new_average_cost}, using token price")
                    new_average_cost = effective_price_per_token
                
                # Handle very small average costs that might cause precision issues
                if new_average_cost < Decimal("0.0000000001"):  # Very small threshold
                    print(f"⚠️  Warning: Average cost is very small ({new_average_cost}), using token price")
                    new_average_cost = effective_price_per_token
                
                # Update total cost (this includes all trading costs)
                new_total_cost = old_total_cost + total_cost
                
                # 更新持仓数据
                existing_position.quantity = new_quantity
                existing_position.average_cost_usd = new_average_cost
                existing_position.total_cost_usd = new_total_cost
                existing_position.updated_at = datetime.now(timezone.utc)
                
                # Don't commit here - let the calling method handle the transaction
                db.flush()  # Flush to get updated values but don't commit
                
                print(f"📊 Position updated: {existing_position.token.symbol if existing_position.token else 'Unknown'}")
                print(f"   Old quantity: {old_quantity}, New quantity: {new_quantity}")
                print(f"   Old avg cost: ${old_avg_cost:.8f}, New avg cost: ${new_average_cost:.8f}")
                print(f"   Old total cost: ${old_total_cost:.2f}, New total cost: ${new_total_cost:.2f}")
                
                return existing_position
            else:
                print(f"🆕 Creating new position for token {token_id}")
                # Create new position
                # For new positions, the average cost should be the actual token price
                # Trading fees are included in total_cost_usd but not in average_cost_usd
                position = Position(
                    bot_id=bot_id,
                    token_id=token_id,
                    quantity=quantity,
                    average_cost_usd=price,  # Use actual token price
                    total_cost_usd=total_cost,  # This includes trading fees
                    current_price_usd=price,
                    current_value_usd=quantity * price,
                    unrealized_pnl_usd=Decimal("0"),
                    unrealized_pnl_percentage=Decimal("0")
                )
                
                db.add(position)
                db.flush()  # To get the ID but don't commit yet
                
                print(f"📊 New position created: {position.token.symbol if position.token else 'Unknown'}")
                print(f"   Position ID: {position.id}")
                print(f"   Quantity: {quantity}")
                print(f"   Token Price: ${price:.8f}")
                print(f"   Average Cost: ${price:.8f}")
                print(f"   Total Cost (with fees): ${total_cost:.2f}")
                
                return position
                
        except Exception as e:
            print(f"Error creating/updating position: {e}")
            # Don't rollback here - let the calling method handle rollback
            return None
    
    def _calculate_total_position_value(self, db: Session, bot_id: str) -> Decimal:
        """Calculate total value of all positions for a bot"""
        try:
            positions = db.query(Position).filter(
                Position.bot_id == bot_id,
                Position.is_active == True
            ).all()
            
            total_value = Decimal("0")
            for pos in positions:
                if pos.current_value_usd:
                    total_value += pos.current_value_usd
            
            return total_value
            
        except Exception as e:
            print(f"Error calculating total position value: {e}")
            return Decimal("0")
    
    # ===== HISTORY AND SNAPSHOTS =====
    
    async def _create_position_history(self, db: Session, position: Position, 
                                     trigger_event: str, transaction_id: Optional[str] = None) -> bool:
        """Create position history record"""
        try:
            print(f"📝 Creating position history: position_id={position.id}, trigger={trigger_event}")
            history = PositionHistory(
                position_id=position.id,
                bot_id=position.bot_id,
                token_id=position.token_id,
                quantity=position.quantity,
                average_cost_usd=position.average_cost_usd,
                total_cost_usd=position.total_cost_usd,
                token_price_usd=position.current_price_usd or Decimal("0"),
                position_value_usd=position.current_value_usd or Decimal("0"),
                unrealized_pnl_usd=position.unrealized_pnl_usd or Decimal("0"),
                unrealized_pnl_percentage=position.unrealized_pnl_percentage or Decimal("0"),
                stop_loss_price=position.stop_loss_price,
                take_profit_price=position.take_profit_price,
                trigger_event=trigger_event,
                transaction_id=transaction_id,
                recorded_at=datetime.now(timezone.utc)
            )
            
            db.add(history)
            # Don't commit here - let the calling method handle the transaction
            db.flush()  # Flush to ensure the history is added to the session
            print(f"✅ Position history created successfully")
            return True
            
        except Exception as e:
            print(f"Error creating position history: {e}")
            # Don't rollback here - let the calling method handle rollback
            return False
    
    async def _create_revenue_snapshot(self, db: Session, bot_id: str, 
                                     snapshot_type: str = "hourly") -> bool:
        """Create revenue snapshot for tracking performance"""
        try:
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                return False
            
            # Get all positions for unrealized P&L calculation
            positions = db.query(Position).filter(
                Position.bot_id == bot_id,
                Position.is_active == True
            ).all()
            
            # Calculate totals
            total_positions_value = sum(float(pos.current_value_usd or 0) for pos in positions)
            total_unrealized_pnl = sum(float(pos.unrealized_pnl_usd or 0) for pos in positions)
            
            # Calculate realized P&L from transactions
            total_realized_pnl = float(bot.total_profit_usd)
            
            # Calculate total profit
            total_profit = total_unrealized_pnl + total_realized_pnl
            total_profit_percentage = (total_profit / float(bot.initial_balance_usd)) * 100
            
            # Create snapshot
            snapshot = RevenueSnapshot(
                bot_id=bot_id,
                total_assets_usd=bot.total_assets_usd,
                available_balance_usd=bot.current_balance_usd,
                total_positions_value_usd=Decimal(str(total_positions_value)),
                total_unrealized_pnl_usd=Decimal(str(total_unrealized_pnl)),
                total_realized_pnl_usd=Decimal(str(total_realized_pnl)),
                total_profit_usd=Decimal(str(total_profit)),
                total_profit_percentage=Decimal(str(total_profit_percentage)),
                total_trades=bot.total_trades,
                profitable_trades=bot.profitable_trades,
                win_rate=Decimal(str((bot.profitable_trades / max(bot.total_trades, 1)) * 100)),
                active_positions_count=len(positions),
                snapshot_type=snapshot_type,
                snapshot_time=datetime.now(timezone.utc)
            )
            
            db.add(snapshot)
            # Don't commit here - let the calling method handle the transaction
            db.flush()  # Flush to ensure the snapshot is added to the session
            return True
            
        except Exception as e:
            print(f"Error creating revenue snapshot: {e}")
            # Don't rollback here - let the calling method handle rollback
            return False 