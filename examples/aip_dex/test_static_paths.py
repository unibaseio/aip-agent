#!/usr/bin/env python3
"""
Static File Path Test Script

This script tests if static files are accessible via the correct paths.
"""

import os
import sys
import requests
from pathlib import Path

def test_file_exists(file_path):
    """Test if a file exists on disk"""
    path = Path(file_path)
    if path.exists() and path.is_file():
        print(f"✓ {file_path} exists on disk")
        return True
    else:
        print(f"✗ {file_path} not found on disk")
        return False

def test_static_paths():
    """Test static file paths"""
    print("Testing Static File Paths")
    print("=" * 40)
    
    # Files to test
    files_to_test = [
        "static/js/metamask.js",
        "static/login.html", 
        "static/bot-management.html",
        "static/metamask-test.html"
    ]
    
    all_exist = True
    for file_path in files_to_test:
        if not test_file_exists(file_path):
            all_exist = False
    
    return all_exist

def check_html_references():
    """Check HTML files for correct script references"""
    print("\nChecking HTML Script References")
    print("=" * 40)
    
    html_files = [
        "static/login.html",
        "static/bot-management.html", 
        "static/metamask-test.html",
        "static/index.html"
    ]
    
    all_correct = True
    
    for html_file in html_files:
        if not test_file_exists(html_file):
            continue
            
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for correct metamask.js reference
            if '/static/js/metamask.js' in content:
                print(f"✓ {html_file} has correct metamask.js reference")
            elif 'js/metamask.js' in content:
                print(f"✗ {html_file} has incorrect relative path")
                all_correct = False
            else:
                print(f"ℹ {html_file} has no metamask.js reference")
                
        except Exception as e:
            print(f"✗ Error reading {html_file}: {e}")
            all_correct = False
    
    return all_correct

def main():
    """Main test function"""
    print("Static File Path Verification")
    print("=" * 40)
    
    # Change to the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Run tests
    files_exist = test_static_paths()
    refs_correct = check_html_references()
    
    print("\n" + "=" * 40)
    print("SUMMARY:")
    
    if files_exist and refs_correct:
        print("✓ All static file paths are correct!")
        print("\nTo test the web interface:")
        print("1. Start your FastAPI server: python main.py")
        print("2. Open http://localhost:8000/login in your browser")
        print("3. Check browser console for any 404 errors")
        print("4. If you see 404 errors, check the Network tab in dev tools")
        return 0
    else:
        print("✗ Some issues were found. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 