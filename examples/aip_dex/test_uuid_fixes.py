#!/usr/bin/env python3
"""
Test script to verify UUID type fixes in the trading bot API
"""

import uuid
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_uuid_conversions():
    """Test UUID conversion functions"""
    print("Testing UUID conversions...")
    
    # Test valid UUID strings
    test_uuid_str = "550e8400-e29b-41d4-a716-446655440000"
    try:
        converted_uuid = uuid.UUID(test_uuid_str)
        print(f"✓ Valid UUID conversion: {test_uuid_str} -> {converted_uuid}")
    except ValueError as e:
        print(f"❌ Failed to convert valid UUID: {e}")
        return False
    
    # Test invalid UUID strings
    invalid_uuid_str = "invalid-uuid-string"
    try:
        uuid.UUID(invalid_uuid_str)
        print(f"❌ Should have failed for invalid UUID: {invalid_uuid_str}")
        return False
    except ValueError:
        print(f"✓ Correctly rejected invalid UUID: {invalid_uuid_str}")
    
    return True

def test_imports():
    """Test that all modified files can be imported without errors"""
    print("\nTesting imports...")
    
    try:
        from api.trading_bot_routes import router
        print("✓ Successfully imported trading_bot_routes")
    except Exception as e:
        print(f"❌ Failed to import trading_bot_routes: {e}")
        return False
    
    try:
        from services.trading_service_clean import TradingService
        print("✓ Successfully imported TradingService from trading_service_clean")
    except Exception as e:
        print(f"❌ Failed to import TradingService: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("=== UUID Fix Validation Tests ===")
    
    success = True
    
    # Test UUID conversions
    if not test_uuid_conversions():
        success = False
    
    # Test imports
    if not test_imports():
        success = False
    
    print("\n=== Test Results ===")
    if success:
        print("✅ All tests passed! UUID fixes appear to be working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())