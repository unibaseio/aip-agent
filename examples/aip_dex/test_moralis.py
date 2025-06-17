#!/usr/bin/env python3
"""
Test script for Moralis provider functionality
Tests token analytics and holder stats APIs
"""

import asyncio
import os
from dotenv import load_dotenv
from data_aggregator.moralis import MoralisProvider

load_dotenv()

async def test_moralis_apis():
    """Test Moralis token analytics and holder stats APIs"""
    
    # Initialize provider
    moralis = MoralisProvider()
    
    # Test tokens - use BEEPER from design document
    test_tokens = [
        {
            "address": "0x238950013FA29A3575EB7a3D99C00304047a77b5",
            "symbol": "BEEPER",
            "chain": "bsc"
        }
    ]
    
    print("🧪 Testing Moralis Provider APIs\n")
    print("=" * 60)
    
    for token in test_tokens:
        print(f"\n📊 Testing {token['symbol']} ({token['address'][:10]}...)")
        print("-" * 50)
        
        try:
            # Test Token Analytics
            print("🔍 Fetching Token Analytics...")
            analytics = await moralis.get_token_analytics(
                token["address"], 
                token["chain"]
            )
            
            if analytics:
                print("✅ Token Analytics Success:")
                print(f"   📈 Price: ${analytics.get('usd_price', 0):.8f}")
                print(f"   💰 Buy Volume 24h: ${analytics.get('buy_volume_24h', 0):,.2f}")
                print(f"   💸 Sell Volume 24h: ${analytics.get('sell_volume_24h', 0):,.2f}")
                print(f"   👥 Unique Wallets 24h: {analytics.get('unique_wallets_24h', 0)}")
                print(f"   📊 Price Change 24h: {analytics.get('price_change_24h', 0):.2f}%")
                print(f"   🏦 Total Liquidity: ${analytics.get('total_liquidity_usd', 0):,.2f}")
            else:
                print("❌ Token Analytics Failed")
            
            # Test Holder Stats  
            await asyncio.sleep(5)
            print("\n🏛️ Fetching Holder Stats...")
            holder_stats = await moralis.get_holder_stats(
                token["address"],
                token["chain"]
            )
            
            if holder_stats:
                print("✅ Holder Stats Success:")
                print(f"   👥 Total Holders: {holder_stats.get('total_holders', 0):,}")
                print(f"   📈 Holder Change 24h: {holder_stats.get('holder_change_24h', 0):+d} ({holder_stats.get('holder_change_24h_percent', 0):+.2f}%)")
                print(f"   🐋 Whales: {holder_stats.get('whales_count', 0)}")
                print(f"   🦈 Sharks: {holder_stats.get('sharks_count', 0)}")
                print(f"   🐬 Dolphins: {holder_stats.get('dolphins_count', 0)}")
                print(f"   🔥 Top 10 Supply: {holder_stats.get('top10_supply_percent', 0):.1f}%")
                print(f"   📊 Top 50 Supply: {holder_stats.get('top50_supply_percent', 0):.1f}%")
            else:
                print("❌ Holder Stats Failed")
            
            # Test Combined Stats
            print("\n🔗 Fetching Combined Stats...")
            combined = await moralis.get_token_stats(
                token["address"],
                token["chain"]
            )
            
            if combined:
                print("✅ Combined Stats Success:")
                print(f"   📊 Total Volume 24h: ${combined.get('total_volume_24h', 0):,.2f}")
                print(f"   ⚖️ Buy/Sell Ratio: {combined.get('buy_sell_ratio_24h', 0):.2f}")
                print(f"   💵 Net Volume 24h: ${combined.get('net_volume_24h', 0):,.2f}")
                print(f"   🎯 Data Sources: Analytics + Holders")
            else:
                print("❌ Combined Stats Failed")
                
        except Exception as e:
            print(f"❌ Error testing {token['symbol']}: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Moralis API Testing Complete")
    
    # Close the provider
    await moralis.close()

async def test_moralis_error_handling():
    """Test error handling with invalid inputs"""
    print("\n🧪 Testing Error Handling\n")
    print("=" * 40)
    
    moralis = MoralisProvider()
    
    # Test with invalid token address
    print("🔍 Testing invalid token address...")
    result = await moralis.get_token_analytics("0xinvalid", "bsc")
    print(f"   Result: {'✅ Handled gracefully' if result is None else '❌ Did not handle properly'}")
    
    # Test with invalid chain
    print("\n🔍 Testing invalid chain...")
    result = await moralis.get_holder_stats(
        "0x238950013FA29A3575EB7a3D99C00304047a77b5", 
        "invalid_chain"
    )
    print(f"   Result: {'✅ Handled gracefully' if result is None else '❌ Did not handle properly'}")
    
    await moralis.close()

if __name__ == "__main__":
    # Check if API key is set
    api_key = os.getenv("MORALIS_API_KEY")
    if not api_key:
        print("❌ MORALIS_API_KEY not found in environment variables")
        print("📝 Please set your Moralis API key in .env file:")
        print("   MORALIS_API_KEY=your_api_key_here")
        exit(1)
    
    print("🚀 Starting Moralis Provider Tests...")
    print(f"🔑 API Key: {'✅ Found' if api_key else '❌ Missing'}")
    
    # Run tests
    asyncio.run(test_moralis_apis())
    asyncio.run(test_moralis_error_handling()) 