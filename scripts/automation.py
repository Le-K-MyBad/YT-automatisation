import os
import yaml
import subprocess
import sys
import json
from pathlib import Path

# selenium used for scraping channel pages instead of YouTube Data API
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    webdriver = None
    Options = None
    By = None
    WebDriverException = None

# Import google API libraries only when needed for upload
try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    import google.auth
    import pickle
except ImportError:
    build = None


CONFIG_PATH = Path(__file__).parent.parent / "config.yml"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def load_config(path=CONFIG_PATH):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def download_video(url, output_dir, config=None):
    """Download a video from YouTube.
    
    For Shorts, we try multiple approaches to bypass bot detection.
    """
    if config is None:
        config = load_config()
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if it's a Short
    is_short = "shorts" in url.lower()
    
    if is_short:
        print(f"Detected Short: {url}")
        # Try Selenium first if available
        if webdriver is not None and is_chrome_available():
            try:
                print("Attempting download with Selenium...")
                return download_short_with_selenium(url, output_dir)
            except Exception as e:
                print(f"Selenium failed: {e}. Trying enhanced yt-dlp...")
        
        # Try enhanced yt-dlp strategies for Shorts
        cookies_file = config.get('youtube_cookies_file')
        if cookies_file:
            cookies_path = Path(cookies_file)
            if not cookies_path.is_absolute():
                cookies_path = Path(__file__).parent.parent / cookies_file
            if cookies_path.exists():
                print(f"Using cookies file: {cookies_path}")
            else:
                cookies_path = None
        else:
            cookies_path = None
            
        try:
            return download_short_with_yt_dlp(url, output_dir, cookies_path)
        except Exception as e:
            print(f"Enhanced yt-dlp failed: {e}. Trying basic yt-dlp...")
    
    # Fallback: use yt-dlp with options to avoid bot detection
    print(f"Using yt-dlp to download: {url}")
    cmd = [
        "yt-dlp",
        "--no-check-certificates",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-f",
        "best[ext=mp4]/best",
        "-o",
        str(output_dir / "%(title)s.%(ext)s"),
        url,
    ]
    
    # Add cookies if available
    if config and config.get('youtube_cookies_file'):
        cookies_file = config['youtube_cookies_file']
        if not Path(cookies_file).is_absolute():
            cookies_file = Path(__file__).parent.parent / cookies_file
        if cookies_file.exists():
            cmd.extend(["--cookies", str(cookies_file)])
            print(f"Using cookies file: {cookies_file}")
    
    subprocess.check_call(cmd)
    # return path to downloaded file (simplest heuristic: choose newest file)
    files = list(output_dir.glob("*"))
    return max(files, key=lambda p: p.stat().st_mtime)


def download_short_with_yt_dlp(url, output_dir, cookies_file=None):
    """Download a YouTube Short using enhanced yt-dlp options."""
    output_dir = Path(output_dir)
    
    print(f"Downloading Short with enhanced yt-dlp: {url}")
    
    # Base command parts
    base_cmd = [
        "yt-dlp",
        "--no-check-certificates",
        "--retries", "3",
        "--fragment-retries", "3",
        "-f", "best[ext=mp4]/best",
        "-o", str(output_dir / "%(title)s.%(ext)s"),
    ]
    
    # Add cookies if provided
    if cookies_file and Path(cookies_file).exists():
        base_cmd.extend(["--cookies", str(cookies_file)])
    
    # Multiple fallback strategies for Shorts
    strategies = [
        {
            "name": "Mobile Android with cookies",
            "extra_args": [
                "--user-agent", "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
                "--add-header", "Referer:https://www.youtube.com/",
                "--add-header", "Origin:https://www.youtube.com",
                "--extractor-args", "youtube:player_client=android",
            ]
        },
        {
            "name": "Desktop with browser cookies",
            "extra_args": [
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--add-header", "Referer:https://www.youtube.com/",
                "--add-header", "Origin:https://www.youtube.com",
                "--cookies-from-browser", "chrome",  # Try to get cookies from Chrome
            ]
        },
        {
            "name": "Basic with minimal headers",
            "extra_args": [
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
        }
    ]
    
    for strategy in strategies:
        try:
            print(f"Trying strategy: {strategy['name']}")
            cmd = base_cmd + strategy['extra_args'] + [url]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print(f"✓ Strategy '{strategy['name']}' succeeded")
                # Find the downloaded file
                files = list(output_dir.glob("*.mp4"))
                if files:
                    latest_file = max(files, key=lambda p: p.stat().st_mtime)
                    size = latest_file.stat().st_size
                    print(f"Downloaded file: {latest_file} ({size} bytes)")
                    if size > 10000:  # At least 10KB to be valid
                        return latest_file
                    else:
                        print(f"File too small ({size} bytes), trying next strategy...")
                        continue
                else:
                    print("No mp4 file found after successful download")
                    continue
            else:
                print(f"✗ Strategy '{strategy['name']}' failed")
                # Show some error details
                error_lines = result.stderr.strip().split('\n')[-5:]  # Last 5 lines
                for line in error_lines:
                    if line.strip():
                        print(f"  {line}")
                continue
                
        except subprocess.TimeoutExpired:
            print(f"✗ Strategy '{strategy['name']}' timed out")
            continue
        except Exception as e:
            print(f"✗ Strategy '{strategy['name']}' error: {e}")
            continue
    
    raise RuntimeError("All download strategies failed for YouTube Short")


def merge_with_relaxing(original_path, relaxing_path, output_path):
    # simple ffmpeg concat: put relaxing video overlay or background
    # here we assume we just concatenate for simplicity
    cmd = [
        "ffmpeg",
        "-i",
        str(relaxing_path),
        "-i",
        str(original_path),
        "-filter_complex",
        "[0:v][1:v]concat=n=2:v=1:a=0[out]",
        "-map",
        "[out]",
        str(output_path),
    ]
    subprocess.check_call(cmd)


def authenticate_youtube(client_secrets_file):
    creds = None
    token_path = Path("token.pickle")
    if token_path.exists():
        with open(token_path, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, file_path, title=None, description=None, tags=None, privacy="public"):
    body = {
        "snippet": {
            "title": title or file_path.stem,
            "description": description or "Processed video",
            "tags": tags or [],
        },
        "status": {"privacyStatus": privacy},
    }
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=file_path,
    )
    response = request.execute()
    return response



STATE_PATH = Path("state.json")

def load_state(path=STATE_PATH):
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}


def save_state(state, path=STATE_PATH):
    with open(path, "w") as f:
        json.dump(state, f)


def get_latest_videos_for_channel(youtube, channel_id, max_results=1):
    """Fetch latest videos from a channel using YouTube Data API."""
    req = youtube.search().list(
        part="id",
        channelId=channel_id,
        order="date",
        type="video",
        maxResults=max_results,
    )
    res = req.execute()
    return [f"https://www.youtube.com/watch?v={item['id']['videoId']}" for item in res.get("items", [])]



def is_chrome_available() -> bool:
    """Return True if a Chrome/Chromium binary exists in PATH.

    We try to call various chromium/chrome commands and
    consider success indicative that selenium might work.
    """
    for cmd in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):  # noqa
        try:
            subprocess.check_call([cmd, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            continue
    return False


def resolve_channel_identifier(identifier: str) -> str:
    """Return a canonical channel ID from a given channel identifier.

    The input may already be a channel ID (UC…), a handle (@name), or even a
    custom name. We fetch the channel page and look for the `<link
    rel="canonical">` or `meta[itemprop=channelId]` tags to obtain the proper
    ID.
    """
    if identifier.startswith("UC"):
        return identifier
    # try handle or other page
    if webdriver is None or Options is None:
        # cannot resolve without selenium; assume the identifier is already an ID
        return identifier
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    driver = None
    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
        url = identifier
        if not identifier.startswith("https://"):
            # assume it's a handle
            url = f"https://www.youtube.com/{identifier}"
        driver.get(url)
        driver.implicitly_wait(5)
        # look for meta channelId
        try:
            meta = driver.find_element(By.CSS_SELECTOR, "meta[itemprop='channelId']")
            cid = meta.get_attribute("content")
            if cid:
                return cid
        except Exception:
            pass
        # fallback: canonical link
        try:
            link = driver.find_element(By.CSS_SELECTOR, "link[rel='canonical']")
            href = link.get_attribute("href")
            # href is like https://www.youtube.com/channel/UCxxxxx
            if "/channel/" in href:
                return href.split("/channel/")[-1]
        except Exception:
            pass
    except Exception:
        pass
    finally:
        if driver:
            driver.quit()
    # give up
    return identifier


def get_latest_videos_for_channel_selenium(channel_id, max_results=1):
    """Scrape the channel's /videos page with selenium and return newest video URLs.

    Accepts any identifier; resolves handles to actual channel ID first.
    """
    real_id = resolve_channel_identifier(channel_id)
    if webdriver is None or Options is None:
        raise RuntimeError("selenium not installed; cannot scrape channel")
    if not is_chrome_available():
        raise RuntimeError("no Chrome/Chromium binary found in PATH")
    url = f"https://www.youtube.com/channel/{real_id}/videos"
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    driver = None
    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
        driver.get(url)
        driver.implicitly_wait(5)
        elems = driver.find_elements(By.CSS_SELECTOR, "a#video-title")
        results = []
        for a in elems[:max_results]:
            href = a.get_attribute("href")
            if href:
                results.append(href)
        return results
    except WebDriverException as e:
        raise RuntimeError(f"selenium webdriver error: {e}")
    finally:
        if driver:
            driver.quit()


def main():
    config = load_config()
    urls = config.get("video_urls") or []
    
    # check if URLs are provided via CLI first; if so skip channel processing
    has_cli_urls = len(sys.argv) > 1
    if has_cli_urls:
        urls = sys.argv[1:]
    else:
        # gather from channels if provided (only if no CLI URLs)
        channels = config.get("channels", [])
        if channels:
            state = load_state()
            for ch in channels:
                vids = []
                # first try selenium scraping
                if webdriver is not None:
                    try:
                        vids = get_latest_videos_for_channel_selenium(ch, max_results=3)
                    except Exception as e:
                        print(f"Selenium scraping failed for {ch}: {e}")
                # fallback to YouTube Data API if available and we have secrets
                if not vids:
                    if build is not None:
                        if os.path.exists(config.get("youtube_client_secrets", "")):
                            try:
                                yt = authenticate_youtube(config["youtube_client_secrets"])
                                vids = get_latest_videos_for_channel(yt, ch, max_results=3)
                            except Exception as e:
                                print(f"API scraping failed for {ch}: {e}")
                        else:
                            print(f"Skipping API fallback for {ch}: client_secrets.json not found")
                if not vids:
                    print(f"Unable to retrieve videos for channel {ch}. "
                          "Make sure Chrome is installed or provide client_secrets.json.")
                last_id = state.get(ch)
                for vid in vids:
                    vid_id = vid.split("v=")[-1]
                    if vid_id == last_id:
                        break
                    urls.append(vid)
                if vids:
                    state[ch] = vids[0].split("v=")[-1]
            save_state(state)

    # if still no URLs, show error
    if not urls:
        print("No videos found to process.\n"
              "Please provide video URLs via the CLI or add `video_urls` to\n"
              "config.yml. If you are using `channels`, ensure that Chrome/\n"
              "Chromedriver are installed or that `client_secrets.json` is\n"
              "present so the API fallback can run.")
        sys.exit(1)

    relaxing = Path(config["relaxing_video"])
    out_dir = Path(config.get("output_dir", "output"))
    yt_client = None
    
    # only authenticate if client_secrets exists and we have the library
    client_secrets_file = config.get("youtube_client_secrets", "client_secrets.json")
    if build and Path(client_secrets_file).exists():
        try:
            yt_client = authenticate_youtube(client_secrets_file)
        except Exception as e:
            print(f"Warning: could not authenticate YouTube API: {e}")

    for url in urls:
        print(f"Processing {url}")
        orig = download_video(url, out_dir, config)
        merged = out_dir / f"merged_{orig.name}"
        merge_with_relaxing(orig, relaxing, merged)
        print(f"Merged file at {merged}")
        if yt_client:
            try:
                resp = upload_video(yt_client, merged)
                print("Upload response:", resp)
            except Exception as e:
                print(f"Warning: upload failed: {e}")


if __name__ == "__main__":
    main()
