#!/usr/bin/env python3
"""
Simple Strategy Creation Test Script

This script tests strategy creation using the MetaMask authentication flow
to get a real owner_id from the database.
"""

import os
import sys
import json
import requests
from decimal import Decimal

def test_metamask_auth_and_strategy():
    """Test MetaMask auth and strategy creation"""
    print("Testing MetaMask Auth and Strategy Creation")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Step 1: Test MetaMask authentication
    print("\n1️⃣ Testing MetaMask Authentication")
    print("-" * 30)
    
    # Mock MetaMask authentication data
    auth_data = {
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "signature": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1b",
        "message": "Login to AIP DEX Trading Bot\n\nWallet: 0x1234567890abcdef1234567890abcdef12345678\nTimestamp: 1720500000000"
    }
    
    try:
        auth_response = requests.post(
            f"{base_url}/api/v1/auth/metamask",
            json=auth_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer aip-dex-default-token-2025"
            }
        )
        
        print(f"✅ Auth response status: {auth_response.status_code}")
        
        if auth_response.status_code == 200:
            auth_result = auth_response.json()
            owner_id = auth_result.get("owner_id")
            print(f"✅ Authentication successful, owner_id: {owner_id}")
            
            # Step 2: Test strategy creation with real owner_id
            print("\n2️⃣ Testing Strategy Creation")
            print("-" * 30)
            
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
            
            strategy_response = requests.post(
                f"{base_url}/api/v1/strategies",
                json=strategy_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer aip-dex-default-token-2025"
                }
            )
            
            print(f"✅ Strategy response status: {strategy_response.status_code}")
            
            if strategy_response.status_code == 200:
                strategy_result = strategy_response.json()
                print(f"✅ Strategy created successfully: {json.dumps(strategy_result, indent=2)}")
                return True
            else:
                print(f"❌ Strategy creation failed: {strategy_response.text}")
                return False
        else:
            print(f"❌ Authentication failed: {auth_response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_owner_creation():
    """Test owner creation API"""
    print("\n3️⃣ Testing Owner Creation API")
    print("-" * 30)
    
    base_url = "http://localhost:8000"
    
    owner_data = {
        "owner_name": "Test Owner",
        "email": "test@example.com",
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "subscription_tier": "basic",
        "max_bots_allowed": 1
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/owners",
            json=owner_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer aip-dex-default-token-2025"
            }
        )
        
        print(f"✅ Owner creation status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Owner created: {json.dumps(result, indent=2)}")
            return result.get("id")
        else:
            print(f"❌ Owner creation failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating owner: {e}")
        return None

def test_strategy_with_created_owner():
    """Test strategy creation with manually created owner"""
    print("\n4️⃣ Testing Strategy with Created Owner")
    print("-" * 30)
    
    # First create an owner
    owner_id = test_owner_creation()
    
    if not owner_id:
        print("❌ Could not create owner, skipping strategy test")
        return False
    
    base_url = "http://localhost:8000"
    
    strategy_data = {
        "owner_id": owner_id,
        "strategy_name": "Test Strategy 2",
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
        response = requests.post(
            f"{base_url}/api/v1/strategies",
            json=strategy_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer aip-dex-default-token-2025"
            }
        )
        
        print(f"✅ Strategy creation status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Strategy created successfully: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Strategy creation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating strategy: {e}")
        return False

def main():
    """Main test function"""
    print("Simple Strategy Creation Test")
    print("=" * 50)
    
    # Run tests
    auth_test = test_metamask_auth_and_strategy()
    owner_test = test_owner_creation()
    strategy_test = test_strategy_with_created_owner()
    
    print("\n" + "=" * 50)
    print("FINAL RESULTS:")
    
    if auth_test or strategy_test:
        print("✅ Strategy creation tests passed!")
        print("\nTo test the web interface:")
        print("1. Start your FastAPI server: python main.py")
        print("2. Open http://localhost:8000/bot-management in your browser")
        print("3. Connect MetaMask and sign in")
        print("4. Try creating a strategy - should work now")
        return 0
    else:
        print("❌ Strategy creation tests failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 