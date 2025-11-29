#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["playwright"]
# ///

"""
Execute Playwright browser automation commands directly.

This script connects to a persistent browser instance via CDP (Chrome DevTools Protocol).
The browser stays open between commands, providing a persistent session.

Usage:
    uv run servers/playwright/run.py start                    # Start persistent browser
    uv run servers/playwright/run.py navigate "https://example.com"
    uv run servers/playwright/run.py snapshot
    uv run servers/playwright/run.py click "button[data-testid='submit']"
    uv run servers/playwright/run.py screenshot output.png
    uv run servers/playwright/run.py eval "document.title"
    uv run servers/playwright/run.py stop                     # Stop browser
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

# State files
STATE_FILE = Path("/tmp/playwright_state.json")
CDP_PORT = 9222


def load_state() -> dict:
    """Load browser state from file."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    """Save browser state to file."""
    current = load_state()
    current.update(state)
    STATE_FILE.write_text(json.dumps(current))


def is_browser_running() -> bool:
    """Check if browser is running on CDP port."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', CDP_PORT))
    sock.close()
    return result == 0


def start_browser():
    """Start a persistent Chrome browser with remote debugging."""
    if is_browser_running():
        return {"success": True, "message": "Browser already running", "port": CDP_PORT}

    # Find chromium path from playwright
    result = subprocess.run(
        ["python", "-c", "from playwright._impl._driver import compute_driver_executable; print(compute_driver_executable())"],
        capture_output=True, text=True
    )
    driver_path = Path(result.stdout.strip()).parent

    # Try common chromium locations (macOS)
    chromium_paths = [
        Path.home() / "Library" / "Caches" / "ms-playwright" / "chromium-1194" / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
        Path.home() / "Library" / "Caches" / "ms-playwright" / "chromium-1187" / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
        Path.home() / ".cache" / "ms-playwright" / "chromium-1194" / "chrome-linux" / "chrome",
        Path.home() / ".cache" / "ms-playwright" / "chromium-1187" / "chrome-linux" / "chrome",
    ]

    chromium_path = None
    for p in chromium_paths:
        if p.exists():
            chromium_path = p
            break

    if not chromium_path:
        # Use system Chrome as fallback
        mac_chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        if mac_chrome.exists():
            chromium_path = mac_chrome
        else:
            return {"error": "Could not find Chrome/Chromium. Install it or run: playwright install chromium"}

    # Start browser with remote debugging
    cmd = [
        str(chromium_path),
        f"--remote-debugging-port={CDP_PORT}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--window-size=1800,1400",
    ]

    # Start detached
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

    # Wait for browser to be ready
    for _ in range(30):
        if is_browser_running():
            save_state({"pid": proc.pid})
            return {"success": True, "message": "Browser started", "port": CDP_PORT, "pid": proc.pid}
        time.sleep(0.2)

    return {"error": "Browser failed to start"}


def stop_browser():
    """Stop the persistent browser."""
    state = load_state()
    pid = state.get("pid")

    # Kill by PID if we have it
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    # Also kill any process on the CDP port
    subprocess.run(["pkill", "-f", f"--remote-debugging-port={CDP_PORT}"], capture_output=True)

    # Clear state
    if STATE_FILE.exists():
        STATE_FILE.unlink()

    return {"success": True, "message": "Browser stopped"}


async def get_page():
    """Connect to persistent browser and get page."""
    if not is_browser_running():
        # Auto-start browser if not running
        result = start_browser()
        if "error" in result:
            raise RuntimeError(result["error"])
        await asyncio.sleep(0.5)

    p = await async_playwright().start()
    browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")

    # Get or create context and page
    contexts = browser.contexts
    if contexts:
        context = contexts[0]
        pages = context.pages
        if pages:
            page = pages[0]
        else:
            page = await context.new_page()
    else:
        context = await browser.new_context()
        page = await context.new_page()

    return p, browser, page


async def cmd_start():
    """Start persistent browser."""
    return start_browser()


async def cmd_stop():
    """Stop persistent browser."""
    return stop_browser()


async def cmd_navigate(url: str):
    """Navigate to a URL."""
    p, browser, page = await get_page()
    await page.goto(url, wait_until="domcontentloaded")
    title = await page.title()
    save_state({"url": url})
    await p.stop()
    return {"success": True, "url": url, "title": title}


async def cmd_snapshot():
    """Get accessibility snapshot of the page."""
    p, browser, page = await get_page()
    snapshot = await page.accessibility.snapshot()
    await p.stop()
    return {"snapshot": snapshot}


async def cmd_screenshot(filename: str = "/tmp/screenshot.png", full_page: bool = False):
    """Take a screenshot."""
    p, browser, page = await get_page()
    path = Path(filename).absolute()
    await page.screenshot(path=path, full_page=full_page)
    await p.stop()
    return {"success": True, "path": str(path)}


async def cmd_click(selector: str):
    """Click an element by selector."""
    p, browser, page = await get_page()
    await page.click(selector)
    new_url = page.url
    save_state({"url": new_url})
    await p.stop()
    return {"success": True, "clicked": selector}


async def cmd_type(selector: str, text: str):
    """Type text into an element."""
    p, browser, page = await get_page()
    await page.fill(selector, text)
    await p.stop()
    return {"success": True, "selector": selector, "text": text}


async def cmd_eval(expression: str):
    """Evaluate JavaScript expression."""
    p, browser, page = await get_page()
    result = await page.evaluate(expression)
    await p.stop()
    return {"result": result}


async def cmd_content():
    """Get page text content."""
    p, browser, page = await get_page()
    text = await page.inner_text("body")
    await p.stop()
    return {"text": text[:5000]}


async def cmd_wait(selector: str = None, timeout: int = 5000):
    """Wait for selector or timeout."""
    p, browser, page = await get_page()
    if selector:
        await page.wait_for_selector(selector, timeout=timeout)
    else:
        await page.wait_for_timeout(timeout)
    await p.stop()
    return {"success": True}


async def cmd_reload():
    """Reload the current page."""
    p, browser, page = await get_page()
    await page.reload(wait_until="domcontentloaded")
    await p.stop()
    return {"success": True, "url": page.url}


async def cmd_press(selector_or_key: str, key: str = None):
    """Press a keyboard key. Usage: press <selector> <key> OR press <key>."""
    p, browser, page = await get_page()
    if key:
        # press selector key - focus on element first
        await page.press(selector_or_key, key)
        result = {"success": True, "selector": selector_or_key, "key": key}
    else:
        # press key - use global keyboard
        await page.keyboard.press(selector_or_key)
        result = {"success": True, "key": selector_or_key}
    await p.stop()
    return result


COMMANDS = {
    "start": cmd_start,
    "stop": cmd_stop,
    "navigate": cmd_navigate,
    "nav": cmd_navigate,
    "snapshot": cmd_snapshot,
    "snap": cmd_snapshot,
    "screenshot": cmd_screenshot,
    "ss": cmd_screenshot,
    "click": cmd_click,
    "type": cmd_type,
    "fill": cmd_type,
    "press": cmd_press,
    "key": cmd_press,
    "eval": cmd_eval,
    "content": cmd_content,
    "text": cmd_content,
    "wait": cmd_wait,
    "reload": cmd_reload,
}


async def main():
    if len(sys.argv) < 2:
        print("Playwright Persistent Browser Runner")
        print("\nCommands:")
        print("  start                 - Start persistent browser")
        print("  stop                  - Stop persistent browser")
        print("  navigate <url>        - Go to URL")
        print("  snapshot              - Get accessibility tree")
        print("  screenshot [file]     - Take screenshot")
        print("  click <selector>      - Click element")
        print("  type <selector> <text>- Type into element")
        print("  eval <js>             - Run JavaScript")
        print("  content               - Get page text")
        print("  wait [selector]       - Wait for element/timeout")
        print("  reload                - Reload current page")
        print("\nExamples:")
        print('  uv run servers/playwright/run.py start')
        print('  uv run servers/playwright/run.py navigate "http://localhost:8500"')
        print("  uv run servers/playwright/run.py screenshot /tmp/test.png")
        print('  uv run servers/playwright/run.py stop')
        sys.exit(0)

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    try:
        func = COMMANDS[cmd]
        if asyncio.iscoroutinefunction(func):
            result = await func(*args)
        else:
            result = func(*args)
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
