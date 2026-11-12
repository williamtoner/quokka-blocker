#!/usr/bin/env python3
"""Draw the toolbar and store icons from icons/mark.svg (needs Python Playwright)."""
import glob
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
MARK = (ROOT / "extension/icons/mark.svg").read_text()
GREEN, CREAM = "#2F5D50", "#F6EBDD"


def tile(size):
    # Small sizes drop the face details and fill more of the tile.
    scale, dx, dy = (0.9, 3.5, 0.5) if size <= 16 else (0.86, 5, 2)
    inner = MARK.split(">", 1)[1].rsplit("</svg>", 1)[0]
    if size <= 16:
        inner = inner.split("<circle cx=\"43.8\"")[0]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}">
<rect width="64" height="64" rx="15" fill="{GREEN}"/>
<g transform="translate({dx} {dy}) scale({scale})" style="color:{CREAM};--qb-cut:{GREEN}">{inner}</g></svg>"""


def main():
    exe = (sys.argv[1:] or glob.glob(str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux*/chrome")))[0]
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe)
        for size in (16, 32, 48, 128):
            page = browser.new_page(viewport={"width": size, "height": size})
            page.set_content(f"<html><body style='margin:0;background:transparent'>{tile(size)}</body></html>")
            page.screenshot(path=str(ROOT / f"extension/icons/icon{size}.png"), omit_background=True)
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
