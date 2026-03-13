#!/usr/bin/env python3
"""Test script to check Chrome and Selenium functionality."""

import subprocess
import sys
import os

def test_chrome():
    """Test if Chrome is available."""
    print("Testing Chrome availability...")
    for cmd in ("google-chrome", "chromium-browser", "chromium"):
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✓ {cmd} found: {result.stdout.strip()}")
                return True
        except Exception as e:
            print(f"✗ {cmd} failed: {e}")
    print("✗ No Chrome binary found")
    return False

def test_selenium():
    """Test if Selenium can start Chrome."""
    print("\nTesting Selenium...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")

        print("Starting Chrome driver...")
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
        print("✓ Chrome driver started successfully")

        driver.get("https://www.google.com")
        title = driver.title
        print(f"✓ Page loaded, title: {title}")

        driver.quit()
        print("✓ Chrome driver closed successfully")
        return True

    except Exception as e:
        print(f"✗ Selenium test failed: {e}")
        return False

if __name__ == "__main__":
    chrome_ok = test_chrome()
    selenium_ok = test_selenium()

    if chrome_ok and selenium_ok:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)