#!/usr/bin/env python3
"""
Simple script to run the trading bot
"""

import asyncio
import sys
import os
import logging

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

async def main():
    print("🤖 AIP DEX Trading Bot")
    print("=" * 50)
    
    # Create a simple configuration
    config = {
        "bot_name": "Test Trading Bot4",
        "account_address": "0x4234567890abcdef1234567890abcdef12345678",
        "chain": "bsc",
        "initial_balance_usd": 1000.0,
        "strategy_type": "aggressive",
        "polling_interval_hours": 0.1,
        "min_trade_amount_usd": 10.0,
        "is_active": True
    }
    
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