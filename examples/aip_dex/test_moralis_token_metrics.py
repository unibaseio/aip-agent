#!/usr/bin/env python3
"""
Test script for Moralis-based TokenMetric calculation
"""

import asyncio
import os
from sqlalchemy.orm import Session

from models.database import get_db, Token, TokenMetric
from services.token_service import TokenService

async def test_moralis_token_metrics():
    """Test the new Moralis-based TokenMetric calculation"""
    
    # Initialize token service
    token_service = TokenService()
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Test with a known token (you can change this)
        test_symbol = "PEPE"
        test_contract = "0x6982508145454ce325ddbe47a25d4ec3d2311933"  # PEPE on BSC
        test_chain = "bsc"
        
        print(f"Testing Moralis-based TokenMetric calculation for {test_symbol}")
        print("=" * 60)
        
        # Step 1: Get or create token
        token = await token_service.get_or_create_token(
            db=db,
            symbol=test_symbol,
            contract_address=test_contract,
            chain=test_chain
        )
        
        if not token:
            print(f"❌ Failed to create/get token {test_symbol}")
            return
        
        print(f"✅ Token found/created: {token.symbol} ({token.contract_address})")
        
        # Step 2: Calculate TokenMetric using new Moralis-based approach
        print(f"\n🔍 Calculating TokenMetric from Moralis data...")
        
        token_metric = await token_service.calculate_token_metrics(db, str(token.id))
        
        if not token_metric:
            print(f"❌ Failed to calculate TokenMetric for {test_symbol}")
            return
        
        print(f"✅ TokenMetric calculated successfully!")
        
        # Step 3: Display results
        print(f"\n📊 TokenMetric Results for {test_symbol}:")
        print("-" * 50)
        
        # Price data
        print(f"💰 Price (USD): ${float(token_metric.avg_price_usd or 0):.10f}")
        print(f"💰 Market Cap: ${float(token_metric.market_cap or 0):,.2f}")
        
        # Volume data
        print(f"📈 Total Volume 24h: ${float(token_metric.total_volume_24h or 0):,.2f}")
        print(f"💧 Total Liquidity: ${float(token_metric.total_liquidity_usd or 0):,.2f}")
        
        # Moralis analytics
        print(f"\n🔥 Moralis Analytics:")
        print(f"  🟢 Buy Volume 24h: ${float(token_metric.buy_volume_24h or 0):,.2f}")
        print(f"  🔴 Sell Volume 24h: ${float(token_metric.sell_volume_24h or 0):,.2f}")
        print(f"  👥 Total Buyers 24h: {token_metric.total_buyers_24h or 0}")
        print(f"  👥 Total Sellers 24h: {token_metric.total_sellers_24h or 0}")
        print(f"  🏦 Unique Wallets 24h: {token_metric.unique_wallets_24h or 0}")
        
        # Price changes
        print(f"\n📊 Price Changes:")
        print(f"  5m: {float(token_metric.price_change_5m or 0):.2f}%")
        print(f"  1h: {float(token_metric.price_change_1h or 0):.2f}%")
        print(f"  6h: {float(token_metric.price_change_6h or 0):.2f}%")
        print(f"  24h: {float(token_metric.price_change_24h or 0):.2f}%")
        
        # Holder stats
        print(f"\n👥 Holder Statistics:")
        print(f"  Total Holders: {token_metric.holder_count or 0}")
        print(f"  Holder Change 24h: {token_metric.holder_change_24h or 0} ({float(token_metric.holder_change_24h_percent or 0):.2f}%)")
        print(f"  Holder Change 7d: {token_metric.holder_change_7d or 0} ({float(token_metric.holder_change_7d_percent or 0):.2f}%)")
        
        # Holder distribution
        print(f"\n🐋 Holder Distribution:")
        print(f"  Whales: {token_metric.whales_count or 0}")
        print(f"  Sharks: {token_metric.sharks_count or 0}")
        print(f"  Dolphins: {token_metric.dolphins_count or 0}")
        print(f"  Fish: {token_metric.fish_count or 0}")
        
        # Supply distribution
        print(f"\n💎 Supply Distribution:")
        print(f"  Top 10 holders: {float(token_metric.top10_supply_percent or 0):.2f}%")
        print(f"  Top 25 holders: {float(token_metric.top25_supply_percent or 0):.2f}%")
        print(f"  Top 50 holders: {float(token_metric.top50_supply_percent or 0):.2f}%")
        print(f"  Top 100 holders: {float(token_metric.top100_supply_percent or 0):.2f}%")
        
        # Signals
        print(f"\n🎯 Trading Signals:")
        print(f"  Trend Direction: {token_metric.trend_direction or 'Unknown'}")
        print(f"  Signal Strength: {token_metric.signal_strength or 0:.2f}")
        print(f"  Breakout Signal: {'🚀 Yes' if token_metric.breakout_signal else '❌ No'}")
        
        # Meta info
        print(f"\n🔧 Meta Information:")
        print(f"  Pools Count: {token_metric.pools_count}")
        print(f"  Last Calculation: {token_metric.last_calculation_at}")
        print(f"  Data Source: Moralis API")
        
        print(f"\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        db.close()
        await token_service.close()

async def main():
    """Main entry point"""
    print("🧪 Moralis TokenMetric Calculation Test")
    print("=" * 60)
    
    # Check if Moralis API key is set
    if not os.getenv("MORALIS_API_KEY"):
        print("❌ MORALIS_API_KEY environment variable is not set!")
        print("Please set your Moralis API key before running this test.")
        return
    
    await test_moralis_token_metrics()

if __name__ == "__main__":
    asyncio.run(main()) 