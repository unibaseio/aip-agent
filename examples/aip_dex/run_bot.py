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

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot import AIPTradingBot

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
        "strategy_type", "polling_interval_hours", "min_trade_amount_usd", "is_active"
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
    
    # Create and run bot
    bot = AIPTradingBot(config)
    
    if await bot.initialize():
        print("✅ Bot initialized successfully")
        logging.info(f"Trading bot '{config['bot_name']}' initialized successfully")
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