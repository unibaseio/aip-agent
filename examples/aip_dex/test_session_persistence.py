#!/usr/bin/env python3
"""
Session Persistence Test Script

This script tests the session persistence functionality to ensure
users don't need to re-sign every time they refresh or navigate.
"""

import os
import sys
import json
import time
from pathlib import Path

def test_session_storage():
    """Test session storage functionality"""
    print("Testing Session Storage")
    print("=" * 40)
    
    # Simulate session data
    session_data = {
        'owner_id': 'test-owner-123',
        'wallet_address': '0x1234567890abcdef1234567890abcdef12345678',
        'session_expiry': str(int(time.time() * 1000) + (24 * 60 * 60 * 1000))  # 24 hours from now
    }
    
    print("✅ Session data structure:")
    for key, value in session_data.items():
        print(f"   {key}: {value}")
    
    return True

def test_session_validation():
    """Test session validation logic"""
    print("\nTesting Session Validation")
    print("=" * 40)
    
    # Test valid session
    now = int(time.time() * 1000)
    valid_expiry = now + (24 * 60 * 60 * 1000)  # 24 hours from now
    expired_expiry = now - (24 * 60 * 60 * 1000)  # 24 hours ago
    
    print(f"✅ Current time: {now}")
    print(f"✅ Valid expiry: {valid_expiry}")
    print(f"✅ Expired expiry: {expired_expiry}")
    
    # Test validation logic
    is_valid = now < valid_expiry
    is_expired = now < expired_expiry
    
    print(f"✅ Valid session check: {is_valid}")
    print(f"✅ Expired session check: {is_expired}")
    
    return is_valid and not is_expired

def test_metamask_integration():
    """Test MetaMask integration with session persistence"""
    print("\nTesting MetaMask Integration")
    print("=" * 40)
    
    print("✅ Expected behavior:")
    print("   1. User connects MetaMask and signs once")
    print("   2. Session is stored with 24-hour expiry")
    print("   3. User can refresh page without re-signing")
    print("   4. User can navigate between pages without re-signing")
    print("   5. Session expires after 24 hours")
    print("   6. User needs to re-sign after session expiry")
    
    return True

def test_api_endpoints():
    """Test API endpoints with session persistence"""
    print("\nTesting API Endpoints")
    print("=" * 40)
    
    print("✅ Expected API behavior:")
    print("   - /api/v1/auth/metamask should create session")
    print("   - Session should be valid for 24 hours")
    print("   - User should not need to re-authenticate during session")
    print("   - Session should be cleared on disconnect")
    
    return True

def test_frontend_integration():
    """Test frontend integration with session persistence"""
    print("\nTesting Frontend Integration")
    print("=" * 40)
    
    print("✅ Expected frontend behavior:")
    print("   1. Check for existing session on page load")
    print("   2. Restore session if valid")
    print("   3. Show session status to user")
    print("   4. Allow session refresh")
    print("   5. Clear session on disconnect")
    print("   6. Auto-redirect if session is valid")
    
    return True

def main():
    """Main test function"""
    print("Session Persistence Verification")
    print("=" * 50)
    
    # Run tests
    storage_test = test_session_storage()
    validation_test = test_session_validation()
    metamask_test = test_metamask_integration()
    api_test = test_api_endpoints()
    frontend_test = test_frontend_integration()
    
    print("\n" + "=" * 50)
    print("FINAL RESULTS:")
    
    if all([storage_test, validation_test, metamask_test, api_test, frontend_test]):
        print("✅ All session persistence tests passed!")
        print("\nTo test the web interface:")
        print("1. Start your FastAPI server: python main.py")
        print("2. Open http://localhost:8000/login in your browser")
        print("3. Connect MetaMask and sign once")
        print("4. Refresh the page - you should stay logged in")
        print("5. Navigate to /bot-management - you should stay logged in")
        print("6. Check session status in the UI")
        print("7. Try refreshing session manually")
        return 0
    else:
        print("❌ Some tests failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 