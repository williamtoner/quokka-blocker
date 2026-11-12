#!/usr/bin/env python3
"""The test page in Firefox, with the Firefox build installed as a temporary add-on.

    QB_FIREFOX=/path/to/firefox QB_GECKODRIVER=/path/to/geckodriver python3 test/e2e_firefox.py [--shot FILE]

Needs Selenium. Builds dist/quokka-blocker-firefox.zip first.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2e  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot")
    args = ap.parse_args()
    subprocess.run([sys.executable, str(ROOT / "tools/build.py")], check=True, stdout=subprocess.DEVNULL)
    httpd = e2e.serve(ROOT / "demo")
    url = "http://127.0.0.1:%d/" % httpd.server_address[1]

    opts = Options()
    opts.binary_location = os.environ["QB_FIREFOX"]
    opts.add_argument("-headless")
    opts.set_preference("media.autoplay.default", 0)
    driver = webdriver.Firefox(options=opts, service=Service(os.environ["QB_GECKODRIVER"]))
    failures = []
    try:
        driver.set_window_size(1280, 1000)
        driver.install_addon(str(ROOT / "dist/quokka-blocker-firefox.zip"), temporary=True)
        time.sleep(1)
        for handle in driver.window_handles[1:]:  # the welcome page
            driver.switch_to.window(handle)
            driver.close()
        driver.switch_to.window(driver.window_handles[0])
        driver.get(url)
        time.sleep(5)
        state = driver.execute_script("return (" + e2e.STATE + ")()")
        for name, want in e2e.SLOTS.items():
            s = state.get(name)
            if not s or not s["hidden"] or s["cards"] != want:
                failures.append("%s: %s" % (name, s))
        if state.get("content-image", {}).get("hidden"):
            failures.append("content image was touched")
        if args.shot:
            time.sleep(1.5)
            driver.save_screenshot(args.shot)
        print("%d cards on the page" % state["total"])
    finally:
        driver.quit()
        httpd.shutdown()
    if failures:
        print("FAIL\n  " + "\n  ".join(failures))
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
