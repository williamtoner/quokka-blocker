#!/usr/bin/env python3
"""Debugging aid: load one site with the extension and report, as JSON, what
it did there: every card and what it covers, slots marked but never filled,
and ad-sized frames it did not touch.

    python3 test/inspect_site.py URL
"""
import json
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

REPORT = r"""() => {
  const desc = el => el ? (el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
      (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.') : '')) : null;
  const size = el => { const r = el.getBoundingClientRect(); return Math.round(r.width) + 'x' + Math.round(r.height); };
  const hiddenUp = el => { for (let e = el.parentElement; e; e = e.parentElement) if (getComputedStyle(e).display === 'none') return desc(e); return null; };
  const cards = [...document.querySelectorAll('quokka-blocker')].map(h => ({
    size: size(h), target: desc(h.nextElementSibling), parent: desc(h.parentElement),
    hiddenAncestor: hiddenUp(h), slot: desc(h.closest('[data-quokka-blocked]')) }));
  const empty = [...document.querySelectorAll('[data-quokka-blocked]')].filter(s =>
    !s.querySelector('quokka-blocker') && !(s.previousElementSibling && s.previousElementSibling.matches('quokka-blocker')))
    .map(s => ({ slot: desc(s), size: size(s), display: getComputedStyle(s).display, parent: desc(s.parentElement) }));
  const missed = [...document.querySelectorAll('iframe')].filter(f => {
    const r = f.getBoundingClientRect(); return r.width >= 120 && r.height >= 50 && !f.closest('[data-quokka-blocked]');
  }).map(f => ({ frame: desc(f), size: size(f), src: (f.src || '').slice(0, 90), up: [desc(f.parentElement), desc(f.parentElement && f.parentElement.parentElement)] }));
  return { cards, empty, missed };
}"""


def main():
    url = sys.argv[1]
    ext = str(ROOT / "extension")
    with sync_playwright() as p, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        ctx = p.chromium.launch_persistent_context(
            profile, executable_path=live.chromium(), headless=False, user_agent=live.UA, viewport={"width": 1366, "height": 900},
            args=["--headless=new", "--disable-extensions-except=" + ext, "--load-extension=" + ext])
        time.sleep(1)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
        live.accept_consent(page)
        page.wait_for_timeout(2000)
        for _ in range(10):
            page.mouse.wheel(0, 700)
            page.wait_for_timeout(600)
        page.wait_for_timeout(2500)
        print(json.dumps(page.evaluate(REPORT), indent=1, ensure_ascii=False))
        ctx.close()


if __name__ == "__main__":
    main()
