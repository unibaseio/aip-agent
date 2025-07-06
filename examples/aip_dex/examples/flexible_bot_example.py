#!/usr/bin/env python3
"""
Example demonstrating flexible bot startup mode
"""

import asyncio
import sys
import os
from decimal import Decimal

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import get_db, init_database
from services.owner_service import OwnerService
from services.trading_service import TradingService
from api.schemas import BotOwnerCreate, TradingStrategyCreate

async def main():
    """Example of flexible bot startup and configuration"""
    print("🤖 Flexible Bot Startup Example")
    print("=" * 40)
    
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
        
        # Step 1: Create owner
        print("\n👤 Step 1: Creating owner...")
        owner_data = BotOwnerCreate(
            owner_name="Flexible User",
            email="flexible@example.com",
            wallet_address="0x1111111111111111111111111111111111111111",
            subscription_tier="basic"
        )
        
        owner = await owner_service.create_bot_owner(db, owner_data)
        if not owner:
            print("❌ Failed to create owner")
            return
        
        print(f"✅ Created owner: {owner.owner_name}")
        
        # Step 2: Create strategy
        print("\n📈 Step 2: Creating strategy...")
        strategy_data = TradingStrategyCreate(
            strategy_name="Flexible Strategy",
            strategy_type="user_defined",
            risk_level="medium",
            max_position_size=Decimal("15.0"),
            stop_loss_percentage=Decimal("8.0"),
            take_profit_percentage=Decimal("20.0"),
            min_profit_threshold=Decimal("3.0"),
            max_daily_trades=12,
            llm_confidence_threshold=Decimal("0.7"),
            buy_strategy_description="Flexible buy strategy: Look for tokens with positive momentum",
            sell_strategy_description="Flexible sell strategy: Exit when profit target reached or stop loss hit",
            filter_strategy_description="Flexible filter: Market cap > $1M, volume > $50K",
            summary_strategy_description="A flexible strategy for demonstration"
        )
        
        strategy = await owner_service.create_trading_strategy(db, owner.id, strategy_data)
        if not strategy:
            print("❌ Failed to create strategy")
            return
        
        print(f"✅ Created strategy: {strategy.strategy_name}")
        
        # Step 3: Create bot WITHOUT owner and strategy (flexible startup)
        print("\n🤖 Step 3: Creating bot without owner and strategy...")
        bot_config = {
            "bot_name": "Flexible Bot",
            "account_address": "0x2222222222222222222222222222222222222222",
            "chain": "bsc",
            "initial_balance_usd": 2000.0,
            # Note: No owner_id or strategy_id - bot will be created in unconfigured state
            "is_active": True
        }
        
        bot = await trading_service.create_trading_bot(db, bot_config)
        if not bot:
            print("❌ Failed to create bot")
            return
        
        print(f"✅ Created bot: {bot.bot_name}")
        print(f"   Status: {'Configured' if bot.is_configured else 'Not Configured'}")
        print(f"   Owner: {bot.owner_id or 'None'}")
        print(f"   Strategy: {bot.strategy_id or 'None'}")
        print(f"   Balance: ${float(bot.initial_balance_usd):,.2f}")
        
        # Step 4: Configure the bot later
        print("\n⚙️ Step 4: Configuring bot with owner and strategy...")
        configured_bot = await trading_service.configure_bot(db, bot.id, owner.id, strategy.id)
        if not configured_bot:
            print("❌ Failed to configure bot")
            return
        
        print(f"✅ Bot configured successfully!")
        print(f"   Status: {'Configured' if configured_bot.is_configured else 'Not Configured'}")
        print(f"   Owner: {configured_bot.owner_id}")
        print(f"   Strategy: {configured_bot.strategy_id}")
        
        # Step 5: Create another bot with immediate configuration
        print("\n🤖 Step 5: Creating bot with immediate configuration...")
        bot_config2 = {
            "bot_name": "Pre-configured Bot",
            "account_address": "0x3333333333333333333333333333333333333333",
            "chain": "bsc",
            "initial_balance_usd": 1500.0,
            "owner_id": owner.id,  # Immediate configuration
            "strategy_id": strategy.id,  # Immediate configuration
            "is_active": True
        }
        
        bot2 = await trading_service.create_trading_bot(db, bot_config2)
        if not bot2:
            print("❌ Failed to create pre-configured bot")
            return
        
        print(f"✅ Created pre-configured bot: {bot2.bot_name}")
        print(f"   Status: {'Configured' if bot2.is_configured else 'Not Configured'}")
        print(f"   Owner: {bot2.owner_id}")
        print(f"   Strategy: {bot2.strategy_id}")
        
        # Step 6: Show different bot states
        print("\n📋 Step 6: Bot states comparison...")
        bots = [bot, bot2]
        for i, b in enumerate(bots, 1):
            print(f"\nBot {i}: {b.bot_name}")
            print(f"   Configured: {b.is_configured}")
            print(f"   Active: {b.is_active}")
            print(f"   Owner: {b.owner_id or 'None'}")
            print(f"   Strategy: {b.strategy_id or 'None'}")
            print(f"   Ready for trading: {b.is_configured and b.is_active}")
        
        print("\n🎉 Example completed successfully!")
        print("=" * 40)
        print("Key benefits of flexible startup:")
        print("1. Bots can be created without owner/strategy")
        print("2. Configuration can be done later")
        print("3. Bots remain inactive until configured")
        print("4. More flexible deployment options")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main()) 