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
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot import AIPTradingBot
from models.database import get_db, TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

def load_config_from_file(config_path):
    """
    Load configuration from JSON file
    
    Args:
        config_path (str): Path to the configuration file
        
    Returns:
        dict: Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
        ValueError: If required config fields are missing
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in config file: {e}")
    
    # Validate required fields
    required_fields = [
        "bot_name", "account_address", "chain", "initial_balance_usd",
        "is_active"
    ]
    
    missing_fields = [field for field in required_fields if field not in config]
    if missing_fields:
        raise ValueError(f"Missing required configuration fields: {missing_fields}")
    
    return config

def get_default_config():
    """
    Get default configuration
    
    Returns:
        dict: Default configuration dictionary
    """
    return {
        "bot_name": "Test Trading Bot4",
        "account_address": "0x4234567890abcdef1234567890abcdef12345678",
        "chain": "bsc",
        "initial_balance_usd": 1000.0,
        # owner_id and strategy_id are optional - bot can be created without them
        # and configured later
        "is_active": True
    }

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

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='AIP DEX Trading Bot')
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (JSON format)'
    )
    parser.add_argument(
        '--default',
        action='store_true',
        help='Use default configuration'
    )
    parser.add_argument(
        '--wait-config',
        action='store_true',
        help='Wait for bot configuration (owner and strategy) before starting trading'
    )
    parser.add_argument(
        '--check-interval',
        type=int,
        default=5,
        help='Configuration check interval in minutes (default: 5)'
    )
    
    args = parser.parse_args()
    
    print("🤖 AIP DEX Trading Bot")
    print("=" * 50)
    
    # Load configuration
    if args.config:
        try:
            config = load_config_from_file(args.config)
            print(f"📁 Loaded configuration from: {args.config}")
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            print(f"❌ Error loading config file: {e}")
            return
    elif args.default:
        config = get_default_config()
        print("📋 Using default configuration")
    else:
        # Interactive mode - ask user for config file
        print("Choose configuration source:")
        print("1. Load from config file")
        print("2. Use default configuration")
        
        while True:
            choice = input("Enter your choice (1 or 2): ").strip()
            if choice == "1":
                config_path = input("Enter config file path: ").strip()
                try:
                    config = load_config_from_file(config_path)
                    print(f"📁 Loaded configuration from: {config_path}")
                    break
                except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
                    print(f"❌ Error loading config file: {e}")
                    continue
            elif choice == "2":
                config = get_default_config()
                print("📋 Using default configuration")
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
    
    print("📋 Configuration:")
    for key, value in config.items():
        print(f"   {key}: {value}")
    
    print("\n🚀 Starting bot...")
    
    # Create and initialize bot
    bot = AIPTradingBot(config)
    
    if await bot.initialize():
        print("✅ Bot initialized successfully")
        logging.info(f"Trading bot '{config['bot_name']}' initialized successfully")
        
        # Check if we should wait for configuration
        if args.wait_config or not config.get('owner_id') or not config.get('strategy_id'):
            print("\n🔍 Checking bot configuration status...")
            
            # Wait for configuration if needed
            if not await check_bot_configuration(bot.bot_id):
                print(f"\n⏳ Bot is not configured. Waiting for owner and strategy...")
                await wait_for_configuration(bot.bot_id, args.check_interval)
        
        # Start trading
        await bot.run()
    else:
        print("❌ Failed to initialize bot")
        logging.error(f"Failed to initialize trading bot '{config['bot_name']}'")

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