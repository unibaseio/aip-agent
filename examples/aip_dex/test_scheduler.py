#!/usr/bin/env python3
"""
Test script for AIP DEX Token Data Scheduler
Run this to verify all components are working correctly
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from data_aggregator.birdeye import BirdEyeProvider
from data_aggregator.dex_screener import DexScreenerProvider
from models.database import create_tables, create_indexes, get_db
from services.token_service import TokenService
from indicators.calculator import TokenSignalCalculator

async def test_birdeye_api():
    """Test BirdEye API connection"""
    print("🔍 Testing BirdEye API...")
    
    try:
        birdeye = BirdEyeProvider()
        result = await birdeye.get_top_tokens(chain="bsc", limit=5)
        
        if result and result.get("success"):
            tokens = result.get("tokens", [])
            print(f"✅ BirdEye API working! Retrieved {len(tokens)} tokens")
            
            # Show first token as example
            if tokens:
                token = tokens[0]
                print(f"   Example: {token.get('symbol')} - ${token.get('price_usd'):.6f}")
        else:
            print("❌ BirdEye API failed - no data returned")
            return False
        
        await birdeye.close()
        return True
        
    except Exception as e:
        print(f"❌ BirdEye API error: {e}")
        return False

async def test_dex_screener_api():
    """Test DexScreener API connection"""
    print("🔍 Testing DexScreener API...")
    
    try:
        dex_screener = DexScreenerProvider()
        # Test with a well-known token (USDC on BSC)
        result = await dex_screener.search_token("USDC")
        
        if result and result.get("tokens"):
            tokens = result.get("tokens", [])
            print(f"✅ DexScreener API working! Retrieved {len(tokens)} pool pairs")
            
            # Show first pool as example
            if tokens:
                token = tokens[0]
                print(f"   Example: {token.get('symbol')} - Liquidity: ${token.get('liquidity_usd'):,.0f}")
        else:
            print("❌ DexScreener API failed - no data returned")
            return False
        
        await dex_screener.close()
        return True
        
    except Exception as e:
        print(f"❌ DexScreener API error: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("🔍 Testing database connection...")
    
    try:
        # Test database connection
        db_gen = get_db()
        db = next(db_gen)
        
        # Try to execute a simple query
        result = db.execute("SELECT 1 as test").fetchone()
        db.close()
        
        if result and result[0] == 1:
            print("✅ Database connection working!")
            return True
        else:
            print("❌ Database connection failed - invalid result")
            return False
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_database_schema():
    """Test database schema creation"""
    print("🔍 Testing database schema...")
    
    try:
        create_tables()
        create_indexes()
        print("✅ Database schema created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database schema error: {e}")
        return False

async def test_token_service():
    """Test token service functionality"""
    print("🔍 Testing token service...")
    
    try:
        token_service = TokenService()
        db_gen = get_db()
        db = next(db_gen)
        
        # Test getting top tokens (but don't save to DB)
        result = await token_service.get_top_tokens_by_volume(
            db=db,
            chain="bsc",
            limit=3,
            save_to_db=False
        )
        
        if result and result.get("success"):
            tokens = result.get("tokens", [])
            print(f"✅ Token service working! Retrieved {len(tokens)} tokens")
        else:
            print("❌ Token service failed")
            return False
        
        db.close()
        await token_service.close()
        return True
        
    except Exception as e:
        print(f"❌ Token service error: {e}")
        return False

def test_signal_calculator():
    """Test signal calculator"""
    print("🔍 Testing signal calculator...")
    
    try:
        calculator = TokenSignalCalculator()
        
        # Test with dummy data
        dummy_data = [
            {"price_usd": 100, "volume_24h": 1000000, "holders": 1000},
            {"price_usd": 105, "volume_24h": 1200000, "holders": 1050},
            {"price_usd": 110, "volume_24h": 1100000, "holders": 1100},
        ]
        
        indicators = calculator.calculate_indicators(dummy_data)
        
        if indicators and "rsi" in indicators:
            print(f"✅ Signal calculator working! RSI: {indicators['rsi']:.2f}")
            return True
        else:
            print("❌ Signal calculator failed")
            return False
        
    except Exception as e:
        print(f"❌ Signal calculator error: {e}")
        return False

def check_environment():
    """Check environment variables"""
    print("🔍 Checking environment variables...")
    
    required_vars = ["DATABASE_URL", "BIRDEYE_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    else:
        print("✅ All required environment variables are set!")
        return True

async def run_integration_test():
    """Run a mini integration test"""
    print("🔍 Running integration test...")
    
    try:
        from scheduler import TokenDataScheduler
        
        scheduler = TokenDataScheduler(chain="bsc", fetch_limit=3)
        await scheduler.initialize()
        
        # Run a single update with minimal data
        db_gen = get_db()
        db = next(db_gen)
        
        tokens = await scheduler.fetch_and_save_top_tokens(db)
        if tokens and len(tokens) > 0:
            print(f"✅ Integration test passed! Processed {len(tokens)} tokens")
            
            # Test pool updates for first token only
            pool_stats = await scheduler.update_token_pools(db, tokens[:1])
            print(f"   Pool stats: {pool_stats}")
            
            # Test signal calculation
            signal_stats = await scheduler.calculate_and_save_signals(db, tokens[:1])
            print(f"   Signal stats: {signal_stats}")
            
        else:
            print("❌ Integration test failed - no tokens processed")
            return False
        
        db.close()
        await scheduler.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 AIP DEX Token Data Scheduler - System Tests")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", check_environment),
        ("Database Connection", test_database_connection),
        ("Database Schema", test_database_schema),
        ("BirdEye API", test_birdeye_api),
        ("DexScreener API", test_dex_screener_api),
        ("Token Service", test_token_service),
        ("Signal Calculator", test_signal_calculator),
        ("Integration Test", run_integration_test),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            
            results.append((test_name, success))
            
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {test_name}")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print("-" * 50)
    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    
    if failed == 0:
        print("\n🎉 All tests passed! System is ready to run.")
        return 0
    else:
        print(f"\n⚠️  {failed} tests failed. Please fix issues before running scheduler.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 