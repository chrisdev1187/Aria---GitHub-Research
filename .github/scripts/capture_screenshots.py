"""
Capture screenshots of the ARIA dashboard with proper UI interactions.
Each screenshot shows a distinct view via clicking tabs and buttons.

Usage: python capture_screenshots.py
Prerequisites: ARIA server running at http://127.0.0.1:8080/
"""

import os
import sys
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent.parent.parent / "docs" / "screenshots"
BASE_URL = "http://127.0.0.1:8080"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def log(msg):
    print(msg, flush=True)


def capture(name, page_fn):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = ctx.new_page()
        page.set_default_timeout(15000)
        try:
            page_fn(page)
            page.wait_for_timeout(1500)
            path = OUTPUT_DIR / f"{name}.png"
            page.screenshot(path=str(path), full_page=True)
            sz = os.path.getsize(path)
            log(f"  OK  {name}.png ({sz//1024}K)")
        except Exception as e:
            log(f"  FAIL {name}.png: {e}")
        finally:
            browser.close()


def intake_screen(page):
    """Navigate to root and reset to show the empty intake form."""
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_timeout(1000)
    # Try clicking a reset/new-run button to return to intake form
    for text in ["New Run", "New run", "Reset", "Clear"]:
        btn = page.query_selector(f"button:has-text('{text}')")
        if btn:
            btn.click()
            page.wait_for_timeout(1000)
            break


def pipeline_screen(page):
    """Show the pipeline in-progress (or main view with agents)."""
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_timeout(1000)
    # If there's a Pipeline tab, click it
    for text in ["Pipeline", "Agents", "Progress"]:
        tab = page.query_selector(f"button:has-text('{text}'), [role='tab']:has-text('{text}')")
        if tab:
            tab.click()
            page.wait_for_timeout(1000)
            break
    page.wait_for_timeout(500)


def package_screen(page):
    """Show the Package tab with results."""
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_timeout(1000)
    for text in ["Package", "Results", "Knowledge"]:
        tab = page.query_selector(f"button:has-text('{text}'), [role='tab']:has-text('{text}')")
        if tab:
            tab.click()
            page.wait_for_timeout(1000)
            break
    page.wait_for_timeout(500)


def brief_tab(page):
    """Click on the Brief tab within the Package view."""
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_timeout(1000)
    for text in ["Brief", "Summary"]:
        tab = page.query_selector(f"button:has-text('{text}'), [role='tab']:has-text('{text}')")
        if tab:
            tab.click()
            page.wait_for_timeout(1000)
            break
    page.wait_for_timeout(500)


def subproblems_tab(page):
    """Click on the Sub-problems tab."""
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_timeout(1000)
    for text in ["Sub-problem", "Problems", "Decomposition"]:
        tab = page.query_selector(f"button:has-text('{text}'), [role='tab']:has-text('{text}')")
        if tab:
            tab.click()
            page.wait_for_timeout(1000)
            break
    page.wait_for_timeout(500)


def settings_panel(page):
    """Open settings/tweaks panel."""
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_timeout(1000)
    for text in ["Tweaks", "Settings", "Theme", "Configure"]:
        btn = page.query_selector(f"button:has-text('{text}')")
        if btn:
            btn.click()
            page.wait_for_timeout(1000)
            break
    page.wait_for_timeout(500)


if __name__ == "__main__":
    shots = [
        ("01-intake-screen", intake_screen),
        ("02-pipeline-screen", pipeline_screen),
        ("03-package-screen", package_screen),
        ("04-brief-tab", brief_tab),
        ("05-sub-problems-tab", subproblems_tab),
        ("06-settings-panel", settings_panel),
    ]
    log(f"Capturing {len(shots)} screenshots to {OUTPUT_DIR}")
    for name, fn in shots:
        capture(name, fn)
    files = list(OUTPUT_DIR.glob("*.png"))
    log(f"Done -- {len(files)} screenshots, {sum(f.stat().st_size for f in files)//1024}K total")
