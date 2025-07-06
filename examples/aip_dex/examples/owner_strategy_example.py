#!/usr/bin/env python3
"""
Example script demonstrating owner and strategy management functionality
"""

import asyncio
import sys
import os
import uuid
from decimal import Decimal

# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from models.database import get_db, init_database
from services.owner_service import OwnerService
from services.trading_service import TradingService
from api.schemas import BotOwnerCreate, TradingStrategyCreate, TradingBotCreate

async def main():
    """Main example function"""
    print("🤖 AIP DEX Trading Bot - Owner & Strategy Management Example")
    print("=" * 60)
    
    # Initialize database
    print("📊 Initializing database...")
    if not init_database():
        print("❌ Failed to initialize database")
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Initialize services
        owner_service = OwnerService()
        trading_service = TradingService()
        
        # ===== STEP 1: Create Bot Owner =====
        print("\n👤 Step 1: Creating Bot Owner")
        print("-" * 30)
        
        owner_data = BotOwnerCreate(
            owner_name="John Doe",
            email="john.doe@example.com",
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            phone="+1234567890",
            subscription_tier="premium",
            max_bots_allowed=10
        )
        
        owner = await owner_service.create_bot_owner(db, owner_data)
        if not owner:
            print("❌ Failed to create bot owner")
            return
        
        print(f"✅ Created owner: {owner.owner_name}")
        print(f"   Email: {owner.email}")
        print(f"   Wallet: {owner.wallet_address}")
        print(f"   Subscription: {owner.subscription_tier}")
        print(f"   Max Bots: {owner.max_bots_allowed}")
        
        # ===== STEP 2: Create Default Strategies =====
        print("\n📈 Step 2: Creating Default Strategies")
        print("-" * 30)
        
        strategies = await owner_service.create_default_strategies(db, owner.id)
        print(f"✅ Created {len(strategies)} default strategies:")
        
        for strategy in strategies:
            print(f"   - {strategy.strategy_name} ({strategy.strategy_type})")
            print(f"     Risk Level: {strategy.risk_level}")
            print(f"     Max Position: {float(strategy.max_position_size)}%")
            print(f"     Stop Loss: {float(strategy.stop_loss_percentage)}%")
            print(f"     Take Profit: {float(strategy.take_profit_percentage)}%")
        
        # ===== STEP 3: Create Custom Strategy =====
        print("\n🎯 Step 3: Creating Custom Strategy")
        print("-" * 30)
        
        custom_strategy_data = TradingStrategyCreate(
            strategy_name="My Custom Strategy",
            strategy_description="A custom strategy combining momentum and mean reversion",
            strategy_type="user_defined",
            risk_level="medium",
            
            # 数值参数设置
            max_position_size=Decimal("25.0"),
            stop_loss_percentage=Decimal("8.0"),
            take_profit_percentage=Decimal("30.0"),
            min_profit_threshold=Decimal("4.0"),
            max_daily_trades=15,
            llm_confidence_threshold=Decimal("0.75"),
            
            # 交易费用设置
            gas_fee_native=Decimal("0.00003"),
            trading_fee_percentage=Decimal("0.1"),
            slippage_tolerance=Decimal("1.5"),
            
            # 运行控制参数
            min_trade_amount_usd=Decimal("15.0"),
            polling_interval_hours=Decimal("0.5"),
            
            # 功能开关
            enable_stop_loss=True,
            enable_take_profit=True,
            
            # 策略描述性配置
            buy_strategy_description="Custom buying strategy that looks for tokens with strong momentum but also considers mean reversion opportunities. Focus on tokens with volume spikes and positive holder growth.",
            sell_strategy_description="Custom selling strategy that uses a combination of technical indicators and profit targets. Exit positions when momentum weakens or when profit targets are reached.",
            filter_strategy_description="Filter for tokens with market cap > $5M, volume > $75K, and positive price momentum. Avoid extremely volatile tokens and prefer those with stable holder growth.",
            summary_strategy_description="A balanced strategy that combines momentum trading with mean reversion principles. Suitable for investors who want growth potential while managing risk."
        )
        
        custom_strategy = await owner_service.create_trading_strategy(db, owner.id, custom_strategy_data)
        if custom_strategy:
            print(f"✅ Created custom strategy: {custom_strategy.strategy_name}")
            print(f"   Type: {custom_strategy.strategy_type}")
            print(f"   Risk Level: {custom_strategy.risk_level}")
            print(f"   Max Position: {float(custom_strategy.max_position_size)}%")
            print(f"   Stop Loss: {float(custom_strategy.stop_loss_percentage)}%")
            print(f"   Take Profit: {float(custom_strategy.take_profit_percentage)}%")
            print(f"   Buy Strategy: {custom_strategy.buy_strategy_description[:100]}...")
        
        # ===== STEP 4: List Owner's Strategies =====
        print("\n📋 Step 4: Listing Owner's Strategies")
        print("-" * 30)
        
        owner_strategies = await owner_service.list_owner_strategies(db, owner.id)
        print(f"✅ Owner has {len(owner_strategies)} strategies:")
        
        for strategy in owner_strategies:
            print(f"   - {strategy.strategy_name}")
            print(f"     Type: {strategy.strategy_type}, Risk: {strategy.risk_level}")
            print(f"     Usage Count: {strategy.usage_count}")
            print(f"     Is Public: {strategy.is_public}")
        
        # ===== STEP 5: Create Trading Bot with Strategy =====
        print("\n🤖 Step 5: Creating Trading Bot with Strategy")
        print("-" * 30)
        
        # Use the custom strategy
        bot_config = {
            "bot_name": "John's Custom Bot",
            "account_address": "0xabcdef1234567890abcdef1234567890abcdef12",
            "chain": "bsc",
            "initial_balance_usd": 5000.0,
            "owner_id": owner.id,
            "strategy_id": custom_strategy.id if custom_strategy else None,
            "is_active": True
        }
        
        bot = await trading_service.create_trading_bot(db, bot_config)
        if bot:
            print(f"✅ Created trading bot: {bot.bot_name}")
            print(f"   Owner: {bot.owner_id}")
            print(f"   Strategy: {bot.strategy_id}")
            print(f"   Chain: {bot.chain}")
            print(f"   Initial Balance: ${float(bot.initial_balance_usd):,.2f}")
        
        # ===== STEP 6: Create Another Bot with Default Strategy =====
        print("\n🤖 Step 6: Creating Another Bot with Default Strategy")
        print("-" * 30)
        
        # Get a default strategy
        default_strategies = await owner_service.get_default_strategies(db)
        conservative_strategy = next((s for s in default_strategies if s.strategy_type == "conservative"), None)
        
        if conservative_strategy:
            bot_config2 = {
                "bot_name": "John's Conservative Bot",
                "account_address": "0x9876543210fedcba9876543210fedcba98765432",
                "chain": "bsc",
                "initial_balance_usd": 3000.0,
                "owner_id": owner.id,
                "strategy_id": conservative_strategy.id,
                "is_active": True
            }
            
            bot2 = await trading_service.create_trading_bot(db, bot_config2)
            if bot2:
                print(f"✅ Created conservative bot: {bot2.bot_name}")
                print(f"   Strategy: {bot2.strategy_id}")
        
        # ===== STEP 7: List Owner's Bots =====
        print("\n📋 Step 7: Listing Owner's Bots")
        print("-" * 30)
        
        owner_bots = await owner_service.get_owner_bots(db, owner.id)
        print(f"✅ Owner has {len(owner_bots)} bots:")
        
        for bot in owner_bots:
            print(f"   - {bot.bot_name}")
            print(f"     Account: {bot.account_address}")
            print(f"     Chain: {bot.chain}")
            print(f"     Strategy ID: {bot.strategy_id}")
            print(f"     Current Balance: ${float(bot.current_balance_usd):,.2f}")
            print(f"     Total Assets: ${float(bot.total_assets_usd):,.2f}")
            print(f"     Is Active: {bot.is_active}")
        
        # ===== STEP 8: Update Strategy =====
        print("\n🔄 Step 8: Updating Strategy")
        print("-" * 30)
        
        if custom_strategy:
            from api.schemas import TradingStrategyUpdate
            
            update_data = TradingStrategyUpdate(
                max_position_size=Decimal("30.0"),
                take_profit_percentage=Decimal("35.0"),
                buy_strategy_description="Updated buying strategy with more aggressive position sizing and higher profit targets."
            )
            
            updated_strategy = await owner_service.update_trading_strategy(db, custom_strategy.id, update_data)
            if updated_strategy:
                print(f"✅ Updated strategy: {updated_strategy.strategy_name}")
                print(f"   New Max Position: {float(updated_strategy.max_position_size)}%")
                print(f"   New Take Profit: {float(updated_strategy.take_profit_percentage)}%")
                print(f"   Updated Buy Strategy: {updated_strategy.buy_strategy_description[:100]}...")
        
        print("\n🎉 Example completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error in example: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main()) 