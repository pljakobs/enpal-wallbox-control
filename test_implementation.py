#!/usr/bin/env python3
"""
Simple test script for wallbox functionality
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work correctly"""
    print("Testing imports...")
    
    try:
        from wallbox import WallboxController
        print("✓ WallboxController import successful")
    except ImportError as e:
        print(f"✗ WallboxController import failed: {e}")
        return False
    
    try:
        # Test if webhook server can be imported (Flask may not be installed)
        from webhook_server import WebhookServer
        print("✓ WebhookServer import successful")
    except ImportError as e:
        print(f"⚠ WebhookServer import failed (expected if Flask not installed): {e}")
    
    return True

def test_wallbox_controller():
    """Test WallboxController initialization"""
    print("\nTesting WallboxController...")
    
    try:
        from wallbox import WallboxController
        
        # Test with default config
        controller = WallboxController(headless=True, verbose=True)
        print("✓ WallboxController initialization successful")
        
        # Test config loading
        print(f"✓ Config loaded: {controller.config}")
        
        # Test button mapping
        print(f"✓ Action mapping: {controller.action_button_map}")
        
        return True
        
    except Exception as e:
        print(f"✗ WallboxController test failed: {e}")
        return False

def test_cli_parsing():
    """Test command line argument parsing"""
    print("\nTesting CLI parsing...")
    
    try:
        from wallbox import parse_arguments
        
        # This would normally parse sys.argv, so we'll just check the function exists
        print("✓ parse_arguments function available")
        return True
        
    except Exception as e:
        print(f"✗ CLI parsing test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Wallbox Implementation Test")
    print("=" * 30)
    
    tests = [
        test_imports,
        test_wallbox_controller,
        test_cli_parsing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nTest Results: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All tests passed! Implementation looks good.")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
