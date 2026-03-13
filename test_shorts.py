#!/usr/bin/env python3
"""Test script to check if Shorts download works."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from automation import download_video, Path
import shutil

def test_shorts_download():
    """Test downloading a YouTube Short."""
    # Clean output directory
    output_dir = Path("output")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Test URL
    test_url = "https://www.youtube.com/shorts/hj_mb_1GvL0"

    try:
        print(f"Testing download of: {test_url}")
        result_file = download_video(test_url, output_dir)
        print(f"✓ Download successful: {result_file}")
        print(f"File size: {result_file.stat().st_size} bytes")
        return True
    except Exception as e:
        print(f"✗ Download failed: {e}")
        return False

if __name__ == "__main__":
    success = test_shorts_download()
    sys.exit(0 if success else 1)