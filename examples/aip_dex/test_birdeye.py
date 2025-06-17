"""
快速测试BirdEye API集成
Quick test script for BirdEye API integration
"""
import asyncio
import os
from data_aggregator.birdeye import BirdEyeProvider

async def test_birdeye_basic():
    """Test basic BirdEye API functionality"""
    
    # Initialize with test API key (you can also set BIRDEYE_API_KEY environment variable)
    api_key = os.getenv("BIRDEYE_API_KEY", "")
    birdeye = BirdEyeProvider(api_key=api_key)
    
    try:
        print("🔄 Testing BirdEye API connection...")
        
        # Test 1: Get top tokens by volume (default)
        print("\n📊 Test 1: Getting top 10 tokens by 24h volume")
        result = await birdeye.get_top_tokens(
            chain="bsc", 
            sort_by="v24hUSD", 
            sort_type="desc", 
            limit=10
        )
        
        if result and result.get("tokens"):
            print(f"✅ Success! Found {result['total_tokens']} tokens")
            print(f"Chain: {result['chain']}")
            print(f"Sort by: {result['sort_by']}")
            print(f"Provider: {result['provider']}")
            
            print("\nTop 5 tokens:")
            for i, token in enumerate(result["tokens"][:5], 1):
                name = token.get('name', 'Unknown')
                symbol = token.get('symbol', 'Unknown')
                volume = token.get('v24hUSD', 0)
                price = token.get('price', 0)
                print(f"  {i}. {name} ({symbol})")
                print(f"     Price: ${price:.6f}")
                print(f"     Volume 24h: ${volume:,.0f}")
                print()
        else:
            print("❌ Failed to get token data")
            return
        
        await asyncio.sleep(5)
        # Test 2: Get top tokens by market cap
        print("\n💰 Test 2: Getting top 5 tokens by market cap")
        result_mc = await birdeye.get_top_tokens(
            chain="bsc", 
            sort_by="mc", 
            sort_type="desc", 
            limit=5
        )
        
        if result_mc and result_mc.get("tokens"):
            print(f"✅ Success! Found tokens sorted by market cap")
            for i, token in enumerate(result_mc["tokens"], 1):
                name = token.get('name', 'Unknown')
                symbol = token.get('symbol', 'Unknown')
                mc = token.get('mc', 0)
                print(f"  {i}. {name} ({symbol}) - MC: ${mc:,.0f}")
        else:
            print("❌ Failed to get market cap data")
        
        await asyncio.sleep(5)
        # Test 3: Get tokens with higher minimum liquidity
        print("\n💧 Test 3: Getting tokens with high liquidity requirement")
        result_liquidity = await birdeye.get_top_tokens(
            chain="bsc", 
            sort_by="liquidity", 
            sort_type="desc", 
            limit=5,
            min_liquidity=10000
        )
        
        if result_liquidity and result_liquidity.get("tokens"):
            print(f"✅ Success! Found high liquidity tokens")
            for i, token in enumerate(result_liquidity["tokens"], 1):
                name = token.get('name', 'Unknown')
                symbol = token.get('symbol', 'Unknown')
                liquidity = token.get('liquidity', 0)
                print(f"  {i}. {name} ({symbol}) - Liquidity: ${liquidity:,.0f}")
        else:
            print("❌ Failed to get high liquidity data")
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await birdeye.close()

async def test_birdeye_error_handling():
    """Test error handling with invalid API key"""
    print("\n🧪 Testing error handling...")
    
    # Test with invalid API key
    birdeye = BirdEyeProvider(api_key="invalid_key")
    
    try:
        result = await birdeye.get_top_tokens(chain="bsc", limit=5)
        if not result or not result.get("tokens"):
            print("✅ Error handling working correctly - no data returned with invalid key")
        else:
            print("⚠️  Unexpected: Got data with invalid API key")
    except Exception as e:
        print(f"✅ Exception caught as expected: {e}")
    finally:
        await birdeye.close()

async def main():
    """Run all tests"""
    await test_birdeye_basic()
    await test_birdeye_error_handling()

if __name__ == "__main__":
    asyncio.run(main()) 