#!/usr/bin/env python3
"""
Simple script to run the trading bot
"""

import asyncio
import sys
import os
import logging
import json
import argparse
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot import AIPTradingBot
from models.database import get_db, TradingBot, BotOwner, TradingStrategy
from services.trading_service import TradingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

# Configuration functions removed - now using database-driven approach

async def check_bot_configuration(bot_id: str) -> bool:
    """
    Check if bot has owner and strategy configured
    
    Args:
        bot_id (str): Bot ID to check
        
    Returns:
        bool: True if bot is configured (has owner and strategy), False otherwise
    """
    try:
        db = next(get_db())
        try:
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                print(f"❌ Bot with ID {bot_id} not found")
                return False
            
            is_configured = bot.is_configured and bot.owner_id and bot.strategy_id
            if is_configured:
                print(f"✅ Bot is configured:")
                print(f"   Owner ID: {bot.owner_id}")
                print(f"   Strategy ID: {bot.strategy_id}")
                print(f"   Strategy Type: {bot.strategy.strategy_type if bot.strategy else 'Unknown'}")
            else:
                print(f"⏳ Bot is not configured:")
                print(f"   Owner ID: {bot.owner_id or 'None'}")
                print(f"   Strategy ID: {bot.strategy_id or 'None'}")
                print(f"   Is Configured: {bot.is_configured}")
            
            return is_configured
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error checking bot configuration: {e}")
        return False

async def wait_for_configuration(bot_id: str, check_interval_minutes: int = 5):
    """
    Wait for bot to be configured with owner and strategy
    
    Args:
        bot_id (str): Bot ID to monitor
        check_interval_minutes (int): How often to check for configuration (default: 5 minutes)
    """
    print(f"\n⏳ Waiting for bot configuration...")
    print(f"   Check interval: {check_interval_minutes} minutes")
    print(f"   Press Ctrl+C to stop waiting")
    
    check_interval_seconds = check_interval_minutes * 60
    check_count = 0
    
    while True:
        check_count += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n🔄 Configuration check #{check_count} at {current_time}")
        
        # Check if bot is configured
        if await check_bot_configuration(bot_id):
            print(f"✅ Bot is ready to start trading!")
            return True
        
        # Wait before next check
        print(f"⏳ Next check in {check_interval_minutes} minutes...")
        
        # Sleep in small chunks to allow for graceful shutdown
        remaining_time = check_interval_seconds
        while remaining_time > 0:
            chunk_sleep = min(remaining_time, 30)  # Sleep max 30 seconds at a time
            await asyncio.sleep(chunk_sleep)
            remaining_time -= chunk_sleep

# ===== BOT MANAGEMENT FUNCTIONS =====

async def create_new_bot(config: Dict[str, Any]) -> Optional[str]:
    """
    Create a new trading bot
    
    Args:
        config (dict): Bot configuration
        
    Returns:
        str: Bot ID if successful, None otherwise
    """
    try:
        db = next(get_db())
        try:
            # Validate owner exists if provided
            if config.get('owner_id'):
                owner = db.query(BotOwner).filter(BotOwner.id == config['owner_id']).first()
                if not owner:
                    print(f"❌ Owner with ID {config['owner_id']} not found")
                    return None
            
            # Validate strategy exists if provided
            if config.get('strategy_id'):
                strategy = db.query(TradingStrategy).filter(TradingStrategy.id == config['strategy_id']).first()
                if not strategy:
                    print(f"❌ Strategy with ID {config['strategy_id']} not found")
                    return None
            
            # Create new bot
            new_bot = TradingBot(
                id=uuid.uuid4(),
                bot_name=config['bot_name'],
                account_address=config['account_address'],
                chain=config['chain'],
                initial_balance_usd=config['initial_balance_usd'],
                current_balance_usd=config['initial_balance_usd'],
                total_assets_usd=config['initial_balance_usd'],
                owner_id=config.get('owner_id'),
                strategy_id=config.get('strategy_id'),
                is_active=False,  # Default to inactive
                is_configured=bool(config.get('owner_id') and config.get('strategy_id')),
                total_trades=0,
                profitable_trades=0,
                total_profit_usd=0,
                max_drawdown_percentage=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_bot)
            db.commit()
            db.refresh(new_bot)
            
            print(f"✅ Bot created successfully with ID: {new_bot.id}")
            return str(new_bot.id)
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error creating bot: {e}")
        return None

async def update_bot_strategy(bot_id: str, strategy_id: str) -> bool:
    """
    Update bot strategy
    
    Args:
        bot_id (str): Bot ID
        strategy_id (str): Strategy ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = next(get_db())
        try:
            # Find the bot
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                print(f"❌ Bot with ID {bot_id} not found")
                return False
            
            # Validate strategy exists
            strategy = db.query(TradingStrategy).filter(TradingStrategy.id == strategy_id).first()
            if not strategy:
                print(f"❌ Strategy with ID {strategy_id} not found")
                return False
            
            # Update bot strategy
            bot.strategy_id = strategy_id
            bot.is_configured = bool(bot.owner_id and strategy_id)
            bot.updated_at = datetime.utcnow()
            
            db.commit()
            
            print(f"✅ Bot strategy updated successfully")
            print(f"   Bot ID: {bot_id}")
            print(f"   Strategy: {strategy.strategy_name} ({strategy.strategy_type})")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error updating bot strategy: {e}")
        return False

async def update_bot_status(bot_id: str, is_active: bool) -> bool:
    """
    Update bot status (active/inactive)
    
    Args:
        bot_id (str): Bot ID
        is_active (bool): Active status
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = next(get_db())
        try:
            # Find the bot
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                print(f"❌ Bot with ID {bot_id} not found")
                return False
            
            # Check if bot is configured before activating
            if is_active and not bot.is_configured:
                print(f"❌ Bot must be configured (have owner and strategy) before activation")
                return False
            
            # Update status
            bot.is_active = is_active
            bot.updated_at = datetime.utcnow()
            
            db.commit()
            
            status_text = "activated" if is_active else "deactivated"
            print(f"✅ Bot {status_text} successfully")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error updating bot status: {e}")
        return False

async def should_run_bot(bot_id: str) -> bool:
    """
    Check if bot should run based on status and trading interval
    
    Args:
        bot_id (str): Bot ID
        
    Returns:
        bool: True if bot should run, False otherwise
    """
    try:
        db = next(get_db())
        try:
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                return False
            
            # Check if bot is active and configured
            if not bot.is_active or not bot.is_configured:
                return False
            
            # Check if bot has strategy with polling interval
            if not bot.strategy or not bot.strategy.polling_interval_hours:
                return False
            
            # Check if enough time has passed since last activity
            if bot.last_activity_at:
                time_since_last_run = datetime.utcnow() - bot.last_activity_at
                required_interval = timedelta(hours=float(bot.strategy.polling_interval_hours))
                
                if time_since_last_run < required_interval:
                    return False
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error checking if bot should run: {e}")
        return False

async def update_bot_trading_time(bot_id: str) -> bool:
    """
    Update bot's last activity time
    
    Args:
        bot_id (str): Bot ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = next(get_db())
        try:
            bot = db.query(TradingBot).filter(TradingBot.id == bot_id).first()
            if not bot:
                return False
            
            bot.last_activity_at = datetime.utcnow()
            bot.updated_at = datetime.utcnow()
            
            db.commit()
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error updating bot trading time: {e}")
        return False

async def load_bots_from_database():
    """Load all active and configured bots from database"""
    try:
        db = next(get_db())
        try:
            bots = db.query(TradingBot).filter(
                TradingBot.is_active == True,
                TradingBot.is_configured == True
            ).all()
            
            bot_configs = []
            for bot in bots:
                config = {
                    'bot_id': str(bot.id),
                    'bot_name': bot.bot_name,
                    'account_address': bot.account_address,
                    'chain': bot.chain,
                    'initial_balance_usd': float(bot.initial_balance_usd),
                    'owner_id': str(bot.owner_id) if bot.owner_id else None,
                    'strategy_id': str(bot.strategy_id) if bot.strategy_id else None,
                    'is_active': bot.is_active
                }
                bot_configs.append(config)
            
            return bot_configs
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Error loading bots from database: {e}")
        logging.error(f"Error loading bots from database: {e}", exc_info=True)
        return []

async def run_all_bots():
    """Run all active bots from database"""
    print("🤖 Loading bots from database...")
    bot_configs = await load_bots_from_database()
    
    if not bot_configs:
        print("📭 No active and configured bots found in database")
        return
    
    print(f"📊 Found {len(bot_configs)} active bots to run")
    
    for config in bot_configs:
        try:
            print(f"\n🚀 Starting bot: {config['bot_name']} (ID: {config['bot_id']})")
            
            # Create and run bot
            bot = AIPTradingBot(config)
            if await bot.initialize():
                print(f"✅ Bot {config['bot_name']} initialized successfully")
                await bot.run()
                # Update last activity time
                await update_bot_trading_time(config['bot_id'])
                print(f"✅ Bot {config['bot_name']} completed trading cycle")
            else:
                print(f"❌ Failed to initialize bot {config['bot_name']}")
                
        except Exception as e:
            print(f"❌ Error running bot {config['bot_name']}: {e}")
            logging.error(f"Error running bot {config['bot_name']}: {e}", exc_info=True)
            continue

async def run_bot_polling(polling_interval_minutes: int = 5):
    """
    Run bot polling mechanism - check all bots and run eligible ones
    
    Args:
        polling_interval_minutes (int): How often to check bots (default: 5 minutes)
    """
    print(f"\n🔄 Starting bot polling mechanism...")
    print(f"   Polling interval: {polling_interval_minutes} minutes")
    print(f"   Press Ctrl+C to stop polling")
    
    polling_interval_seconds = polling_interval_minutes * 60
    poll_count = 0
    
    while True:
        poll_count += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n🔄 Polling cycle #{poll_count} at {current_time}")
        
        try:
            db = next(get_db())
            try:
                # Get all active and configured bots
                bots = db.query(TradingBot).filter(
                    TradingBot.is_active == True,
                    TradingBot.is_configured == True
                ).all()
                
                print(f"📊 Found {len(bots)} active and configured bots")
                
                for bot in bots:
                    try:
                        if await should_run_bot(str(bot.id)):
                            print(f"🚀 Running bot: {bot.bot_name} (ID: {bot.id})")
                            
                            # Create bot config from database
                            bot_config = {
                                "bot_id": str(bot.id),
                                "bot_name": bot.bot_name,
                                "account_address": bot.account_address,
                                "chain": bot.chain,
                                "initial_balance_usd": float(bot.initial_balance_usd),
                                "owner_id": str(bot.owner_id) if bot.owner_id else None,
                                "strategy_id": str(bot.strategy_id) if bot.strategy_id else None,
                                "is_active": bot.is_active
                            }
                            
                            # Run bot once
                            trading_bot = AIPTradingBot(bot_config)
                            if await trading_bot.initialize():
                                # Update trading time before running
                                await update_bot_trading_time(str(bot.id))
                                
                                # Run one trading cycle
                                await trading_bot._trading_cycle()
                                print(f"✅ Bot {bot.bot_name} completed trading cycle")
                            else:
                                print(f"❌ Failed to initialize bot {bot.bot_name}")
                        else:
                            # Check why bot shouldn't run
                            if bot.last_activity_at and bot.strategy:
                                time_since_last = datetime.utcnow() - bot.last_activity_at
                                required_interval = timedelta(hours=float(bot.strategy.polling_interval_hours))
                                remaining_time = required_interval - time_since_last
                                if remaining_time.total_seconds() > 0:
                                    hours = int(remaining_time.total_seconds() // 3600)
                                    minutes = int((remaining_time.total_seconds() % 3600) // 60)
                                    print(f"⏳ Bot {bot.bot_name}: {hours}h {minutes}m until next run")
                    
                    except Exception as e:
                        print(f"❌ Error running bot {bot.bot_name}: {e}")
                        continue
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error in polling cycle: {e}")
        
        # Wait before next polling cycle
        print(f"⏳ Next polling cycle in {polling_interval_minutes} minutes...")
        
        # Sleep in small chunks to allow for graceful shutdown
        remaining_time = polling_interval_seconds
        while remaining_time > 0:
            chunk_sleep = min(remaining_time, 30)  # Sleep max 30 seconds at a time
            await asyncio.sleep(chunk_sleep)
            remaining_time -= chunk_sleep

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='AIP DEX Trading Bot')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run all bots command (default behavior)
    run_parser = subparsers.add_parser('run', help='Run all active bots from database')
    run_parser.add_argument(
        '--once',
        action='store_true',
        help='Run all bots once and exit (default: continuous polling)'
    )
    
    # Create bot command
    create_parser = subparsers.add_parser('create', help='Create a new trading bot')
    create_parser.add_argument('--name', type=str, required=True, help='Bot name')
    create_parser.add_argument('--address', type=str, required=True, help='Account address')
    create_parser.add_argument('--chain', type=str, required=True, help='Blockchain chain')
    create_parser.add_argument('--balance', type=float, required=True, help='Initial balance in USD')
    create_parser.add_argument('--owner-id', type=str, help='Owner ID')
    create_parser.add_argument('--strategy-id', type=str, help='Strategy ID')
    
    # Update strategy command
    strategy_parser = subparsers.add_parser('set-strategy', help='Update bot strategy')
    strategy_parser.add_argument('--bot-id', type=str, required=True, help='Bot ID')
    strategy_parser.add_argument('--strategy-id', type=str, required=True, help='Strategy ID')
    
    # Update status command
    status_parser = subparsers.add_parser('set-status', help='Update bot status')
    status_parser.add_argument('--bot-id', type=str, required=True, help='Bot ID')
    status_parser.add_argument('--active', action='store_true', help='Activate bot')
    status_parser.add_argument('--inactive', action='store_true', help='Deactivate bot')
    
    # Polling command
    poll_parser = subparsers.add_parser('poll', help='Run bot polling mechanism')
    poll_parser.add_argument('--interval', type=int, default=5,
                            help='Polling interval in minutes (default: 5)')
    
    args = parser.parse_args()
    
    print("🤖 AIP DEX Trading Bot")
    print("=" * 50)
    
    try:
        # Handle different commands
        if args.command == 'create':
            # Create new bot
            config = {
                'bot_name': args.name,
                'account_address': args.address,
                'chain': args.chain,
                'initial_balance_usd': args.balance,
                'owner_id': args.owner_id,
                'strategy_id': args.strategy_id
            }
            
            bot_id = await create_new_bot(config)
            if bot_id:
                print(f"\n✅ Bot created successfully!")
                print(f"   Bot ID: {bot_id}")
                print(f"   Name: {args.name}")
                print(f"   Chain: {args.chain}")
                print(f"   Address: {args.address}")
                print(f"   Balance: ${args.balance:,.2f}")
                if args.owner_id:
                    print(f"   Owner ID: {args.owner_id}")
                if args.strategy_id:
                    print(f"   Strategy ID: {args.strategy_id}")
            else:
                print("❌ Failed to create bot")
            return
        
        elif args.command == 'set-strategy':
            # Update bot strategy
            success = await update_bot_strategy(args.bot_id, args.strategy_id)
            if not success:
                print("❌ Failed to update bot strategy")
            return
        
        elif args.command == 'set-status':
            # Update bot status
            if args.active and args.inactive:
                print("❌ Cannot specify both --active and --inactive")
                return
            
            if not args.active and not args.inactive:
                print("❌ Must specify either --active or --inactive")
                return
            
            is_active = args.active
            success = await update_bot_status(args.bot_id, is_active)
            if not success:
                print("❌ Failed to update bot status")
            return
        
        elif args.command == 'poll':
            # Run polling mechanism
            await run_bot_polling(args.interval)
            return
        
        elif args.command == 'run':
            # Run all bots from database
            if args.once:
                # Run all bots once and exit
                await run_all_bots()
            else:
                # Start continuous polling (default behavior)
                await run_bot_polling(5)  # Default 5 minutes interval
            
        elif args.command is None:
            # Default behavior when no command is specified
            # Run all bots from database with continuous polling
            print("🤖 Starting bot management system...")
            print("📊 Running all active bots from database")
            await run_bot_polling(5)  # Default 5 minutes interval
        
        else:
            print(f"❌ Unknown command: {args.command}")
            return
            
    except Exception as e:
        print(f"❌ Error: {e}")
        logging.error(f"Trading bot error: {e}", exc_info=True)
        sys.exit(1)

# run_single_bot function removed - now using database-driven approach

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        logging.info("Trading bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        logging.error(f"Trading bot error: {e}", exc_info=True)
        sys.exit(1)