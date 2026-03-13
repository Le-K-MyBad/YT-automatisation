#!/usr/bin/env python3
"""Test script to check if the new Shorts download method works."""

import sys
import os
import shutil
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from automation import download_video

def test_shorts_download():
    """Test downloading a YouTube Short with the new method."""
    # Clean output directory
    output_dir = Path("output")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Test URL - let's try a different Short to see if it works
    test_urls = [
        "https://www.youtube.com/shorts/hj_mb_1GvL0",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",  # Rick Astley - might be blocked
        "https://www.youtube.com/shorts/BROWqjuTM0g"   # Try another one
    ]

    for url in test_urls:
        try:
            print(f"\n{'='*50}")
            print(f"Testing download of: {url}")
            print(f"{'='*50}")

            result_file = download_video(url, output_dir)

            if result_file and result_file.exists():
                size = result_file.stat().st_size
                print(f"✓ Download successful: {result_file}")
                print(f"✓ File size: {size} bytes")
                if size > 1000:  # At least 1KB
                    print("✓ File appears to be valid")
                    return True
                else:
                    print("✗ File too small, probably failed")
            else:
                print("✗ No file returned")

        except Exception as e:
            print(f"✗ Download failed: {e}")
            continue

    return False

if __name__ == "__main__":
    success = test_shorts_download()
    if success:
        print("\n🎉 Shorts download test PASSED!")
    else:
        print("\n❌ Shorts download test FAILED!")
    sys.exit(0 if success else 1)