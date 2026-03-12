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


def download_video(url, output_dir):
    """Download a video from YouTube.
    
    For Shorts, we use Selenium to authenticate as a real browser.
    For regular videos, we use yt-dlp.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if it's a Short
    is_short = "shorts" in url.lower()
    
    if is_short and webdriver is not None and is_chrome_available():
        print(f"Using Selenium to download Short: {url}")
        return download_short_with_selenium(url, output_dir)
    
    # Fallback: use yt-dlp with options to avoid bot detection
    print(f"Using yt-dlp to download: {url}")
    cmd = [
        "yt-dlp",
        "--no-check-certificates",
        "-f",
        "best[ext=mp4]/best",
        "-o",
        str(output_dir / "%(title)s.%(ext)s"),
        url,
    ]
    subprocess.check_call(cmd)
    # return path to downloaded file (simplest heuristic: choose newest file)
    files = list(output_dir.glob("*"))
    return max(files, key=lambda p: p.stat().st_mtime)


def download_short_with_selenium(url, output_dir):
    """Download a YouTube Short using Selenium to bypass bot detection."""
    if webdriver is None or Options is None:
        raise RuntimeError("Selenium not available for Short download")
    
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = None
    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
        driver.get(url)
        driver.implicitly_wait(10)
        
        # Wait for the video player to load and extract video info
        # Try to find the video source or title
        try:
            title_elem = driver.find_element(By.CSS_SELECTOR, "h1.style-scope.ytd-rich-metadata-row-renderer")
            title = title_elem.text or "short_video"
        except Exception:
            title = "short_video"
        
        # Get page source to extract JSON metadata
        page_source = driver.page_source
        
        # Extract video ID from URL
        video_id = url.split("/")[-1] if "/" in url else url
        
        # Use yt-dlp in a subprocess with the URL (Selenium+browser cookies might help)
        # But we'll try a simpler approach: call yt-dlp with the URL directly
        # since we've loaded it in a browser context
        output_file = output_dir / f"{title}.mp4"
        
        cmd = [
            "yt-dlp",
            "-f", "best[ext=mp4]/best",
            "-o", str(output_file),
            "--no-check-certificates",
            url,
        ]
        subprocess.check_call(cmd)
        
        return output_file if output_file.exists() else max(output_dir.glob("*"), key=lambda p: p.stat().st_mtime)
    
    except Exception as e:
        print(f"Selenium download failed: {e}. Falling back to yt-dlp...")
        # Fallback to regular yt-dlp
        cmd = [
            "yt-dlp",
            "--no-check-certificates",
            "-f",
            "best[ext=mp4]/best",
            "-o",
            str(output_dir / "%(title)s.%(ext)s"),
            url,
        ]
        subprocess.check_call(cmd)
        files = list(output_dir.glob("*"))
        return max(files, key=lambda p: p.stat().st_mtime)
    
    finally:
        if driver:
            driver.quit()


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

    We try to call `chromedriver --version` or `google-chrome --version` and
    consider success indicative that selenium might work.
    """
    for cmd in ("chromedriver", "google-chrome", "chromium-browser", "chromium"):  # noqa
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
        orig = download_video(url, out_dir)
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
