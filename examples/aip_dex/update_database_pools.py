#!/usr/bin/env python3
"""
Update Pool Data for All Database Tokens
This script updates pool information for all tokens already stored in the database
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from scheduler import TokenDataScheduler
from models.database import get_db, Token

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Update pool data for all tokens in database")
    parser.add_argument("--chain", default="bsc", help="Blockchain chain (default: bsc)")
    parser.add_argument("--dry-run", action="store_true", help="Show tokens that would be updated without actually updating")
    return parser.parse_args()

def check_environment():
    """Check required environment variables"""
    required_vars = ["DATABASE_URL"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    return True

async def show_database_tokens(chain: str):
    """Show all tokens in database for the given chain"""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        tokens = db.query(Token).filter(Token.chain == chain).all()
        
        if not tokens:
            print(f"❌ No tokens found in database for chain '{chain}'")
            return []
        
        print(f"📊 Found {len(tokens)} tokens in database for chain '{chain}':")
        print("-" * 80)
        print(f"{'Symbol':<15} {'Name':<30} {'Contract Address':<45}")
        print("-" * 80)
        
        for token in tokens:
            symbol = token.symbol[:14] if token.symbol else "N/A"
            name = token.name[:29] if token.name else "N/A"
            address = token.contract_address[:44] if token.contract_address else "N/A"
            print(f"{symbol:<15} {name:<30} {address:<45}")
        
        return tokens
        
    finally:
        db.close()

async def main():
    """Main function"""
    args = parse_args()
    
    print("🔄 AIP DEX Pool Data Updater")
    print("=" * 50)
    print(f"Chain: {args.chain}")
    print(f"Mode: {'Dry Run' if args.dry_run else 'Update Pools'}")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Show tokens in database
    tokens = await show_database_tokens(args.chain)
    if not tokens:
        sys.exit(1)
    
    if args.dry_run:
        print("\n✅ Dry run completed - no pools were updated")
        return
    
    # Ask for confirmation
    print(f"\n❓ Do you want to update pool data for all {len(tokens)} tokens? (y/N): ", end="")
    try:
        confirmation = input().strip().lower()
        if confirmation not in ['y', 'yes']:
            print("❌ Operation cancelled")
            return
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return
    
    # Create scheduler and update pools
    scheduler = TokenDataScheduler(chain=args.chain, fetch_limit=50)
    
    try:
        print("\n🔄 Initializing database...")
        await scheduler.initialize()
        
        print("🔄 Updating pool data for all database tokens...")
        
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Update pools for all tokens in database
            stats = await scheduler.update_token_pools(db)
            
            print("\n✅ Pool update completed!")
            print(f"📊 Statistics:")
            print(f"   - Tokens processed: {stats.get('processed_tokens', 0)}")
            print(f"   - Pools updated: {stats.get('updated_pools', 0)}")
            print(f"   - New pools created: {stats.get('new_pools', 0)}")
            print(f"   - Errors: {stats.get('errors', 0)}")
            
            if stats.get('errors', 0) > 0:
                print("⚠️  Some errors occurred during update. Check logs for details.")
            
        finally:
            db.close()
    
    except Exception as e:
        print(f"❌ Error during pool update: {e}")
        sys.exit(1)
    finally:
        await scheduler.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Update cancelled!")
        sys.exit(0) 