#!/usr/bin/env python3
"""
AIP DEX Trading Bot

A virtual trading bot that simulates cryptocurrency trading with LLM-powered decision making.
Supports BSC and Solana chains with configurable strategies.

Usage:
    python trading_bot.py --config config.json
    python trading_bot.py --name "My Bot" --chain bsc --balance 5000 --strategy moderate
"""

import asyncio
import argparse
import json
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import signal
import time

# Add current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from models.database import Position, get_db, TradingBot, LLMDecision, init_database
from services.trading_service import TradingService
from services.token_service import TokenService
from llm.trading_analyzer import TradingDecisionAnalyzer

class AIPTradingBot:
    """Main trading bot class with configuration, initialization and trading loop"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bot_id = None
        self.is_running = False
        self.trading_service = TradingService()
        self.token_service = TokenService()
        self.trading_analyzer = TradingDecisionAnalyzer()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n📡 Received signal {signum}, shutting down gracefully...")
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Initialize the trading bot and database"""
        try:
            print("🤖 Initializing AIP DEX Trading Bot...")
            
            # Initialize database
            if not init_database():
                print("❌ Failed to initialize database")
                return False
            
            # Get database session
            db = next(get_db())
            try:
                # Create or get existing trading bot
                bot = await self.trading_service.create_trading_bot(db, self.config)
                if not bot:
                    print("❌ Failed to create trading bot")
                    return False
                
                self.bot_id = str(bot.id)
                print(f"✅ Trading bot initialized: {bot.bot_name} (ID: {self.bot_id})")
                
                # Display bot configuration
                self._display_bot_config(bot)
                
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    def _display_bot_config(self, bot: TradingBot):
        """Display bot configuration summary"""
        print("\n📋 Bot Configuration:")
        print(f"   Name: {bot.bot_name}")
        print(f"   Account: {bot.account_address}")
        print(f"   Chain: {bot.chain.upper()}")
        print(f"   Strategy: {bot.strategy_type}")
        print(f"   Initial Balance: ${float(bot.initial_balance_usd):,.2f}")
        print(f"   Max Position Size: {float(bot.max_position_size):.1f}%")
        print(f"   Stop Loss: {float(bot.stop_loss_percentage):.1f}%")
        print(f"   Take Profit: {float(bot.take_profit_percentage):.1f}%")
        # Display polling interval in a user-friendly format
        interval_hours = float(bot.polling_interval_hours)
        if interval_hours >= 1:
            if interval_hours == int(interval_hours):
                print(f"   Polling Interval: {int(interval_hours)}h")
            else:
                print(f"   Polling Interval: {interval_hours:.2f}h")
        else:
            minutes = interval_hours * 60
            if minutes == int(minutes):
                print(f"   Polling Interval: {int(minutes)}m")
            else:
                print(f"   Polling Interval: {minutes:.1f}m")
        print(f"   Min Trade: ${float(bot.min_trade_amount_usd)}")
        print(f"   Max Daily Trades: {bot.max_daily_trades}")
    
    async def run(self):
        """Main trading loop"""
        if not self.bot_id:
            print("❌ Bot not initialized")
            return
        
        self.is_running = True
        print(f"\n🚀 Starting trading bot {self.bot_id}")
        print("   Press Ctrl+C to stop gracefully")
        
        # Support decimal hours for minute-level polling intervals
        polling_interval_hours = self.config.get("polling_interval_hours", 1)
        polling_interval = float(polling_interval_hours) * 3600  # Convert to seconds
        
        while self.is_running:
            try:
                cycle_start = time.time()
                print(f"\n🔄 Trading cycle started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Execute trading cycle
                await self._trading_cycle()
                
                # Calculate sleep time
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, polling_interval - cycle_duration)
                
                if sleep_time > 0:
                    # Display time in a user-friendly format
                    if sleep_time >= 3600:  # 1 hour or more
                        hours = sleep_time / 3600
                        print(f"⏳ Next cycle in {hours:.1f} hours")
                    elif sleep_time >= 60:  # 1 minute or more
                        minutes = sleep_time / 60
                        print(f"⏳ Next cycle in {minutes:.1f} minutes")
                    else:
                        print(f"⏳ Next cycle in {sleep_time:.0f} seconds")
                    
                    # Sleep in small chunks to allow for graceful shutdown
                    # Update position current value every 10 minutes
                    refresh_position = 0
                    while sleep_time > 0 and self.is_running:
                        chunk_sleep = min(sleep_time, 10)  # Sleep max 10 seconds at a time
                        await asyncio.sleep(chunk_sleep)
                        refresh_position += chunk_sleep
                        sleep_time -= chunk_sleep
                        if refresh_position >= 600:
                            await self._update_positions()
                            refresh_position = 0
                else:
                    print("⚠️  Trading cycle took longer than polling interval")
                
            except Exception as e:
                print(f"❌ Error in trading cycle: {e}")
                print("   Waiting 5 minutes before retry...")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
        
        print("🛑 Trading bot stopped")
    
    async def _trading_cycle(self):
        """Execute one complete trading cycle (two-phase decision making)"""
        db = next(get_db())
        try:
            await self._print_cycle_summary(db)
            
            # 1. 读取bot配置，保存为bot_config
            bot = db.query(TradingBot).filter(TradingBot.id == self.bot_id).first()
            if not bot:
                print("❌ Bot not found in DB")
                return
            bot_config = {
                "strategy_type": bot.strategy_type,
                "trading_fee_percentage": float(bot.trading_fee_percentage),
                "max_position_size": float(bot.max_position_size),
                "min_trade_amount_usd": float(bot.min_trade_amount_usd),
                "llm_confidence_threshold": float(getattr(bot, "llm_confidence_threshold", 0)),
                "chain": bot.chain,
                "gas_fee_native": float(getattr(bot, "gas_fee_native", 0)),
                "stop_loss_percentage": float(bot.stop_loss_percentage),
                "take_profit_percentage": float(bot.take_profit_percentage),
                "min_profit_threshold": float(getattr(bot, "min_profit_threshold", 0)),
                "initial_balance_usd": float(bot.initial_balance_usd),
                "account_address": getattr(bot, "account_address", None),
                # ...如有其他参数可补充
            }
            
            # 2. 获取gas_cost_usd
            print("⛽ Updating native token price for gas cost calculation...")
            gas_cost_usd = None
            native_price = await self.trading_service.get_native_token_price(bot_config["chain"])
            if native_price:
                gas_cost_usd = await self.trading_service.calculate_gas_cost_usd(bot_config["chain"])
                print(f"   💰 {bot_config['chain'].upper()} native token price: ${float(native_price):.4f}")
                print(f"   ⛽ Gas cost: ${float(gas_cost_usd):.4f}")
            else:
                print(f"   ⚠️ Could not get {bot_config['chain'].upper()} native token price, using cached/default value")
            
            # Phase 1: Sell Analysis
            print("📊 Phase 1: Analyzing current positions for selling opportunities...")
            sell_decisions = await self._phase_1_sell_analysis(db, bot_config)
            
            if sell_decisions.get("decisions"):
                await self._execute_sell_decisions(db, sell_decisions["decisions"], bot_config)
            else:
                print("   No sell actions recommended")
            
            # Phase 2: Buy Analysis  
            print("🛒 Phase 2: Analyzing market for buying opportunities...")
            buy_decision = await self._phase_2_buy_analysis(db, bot_config)

            print(buy_decision)
            
            if buy_decision.get("decision") == "BUY":
                await self._execute_buy_decision(db, buy_decision, bot_config)
            else:
                print("   No buy action recommended")

            # Update positions current value
            await self._update_positions_with_db(db)
            
            # Create position history for all active positions
            await self._create_cycle_position_history(db)
            
            # Update revenue snapshot
            await self.trading_service._create_revenue_snapshot(db, self.bot_id, "hourly")
            
            # Print cycle summary report
            await self._print_cycle_summary(db)
            
            print("✅ Trading cycle completed")
            
        except Exception as e:
            print(f"❌ Error in trading cycle: {e}")
        finally:
            db.close()
    
    async def _update_positions(self):
        db = next(get_db())
        try:
            await self._update_positions_with_db(db)
        except Exception as e:
            print(f"❌ Error in updating positions: {e}")
        finally:
            db.close()
    
    async def _update_positions_with_db(self, db: Session):
        try:
            positions = db.query(Position).filter(Position.bot_id == self.bot_id).all()
            for pos in positions:
                await self.trading_service._update_position_current_value(db, pos)
        except Exception as e:
            print(f"❌ Error in updating positions: {e}")

    async def _phase_1_sell_analysis(self, db: Session, bot_config: dict) -> Dict[str, Any]:
        """Phase 1: Analyze current positions for selling"""
        try:
            # Get current positions
            bot_status = await self.trading_service.get_bot_status(db, self.bot_id)
            if not bot_status:
                print("   No bot status found")
                return {"decisions": [], "message": "No bot status found"}
            
            positions = bot_status.get("positions", [])
            if not positions or len(positions) == 0:
                print("   No active positions")
                return {"decisions": [], "message": "No active positions"}
            
            print(f"   Found {len(positions)} active positions")
            
            # Prepare position data for LLM analysis
            positions_data = []
            for position in positions:
                # Get token decision data
                token_decision_data = await self.token_service.get_token_decision_data(
                    db, position["token_id"]
                )
                if not token_decision_data:
                    continue
                # Calculate expected returns for different sell percentages
                expected_returns = {}
                for percentage in [10, 20, 30, 50, 75, 100]:
                    # Use price from token_decision_data instead of position (which might be 0)
                    current_price = token_decision_data["current_metrics"].get("weighted_price_usd", 0)
                    position_price = float(position["current_price_usd"])
                    
                    # Debug: Print price sources
                    if current_price != position_price:
                        print(f"   📊 Price mismatch for {token_decision_data['token_info'].get('symbol', 'Unknown')}: token_data=${current_price:.8f}, position=${position_price:.8f}")
                    
                    if current_price > 0:
                        from models.database import Position
                        from decimal import Decimal
                        import uuid
                        pos_obj = Position(
                            quantity=Decimal(str(position["quantity"])),
                            average_cost_usd=Decimal(str(position["average_cost_usd"])), 
                            total_cost_usd=Decimal(str(position["total_cost_usd"])),
                            bot_id=uuid.UUID(self.bot_id),
                            token_id=uuid.UUID(position["token_id"])
                        )
                        expected_return = await self.trading_service.calculate_position_expected_return(
                            db, pos_obj, percentage, current_price
                        )
                        expected_returns[str(percentage)] = expected_return
                        
                        # Debug: Print expected return calculation
                        if percentage == 100:  # Only print for 100% to avoid spam
                            financial_impact = expected_return.get('financial_impact', {}) if expected_return else {}
                            net_profit = financial_impact.get('net_profit_usd', 0) if financial_impact else 0
                            net_rate = financial_impact.get('net_return_rate', 0) if financial_impact else 0
                            print(f"   💰 Expected return for 100% sell: net_profit=${float(net_profit or 0):.2f}, net_rate={float(net_rate or 0):.2f}%")
                    else:
                        print(f"   ❌ No valid price found for {token_decision_data['token_info'].get('symbol', 'Unknown')}: token_data=${current_price:.8f}, position=${position_price:.8f}")
                position_data = {
                    "position_id": position["id"],
                    "token_info": token_decision_data["token_info"],
                    "quantity": position["quantity"],
                    "average_cost_usd": position["average_cost_usd"],
                    "total_cost_usd": position["total_cost_usd"],
                    "current_value_usd": position["current_value_usd"],
                    "unrealized_pnl_usd": position["unrealized_pnl_usd"],
                    "unrealized_pnl_percentage": position["unrealized_pnl_percentage"],
                    "current_metrics": token_decision_data["current_metrics"],
                    "technical_indicators": token_decision_data["technical_indicators"],
                    "moralis_data": token_decision_data["moralis_data"],
                    "expected_returns": expected_returns
                }
                positions_data.append(position_data)
            if not positions_data:
                return {"decisions": [], "message": "No positions with valid data"}
            # 直接用bot_config
            analysis_result = await self.trading_analyzer.analyze_sell_decisions(
                positions_data, bot_status, bot_config
            )

            print("sell analysis: ", analysis_result)
            
            # Save LLM decision to database
            await self._save_llm_decision(db, analysis_result, "sell_analysis", "phase_1_sell")
            
            return analysis_result
        except Exception as e:
            print(f"❌ Error in sell analysis: {e}")
            return {"decisions": [], "error": str(e)}
    
    async def _phase_2_buy_analysis(self, db: Session, bot_config: dict) -> Dict[str, Any]:
        """Phase 2: Analyze market for buying opportunities"""
        try:
            # Get bot status
            bot_status = await self.trading_service.get_bot_status(db, self.bot_id)
            if not bot_status:
                return {"decision": "no_buy", "error": "Could not get bot status"}
            print(bot_status)
            available_balance = bot_status["financial_status"]["current_balance_usd"]
            if available_balance < float(bot_config.get("min_trade_amount_usd", 10)):
                return {
                    "decision": "no_buy", 
                    "reasoning": f"Insufficient balance: ${available_balance:.2f}"
                }
            # Get all tokens with recent metrics, then sort by volume and take top 50
            from models.database import Token, TokenMetric
            from sqlalchemy import desc
            
            # Get all tokens with metrics for the current chain, sorted by liquidity
            available_tokens_query = db.query(Token).join(TokenMetric).filter(
                Token.chain == bot_config["chain"],
                TokenMetric.total_liquidity_usd.isnot(None),
                TokenMetric.total_liquidity_usd > 0
            ).order_by(desc(TokenMetric.total_liquidity_usd)).limit(100).all()
            available_tokens = []
            for token in available_tokens_query:
                token_data = await self.token_service.get_token_decision_data(db, str(token.id))
                if token_data:
                    available_tokens.append(token_data)
                    current_price = token_data.get("current_metrics", {}).get("weighted_price_usd", 0)
                    symbol = token_data.get("token_info", {}).get("symbol", "Unknown")
                    liquidity_usd = token_data.get("current_metrics", {}).get("total_liquidity_usd", 0)
                    price_change_24h = token_data.get("moralis_data", {}).get("price_changes", {}).get("24h", 0)
                    print(f"   📊 Token: {symbol}, Price: ${current_price:.8f}, Liquidity: ${liquidity_usd:,.0f}, 24h Change: {price_change_24h:+.2f}%")
            if not available_tokens:
                return {"decision": "no_buy", "reasoning": "No tokens with valid liquidity data found for analysis"}
            print(f"   📋 Found {len(available_tokens)} tokens with valid liquidity data for analysis")
            
            # Debug: Print key parameters being passed to LLM
            print(f"   🔧 Key parameters for LLM analysis:")
            print(f"      Strategy: {bot_config.get('strategy_type', 'unknown')}")
            print(f"      Max Position Size: {bot_config.get('max_position_size', 10)}%")
            print(f"      Min Trade Amount: ${bot_config.get('min_trade_amount_usd', 10)}")
            print(f"      Confidence Threshold: {bot_config.get('llm_confidence_threshold', 0.7)}")
            print(f"      Available Balance: ${available_balance:,.2f}")
            
            # 直接用bot_config
            analysis_result = await self.trading_analyzer.analyze_buy_decisions(
                available_tokens, bot_status, bot_config
            )
            
            # Save LLM decision to database
            await self._save_llm_decision(db, analysis_result, "buy_analysis", "phase_2_buy")
            
            return analysis_result
        except Exception as e:
            print(f"❌ Error in buy analysis: {e}")
            return {"decision": "no_buy", "error": str(e)}
    
    async def _execute_sell_decisions(self, db: Session, decisions: List[Dict[str, Any]], bot_config: dict):
        """Execute sell decisions from LLM analysis"""
        for decision in decisions:
            try:
                if decision.get("action") != "SELL":
                    continue
                token_symbol = decision.get("token_symbol")
                sell_percentage = decision.get("sell_percentage", 0)
                confidence_score = decision.get("confidence_score", 0)
                print(f"   🔴 Executing SELL: {sell_percentage}% of {token_symbol} (confidence: {confidence_score:.2f})")
                # Find position
                positions = await self.trading_service.get_bot_positions(db, self.bot_id)
                target_position = None
                for pos in positions:
                    if pos["token_symbol"] == token_symbol:
                        target_position = pos
                        break
                if not target_position:
                    print(f"   ❌ Position for {token_symbol} not found")
                    continue
                current_price = target_position["current_price_usd"]
                if current_price <= 0:
                    print(f"   ❌ Invalid price for {token_symbol}")
                    continue
                transaction = await self.trading_service.execute_sell_order(
                    db, self.bot_id, target_position["id"], 
                    sell_percentage, current_price, None
                )
                if transaction:
                    pnl = float(transaction.realized_pnl_usd or 0)
                    print(f"   ✅ Sell executed: P&L ${pnl:,.2f}")
                else:
                    print(f"   ❌ Sell failed for {token_symbol}")
            except Exception as e:
                print(f"   ❌ Error executing sell for {decision.get('token_symbol', 'Unknown')}: {e}")
    
    async def _execute_buy_decision(self, db: Session, decision: Dict[str, Any], bot_config: dict):
        """Execute buy decision from LLM analysis"""
        try:
            selected_token = decision.get("selected_token", {})
            buy_amount = decision.get("buy_amount_usd", 0)
            confidence_score = decision.get("confidence_score", 0)
            
            # Check confidence threshold
            llm_confidence_threshold = float(bot_config.get("llm_confidence_threshold", 0.7))
            if confidence_score < llm_confidence_threshold:
                print(f"   ❌ Confidence score {confidence_score:.2f} below threshold {llm_confidence_threshold:.2f}")
                return
            
            try:
                buy_amount = float(buy_amount)
            except (ValueError, TypeError):
                print(f"   ❌ Invalid buy_amount_usd type: {type(buy_amount)}, value: {buy_amount}")
                return
            min_trade_amount = float(bot_config.get("min_trade_amount_usd", 10))
            if buy_amount < min_trade_amount:
                print(f"   ❌ Buy amount ${buy_amount:.2f} below minimum ${min_trade_amount}")
                return
            if buy_amount > 10000:
                print(f"   ⚠️  Buy amount ${buy_amount:.2f} too high, capping at $10,000")
                buy_amount = 10000
            token_symbol = selected_token.get("symbol")
            if not token_symbol:
                print("   ❌ Missing token symbol in buy decision")
                return
            print(f"   🟢 Executing BUY: ${buy_amount} of {token_symbol} (confidence: {confidence_score:.2f})")
            token = await self.token_service.get_or_create_token(
                db, symbol=token_symbol, chain=bot_config["chain"]
            )
            if not token:
                print(f"   ❌ Could not get token {token_symbol}")
                return
            token_decision_data = await self.token_service.get_token_decision_data(
                db, str(token.id)
            )
            if not token_decision_data:
                print(f"   ❌ Could not get price data for {token_symbol}")
                return
            current_price = token_decision_data["current_metrics"].get("weighted_price_usd", 0)
            if current_price <= 0:
                print(f"   ❌ Invalid price for {token_symbol}")
                return
            
            # Check position size limit
            max_position_size = float(bot_config.get("max_position_size", 10))
            bot_status = await self.trading_service.get_bot_status(db, self.bot_id)
            if bot_status:
                total_assets = float(bot_status["financial_status"]["total_assets_usd"])
                max_position_value = total_assets * (max_position_size / 100)
                if buy_amount > max_position_value:
                    print(f"   ❌ Buy amount ${buy_amount:.2f} exceeds max position size ${max_position_value:.2f} ({max_position_size}%)")
                    return
            
            transaction = await self.trading_service.execute_buy_order(
                db, self.bot_id, str(token.id), buy_amount, current_price, None)
            if transaction:
                quantity = float(transaction.token_amount)
                print(f"   ✅ Buy executed: {quantity:,.2f} {token_symbol}")
            else:
                print(f"   ❌ Buy failed for {token_symbol}")
        except Exception as e:
            print(f"   ❌ Error executing buy: {e}")
    
    async def _save_llm_decision(self, db: Session, analysis_result: Dict[str, Any], decision_type: str, decision_phase: str):
        """Save LLM decision to database"""
        try:
            # Extract decision data
            llm_response = analysis_result.get("llm_response", "")
            reasoning = analysis_result.get("reasoning", "")
            confidence_score = analysis_result.get("confidence_score", 0)
            
            # Extract recommended action and token
            recommended_action = None
            recommended_token_id = None
            recommended_amount = None
            recommended_percentage = None
            
            if decision_type == "sell_analysis":
                decisions = analysis_result.get("decisions", [])
                if decisions:
                    # For sell analysis, we might have multiple decisions
                    # For now, just save the first one
                    first_decision = decisions[0]
                    recommended_action = first_decision.get("action")
                    recommended_percentage = first_decision.get("sell_percentage")
            elif decision_type == "buy_analysis":
                recommended_action = analysis_result.get("decision")
                selected_token = analysis_result.get("selected_token", {})
                if selected_token:
                    # Get token ID from symbol
                    from models.database import Token
                    token = db.query(Token).filter(Token.symbol == selected_token.get("symbol")).first()
                    if token:
                        recommended_token_id = token.id
                recommended_amount = analysis_result.get("buy_amount_usd")
            
            # Create LLM decision record
            llm_decision = LLMDecision(
                bot_id=self.bot_id,
                decision_type=decision_type,
                decision_phase=decision_phase,
                input_data=analysis_result.get("input_data", {}),
                prompt_template="",  # Could be enhanced to save actual prompt
                llm_response=llm_response,
                reasoning=reasoning,
                confidence_score=confidence_score,
                recommended_action=recommended_action,
                recommended_token_id=recommended_token_id,
                recommended_amount=recommended_amount,
                recommended_percentage=recommended_percentage,
                expected_return_percentage=analysis_result.get("expected_return", 0),
                risk_assessment=analysis_result.get("risk_assessment", "medium"),
                market_sentiment=analysis_result.get("market_sentiment", "neutral"),
                technical_indicators=analysis_result.get("technical_indicators", {}),
                fundamental_analysis=analysis_result.get("fundamental_analysis", {}),
                was_executed=False,  # Will be updated when decision is executed
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(llm_decision)
            db.commit()
            db.refresh(llm_decision)
            
            print(f"   💾 Saved LLM decision: {decision_type} - {decision_phase}")
            
        except Exception as e:
            print(f"   ❌ Error saving LLM decision: {e}")
            db.rollback()
    
    async def _print_cycle_summary(self, db: Session):
        """Print detailed cycle summary including profits and positions"""
        try:
            print("\n" + "="*60)
            print("📊 CYCLE SUMMARY REPORT")
            print("="*60)
            
            # Get bot status
            bot_status = await self.trading_service.get_bot_status(db, self.bot_id)
            if not bot_status:
                print("❌ Could not get bot status for summary")
                return
            
            # Financial Summary
            financial = bot_status["financial_status"]
            trading_stats = bot_status["trading_stats"]
            
            print(f"\n💰 FINANCIAL STATUS:")
            print(f"   Initial Balance: ${financial['initial_balance_usd']:,.2f}")
            print(f"   Current Balance: ${financial['current_balance_usd']:,.2f}")
            print(f"   Total Assets: ${financial['total_assets_usd']:,.2f}")
            print(f"   Total Profit: ${financial['total_profit_usd']:,.2f}")
            max_drawdown = financial.get('max_drawdown_percentage', None)
            if max_drawdown is not None:
                print(f"   Max Drawdown: {max_drawdown:.2f}%")
            else:
                print(f"   Max Drawdown: N/A")
            
            # Calculate profit percentage
            initial_balance = float(financial['initial_balance_usd'])
            total_assets = float(financial['total_assets_usd'])
            if initial_balance > 0:
                profit_percentage = ((total_assets - initial_balance) / initial_balance) * 100
                print(f"   Profit Percentage: {profit_percentage:+.2f}%")
            
            # Trading Statistics
            print(f"\n📈 TRADING STATISTICS:")
            total_trades = trading_stats.get('total_trades', 0)
            profitable_trades = trading_stats.get('profitable_trades', 0)
            print(f"   Total Trades: {total_trades}")
            print(f"   Profitable Trades: {profitable_trades}")
            win_rate = trading_stats.get('win_rate', None)
            if win_rate is not None:
                print(f"   Win Rate: {win_rate:.1f}%")
            else:
                print(f"   Win Rate: N/A")
            today_trades = trading_stats.get('today_trades', None)
            if today_trades is not None:
                print(f"   Today's Trades: {today_trades}")
            else:
                print(f"   Today's Trades: N/A")
            
            # Positions Summary
            positions = bot_status.get("positions", [])
            if positions:
                print(f"\n📋 POSITIONS SUMMARY ({len(positions)} active):")
                print("-" * 60)
                
                total_position_value = 0
                total_unrealized_pnl = 0
                total_position_cost = 0
                
                for i, pos in enumerate(positions, 1):
                    position_value = float(pos.get('current_value_usd', 0))
                    unrealized_pnl = float(pos.get('unrealized_pnl_usd', 0))
                    unrealized_pnl_percentage = float(pos.get('unrealized_pnl_percentage', 0))
                    
                    # Get position data
                    token_symbol = pos.get('token_symbol', 'Unknown')
                    quantity = pos.get('quantity', 0)
                    avg_cost = pos.get('average_cost_usd', 0)
                    current_price = pos.get('current_price_usd', 0)
                    
                    # Always calculate cost basis from quantity and average cost for accuracy
                    # The total_cost_usd field might be incorrect in the database
                    position_cost = float(quantity) * float(avg_cost)
                    
                    total_position_value += position_value
                    total_unrealized_pnl += unrealized_pnl
                    total_position_cost += position_cost
                    
                    # Calculate position percentage of total assets
                    position_percentage = (position_value / float(financial['total_assets_usd'])) * 100 if float(financial['total_assets_usd']) > 0 else 0
                    
                    print(f"   {i}. {token_symbol}:")
                    print(f"      Quantity: {float(quantity):,.2f}")
                    print(f"      Avg Cost: ${float(avg_cost):.8f}")
                    print(f"      Current Value: ${position_value:,.2f} ({position_percentage:.1f}% of total)")
                    print(f"      Current Price: ${float(current_price):,.8f}")
                    print(f"      Unrealized P&L: ${unrealized_pnl:+,.2f} ({unrealized_pnl_percentage:+.2f}%)")
                    print(f"      Cost Basis: ${position_cost:,.2f}")
                    print()
                
                # Portfolio Summary
                print(f"📊 PORTFOLIO SUMMARY:")
                print(f"   Total Position Value: ${total_position_value:,.2f}")
                print(f"   Total Position Cost: ${total_position_cost:,.2f}")
                print(f"   Total Unrealized P&L: ${total_unrealized_pnl:+,.2f}")
                
                if total_position_cost > 0:
                    portfolio_return = (total_unrealized_pnl / total_position_cost) * 100
                    print(f"   Portfolio Return: {portfolio_return:+.2f}%")
                    
                    # Add validation check for unrealistic returns
                    if abs(portfolio_return) > 10000:  # More than 10000%
                        print(f"   ⚠️  Warning: Unusually high return rate detected. Please verify data accuracy.")
                
                # Position concentration analysis
                if len(positions) > 1:
                    largest_position = max(positions, key=lambda x: float(x.get('current_value_usd', 0)))
                    largest_value = float(largest_position.get('current_value_usd', 0))
                    largest_percentage = (largest_value / total_position_value) * 100 if total_position_value > 0 else 0
                    largest_symbol = largest_position.get('token_symbol', 'Unknown')
                    print(f"   Largest Position: {largest_symbol} ({largest_percentage:.1f}% of portfolio)")
            else:
                print(f"\n📋 POSITIONS: No active positions")
            
            # Recent Transactions
            recent_transactions = bot_status.get("recent_transactions", [])
            if recent_transactions:
                print(f"\n🔄 RECENT TRANSACTIONS (Last 24h):")
                print("-" * 60)
                
                for i, tx in enumerate(recent_transactions[:5], 1):  # Show last 5 transactions
                    tx_type = tx.get('type', 'unknown').upper()
                    amount = float(tx.get('amount_usd', 0) or 0)
                    pnl = float(tx.get('realized_pnl_usd', 0) or 0)
                    token_symbol = tx.get('token_symbol', 'Unknown')
                    status = tx.get('status', 'unknown')
                    created_at = tx.get('created_at', '')
                    
                    print(f"   {i}. {tx_type} {token_symbol}: ${amount:,.2f}")
                    if pnl != 0:
                        print(f"      P&L: ${pnl:+,.2f}")
                    print(f"      Status: {status}")
                    if created_at:
                        print(f"      Time: {created_at[:19]}")  # Show date and time
                    print()
            
            # Latest Revenue Snapshot
            latest_revenue = bot_status.get("latest_revenue")
            if latest_revenue:
                print(f"\n📊 LATEST REVENUE SNAPSHOT:")
                total_profit = latest_revenue.get('total_profit_usd', 0)
                total_profit_pct = latest_revenue.get('total_profit_percentage', 0)
                snapshot_time = latest_revenue.get('snapshot_time', '')
                print(f"   Total Profit: ${float(total_profit):,.2f}")
                print(f"   Total Profit %: {float(total_profit_pct):+.2f}%")
                if snapshot_time:
                    print(f"   Snapshot Time: {snapshot_time[:19]}")
            
            print("\n" + "="*60)
            
        except Exception as e:
            print(f"❌ Error generating cycle summary: {e}")
            import traceback
            traceback.print_exc()
    
    async def _create_cycle_position_history(self, db: Session):
        """Create position history records for all active positions at the end of each cycle"""
        try:
            from models.database import Position
            
            # Get all active positions
            positions = db.query(Position).filter(
                Position.bot_id == self.bot_id,
                Position.is_active == True
            ).all()
            
            if not positions:
                return
            
            print(f"📝 Creating position history for {len(positions)} active positions")
            
            # Create position history for each position
            success_count = 0
            for position in positions:
                try:
                    success = await self.trading_service._create_position_history(
                        db, position, "periodic", None
                    )
                    if success:
                        success_count += 1
                except Exception as e:
                    print(f"   ❌ Error creating history for {position.token.symbol if position.token else 'Unknown'}: {e}")
            
            print(f"   ✅ Position history created for {success_count}/{len(positions)} positions")
            
        except Exception as e:
            print(f"❌ Error creating cycle position history: {e}")


def load_config_from_file(config_path: str) -> Optional[Dict[str, Any]]:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        return None

def create_config_from_args(args) -> Dict[str, Any]:
    """Create configuration from command line arguments"""
    return {
        "bot_name": args.name,
        "account_address": args.account_address or f"0x{args.name.replace(' ', '').lower()}_account",
        "chain": args.chain,
        "initial_balance_usd": args.balance,
        "strategy_type": args.strategy,
        "polling_interval_hours": args.interval,
        "min_trade_amount_usd": args.min_trade,
        "is_active": True
    }

def create_sample_config() -> Dict[str, Any]:
    """Create a sample configuration"""
    return {
        "bot_name": "Sample Trading Bot",
        "account_address": "0x1234567890abcdef1234567890abcdef12345678",
        "chain": "bsc",
        "initial_balance_usd": 1000.0,
        "strategy_type": "conservative",
        "polling_interval_hours": 1,
        "min_trade_amount_usd": 10.0,
        "is_active": True
    }

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AIP DEX Trading Bot")
    
    # Configuration options
    parser.add_argument("--config", type=str, help="Path to configuration JSON file")
    parser.add_argument("--name", type=str, help="Bot name")
    parser.add_argument("--account_address", type=str, help="Account address")
    parser.add_argument("--chain", type=str, choices=["bsc", "solana"], default="bsc", help="Blockchain chain")
    parser.add_argument("--balance", type=float, help="Initial balance in USD")
    parser.add_argument("--strategy", type=str, choices=["conservative", "moderate", "aggressive", "momentum", "mean_reversion"], 
                       default="conservative", help="Trading strategy")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in hours (supports decimals, e.g., 0.5 for 30 minutes)")
    parser.add_argument("--min-trade", type=float, default=10.0, help="Minimum trade amount in USD")
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = load_config_from_file(args.config)
        if not config:
            return
    else:
        if not all([args.name, args.balance]):
            print("❌ --name and --balance are required when not using --config")
            parser.print_help()
            return
        config = create_config_from_args(args)
    
    # Create and run trading bot
    bot = AIPTradingBot(config)
    
    if await bot.initialize():
        await bot.run()
    else:
        print("❌ Failed to initialize trading bot")

if __name__ == "__main__":
    asyncio.run(main()) 