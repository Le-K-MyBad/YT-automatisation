#!/usr/bin/env python3
"""Quick test to validate the automation script imports and basic functions."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

try:
    from automation import load_config, is_chrome_available
    print("✓ Imports successful")
    
    # Test config loading
    config = load_config()
    print(f"✓ Config loaded: {config.keys()}")
    
    # Test Chrome availability
    chrome_ok = is_chrome_available()
    print(f"✓ Chrome available: {chrome_ok}")
    
    print("All basic tests passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)