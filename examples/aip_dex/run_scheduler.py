#!/usr/bin/env python3
"""
Simple script to run the AIP DEX Token Data Scheduler
Usage: python run_scheduler.py [--chain CHAIN] [--limit LIMIT] [--interval MINUTES]
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from scheduler import TokenDataScheduler

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run AIP DEX Token Data Scheduler")
    parser.add_argument("--chain", default="bsc", help="Blockchain chain (default: bsc)")
    parser.add_argument("--limit", type=int, default=50, help="Number of top tokens to fetch (default: 50)")
    parser.add_argument("--interval", type=int, default=61, help="Update interval in minutes (default: 61)")
    parser.add_argument("--single-run", action="store_true", help="Run once and exit (for testing)")
    parser.add_argument("--update-new-only", action="store_true", help="Only update pools for newly fetched tokens (default: update all)")
    return parser.parse_args()

def check_environment():
    """Check required environment variables"""
    required_vars = ["DATABASE_URL", "BIRDEYE_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        print("Example .env file:")
        print("DATABASE_URL=postgresql://username:password@localhost/aip_dex")
        print("BIRDEYE_API_KEY=your_birdeye_api_key_here")
        return False
    
    return True

async def main():
    """Main function"""
    args = parse_args()
    
    print("🚀 AIP DEX Token Data Scheduler")
    print("=" * 40)
    print(f"Chain: {args.chain}")
    print(f"Token limit: {args.limit}")
    print(f"Update interval: {args.interval} minute(s)")
    print(f"Single run mode: {args.single_run}")
    print(f"Update mode: {'New tokens only' if args.update_new_only else 'All database tokens'}")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create scheduler
    scheduler = TokenDataScheduler(chain=args.chain, fetch_limit=args.limit)
    
    try:
        if args.single_run:
            print("🔄 Running single update cycle...")
            await scheduler.initialize()
            await scheduler.run_single_update(update_all_tokens=not args.update_new_only)
            print("✅ Single update completed successfully!")
        else:
            print(f"🔄 Starting continuous scheduler (every {args.interval} minute(s))")
            print("Press Ctrl+C to stop...")
            await scheduler.run_scheduler(
                interval_minutes=args.interval,
                update_all_tokens=not args.update_new_only
            )
    
    except KeyboardInterrupt:
        print("\n🛑 Scheduler stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await scheduler.cleanup()
        print("🧹 Cleanup completed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0) 