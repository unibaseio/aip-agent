#!/usr/bin/env python3
"""
Metamask Login and Bot Claiming Example

This script demonstrates the complete workflow:
1. Metamask authentication
2. BotOwner account creation
3. Viewing unclaimed bots
4. Claiming bots
5. Creating strategies
6. Configuring bots with strategies
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timezone
from decimal import Decimal

# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_db, init_database
from services.owner_service import OwnerService
from services.trading_service import TradingService
from api.schemas import BotOwnerCreate, TradingStrategyCreate

class MetamaskLoginDemo:
    """Demonstration of Metamask login and bot claiming workflow"""
    
    def __init__(self):
        self.owner_service = OwnerService()
        self.trading_service = TradingService()
        self.current_owner = None
        self.created_strategies = []
        self.claimed_bots = []
    
    async def simulate_metamask_login(self, wallet_address: str) -> bool:
        """
        Simulate Metamask login process
        
        Args:
            wallet_address (str): User's wallet address
            
        Returns:
            bool: True if login successful, False otherwise
        """
        print(f"\n🔐 Step 1: Metamask Login Simulation")
        print("-" * 50)
        print(f"Wallet Address: {wallet_address}")
        
        db = next(get_db())
        try:
            # Check if owner exists
            existing_owner = db.query(BotOwner).filter(
                BotOwner.wallet_address == wallet_address
            ).first()
            
            if existing_owner:
                print(f"✅ Existing user found:")
                print(f"   Owner ID: {existing_owner.id}")
                print(f"   Owner Name: {existing_owner.owner_name}")
                print(f"   Email: {existing_owner.email}")
                print(f"   Subscription: {existing_owner.subscription_tier}")
                self.current_owner = existing_owner
                return True
            
            # Create new owner (simulating automatic account creation)
            print(f"🆕 Creating new user account...")
            
            owner_data = BotOwnerCreate(
                owner_name=f"User_{wallet_address[:8]}",
                email=f"{wallet_address[:8]}@metamask.user",
                wallet_address=wallet_address,
                phone="+1234567890",
                subscription_tier="basic",
                max_bots_allowed=5
            )
            
            new_owner = await self.owner_service.create_bot_owner(db, owner_data)
            if not new_owner:
                print("❌ Failed to create owner account")
                return False
            
            print(f"✅ New user account created:")
            print(f"   Owner ID: {new_owner.id}")
            print(f"   Owner Name: {new_owner.owner_name}")
            print(f"   Email: {new_owner.email}")
            print(f"   Subscription: {new_owner.subscription_tier}")
            print(f"   Max Bots Allowed: {new_owner.max_bots_allowed}")
            
            self.current_owner = new_owner
            return True
            
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
        finally:
            db.close()
    
    async def create_default_strategies(self) -> bool:
        """
        Create default strategies for the user
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.current_owner:
            print("❌ No current owner. Please login first.")
            return False
        
        print(f"\n📈 Step 2: Creating Default Strategies")
        print("-" * 50)
        
        db = next(get_db())
        try:
            strategies = await self.owner_service.create_default_strategies(db, self.current_owner.id)
            if not strategies:
                print("❌ Failed to create default strategies")
                return False
            
            print(f"✅ Created {len(strategies)} default strategies:")
            self.created_strategies = strategies
            
            for strategy in strategies:
                print(f"   📊 {strategy.strategy_name}")
                print(f"      Type: {strategy.strategy_type}")
                print(f"      Risk Level: {strategy.risk_level}")
                print(f"      Max Position: {float(strategy.max_position_size)}%")
                print(f"      Stop Loss: {float(strategy.stop_loss_percentage)}%")
                print(f"      Take Profit: {float(strategy.take_profit_percentage)}%")
                print()
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating strategies: {e}")
            return False
        finally:
            db.close()
    
    async def view_unclaimed_bots(self) -> list:
        """
        View all unclaimed bots
        
        Returns:
            list: List of unclaimed bots
        """
        print(f"\n🤖 Step 3: Viewing Unclaimed Bots")
        print("-" * 50)
        
        db = next(get_db())
        try:
            from models.database import TradingBot
            
            unclaimed_bots = db.query(TradingBot).filter(
                TradingBot.owner_id.is_(None)
            ).all()
            
            if not unclaimed_bots:
                print("ℹ️ No unclaimed bots available")
                return []
            
            print(f"✅ Found {len(unclaimed_bots)} unclaimed bots:")
            
            for i, bot in enumerate(unclaimed_bots, 1):
                print(f"   {i}. {bot.bot_name}")
                print(f"      Address: {bot.account_address}")
                print(f"      Chain: {bot.chain}")
                print(f"      Balance: ${float(bot.current_balance_usd):,.2f}")
                print(f"      Status: {'Active' if bot.is_active else 'Inactive'}")
                print()
            
            return unclaimed_bots
            
        except Exception as e:
            print(f"❌ Error viewing unclaimed bots: {e}")
            return []
        finally:
            db.close()
    
    async def claim_bot(self, bot_id: str) -> bool:
        """
        Claim a bot (set owner_id)
        
        Args:
            bot_id (str): Bot ID to claim
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.current_owner:
            print("❌ No current owner. Please login first.")
            return False
        
        print(f"\n🎯 Step 4: Claiming Bot {bot_id}")
        print("-" * 50)
        
        db = next(get_db())
        try:
            from models.database import TradingBot
            
            # Get bot
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                print(f"❌ Bot with ID {bot_id} not found")
                return False
            
            if bot.owner_id:
                print(f"❌ Bot is already claimed by owner {bot.owner_id}")
                return False
            
            # Claim the bot
            bot.owner_id = self.current_owner.id
            bot.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            print(f"✅ Successfully claimed bot:")
            print(f"   Bot Name: {bot.bot_name}")
            print(f"   Bot ID: {bot.id}")
            print(f"   Owner ID: {bot.owner_id}")
            print(f"   Status: Claimed (not configured)")
            
            self.claimed_bots.append(bot)
            return True
            
        except Exception as e:
            print(f"❌ Error claiming bot: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    async def create_custom_strategy(self) -> bool:
        """
        Create a custom strategy for the user
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.current_owner:
            print("❌ No current owner. Please login first.")
            return False
        
        print(f"\n🎨 Step 5: Creating Custom Strategy")
        print("-" * 50)
        
        db = next(get_db())
        try:
            strategy_data = TradingStrategyCreate(
                strategy_name="My Custom Strategy",
                strategy_type="user_defined",
                risk_level="medium",
                max_position_size=Decimal("25.0"),
                stop_loss_percentage=Decimal("8.0"),
                take_profit_percentage=Decimal("30.0"),
                min_profit_threshold=Decimal("3.0"),
                max_daily_trades=20,
                llm_confidence_threshold=Decimal("0.75"),
                buy_strategy_description="Custom buy strategy: Look for tokens with strong momentum and increasing holders",
                sell_strategy_description="Custom sell strategy: Exit when momentum weakens or profit target reached",
                filter_strategy_description="Custom filter: Market cap > $1M, volume > $100K, positive price momentum",
                summary_strategy_description="A balanced custom strategy combining momentum and mean reversion principles"
            )
            
            custom_strategy = await self.owner_service.create_trading_strategy(
                db, self.current_owner.id, strategy_data
            )
            
            if not custom_strategy:
                print("❌ Failed to create custom strategy")
                return False
            
            print(f"✅ Created custom strategy:")
            print(f"   Strategy Name: {custom_strategy.strategy_name}")
            print(f"   Strategy ID: {custom_strategy.id}")
            print(f"   Type: {custom_strategy.strategy_type}")
            print(f"   Risk Level: {custom_strategy.risk_level}")
            print(f"   Max Position: {float(custom_strategy.max_position_size)}%")
            print(f"   Stop Loss: {float(custom_strategy.stop_loss_percentage)}%")
            print(f"   Take Profit: {float(custom_strategy.take_profit_percentage)}%")
            
            self.created_strategies.append(custom_strategy)
            return True
            
        except Exception as e:
            print(f"❌ Error creating custom strategy: {e}")
            return False
        finally:
            db.close()
    
    async def configure_bot_with_strategy(self, bot_id: str, strategy_id: str) -> bool:
        """
        Configure a bot with a strategy
        
        Args:
            bot_id (str): Bot ID to configure
            strategy_id (str): Strategy ID to assign
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.current_owner:
            print("❌ No current owner. Please login first.")
            return False
        
        print(f"\n⚙️ Step 6: Configuring Bot {bot_id} with Strategy {strategy_id}")
        print("-" * 50)
        
        db = next(get_db())
        try:
            configured_bot = await self.trading_service.configure_bot(
                db, bot_id, self.current_owner.id, strategy_id
            )
            
            if not configured_bot:
                print("❌ Failed to configure bot")
                return False
            
            print(f"✅ Successfully configured bot:")
            print(f"   Bot Name: {configured_bot.bot_name}")
            print(f"   Bot ID: {configured_bot.id}")
            print(f"   Owner ID: {configured_bot.owner_id}")
            print(f"   Strategy ID: {configured_bot.strategy_id}")
            print(f"   Is Configured: {configured_bot.is_configured}")
            print(f"   Status: Ready for trading!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error configuring bot: {e}")
            return False
        finally:
            db.close()
    
    async def list_my_bots(self) -> list:
        """
        List all bots owned by current user
        
        Returns:
            list: List of user's bots
        """
        if not self.current_owner:
            print("❌ No current owner. Please login first.")
            return []
        
        print(f"\n📋 Step 7: Listing My Bots")
        print("-" * 50)
        
        db = next(get_db())
        try:
            owner_bots = await self.owner_service.get_owner_bots(db, self.current_owner.id)
            
            if not owner_bots:
                print("ℹ️ No bots owned by current user")
                return []
            
            print(f"✅ Found {len(owner_bots)} bots owned by current user:")
            
            for i, bot in enumerate(owner_bots, 1):
                print(f"   {i}. {bot.bot_name}")
                print(f"      Bot ID: {bot.id}")
                print(f"      Address: {bot.account_address}")
                print(f"      Chain: {bot.chain}")
                print(f"      Balance: ${float(bot.current_balance_usd):,.2f}")
                print(f"      Strategy ID: {bot.strategy_id or 'None'}")
                print(f"      Is Configured: {bot.is_configured}")
                print(f"      Status: {'Active' if bot.is_active else 'Inactive'}")
                print()
            
            return owner_bots
            
        except Exception as e:
            print(f"❌ Error listing bots: {e}")
            return []
        finally:
            db.close()
    
    async def run_demo(self):
        """Run the complete Metamask login and bot claiming demo"""
        print("🤖 AIP DEX Trading Bot - Metamask Login & Bot Claiming Demo")
        print("=" * 70)
        
        # Initialize database
        if not init_database():
            print("❌ Failed to initialize database")
            return
        
        # Step 1: Simulate Metamask login
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"
        if not await self.simulate_metamask_login(wallet_address):
            print("❌ Login failed. Exiting demo.")
            return
        
        # Step 2: Create default strategies
        if not await self.create_default_strategies():
            print("❌ Failed to create default strategies. Exiting demo.")
            return
        
        # Step 3: View unclaimed bots
        unclaimed_bots = await self.view_unclaimed_bots()
        if not unclaimed_bots:
            print("ℹ️ No unclaimed bots available. Creating some for demo...")
            await self.create_demo_bots()
            unclaimed_bots = await self.view_unclaimed_bots()
        
        # Step 4: Claim a bot
        if unclaimed_bots:
            first_bot = unclaimed_bots[0]
            if not await self.claim_bot(str(first_bot.id)):
                print("❌ Failed to claim bot. Exiting demo.")
                return
        
        # Step 5: Create custom strategy
        if not await self.create_custom_strategy():
            print("❌ Failed to create custom strategy. Exiting demo.")
            return
        
        # Step 6: Configure bot with strategy
        if self.claimed_bots and self.created_strategies:
            bot = self.claimed_bots[0]
            strategy = self.created_strategies[0]  # Use first default strategy
            
            if not await self.configure_bot_with_strategy(str(bot.id), str(strategy.id)):
                print("❌ Failed to configure bot. Exiting demo.")
                return
        
        # Step 7: List my bots
        await self.list_my_bots()
        
        print("\n🎉 Demo completed successfully!")
        print("=" * 70)
        print("Summary:")
        print(f"   ✅ Logged in with wallet: {wallet_address}")
        print(f"   ✅ Created owner account: {self.current_owner.owner_name}")
        print(f"   ✅ Created {len(self.created_strategies)} strategies")
        print(f"   ✅ Claimed {len(self.claimed_bots)} bots")
        print(f"   ✅ Configured bots with strategies")
        print("\nThe user can now start trading with their configured bots!")

async def create_demo_bots():
    """Create some demo bots for the demo"""
    print("\n🔧 Creating demo bots...")
    
    db = next(get_db())
    try:
        from models.database import TradingBot
        
        demo_bots = [
            {
                "bot_name": "Demo Bot 1",
                "account_address": "0x1111111111111111111111111111111111111111",
                "chain": "bsc",
                "initial_balance_usd": 1000.0,
                "current_balance_usd": 1000.0,
                "is_active": True
            },
            {
                "bot_name": "Demo Bot 2", 
                "account_address": "0x2222222222222222222222222222222222222222",
                "chain": "bsc",
                "initial_balance_usd": 2000.0,
                "current_balance_usd": 2000.0,
                "is_active": True
            },
            {
                "bot_name": "Demo Bot 3",
                "account_address": "0x3333333333333333333333333333333333333333", 
                "chain": "bsc",
                "initial_balance_usd": 1500.0,
                "current_balance_usd": 1500.0,
                "is_active": True
            }
        ]
        
        for bot_data in demo_bots:
            bot = TradingBot(**bot_data)
            db.add(bot)
        
        db.commit()
        print(f"✅ Created {len(demo_bots)} demo bots")
        
    except Exception as e:
        print(f"❌ Error creating demo bots: {e}")
        db.rollback()
    finally:
        db.close()

async def main():
    """Main function"""
    demo = MetamaskLoginDemo()
    await demo.run_demo()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo error: {e}")
        sys.exit(1) 