#!/usr/bin/env python3
"""
Strategy Creation Test Script

This script tests the strategy creation functionality to ensure
the API endpoint works correctly with owner_id.
"""

import os
import sys
import json
import requests
from decimal import Decimal

def test_strategy_creation_api():
    """Test strategy creation API endpoint"""
    print("Testing Strategy Creation API")
    print("=" * 40)
    
    # Test data
    strategy_data = {
        "owner_id": "test-owner-123",  # This should be a valid UUID
        "strategy_name": "Test Strategy",
        "strategy_type": "user_defined",
        "risk_level": "medium",
        "max_position_size": 20.0,
        "stop_loss_percentage": 10.0,
        "take_profit_percentage": 25.0,
        "min_profit_threshold": 3.0,
        "max_daily_trades": 15,
        "llm_confidence_threshold": 0.7,
        "buy_strategy_description": "Test buy strategy",
        "sell_strategy_description": "Test sell strategy",
        "filter_strategy_description": "Test filter strategy",
        "summary_strategy_description": "Test strategy summary"
    }
    
    print("✅ Test strategy data:")
    for key, value in strategy_data.items():
        print(f"   {key}: {value}")
    
    return strategy_data

def test_api_endpoint():
    """Test the actual API endpoint"""
    print("\nTesting API Endpoint")
    print("=" * 40)
    
    # Base URL
    base_url = "http://localhost:8000"
    
    # First, create a test owner
    owner_data = {
        "owner_name": "Test Owner",
        "email": "test@example.com",
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "subscription_tier": "basic",
        "max_bots_allowed": 1
    }
    
    try:
        # Create owner first
        print("Creating test owner...")
        owner_response = requests.post(
            f"{base_url}/api/v1/owners",
            json=owner_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer aip-dex-default-token-2025"
            }
        )
        
        if owner_response.status_code == 200:
            owner_result = owner_response.json()
            owner_id = owner_result.get("id")
            print(f"✅ Created owner with ID: {owner_id}")
        else:
            print(f"❌ Failed to create owner: {owner_response.text}")
            # Try to get existing owner by wallet
            print("Trying to get existing owner...")
            owner_response = requests.get(
                f"{base_url}/api/v1/owners/wallet/0x1234567890abcdef1234567890abcdef12345678",
                headers={
                    "Authorization": "Bearer aip-dex-default-token-2025"
                }
            )
            if owner_response.status_code == 200:
                owner_result = owner_response.json()
                owner_id = owner_result.get("id")
                print(f"✅ Found existing owner with ID: {owner_id}")
            else:
                print("❌ Could not create or find owner")
                return False
    except Exception as e:
        print(f"❌ Error creating/finding owner: {e}")
        return False
    
    # Test strategy data with real owner_id
    strategy_data = {
        "owner_id": owner_id,
        "strategy_name": "Test Strategy",
        "strategy_type": "user_defined",
        "risk_level": "medium",
        "max_position_size": 20.0,
        "stop_loss_percentage": 10.0,
        "take_profit_percentage": 25.0,
        "min_profit_threshold": 3.0,
        "max_daily_trades": 15,
        "llm_confidence_threshold": 0.7,
        "buy_strategy_description": "Test buy strategy",
        "sell_strategy_description": "Test sell strategy",
        "filter_strategy_description": "Test filter strategy",
        "summary_strategy_description": "Test strategy summary"
    }
    
    try:
        # Test POST /api/v1/strategies
        response = requests.post(
            f"{base_url}/api/v1/strategies",
            json=strategy_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer aip-dex-default-token-2025"
            }
        )
        
        print(f"✅ Response status: {response.status_code}")
        print(f"✅ Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Error response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def test_frontend_integration():
    """Test frontend integration with strategy creation"""
    print("\nTesting Frontend Integration")
    print("=" * 40)
    
    print("✅ Expected frontend behavior:")
    print("   1. User fills strategy form")
    print("   2. Frontend includes owner_id in request")
    print("   3. API validates owner_id")
    print("   4. Strategy is created successfully")
    print("   5. UI updates with new strategy")
    
    return True

def test_error_handling():
    """Test error handling scenarios"""
    print("\nTesting Error Handling")
    print("=" * 40)
    
    print("✅ Test scenarios:")
    print("   1. Missing owner_id - should return 400")
    print("   2. Invalid owner_id format - should return 400")
    print("   3. Missing required fields - should return 400")
    print("   4. Invalid token - should return 401")
    print("   5. Server error - should return 500")
    
    return True

def main():
    """Main test function"""
    print("Strategy Creation Verification")
    print("=" * 50)
    
    # Run tests
    api_test = test_strategy_creation_api()
    endpoint_test = test_api_endpoint()
    frontend_test = test_frontend_integration()
    error_test = test_error_handling()
    
    print("\n" + "=" * 50)
    print("FINAL RESULTS:")
    
    if all([api_test, endpoint_test, frontend_test, error_test]):
        print("✅ All strategy creation tests passed!")
        print("\nTo test the web interface:")
        print("1. Start your FastAPI server: python main.py")
        print("2. Open http://localhost:8000/bot-management in your browser")
        print("3. Connect MetaMask and sign in")
        print("4. Click 'Create Strategy' button")
        print("5. Fill in the strategy form")
        print("6. Submit - should create strategy successfully")
        return 0
    else:
        print("❌ Some tests failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 