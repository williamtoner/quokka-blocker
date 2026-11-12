#!/usr/bin/env python3
"""Run the extension on real websites and photograph the results.

    QB_CHROMIUM=/path/to/chrome python3 test/live.py OUT_DIR [URL ...]

For each site: open it, accept the consent wall if one appears, scroll down
slowly so lazy ads load, then count the animal cards and screenshot the page
around the first few. Real ads differ by country and day, so this reports
rather than asserts.
"""
import glob
import os
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
SITES = [
    "https://www.accuweather.com/en/jp/tokyo/226396/weather-forecast/226396",
    "https://www.speedtest.net/",
    "https://www.tomshardware.com/",
    "https://gigazine.net/",
    "https://tenki.jp/",
    "https://www.itmedia.co.jp/news/",
    "https://www.theguardian.com/international",
    "https://www.independent.co.uk/",
]
CONSENT = ["Accept all", "Accept All", "ACCEPT ALL", "I Accept", "I accept", "Accept", "Agree", "AGREE", "I agree",
           "Alles accepteren", "Akkoord", "Accepteren", "Toestemming", "Yes, I'm happy", "Allow all", "OK", "同意する", "同意"]


def chromium():
    exe = os.environ.get("QB_CHROMIUM")
    if exe:
        return exe
    return sorted(glob.glob(str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux*/chrome")))[-1]


def accept_consent(page):
    for frame in [page.main_frame] + page.frames:
        for label in CONSENT:
            try:
                btn = frame.get_by_role("button", name=label, exact=True)
                if btn.count() and btn.first.is_visible():
                    btn.first.click(timeout=2000)
                    return label
            except Exception:  # noqa: BLE001
                pass
    return None


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    sites = sys.argv[2:] or SITES
    ext = str(ROOT / "extension")
    with sync_playwright() as p, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        ctx = p.chromium.launch_persistent_context(
            profile, executable_path=chromium(), headless=False, user_agent=UA, viewport={"width": 1366, "height": 900},
            args=["--headless=new", "--disable-extensions-except=" + ext, "--load-extension=" + ext,
                  "--autoplay-policy=no-user-gesture-required"])
        time.sleep(1)
        for pg in ctx.pages:
            if "welcome" in pg.url:
                pg.close()
        for i, url in enumerate(sites):
            page = ctx.new_page()
            name = "%02d-%s" % (i + 1, url.split("/")[2].replace("www.", ""))
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)
                clicked = accept_consent(page)
                page.wait_for_timeout(2000)
                for _ in range(12):
                    page.mouse.wheel(0, 700)
                    page.wait_for_timeout(700)
                page.wait_for_timeout(2500)
                info = page.evaluate("""() => {
                  const hosts = [...document.querySelectorAll('quokka-blocker')];
                  return hosts.map(h => { const r = h.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), Math.round(r.top + scrollY)]; });
                }""")
                slots = page.evaluate("() => document.querySelectorAll('[data-quokka-blocked]').length")
                print("%s: %d cards (%d slots), consent=%s, sizes=%s" % (name, len(info), slots, clicked, [tuple(x[:2]) for x in info][:12]))
                shown = 0
                for w, h, top in info:
                    if w < 60 or h < 30 or shown >= 2:
                        continue
                    page.evaluate("y => window.scrollTo(0, Math.max(0, y - 200))", top)
                    page.wait_for_timeout(1500)
                    page.screenshot(path=str(out / ("%s-%d.png" % (name, shown + 1))))
                    shown += 1
                if not info:
                    page.evaluate("() => window.scrollTo(0, 0)")
                    page.screenshot(path=str(out / ("%s-none.png" % name)))
            except Exception as e:  # noqa: BLE001
                print("%s: error %s" % (name, str(e).splitlines()[0][:160]))
            page.close()
        ctx.close()


if __name__ == "__main__":
    main()
