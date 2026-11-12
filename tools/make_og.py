#!/usr/bin/env python3
"""Draw site/og.jpg, the picture shown when the site is shared (needs Python Playwright)."""
import glob
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
PICS = ["quokka-1278d", "red-panda-52bb5", "long-tailed-tit-e19bb", "sea-otter-3986e"]
MARK = (EXT / "icons/mark.svg").read_text()

HTML = """<html><head><style>
@font-face{font-family:F;src:url('%(ext)s/fonts/fraunces.woff2')}
@font-face{font-family:I;src:url('%(ext)s/fonts/inter.woff2')}
body{margin:0;width:1200px;height:630px;background:#fbf8f3;font-family:I;overflow:hidden;position:relative}
.t{position:absolute;left:72px;top:150px;width:520px}
.b{display:flex;align-items:center;gap:12px;font:560 30px F;color:#221c17;--qb-cut:#fbf8f3}
.b svg{width:44px;height:44px;color:#2f5d50}
h1{margin:34px 0 0;font:460 84px/0.98 F;letter-spacing:-.035em;color:#221c17}
h1 span{color:#2f5d50}
p{margin:26px 0 0;font:400 24px/1.4 I;color:#6e635a}
.g{position:absolute;right:56px;top:56px;width:500px;height:518px;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1.15fr 1fr;gap:14px}
.g div{border-radius:22px;background-size:cover;box-shadow:0 18px 40px rgba(40,25,10,.18)}
</style></head><body>
<div class="t"><div class="b">%(mark)s Quokka Blocker</div>
<h1>Every ad,<br><span>now an animal.</span></h1>
<p>A free browser extension that swaps adverts for photographs of quokkas, otters, red pandas and friends.</p></div>
<div class="g">%(tiles)s</div></body></html>"""


def main():
    import json
    import re
    lib = json.loads(re.search(r"=\s*(\{.*\});", (EXT / "src/library.js").read_text(), re.S).group(1))
    by = {i["id"]: i for i in lib["items"]}
    tiles = ""
    for pid in PICS:
        it = by[pid]
        pos = "%d%% %d%%" % ((it["s"][0] + it["s"][2]) * 50, (it["s"][1] + it["s"][3]) * 50)
        tiles += "<div style=\"background-image:url('%s/%s');background-position:%s\"></div>" % (EXT, it["f"], pos)
    html = HTML % {"ext": EXT, "mark": MARK.replace("<svg ", "<svg "), "tiles": tiles}
    page_file = ROOT / "dist/og.html"
    page_file.parent.mkdir(exist_ok=True)
    page_file.write_text(html)
    exe = sorted(glob.glob(str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux*/chrome")))[-1]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe)
        pg = b.new_page(viewport={"width": 1200, "height": 630})
        pg.goto("file://" + str(page_file))
        pg.wait_for_timeout(800)
        pg.screenshot(path=str(ROOT / "site/og.jpg"), type="jpeg", quality=88)
        b.close()


if __name__ == "__main__":
    main()
