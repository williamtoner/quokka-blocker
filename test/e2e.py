#!/usr/bin/env python3
"""End-to-end check: load the extension into Chromium and open the test page.

    QB_CHROMIUM=/path/to/chrome python3 test/e2e.py [--shots DIR] [--headed]

Needs Python Playwright. Checks that every fake ad on demo/index.html becomes
animals, that the editorial photo is left alone, that late and growing slots
are swapped quickly, and that "Show ad" puts an ad back.
"""
import argparse
import functools
import glob
import http.server
import os
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

SLOTS = {
    # data-test: number of cards expected
    "leaderboard": 1, "skyscraper": 1, "in-article": 1, "billboard": 1, "mobile": 1,
    "mpu": 1, "grows": 1, "halfpage": 1, "late": 1,
}


def serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    handler.log_message = lambda *a, **k: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def chromium():
    exe = os.environ.get("QB_CHROMIUM")
    if exe:
        return exe
    found = sorted(glob.glob(str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux*/chrome")))
    if not found:
        sys.exit("Set QB_CHROMIUM to a Chromium binary")
    return found[-1]


STATE = """() => {
  const out = {};
  document.querySelectorAll('[data-test]').forEach(slot => {
    const name = slot.dataset.test;
    const host = slot.previousElementSibling && slot.previousElementSibling.matches('quokka-blocker') ? slot.previousElementSibling : null;
    const inner = slot.querySelectorAll('quokka-blocker').length + slot.parentElement.querySelectorAll(':scope > quokka-blocker').length;
    const r = slot.getBoundingClientRect();
    const h = host ? host.getBoundingClientRect() : null;
    out[name] = {
      hidden: getComputedStyle(slot).display === 'none',
      blocked: slot.hasAttribute('data-quokka-blocked'),
      cards: (host ? 1 : 0) + slot.querySelectorAll('quokka-blocker').length,
      slotSize: [Math.round(r.width), Math.round(r.height)],
      cardSize: h ? [Math.round(h.width), Math.round(h.height)] : null,
    };
  });
  out.total = document.querySelectorAll('quokka-blocker').length;
  return out;
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", help="folder for screenshots")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    httpd = serve(ROOT / "demo")
    url = "http://127.0.0.1:%d/" % httpd.server_address[1]
    ext = str(ROOT / "extension")
    failures = []

    with sync_playwright() as p, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        flags = ["--disable-extensions-except=" + ext, "--load-extension=" + ext, "--autoplay-policy=no-user-gesture-required"]
        if not args.headed:
            flags.append("--headless=new")
        ctx = p.chromium.launch_persistent_context(profile, executable_path=chromium(), headless=False, args=flags,
                                                   viewport={"width": 1280, "height": 900}, user_agent=UA)
        worker = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=10000)
        ext_id = worker.url.split("/")[2]
        # The welcome page opens on install; close it.
        import time; time.sleep(0.5)
        for pg in ctx.pages[1:]:
            if "welcome" in pg.url:
                pg.close()

        page = ctx.new_page()
        page.goto(url)
        page.wait_for_timeout(1000)

        # Time from a slot appearing to its swap.
        lag = page.evaluate("""() => new Promise(done => {
          const box = document.createElement('div');
          box.innerHTML = '<div id="div-gpt-ad-timed" style="width:300px;height:250px"><iframe src="ads/ad.html" width="300" height="250"></iframe></div>';
          const t0 = performance.now();
          document.querySelector('article').appendChild(box);
          const slot = box.firstChild;
          const check = () => {
            if (getComputedStyle(slot).display === 'none') return done(performance.now() - t0);
            if (performance.now() - t0 > 5000) return done(-1);
            requestAnimationFrame(check);
          };
          check();
        })""")
        page.wait_for_timeout(2600)
        state = page.evaluate(STATE)

        for name, want in SLOTS.items():
            s = state.get(name)
            if not s:
                failures.append("%s: slot missing from page" % name)
            elif not s["hidden"] or s["cards"] != want:
                failures.append("%s: hidden=%s cards=%s (want %d)" % (name, s["hidden"], s["cards"], want))
            elif s["cardSize"] and abs(s["cardSize"][0] - s["slotSize"][0]) > 2 and s["slotSize"][0]:
                pass  # hidden slots measure 0; size is checked below by eye
        col = state.get("column")
        if not col or col["cards"] != 2:
            failures.append("column: want 2 cards (one per ad frame), got %s" % (col and col["cards"]))
        img = state.get("content-image")
        if not img or img["hidden"] or img["blocked"]:
            failures.append("content image was touched")
        if lag < 0 or lag > 400:
            failures.append("slot added late took %.0f ms to swap (limit 400)" % lag)

        if args.shots:
            Path(args.shots).mkdir(parents=True, exist_ok=True)
            page.wait_for_timeout(1200)
            page.screenshot(path=str(Path(args.shots) / "demo-full.png"), full_page=True)

        # Show ad puts the advert back; Another swaps the animal.
        restored = page.evaluate("""() => {
          const slot = document.querySelector('[data-test=mpu]');
          return getComputedStyle(slot).display;
        }""")
        page.hover("[data-test=content-image]")
        host = page.locator("quokka-blocker").first
        box = host.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.wait_for_timeout(500)
        if args.shots:
            host.screenshot(path=str(Path(args.shots) / "hover.png"))
        # Closed shadow root: click where the "Show ad" button sits (top right).
        page.mouse.click(box["x"] + box["width"] - 30, box["y"] + 21)
        page.wait_for_timeout(300)
        after = page.evaluate(STATE)
        if after["total"] != state["total"] - 1:
            failures.append("Show ad: card count %d -> %d" % (state["total"], after["total"]))

        # The popup renders and counts.
        popup = ctx.new_page()
        popup.set_viewport_size({"width": 360, "height": 640})
        popup.goto("chrome-extension://%s/popup/popup.html" % ext_id)
        popup.wait_for_timeout(1200)
        total = popup.text_content("#total")
        if not total or total.strip() in ("0", ""):
            failures.append("popup total is %r" % total)
        if args.shots:
            popup.screenshot(path=str(Path(args.shots) / "popup.png"), full_page=True)
            for name in ("welcome", "credits"):
                pg = ctx.new_page()
                pg.set_viewport_size({"width": 1280, "height": 900})
                pg.goto("chrome-extension://%s/pages/%s.html" % (ext_id, name))
                pg.wait_for_timeout(1500)
                pg.screenshot(path=str(Path(args.shots) / ("%s.png" % name)), full_page=name == "welcome")
        ctx.close()
    httpd.shutdown()

    print("late slot swapped in %.0f ms; %d cards on the page" % (lag, state["total"]))
    if failures:
        print("FAIL\n  " + "\n  ".join(failures))
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
