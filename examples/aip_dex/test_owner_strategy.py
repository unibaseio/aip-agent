#!/usr/bin/env python3
"""
Simple test script for owner and strategy functionality
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

async def test_owner_strategy():
    """Test the owner and strategy functionality"""
    print("🧪 Testing Owner & Strategy Functionality")
    print("=" * 50)
    
    # Initialize database
    print("📊 Initializing database...")
    if not init_database():
        print("❌ Failed to initialize database")
        return False
    
    # Get database session
    db = next(get_db())
    
    try:
        # Initialize services
        owner_service = OwnerService()
        trading_service = TradingService()
        
        # Test 1: Create owner
        print("\n1️⃣ Testing owner creation...")
        owner_data = BotOwnerCreate(
            owner_name="Test User",
            email="test@example.com",
            wallet_address="0x1111111111111111111111111111111111111111",
            subscription_tier="basic"
        )
        
        owner = await owner_service.create_bot_owner(db, owner_data)
        if not owner:
            print("❌ Failed to create owner")
            return False
        
        print(f"✅ Created owner: {owner.owner_name}")
        
        # Test 2: Create default strategies
        print("\n2️⃣ Testing default strategy creation...")
        strategies = await owner_service.create_default_strategies(db, owner.id)
        if not strategies:
            print("❌ Failed to create default strategies")
            return False
        
        print(f"✅ Created {len(strategies)} default strategies")
        
        # Test 3: Create custom strategy
        print("\n3️⃣ Testing custom strategy creation...")
        custom_strategy_data = TradingStrategyCreate(
            strategy_name="Test Strategy",
            strategy_type="user_defined",
            risk_level="medium",
            max_position_size=Decimal("20.0"),
            stop_loss_percentage=Decimal("10.0"),
            take_profit_percentage=Decimal("25.0"),
            min_profit_threshold=Decimal("3.0"),
            max_daily_trades=15,
            llm_confidence_threshold=Decimal("0.7"),
            buy_strategy_description="Test buy strategy description",
            sell_strategy_description="Test sell strategy description",
            filter_strategy_description="Test filter strategy description",
            summary_strategy_description="Test summary strategy description"
        )
        
        custom_strategy = await owner_service.create_trading_strategy(db, owner.id, custom_strategy_data)
        if not custom_strategy:
            print("❌ Failed to create custom strategy")
            return False
        
        print(f"✅ Created custom strategy: {custom_strategy.strategy_name}")
        
        # Test 4: Create trading bot with strategy
        print("\n4️⃣ Testing trading bot creation with strategy...")
        bot_config = {
            "bot_name": "Test Bot",
            "account_address": "0x2222222222222222222222222222222222222222",
            "chain": "bsc",
            "initial_balance_usd": 1000.0,
            "owner_id": owner.id,
            "strategy_id": custom_strategy.id,
            "is_active": True
        }
        
        bot = await trading_service.create_trading_bot(db, bot_config)
        if not bot:
            print("❌ Failed to create trading bot")
            return False
        
        print(f"✅ Created trading bot: {bot.bot_name}")
        print(f"   Owner ID: {bot.owner_id}")
        print(f"   Strategy ID: {bot.strategy_id}")
        
        # Test 5: List owner's strategies
        print("\n5️⃣ Testing strategy listing...")
        owner_strategies = await owner_service.list_owner_strategies(db, owner.id)
        print(f"✅ Owner has {len(owner_strategies)} strategies:")
        for strategy in owner_strategies:
            print(f"   - {strategy.strategy_name} ({strategy.strategy_type})")
        
        # Test 6: List owner's bots
        print("\n6️⃣ Testing bot listing...")
        owner_bots = await owner_service.get_owner_bots(db, owner.id)
        print(f"✅ Owner has {len(owner_bots)} bots:")
        for bot in owner_bots:
            print(f"   - {bot.bot_name} ({bot.chain})")
        
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(test_owner_strategy())
    sys.exit(0 if success else 1) 