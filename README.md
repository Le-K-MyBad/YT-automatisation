# YT-automatisation

Project for automating the download, processing, and upload of YouTube videos.

This repository contains a basic Python script that:

1. Downloads videos from YouTube using `yt-dlp`.
2. Scrapes channel pages with **selenium** to discover recent uploads (no Data API required).
3. Merges each video with a pre‑chosen relaxing overlay/background video via `ffmpeg`.
4. Optionally uploads the processed video to your YouTube channel using the YouTube Data API (this is the only API call; scraping and download avoid it).

## Getting Started

### Quick Start with GitHub Codespaces (Recommended)

The easiest way is to use the included `.devcontainer/` configuration:

1. Open this repository in GitHub Codespaces
2. The environment will **automatically**:
   - Install Chromium and Chromedriver (for YouTube Shorts support)
   - Install FFmpeg (for video merging)
   - Install all Python dependencies
   - Create a test video (`relaxing.mp4`)

3. Once ready, run:
   ```sh
   python scripts/automation.py "https://www.youtube.com/watch?v=VIDEO_ID"
   python scripts/automation.py "https://www.youtube.com/shorts/SHORT_ID"
   ```

### Manual Setup (Local Machine)

If running locally:


- Python 3.8+
- `ffmpeg` installed on your system and available in `PATH`.
- `chromedriver` (managed automatically by `webdriver-manager`) and the `selenium` Python package for scraping.
- A Google Cloud project with YouTube Data API enabled and OAuth 2.0 client credentials (only needed if you want automatic uploads).

### Installation

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### YouTube Cookies (for Shorts) - IMPORTANT

**YouTube Shorts require cookies to work!** Without them, downloads will fail with "Sign in to confirm you're not a bot".

#### How to get YouTube cookies:

1. **Install extension**: Get "Get cookies.txt LOCALLY" for Chrome/Firefox
   - Chrome: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndoehmjpmgmpgmcecfnghjpppnk
   - Firefox: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/

2. **Login to YouTube**: Open YouTube in your browser and login

3. **Export cookies**: Click the extension icon → "Export as cookies.txt"

4. **Save file**: Save as `cookies.txt` in your project root

5. **Update config.yml**:
   ```yaml
   youtube_cookies_file: "cookies.txt"
   ```

#### Alternative: Browser cookies
You can also use `--cookies-from-browser chrome` if yt-dlp can access your browser profile.

**Note**: Cookies expire after ~1 month. Re-export when downloads fail.

### Configuration

Edit `config.yml` and set:

- `relaxing_video`: path to your relaxing overlay video file.
- `output_dir`: directory to store downloaded and merged videos.
- `youtube_client_secrets`: path to your OAuth client secrets JSON.
- `youtube_channel_id`: (optional) ID of the channel you own.
- `video_urls`: array of YouTube video URLs to process (can also be provided via CLI).
- `channels`: array of **channel identifiers** whose latest videos will be scraped automatically.
  Each entry can be a raw ID (`UC…`), a handle like `@Michou`, or a full URL
  (`https://www.youtube.com/@Michou`). The script resolves it to the canonical
  channel ID before fetching. The state of last‑seen videos is stored in
  `state.json`.

### Usage

```sh
python scripts/automation.py <url1> [url2 ...]
```

or simply:

```sh
python scripts/automation.py
```

The script pulls URLs from `video_urls` and/or from `channels` as configured.

> **Codespaces note:** GitHub Codespaces does not include a Chrome/Chromium
> browser or driver by default, so selenium scraping will fail (the `apt update`
> command also errors because the container may be locked down). The script now
> handles four common issues:
>
> 1. *Missing selenium package* – the code checks and skips scraping if the
>    module is absent.
> 2. *No Chrome/Chromium binary* – a helper function `is_chrome_available()`
>    probes the path and raises an informative error if not found.
> 3. *WebDriver exceptions* – any `selenium` errors during browser startup or
>    page load are caught and reported.
> 4. *Container restrictions* – if scraping fails for any reason the script
>    automatically falls back to the YouTube Data API (the only remaining API
>    usage). You’ll need valid credentials for this fallback mode.
>
> **How to make it work in Codespaces**:
> - *Install Chromium manually* in the dev container (e.g. add `apt install -y
>   chromium-browser chromium-chromedriver` to the `devcontainer.json` post-
>   create step) so that selenium can launch headless.
> - Or simply rely on the API fallback by supplying `client_secrets.json` and
>   leaving `channels` configured; the code will detect that scraping failed and
>   use API calls instead.
> - Running the repository on a local machine with Chrome avoids all of these
>   issues.
>
> Below are instructions for testing both modes.

Uploading requires authorizing with your Google account on first run; a `token.pickle` file will be saved for subsequent runs.

## Tests

Run the unit tests (they use the standard `unittest` library so no extra
packages are required):

```sh
python -m unittest tests/test_automation.py
```

- `test_scrape_channel` is marked `skip` because it requires selenium/Chrome;
  you can remove the decorator locally if you install those components.
- `test_chrome_check` simply verifies that the helper returns a boolean.

### Manual verification

1. **Selenium mode (with Chrome available)**
   - Ensure `selenium` and Chrome/Chromedriver are installed (see prerequisites).
   - Add one or more channel IDs to `config.yml` under `channels`.
   - Run `python scripts/automation.py` and observe output. Scraping errors will
     be shown if the browser can’t start.

2. **API fallback mode**
   - Uninstall `selenium` (`pip uninstall selenium webdriver-manager`) or
     remove Chrome from `PATH`.
   - Make sure `config.yml` contains `youtube_client_secrets` and `channels`.
   - Execute the script again; you should see messages about falling back to the
     API and the videos being retrieved via the Data API instead of scraping.

3. **Direct URL mode**
   - Provide one or more video URLs via CLI or `video_urls` in config; the
     script will download and merge them without hitting YouTube or Chrome at
     all.

## Notes

- The current `merge_with_relaxing` function simply concatenates the relaxing video before the downloaded video; modify it to suit your editing requirements (e.g., overlay, picture‑in‑picture, etc.).
- This repo is intended as a starting point; extend and harden as needed.
