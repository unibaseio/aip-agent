#!/usr/bin/env python3
"""
Test script for bot management functionality
"""

import asyncio
import sys
import os
import json
import requests
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_api_endpoints():
    """Test all bot management API endpoints"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Bot Management API Endpoints")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/api/v1/health")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 2: Get unclaimed bots
    print("\n2. Testing get unclaimed bots...")
    try:
        response = requests.get(
            f"{base_url}/api/v1/bots/unclaimed",
            headers={"Authorization": "Bearer aip-dex-default-token-2025"}
        )
        if response.status_code == 200:
            bots = response.json()
            print(f"✅ Found {len(bots)} unclaimed bots")
            for bot in bots[:3]:  # Show first 3 bots
                print(f"   - {bot['bot_name']} (${bot['current_balance_usd']:.2f})")
        else:
            print(f"❌ Get unclaimed bots failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Get unclaimed bots error: {e}")
    
    # Test 3: Get API info
    print("\n3. Testing API info...")
    try:
        response = requests.get(f"{base_url}/api/info")
        if response.status_code == 200:
            info = response.json()
            print("✅ API info retrieved")
            print(f"   Service: {info['service']}")
            print(f"   Version: {info['version']}")
            print(f"   Features: {len(info['features'])} features")
        else:
            print(f"❌ API info failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API info error: {e}")
    
    # Test 4: Test strategy endpoints (without authentication)
    print("\n4. Testing strategy endpoints...")
    try:
        response = requests.get(
            f"{base_url}/api/v1/strategies/owner/test-owner-id",
            headers={"Authorization": "Bearer aip-dex-default-token-2025"}
        )
        if response.status_code == 200:
            strategies = response.json()
            print(f"✅ Strategy endpoint works (found {len(strategies)} strategies)")
        else:
            print(f"⚠️ Strategy endpoint returned {response.status_code} (expected for non-existent owner)")
    except Exception as e:
        print(f"❌ Strategy endpoint error: {e}")
    
    # Test 5: Test owner bots endpoint
    print("\n5. Testing owner bots endpoint...")
    try:
        response = requests.get(
            f"{base_url}/api/v1/bots/owner/test-owner-id",
            headers={"Authorization": "Bearer aip-dex-default-token-2025"}
        )
        if response.status_code == 200:
            bots = response.json()
            print(f"✅ Owner bots endpoint works (found {len(bots)} bots)")
        else:
            print(f"⚠️ Owner bots endpoint returned {response.status_code} (expected for non-existent owner)")
    except Exception as e:
        print(f"❌ Owner bots endpoint error: {e}")

def test_metamask_login_simulation():
    """Simulate MetaMask login process"""
    print("\n🔐 Testing MetaMask Login Simulation")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Simulate login data
    login_data = {
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "signature": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "message": "Login to AIP DEX Trading Bot\n\nWallet: 0x1234567890abcdef1234567890abcdef12345678\nTimestamp: 1703123456789"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/metamask",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer aip-dex-default-token-2025"
            },
            json=login_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ MetaMask login simulation successful")
            print(f"   Owner ID: {data.get('owner_id')}")
            print(f"   Owner Name: {data.get('owner_name')}")
            print(f"   Wallet: {data.get('wallet_address')}")
            print(f"   Message: {data.get('message')}")
            return data.get('owner_id')
        else:
            print(f"❌ MetaMask login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ MetaMask login error: {e}")
        return None

def test_bot_claiming_simulation(owner_id):
    """Simulate bot claiming process"""
    if not owner_id:
        print("❌ Cannot test bot claiming without owner ID")
        return
    
    print(f"\n🤖 Testing Bot Claiming Simulation (Owner: {owner_id})")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # First, get unclaimed bots
    try:
        response = requests.get(
            f"{base_url}/api/v1/bots/unclaimed",
            headers={"Authorization": "Bearer aip-dex-default-token-2025"}
        )
        
        if response.status_code == 200:
            unclaimed_bots = response.json()
            if unclaimed_bots:
                bot_to_claim = unclaimed_bots[0]
                print(f"✅ Found bot to claim: {bot_to_claim['bot_name']}")
                
                # Simulate claiming
                claim_data = {
                    "owner_id": owner_id,
                    "wallet_address": "0x1234567890abcdef1234567890abcdef12345678"
                }
                
                claim_response = requests.post(
                    f"{base_url}/api/v1/bots/{bot_to_claim['id']}/claim",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer aip-dex-default-token-2025"
                    },
                    json=claim_data
                )
                
                if claim_response.status_code == 200:
                    claim_result = claim_response.json()
                    print("✅ Bot claiming simulation successful")
                    print(f"   Bot ID: {claim_result.get('bot_id')}")
                    print(f"   Owner ID: {claim_result.get('owner_id')}")
                    print(f"   Message: {claim_result.get('message')}")
                else:
                    print(f"❌ Bot claiming failed: {claim_response.status_code}")
                    print(f"   Response: {claim_response.text}")
            else:
                print("⚠️ No unclaimed bots available")
        else:
            print(f"❌ Failed to get unclaimed bots: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Bot claiming simulation error: {e}")

def test_strategy_creation_simulation(owner_id):
    """Simulate strategy creation process"""
    if not owner_id:
        print("❌ Cannot test strategy creation without owner ID")
        return
    
    print(f"\n📊 Testing Strategy Creation Simulation (Owner: {owner_id})")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Create a test strategy
    strategy_data = {
        "owner_id": owner_id,  # Add owner_id
        "strategy_name": "Test Strategy",
        "strategy_type": "user_defined",
        "risk_level": "medium",
        "max_position_size": 20.0,
        "stop_loss_percentage": 10.0,
        "take_profit_percentage": 25.0,
        "min_profit_threshold": 3.0,
        "max_daily_trades": 15,
        "llm_confidence_threshold": 0.7,
        "buy_strategy_description": "Test buy strategy for demonstration",
        "sell_strategy_description": "Test sell strategy for demonstration",
        "filter_strategy_description": "Test filter strategy for demonstration",
        "summary_strategy_description": "Test strategy summary for demonstration"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/strategies",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer aip-dex-default-token-2025"
            },
            json=strategy_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Strategy creation simulation successful")
            print(f"   Strategy ID: {result.get('strategy_id')}")
            print(f"   Strategy Name: {result.get('strategy_name')}")
            print(f"   Message: {result.get('message')}")
            return result.get('strategy_id')
        else:
            print(f"❌ Strategy creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Strategy creation simulation error: {e}")
        return None

def test_bot_configuration_simulation(owner_id, strategy_id):
    """Simulate bot configuration process"""
    if not owner_id or not strategy_id:
        print("❌ Cannot test bot configuration without owner ID and strategy ID")
        return
    
    print(f"\n⚙️ Testing Bot Configuration Simulation")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Get owner's bots
    try:
        response = requests.get(
            f"{base_url}/api/v1/bots/owner/{owner_id}",
            headers={"Authorization": "Bearer aip-dex-default-token-2025"}
        )
        
        if response.status_code == 200:
            owner_bots = response.json()
            if owner_bots:
                # Find a bot that's not configured
                unconfigured_bot = None
                for bot in owner_bots:
                    if not bot.get('is_configured'):
                        unconfigured_bot = bot
                        break
                
                if unconfigured_bot:
                    print(f"✅ Found unconfigured bot: {unconfigured_bot['bot_name']}")
                    
                    # Configure the bot
                    config_data = {
                        "owner_id": owner_id,
                        "strategy_id": strategy_id
                    }
                    
                    config_response = requests.post(
                        f"{base_url}/api/v1/bots/{unconfigured_bot['id']}/configure",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": "Bearer aip-dex-default-token-2025"
                        },
                        json=config_data
                    )
                    
                    if config_response.status_code == 200:
                        config_result = config_response.json()
                        print("✅ Bot configuration simulation successful")
                        print(f"   Bot ID: {config_result.get('bot_id')}")
                        print(f"   Owner ID: {config_result.get('owner_id')}")
                        print(f"   Strategy ID: {config_result.get('strategy_id')}")
                        print(f"   Message: {config_result.get('message')}")
                    else:
                        print(f"❌ Bot configuration failed: {config_response.status_code}")
                        print(f"   Response: {config_response.text}")
                else:
                    print("⚠️ No unconfigured bots found")
            else:
                print("⚠️ No bots found for owner")
        else:
            print(f"❌ Failed to get owner bots: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Bot configuration simulation error: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting Bot Management Tests")
    print("=" * 60)
    
    # Test basic API endpoints
    test_api_endpoints()
    
    # Test MetaMask login simulation
    owner_id = test_metamask_login_simulation()
    
    # Test bot claiming simulation
    test_bot_claiming_simulation(owner_id)
    
    # Test strategy creation simulation
    strategy_id = test_strategy_creation_simulation(owner_id)
    
    # Test bot configuration simulation
    test_bot_configuration_simulation(owner_id, strategy_id)
    
    print("\n" + "=" * 60)
    print("🎉 Bot Management Tests Completed!")
    print("\nNext steps:")
    print("1. Start the server: python main.py")
    print("2. Open http://localhost:8000/login")
    print("3. Connect MetaMask and test the full flow")
    print("4. Check bot management page: http://localhost:8000/bot-management")

if __name__ == "__main__":
    main() 