import asyncio
import sys
import os
import pytest
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_aggregator.dex_screener import DexScreenerProvider

class TestDexScreenerProvider:
    """Test cases for DexScreenerProvider"""
    
    @pytest.fixture
    async def provider(self):
        """Create provider instance"""
        provider = DexScreenerProvider()
        yield provider
        await provider.close()
    
    async def test_search_token_by_symbol(self):
        """Test searching token by symbol"""
        provider = DexScreenerProvider()
        try:
            result = await provider.search_token("WETH")
            
            print(f"Search result for WETH:")
            print(f"Total tokens found: {result.get('total_tokens', 0)}")
            print(f"Provider: {result.get('provider')}")
            
            tokens = result.get('tokens', [])
            if tokens:
                first_token = tokens[0]
                print(f"First token:")
                print(f"  Name: {first_token.get('name')}")
                print(f"  Symbol: {first_token.get('symbol')}")
                print(f"  Price USD: ${first_token.get('price_usd')}")
                print(f"  Liquidity USD: ${first_token.get('liquidity_usd')}")
                print(f"  Chain: {first_token.get('chain')}")
                print(f"  DEX: {first_token.get('dex')}")
                
                assert first_token.get('symbol') is not None
                assert first_token.get('price_usd') is not None
                
        except Exception as e:
            print(f"Error during test: {e}")
        finally:
            await provider.close()
    
    async def test_get_token_data_by_address(self):
        """Test getting token data by contract address"""
        provider = DexScreenerProvider()
        try:
            # WETH contract address on Ethereum
            weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            result = await provider.get_token_data_by_address("ethereum", weth_address)
            
            print(f"\nToken data by address:")
            print(f"Total tokens found: {result.get('total_tokens', 0)}")
            print(f"Query: {result.get('query')}")
            
            tokens = result.get('tokens', [])
            if tokens:
                first_token = tokens[0]
                print(f"Token info:")
                print(f"  Name: {first_token.get('name')}")
                print(f"  Symbol: {first_token.get('symbol')}")
                print(f"  Contract: {first_token.get('contract_address')}")
                print(f"  Price USD: ${first_token.get('price_usd')}")
                print(f"  24h Volume: ${first_token.get('volume_24h')}")
                
                assert first_token.get('contract_address').lower() == weth_address.lower()
                
        except Exception as e:
            print(f"Error during test: {e}")
        finally:
            await provider.close()
    
    async def test_get_token_data_auto_detect(self):
        """Test the main get_token_data method with auto-detection"""
        provider = DexScreenerProvider()
        try:
            # Test with contract address
            weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            result1 = await provider.get_token_data(weth_address, "ethereum")
            
            print(f"\nAuto-detect test (address):")
            print(f"Found {result1.get('total_tokens', 0)} tokens")
            
            # Test with symbol
            result2 = await provider.get_token_data("BTC")
            
            print(f"\nAuto-detect test (symbol):")
            print(f"Found {result2.get('total_tokens', 0)} tokens")
            
            if result2.get('tokens'):
                first_token = result2['tokens'][0]
                print(f"  Top result: {first_token.get('symbol')} - ${first_token.get('price_usd')}")
                
        except Exception as e:
            print(f"Error during test: {e}")
        finally:
            await provider.close()
    
    async def test_popular_tokens(self):
        """Test with various popular tokens"""
        provider = DexScreenerProvider()
        try:
            tokens_to_test = ["PEPE", "SHIB", "DOGE"]
            
            for token in tokens_to_test:
                print(f"\n--- Testing {token} ---")
                result = await provider.search_token(token)
                
                if result.get('tokens'):
                    first_result = result['tokens'][0]
                    print(f"  Symbol: {first_result.get('symbol')}")
                    print(f"  Price: ${first_result.get('price_usd')}")
                    print(f"  24h Change: {first_result.get('price_change_24h')}%")
                    print(f"  Volume 24h: ${first_result.get('volume_24h')}")
                    print(f"  Market Cap: ${first_result.get('market_cap')}")
                else:
                    print(f"  No results found for {token}")
                
                # Small delay to be respectful to the API
                await asyncio.sleep(0.5)
                
        except Exception as e:
            print(f"Error during test: {e}")
        finally:
            await provider.close()

# Standalone test functions for direct execution
async def run_basic_test():
    """Run a basic test"""
    print("=== Basic DexScreener Test ===")
    
    provider = DexScreenerProvider()
    try:
        # Test search
        result = await provider.search_token("beeper")
        print(f"Found {result.get('total_tokens', 0)} beeper pairs")
        
        if result.get('tokens'):
            token = result['tokens'][0]
            print(f"Top beeper pair: {token.get('symbol')} on {token.get('chain')}")
            print(f"Price: ${token.get('price_usd')}")
            print(f"Liquidity: ${token.get('liquidity_usd')}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await provider.close()

async def run_detailed_test():
    """Run detailed tests"""
    print("\n=== Detailed DexScreener Tests ===")
    
    test_instance = TestDexScreenerProvider()
    
    print("\n1. Testing token search...")
    await test_instance.test_search_token_by_symbol()
    
    print("\n2. Testing address lookup...")
    await test_instance.test_get_token_data_by_address()
    
    print("\n3. Testing auto-detection...")
    await test_instance.test_get_token_data_auto_detect()
    
    print("\n4. Testing popular tokens...")
    await test_instance.test_popular_tokens()

if __name__ == "__main__":
    print("DexScreener Provider Test Suite")
    print("=" * 50)
    
    # Run basic test
    asyncio.run(run_basic_test())
    
    # Run detailed tests
    asyncio.run(run_detailed_test())
    
    print("\n=== Test completed ===") 