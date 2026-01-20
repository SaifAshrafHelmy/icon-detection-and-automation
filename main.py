"""
Desktop Automation with Remote AI Icon Detection
Connects to Colab API for icon detection, runs automation locally
"""
import time
import pyautogui
import pyperclip
import requests
from pathlib import Path
from PIL import Image
import argparse
import base64
import io
import threading
import keyboard
import os
from datetime import datetime
from PIL import ImageDraw

# =========================
# CONFIGURATION
# =========================
API_URL = "https://dummyjson.com/posts"
OUTPUT_DIR = Path.home() / "Desktop" / "tjm-project"

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.25

# =========================
# EMERGENCY STOP SETUP
# =========================
STOP_AUTOMATION = False

def set_stop():
    global STOP_AUTOMATION
    STOP_AUTOMATION = True
    print("\n[ABORT] Emergency stop triggered")

def listen_for_stop():
    keyboard.add_hotkey("ctrl+shift+q", lambda: set_stop())

threading.Thread(target=listen_for_stop, daemon=True).start()

def check_kill_switch():
    if STOP_AUTOMATION:
        raise KeyboardInterrupt

# =========================
# LOGGING
# =========================
def log(level: str, message: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {message}")

# =========================
# SAFETY
# =========================
def is_notepad_focused() -> bool:
    try:
        win = pyautogui.getActiveWindow()
        focused = win and "notepad" in win.title.lower()
        log("FOCUS", f"Notepad focused: {focused}")
        return focused
    except Exception as e:
        log("FOCUS", f"Unable to read active window: {e}")
        return False

# =========================
# UI HELPERS
# =========================
def minimize_all_windows():
    check_kill_switch()
    log("UI", "Minimizing all windows")
    pyautogui.hotkey("win", "m")
    time.sleep(0.6)

def restore_window(window):
    try:
        check_kill_switch()
        if window:
            log("UI", f"Restoring window: {window.title}")
            window.activate()
            time.sleep(0.6)
    except Exception as e:
        log("UI", f"Failed to restore window: {e}")

def show_detection_preview(screenshot: Image.Image, x: int, y: int, label: str) -> Path:
    """Save screenshot with detection marker and return the path."""
    preview = screenshot.copy()
    draw = ImageDraw.Draw(preview)

    # Draw crosshair at detected location
    size = 20
    draw.line((x - size, y, x + size, y), fill="red", width=3)
    draw.line((x, y - size, x, y + size), fill="red", width=3)
    draw.ellipse((x - 10, y - 10, x + 10, y + 10), outline="red", width=3)

    # Add label
    draw.text((x + 15, y - 25), f"{label}: ({x}, {y})", fill="red")

    preview_path = OUTPUT_DIR / "detection_preview.png"
    preview.save(preview_path)
    return preview_path

def ask_confirmation(prompt: str) -> bool:
    """Ask user for yes/no confirmation."""
    while True:
        response = input(f"{prompt} [y/n]: ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'")

def capture_screenshot() -> Image.Image:
    check_kill_switch()
    log("CAPTURE", "Preparing to take screenshot")
    active_win = pyautogui.getActiveWindow()
    minimize_all_windows()
    screenshot = pyautogui.screenshot()
    log("CAPTURE", f"Screenshot size: {screenshot.size}")
    restore_window(active_win)
    return screenshot

# =========================
# REMOTE DETECTOR
# =========================
class RemoteIconDetector:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def health_check(self) -> bool:
        log("API", f"Health check: GET {self.api_url}/health")
        try:
            r = self.session.get(f"{self.api_url}/health", timeout=10)
            log("API", f"Health status code: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                log("API", f"Health OK, response: {data}")
                return True
            log("API", f"Health FAILED, body: {r.text}")
            return False
        except requests.exceptions.Timeout:
            log("API", "Health check timeout")
            return False
        except Exception as e:
            log("API", f"Health check error: {e}")
            return False

    def detect(self, image: Image.Image, description: str, max_retries: int = 3) -> tuple:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        payload = {
            "image": base64.b64encode(buffer.getvalue()).decode(),
            "description": description,
        }

        for attempt in range(1, max_retries + 1):
            check_kill_switch()
            log("API", f"Detection attempt {attempt}/{max_retries}")
            log("API", f"POST {self.api_url}/detect | description='{description}'")

            try:
                r = self.session.post(
                    f"{self.api_url}/detect",
                    json=payload,
                    timeout=60,
                )

                log("API", f"Response status: {r.status_code}")

                if r.status_code != 200:
                    log("API", f"Non-200 response body: {r.text}")
                else:
                    data = r.json()
                    log("API", f"Response JSON: {data}")

                    if data.get("found"):
                        x, y = data["x"], data["y"]
                        log("API", f"Detection SUCCESS at ({x}, {y})")
                        return x, y
                    else:
                        log("API", "Detection completed: icon NOT found")
                        return None, None

            except requests.exceptions.Timeout:
                log("API", "Detection request TIMEOUT")
            except Exception as e:
                log("API", f"Detection error: {e}")

            if attempt < max_retries:
                log("API", "Retrying after short delay")
                time.sleep(0.8)

        log("API", "Detection FAILED after all retries")
        return None, None

# =========================
# AUTOMATION
# =========================
class AutomationWorkflow:
    def __init__(self, api_url: str, app_name: str, screenshot_path: str | None = None, auto_mode: bool = False):
        self.api_url = api_url
        self.app_name = app_name
        self.screenshot_path = screenshot_path
        self.auto_mode = auto_mode
        self.detector = RemoteIconDetector(api_url)
        self.app_coords = None
        self.last_screenshot = None
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        log("DIR", f"Output directory: {OUTPUT_DIR}")
        log("MODE", f"Running in {'AUTO' if auto_mode else 'CONFIRMATION'} mode")
        log("TARGET", f"Looking for: {app_name}")

    def detect_app_icon(self) -> bool:
        log("FLOW", f"Starting {self.app_name} icon detection")

        if not self.detector.health_check():
            log("FLOW", "API health check failed")
            return False

        if self.screenshot_path:
            log("FLOW", f"Loading screenshot from {self.screenshot_path}")
            screenshot = Image.open(self.screenshot_path)
        else:
            screenshot = capture_screenshot()

        self.last_screenshot = screenshot

        description = f"Locate the {self.app_name} Windows application icon from this desktop screenshot and return the center coordinates as (x, y)"
        x, y = self.detector.detect(screenshot, description)
        if x is not None:
            self.app_coords = (x, y)
            log("FLOW", f"Stored {self.app_name} coordinates: {self.app_coords}")

            if not self.auto_mode:
                if not self.confirm_detection(screenshot, x, y, f"{self.app_name} icon"):
                    log("FLOW", "User rejected detection")
                    return False

            return True

        log("FLOW", f"{self.app_name} icon not detected")
        return False

    def confirm_detection(self, screenshot: Image.Image, x: int, y: int, label: str) -> bool:
        """Show detection result and ask for user confirmation."""
        preview_path = show_detection_preview(screenshot, x, y, label)
        log("CONFIRM", f"Preview saved to: {preview_path}")

        print("\n" + "=" * 50)
        print(f"DETECTION RESULT: {label}")
        print(f"Coordinates: ({x}, {y})")
        print(f"Preview image: {preview_path}")
        print("=" * 50)

        # Open the preview image
        try:
            os.startfile(preview_path)
        except Exception as e:
            log("CONFIRM", f"Could not open preview: {e}")

        return ask_confirmation("Does the detection look correct? Continue?")

    def click_element(self, x: int, y: int, double: bool = False):
        check_kill_switch()
        log("UI", f"Moving mouse to ({x}, {y})")
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(0.15)
        if double:
            log("UI", "Double click")
            pyautogui.doubleClick()
        else:
            log("UI", "Single click")
            pyautogui.click()

    def launch_app(self) -> bool:
        if not self.app_coords:
            log("FLOW", f"No {self.app_name} coordinates available")
            return False
        log("FLOW", f"Minimizing windows to show desktop before launching {self.app_name}")
        minimize_all_windows()
        self.click_element(*self.app_coords, double=True)
        time.sleep(1.2)
        return True

    def close_app(self):
        log("UI", f"Closing {self.app_name}")
        pyautogui.hotkey("alt", "f4")
        time.sleep(0.5)

    def fetch_posts(self, limit: int = 10) -> list[dict]:
        log("API", f"Fetching posts: {API_URL}?limit={limit}")
        try:
            r = requests.get(f"{API_URL}?limit={limit}", timeout=10)
            log("API", f"Posts status code: {r.status_code}")
            r.raise_for_status()
            posts = r.json().get("posts", [])
            log("API", f"Fetched {len(posts)} posts")
            return posts
        except Exception as e:
            log("API", f"Failed to fetch posts: {e}")
            return []

    def format_post_content(self, post: dict) -> str:
        return f"Title: {post['title']}\n\n{post['body']}"

    def get_safe_filepath(self, base: Path) -> Path:
        if not base.exists():
            return base
        for i in range(1, 6):
            alt = base.with_stem(f"{base.stem}_retry_{i}")
            if not alt.exists():
                log("FILE", f"Using fallback filename: {alt.name}")
                return alt
        log("FILE", "Fallback exhausted, using base filename")
        return base

    def verify_file_saved(self, path: Path, expected: str) -> bool:
        try:
            if not path.exists():
                log("VERIFY", "File does not exist")
                return False
            actual = path.read_text(encoding="utf-8")
            match = actual == expected
            log("VERIFY", f"Content match: {match}")
            return match
        except Exception as e:
            log("VERIFY", f"Verification error: {e}")
            return False

    def verify_file_saved_with_retry(self, path: Path, expected: str, retries: int = 3) -> bool:
        for i in range(1, retries + 1):
            check_kill_switch()
            log("VERIFY", f"Verification attempt {i}/{retries}")
            if self.verify_file_saved(path, expected):
                return True
            time.sleep(0.4)
        log("VERIFY", "Verification failed after retries")
        return False

    def save_post_in_notepad(self, post: dict) -> bool:
        check_kill_switch()

        content = self.format_post_content(post)
        filepath = self.get_safe_filepath(
            OUTPUT_DIR / f"post_{post['id']}.txt"
        )

        log("SAVE", f"Saving post {post['id']} to {filepath}")

        pyperclip.copy(content)
        time.sleep(0.15)

        if not is_notepad_focused():
            log("FOCUS", "Attempting to refocus Notepad")
            pyautogui.click()
            time.sleep(0.2)

        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.4)

        pyautogui.hotkey("ctrl", "s")
        time.sleep(0.8)

        pyperclip.copy(str(filepath.absolute()))
        time.sleep(0.15)

        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.25)

        pyautogui.press("enter")
        time.sleep(0.4)
        pyautogui.hotkey("alt", "y")

        return self.verify_file_saved_with_retry(filepath, content)

    def run(self):
        log("FLOW", "Automation started")

        if not self.detect_app_icon():
            log("FLOW", "Stopping due to detection failure")
            return

        time.sleep(1.0)

        posts = self.fetch_posts(10)
        if not posts:
            log("FLOW", "No posts to process")
            return

        for post in posts:
            check_kill_switch()
            log("FLOW", f"Processing post ID {post['id']}")
            if not self.launch_app():
                continue
            try:
                self.save_post_in_notepad(post)
            finally:
                self.close_app()
                time.sleep(0.6)

# =========================
# ENTRY POINT
# =========================
def main():
    parser = argparse.ArgumentParser(
        description="Desktop Automation with Remote AI Icon Detection"
    )
    parser.add_argument("--screenshot", type=str, default=None,
                        help="Path to screenshot file (skips live capture)")
    parser.add_argument("--auto", action="store_true",
                        help="Run in auto mode without confirmation prompts")
    parser.add_argument("--app", type=str, default=None,
                        help="App name to detect (e.g., Notepad, Chrome)")
    args = parser.parse_args()

    ngrok_url = input("Enter ngrok URL: ").strip()
    if not ngrok_url:
        log("INIT", "No URL provided")
        return
    if not ngrok_url.startswith("http"):
        ngrok_url = "https://" + ngrok_url
    ngrok_url = ngrok_url.rstrip("/")

    app_name = args.app
    if not app_name:
        app_name = input("Enter app name to detect (e.g., Notepad): ").strip()
    if not app_name:
        log("INIT", "No app name provided")
        return

    log("INIT", f"Using API URL: {ngrok_url}")

    try:
        workflow = AutomationWorkflow(ngrok_url, app_name, args.screenshot, auto_mode=args.auto)
        workflow.run()
    except KeyboardInterrupt:
        log("STOPPED", "Automation aborted safely")

if __name__ == "__main__":
    main()