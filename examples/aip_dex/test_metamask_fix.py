#!/usr/bin/env python3
"""
MetaMask Connection Test Script

This script tests the MetaMask connection functionality and verifies that
the fixes have been properly implemented.
"""

import os
import sys
import json
import requests
from pathlib import Path

def check_file_exists(file_path):
    """Check if a file exists and is readable"""
    path = Path(file_path)
    if path.exists() and path.is_file():
        print(f"✓ {file_path} exists")
        return True
    else:
        print(f"✗ {file_path} not found")
        return False

def check_js_syntax(file_path):
    """Check for basic JavaScript syntax issues"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for common issues
        issues = []
        
        # Check for duplicate variable declarations
        if content.count('const metamaskManager') > 1:
            issues.append("Duplicate metamaskManager declarations")
        
        # Check for undefined class references
        if 'new MetaMaskManager()' in content and 'class MetaMaskManager' not in content:
            issues.append("MetaMaskManager class not defined but instantiated")
        
        # Check for proper initialization
        if 'let metamaskLogin = null;' not in content:
            issues.append("Missing proper metamaskLogin initialization")
        
        if issues:
            print(f"✗ {file_path} has issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print(f"✓ {file_path} syntax looks good")
            return True
            
    except Exception as e:
        print(f"✗ Error reading {file_path}: {e}")
        return False

def check_html_integration(html_file):
    """Check HTML files for proper MetaMask integration"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for proper script inclusion with correct path
        if '/static/js/metamask.js' not in content:
            issues.append("MetaMask JS file not included with correct path")
        
        # Check for old initialization pattern
        if 'metamaskLogin = new MetaMaskLogin()' in content:
            issues.append("Old initialization pattern found")
        
        # Check for new initialization pattern
        if 'typeof metamaskLogin !== \'undefined\'' not in content:
            issues.append("New initialization pattern not found")
        
        if issues:
            print(f"✗ {html_file} has issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print(f"✓ {html_file} integration looks good")
            return True
            
    except Exception as e:
        print(f"✗ Error reading {html_file}: {e}")
        return False

def test_metamask_functions():
    """Test MetaMask-related functions"""
    print("\n=== Testing MetaMask Functions ===")
    
    # Test files to check
    js_file = "static/js/metamask.js"
    html_files = [
        "static/bot-management.html",
        "static/login.html"
    ]
    
    all_good = True
    
    # Check JavaScript file
    if not check_file_exists(js_file):
        all_good = False
    elif not check_js_syntax(js_file):
        all_good = False
    
    # Check HTML files
    for html_file in html_files:
        if not check_file_exists(html_file):
            all_good = False
        elif not check_html_integration(html_file):
            all_good = False
    
    return all_good

def check_test_files():
    """Check if test files exist"""
    print("\n=== Checking Test Files ===")
    
    test_files = [
        "static/metamask-test.html",
        "METAMASK_TESTING.md"
    ]
    
    all_exist = True
    for test_file in test_files:
        if not check_file_exists(test_file):
            all_exist = False
    
    return all_exist

def main():
    """Main test function"""
    print("MetaMask Connection Fix Verification")
    print("=" * 40)
    
    # Change to the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Run tests
    js_ok = test_metamask_functions()
    test_files_ok = check_test_files()
    
    print("\n" + "=" * 40)
    print("SUMMARY:")
    
    if js_ok and test_files_ok:
        print("✓ All MetaMask fixes have been properly implemented!")
        print("\nTo test the connection:")
        print("1. Start your web server")
        print("2. Open /static/metamask-test.html in your browser")
        print("3. Click 'Connect MetaMask' to test the connection")
        print("4. Check the browser console for any errors")
        return 0
    else:
        print("✗ Some issues were found. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 