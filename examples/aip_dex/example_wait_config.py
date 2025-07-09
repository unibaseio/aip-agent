#!/usr/bin/env python3
"""
Example script demonstrating the new bot startup logic with configuration waiting

This script shows how to:
1. Start a bot without owner and strategy
2. Wait for configuration to be completed
3. Start trading once configured
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import get_db, init_database
from services.owner_service import OwnerService
from services.trading_service import TradingService
from api.schemas import BotOwnerCreate, TradingStrategyCreate
from decimal import Decimal

async def create_owner_and_strategy():
    """Create an owner and strategy for demonstration"""
    print("🔧 Creating owner and strategy for demonstration...")
    
    db = next(get_db())
    try:
        owner_service = OwnerService()
        trading_service = TradingService()
        
        # Create owner
        owner_data = BotOwnerCreate(
            owner_name="Demo User",
            email="demo@example.com",
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            subscription_tier="basic"
        )
        
        owner = await owner_service.create_bot_owner(db, owner_data)
        if not owner:
            print("❌ Failed to create owner")
            return None, None
        
        print(f"✅ Created owner: {owner.owner_name}")
        
        # Create strategy
        strategy_data = TradingStrategyCreate(
            strategy_name="Demo Strategy",
            strategy_type="moderate",
            risk_level="medium",
            max_position_size=Decimal("20.0"),
            stop_loss_percentage=Decimal("10.0"),
            take_profit_percentage=Decimal("25.0"),
            min_profit_threshold=Decimal("3.0"),
            max_daily_trades=15,
            llm_confidence_threshold=Decimal("0.7"),
            buy_strategy_description="Demo buy strategy",
            sell_strategy_description="Demo sell strategy",
            filter_strategy_description="Demo filter strategy",
            summary_strategy_description="Demo strategy summary"
        )
        
        strategy = await owner_service.create_trading_strategy(db, owner.id, strategy_data)
        if not strategy:
            print("❌ Failed to create strategy")
            return owner, None
        
        print(f"✅ Created strategy: {strategy.strategy_name}")
        return owner, strategy
        
    finally:
        db.close()

async def configure_bot(bot_id: str, owner_id: str, strategy_id: str):
    """Configure a bot with owner and strategy"""
    print(f"⚙️ Configuring bot {bot_id}...")
    
    db = next(get_db())
    try:
        trading_service = TradingService()
        configured_bot = await trading_service.configure_bot(db, bot_id, owner_id, strategy_id)
        
        if configured_bot:
            print(f"✅ Bot configured successfully!")
            print(f"   Owner: {configured_bot.owner_id}")
            print(f"   Strategy: {configured_bot.strategy_id}")
            print(f"   Is Configured: {configured_bot.is_configured}")
            return True
        else:
            print("❌ Failed to configure bot")
            return False
            
    finally:
        db.close()

async def main():
    """Main demonstration function"""
    print("🤖 AIP DEX Trading Bot - Configuration Waiting Demo")
    print("=" * 60)
    
    # Initialize database
    if not init_database():
        print("❌ Failed to initialize database")
        return
    
    # Step 1: Create owner and strategy
    owner, strategy = await create_owner_and_strategy()
    if not owner or not strategy:
        print("❌ Failed to create owner and strategy")
        return
    
    # Step 2: Create bot without configuration
    print("\n🤖 Step 2: Creating bot without configuration...")
    db = next(get_db())
    try:
        trading_service = TradingService()
        
        bot_config = {
            "bot_name": "Demo Bot",
            "account_address": "0xabcdef1234567890abcdef1234567890abcdef12",
            "chain": "bsc",
            "initial_balance_usd": 1000.0,
            # Note: No owner_id or strategy_id - bot will be unconfigured
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
        
    finally:
        db.close()
    
    # Step 3: Simulate waiting for configuration
    print("\n⏳ Step 3: Simulating configuration wait...")
    print("   The bot would normally wait here for configuration...")
    print("   For this demo, we'll configure it after 10 seconds...")
    
    for i in range(10, 0, -1):
        print(f"   Configuring bot in {i} seconds...")
        await asyncio.sleep(1)
    
    # Step 4: Configure the bot
    print("\n⚙️ Step 4: Configuring the bot...")
    success = await configure_bot(str(bot.id), str(owner.id), str(strategy.id))
    
    if success:
        print("\n✅ Bot is now configured and ready for trading!")
        print("   You can now run the bot with: python run_bot.py --default")
        print("   Or with custom config: python run_bot.py --config your_config.json")
    else:
        print("\n❌ Failed to configure bot")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 