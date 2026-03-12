import unittest
from pathlib import Path
import json

from scripts.automation import (
    load_config,
    download_video,
    merge_with_relaxing,
    load_state,
    save_state,
    get_latest_videos_for_channel_selenium,
    is_chrome_available,
)


class AutomationTests(unittest.TestCase):
    def test_load_config(self):
        tmp_dir = Path(".")
        cfg = tmp_dir / "cfg.yml"
        cfg.write_text("relaxing_video: relax.mp4\noutput_dir: out\n")
        loaded = load_config(cfg)
        self.assertEqual(loaded["relaxing_video"], "relax.mp4")
        self.assertEqual(loaded["output_dir"], "out")

    def test_state(self):
        tmp_dir = Path(".")
        state_file = tmp_dir / "state.json"
        data = {"UC123": "abc"}
        save_state(data, state_file)
        loaded = load_state(state_file)
        self.assertEqual(loaded, data)

    @unittest.skip("selenium scraping not run in CI or without Chrome")
    def test_scrape_channel(self):
        urls = get_latest_videos_for_channel_selenium(
            "UC_x5XG1OV2P6uZZ5FSM9Ttw", max_results=1
        )
        self.assertTrue(urls and urls[0].startswith("https://www.youtube.com/watch"))

    def test_chrome_check(self):
        self.assertIsInstance(is_chrome_available(), bool)


if __name__ == "__main__":
    unittest.main()

