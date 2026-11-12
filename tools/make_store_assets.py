#!/usr/bin/env python3
"""Draw the Chrome Web Store images into listing/chrome/ (needs Python Playwright).

    python3 tools/make_store_assets.py [chromium-binary]

Screenshots (1280x800) show the real extension on the project's own test page,
so no third-party site or brand appears in them:
  1-page.png      the mock newspaper with every ad turned into animals
  2-before-after  the same page with ads, and with animals
  3-hover.png     a card up close, hovered: name, place, credit, buttons
  4-popup.png     the toolbar popup over the page
  5-welcome.png   the welcome page
Promotional tiles: promo-440x280.png and marquee-1400x560.png.
"""
import functools
import glob
import http.server
import json
import re
import sys
import tempfile
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
OUT = ROOT / "listing/chrome"
W, H = 1280, 800


def serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    handler.log_message = lambda *a, **k: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def label_html(text, sub=""):
    return """<html><head><style>
@font-face{font-family:F;src:url('%s/fonts/fraunces.woff2')}
@font-face{font-family:I;src:url('%s/fonts/inter.woff2')}
body{margin:0;background:transparent}
div{display:inline-block;padding:14px 22px 15px;border-radius:16px;background:rgba(251,248,243,.94);box-shadow:0 10px 30px rgba(40,25,10,.18)}
b{display:block;font:500 34px/1.05 F;letter-spacing:-.02em;color:#221c17}
span{display:block;margin-top:6px;font:400 17px/1.3 I;color:#6e635a}
</style></head><body><div><b>%s</b>%s</div></body></html>""" % (EXT, EXT, text, "<span>%s</span>" % sub if sub else "")


def main():
    exe = (sys.argv[1:] or sorted(glob.glob(str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux*/chrome"))))[-1]
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    httpd = serve(ROOT / "demo")
    url = "http://127.0.0.1:%d/?clean" % httpd.server_address[1]
    ext = str(EXT)

    with sync_playwright() as p:
        # The page with ads (no extension).
        plain = p.chromium.launch(executable_path=exe, args=["--hide-scrollbars"])
        pg = plain.new_page(viewport={"width": W, "height": H})
        pg.goto(url)
        pg.wait_for_timeout(3000)
        pg.screenshot(path=str(tmp / "ads.png"))

        def label(text, sub=""):
            lp = plain.new_page(viewport={"width": 900, "height": 200})
            f = tmp / ("label-%d.html" % (abs(hash(text)) % 10 ** 8))
            f.write_text(label_html(text, sub))
            lp.goto("file://" + str(f))
            lp.wait_for_timeout(400)
            box = lp.locator("div").bounding_box()
            path = tmp / ("label-%d.png" % (abs(hash(text)) % 10 ** 8))
            lp.screenshot(path=str(path), clip=box, omit_background=True)
            lp.close()
            return Image.open(path).convert("RGBA")

        # The same page with the extension.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
            ctx = p.chromium.launch_persistent_context(
                profile, executable_path=exe, headless=False, viewport={"width": W, "height": H},
                args=["--headless=new", "--hide-scrollbars", "--disable-extensions-except=" + ext, "--load-extension=" + ext])
            worker = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
            ext_id = worker.url.split("/")[2]
            time.sleep(1)
            for other in ctx.pages:
                if "welcome" in other.url:
                    other.set_viewport_size({"width": W, "height": H})
                    other.wait_for_timeout(2500)
                    other.screenshot(path=str(OUT / "5-welcome.png"))
                    other.close()
            page = ctx.new_page()
            page.goto(url)
            page.wait_for_timeout(4500)
            page.screenshot(path=str(tmp / "animals.png"))

            # Popup and the welcome page.
            pp = ctx.new_page()
            pp.set_viewport_size({"width": 360, "height": 760})
            pp.goto("chrome-extension://%s/popup/popup.html" % ext_id)
            pp.wait_for_timeout(1800)
            pp.screenshot(path=str(tmp / "popup.png"))
            wp = ctx.new_page()
            wp.set_viewport_size({"width": W, "height": H})
            wp.goto("chrome-extension://%s/pages/welcome.html" % ext_id)
            wp.wait_for_timeout(2500)
            wp.screenshot(path=str(OUT / "5-welcome.png"))
            ctx.close()

        # Hover close-up: the page at twice the pixel density, cropped to the
        # 300x250 card and its surroundings, so it fills 1280x800 crisply.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
            ctx = p.chromium.launch_persistent_context(
                profile, executable_path=exe, headless=False, viewport={"width": 1700, "height": 900}, device_scale_factor=2,
                args=["--headless=new", "--hide-scrollbars", "--disable-extensions-except=" + ext, "--load-extension=" + ext])
            worker = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
            worker.evaluate("chrome.storage.local.set({quokkas: 'only'})")  # the close-up shows the namesake
            time.sleep(1)
            hp = ctx.new_page()
            hp.goto(url)
            hp.wait_for_timeout(4500)
            box = hp.evaluate("""() => { const h = document.querySelector('[data-test=mpu]').previousElementSibling;
              h.scrollIntoView({block: 'center'}); const r = h.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }""")
            hp.wait_for_timeout(600)
            hp.mouse.move(box[0] + box[2] * 0.4, box[1] + box[3] * 0.6)
            hp.wait_for_timeout(1200)
            cx, cy = box[0] + box[2] / 2, box[1] + box[3] / 2
            clip = {"x": cx - 320, "y": cy - 200, "width": 640, "height": 400}
            hp.screenshot(path=str(tmp / "hover.png"), clip=clip)
            ctx.close()

        # Promo tiles, drawn in the browser so the brand type is right.
        lib = json.loads(re.search(r"=\s*(\{.*\});", (EXT / "src/library.js").read_text(), re.S).group(1))
        by = {i["id"]: i for i in lib["items"]}
        mark = (EXT / "icons/mark.svg").read_text()

        def tile(pid):
            it = by[pid]
            pos = "%d%% %d%%" % ((it["s"][0] + it["s"][2]) * 50, (it["s"][1] + it["s"][3]) * 50)
            return "<div style=\"background-image:url('%s/%s');background-position:%s\"></div>" % (EXT, it["f"], pos)

        promo_css = """@font-face{font-family:F;src:url('%s/fonts/fraunces.woff2')}
@font-face{font-family:I;src:url('%s/fonts/inter.woff2')}
body{margin:0;background:#fbf8f3;overflow:hidden;position:relative;font-family:I}
.g div{border-radius:14px;background-size:cover;box-shadow:0 10px 24px rgba(40,25,10,.16)}
.b{display:flex;align-items:center;color:#221c17;font-family:F;font-weight:560;--qb-cut:#fbf8f3}
.b svg{color:#2f5d50}
h1{margin:0;font:460 1em/0.98 F;letter-spacing:-.035em;color:#221c17}h1 span{color:#2f5d50}""" % (EXT, EXT)
        small = """<html><head><style>%s
body{width:440px;height:280px}
.t{position:absolute;left:26px;top:34px;width:200px}
.b{gap:8px;font-size:17px}.b svg{width:26px;height:26px}
h1{margin-top:22px;font-size:38px}
.g{position:absolute;right:20px;top:20px;width:184px;height:240px;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1.2fr 1fr;gap:8px}
.g div{border-radius:12px}
</style></head><body><div class="t"><div class="b">%s Quokka Blocker</div><h1>Every ad,<br><span>now an animal.</span></h1></div>
<div class="g">%s</div></body></html>""" % (promo_css, mark, "".join(tile(x) for x in ["quokka-1278d", "red-panda-52bb5", "long-tailed-tit-e19bb", "sea-otter-3986e"]))
        marquee = """<html><head><style>%s
body{width:1400px;height:560px}
.t{position:absolute;left:84px;top:118px;width:560px}
.b{gap:12px;font-size:30px}.b svg{width:46px;height:46px}
h1{margin-top:34px;font-size:92px}
p{margin:24px 0 0;font:400 24px/1.4 I;color:#6e635a}
.g{position:absolute;right:56px;top:44px;width:640px;height:472px;display:grid;grid-template-columns:1.15fr 1fr 1fr;grid-template-rows:1fr 1fr;gap:14px}
.g div:first-child{grid-row:span 2}
.g div{border-radius:20px}
</style></head><body><div class="t"><div class="b">%s Quokka Blocker</div><h1>Every ad,<br><span>now an animal.</span></h1>
<p>Photographs and short films of quokkas, otters, red pandas and friends, in place of the web's adverts.</p></div>
<div class="g">%s</div></body></html>""" % (promo_css, mark, "".join(tile(x) for x in ["quokka-1278d", "red-panda-52bb5", "snow-monkey-a4f10", "long-tailed-tit-e19bb", "sea-otter-3986e"]))
        for name, html, size in (("promo-440x280.png", small, (440, 280)), ("marquee-1400x560.png", marquee, (1400, 560))):
            f = tmp / (name + ".html")
            f.write_text(html)
            pp = plain.new_page(viewport={"width": size[0], "height": size[1]})
            pp.goto("file://" + str(f))
            pp.wait_for_timeout(800)
            pp.screenshot(path=str(OUT / name))
            pp.close()

        labels = {
            "page": label("Every ad, now an animal", "Quokka Blocker fills each advert space with a photograph or short film, sized to fit."),
            "ads": label("Before"),
            "animals": label("After"),
            "hover": label("Hover for more", "Who it is, where it was taken, who took it. Ask for another, or put the ad back."),
            "popup": label("Your animals, your way", "Pause it on a site, switch films off, choose your animals, or go all quokka."),
        }

        def put(img, lab, xy):
            img.alpha_composite(lab, xy)

        # 1: the page.
        im = Image.open(tmp / "animals.png").convert("RGBA")
        put(im, labels["page"], (W - labels["page"].width - 28, H - labels["page"].height - 28))
        im.convert("RGB").save(OUT / "1-page.png")

        # 2: before and after, split down the middle.
        a = Image.open(tmp / "ads.png").convert("RGBA")
        b = Image.open(tmp / "animals.png").convert("RGBA")
        im = Image.new("RGBA", (W, H))
        im.paste(a.crop((0, 0, W // 2, H)), (0, 0))
        im.paste(b.crop((W // 2, 0, W, H)), (W // 2, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([W // 2 - 2, 0, W // 2 + 1, H], fill=(251, 248, 243, 255))
        put(im, labels["ads"], (W // 2 - labels["ads"].width - 24, H - labels["ads"].height - 28))
        put(im, labels["animals"], (W // 2 + 24, H - labels["animals"].height - 28))
        im.convert("RGB").save(OUT / "2-before-after.png")

        # 3: hover close-up.
        im = Image.open(tmp / "hover.png").convert("RGBA").resize((W, H))
        put(im, labels["hover"], (28, H - labels["hover"].height - 28))
        im.convert("RGB").save(OUT / "3-hover.png")

        # 4: popup over a softened page, where a toolbar popup would open.
        bg = Image.open(tmp / "animals.png").convert("RGBA").filter(ImageFilter.GaussianBlur(3))
        bg.alpha_composite(Image.new("RGBA", (W, H), (20, 14, 10, 70)))
        pop = Image.open(tmp / "popup.png").convert("RGBA")
        pop = pop.crop((0, 0, pop.width, min(pop.height, 740)))
        mask = Image.new("L", pop.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, pop.width - 1, pop.height - 1], 12, fill=255)
        shadow = Image.new("RGBA", (pop.width + 60, pop.height + 60), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle([30, 34, pop.width + 30, pop.height + 34], 14, fill=(0, 0, 0, 110))
        shadow = shadow.filter(ImageFilter.GaussianBlur(14))
        px, py = W - pop.width - 70, 30
        bg.alpha_composite(shadow, (px - 30, py - 30))
        bg.paste(pop, (px, py), mask)
        put(bg, labels["popup"], (40, H - labels["popup"].height - 40))
        bg.convert("RGB").save(OUT / "4-popup.png")
        plain.close()
    httpd.shutdown()
    for f in sorted(OUT.glob("*.png")):
        print(f.name, Image.open(f).size)


if __name__ == "__main__":
    main()
