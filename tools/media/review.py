#!/usr/bin/env python3
"""Contact sheets of the built library, each picture cropped as the extension
would crop it for a few common slot shapes, so the crops can be checked by eye.

    python3 tools/media/review.py OUT_DIR [--animal ID ...]

Each row: the whole picture with its subject box, then 300x250, a 728x90
banner tile (182x90), a 160x600 tower tile (160x198) and 300x600, or a dash
where the picture is not allowed for that shape.
"""
import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "extension"
SLACK = 0.06
SHAPES = [(300, 250), (182, 90), (160, 198), (150, 300)]
ROW_H = 250
PER_SHEET = 8


def crop(item, aspect):
    s = item["s"]
    ratio = item["w"] / item["h"]
    if aspect >= ratio:
        vh = ratio / aspect
        sh = s[3] - s[1]
        cut = max(0, (sh - vh) / sh)
        cy = (s[1] + s[3]) / 2
        top = min(max(cy - vh / 2, 0), 1 - vh)
        if sh > vh:
            top = min(max(s[1] - vh * 0.02, 0), 1 - vh)
        return cut, (0, top, 1, top + vh)
    vw = aspect / ratio
    sw = s[2] - s[0]
    cut = max(0, (sw - vw) / sw)
    cx = (s[0] + s[2]) / 2
    left = min(max(cx - vw / 2, 0), 1 - vw)
    return cut, (left, 0, left + vw, 1)


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--animal", nargs="*")
    args = ap.parse_args()
    lib = json.loads(re.search(r"=\s*(\{.*\});", (EXT / "src/library.js").read_text(), re.S).group(1))
    items = [i for i in lib["items"] if not args.animal or i["a"] in args.animal]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    f = font(13)
    width = 340 + sum(w * ROW_H // max(h, 1) if h > ROW_H else w for w, h in SHAPES) + 20 * len(SHAPES) + 20
    for s0 in range(0, len(items), PER_SHEET):
        page = items[s0:s0 + PER_SHEET]
        sheet = Image.new("RGB", (width, len(page) * (ROW_H + 30)), "white")
        d = ImageDraw.Draw(sheet)
        for r, it in enumerate(page):
            y = r * (ROW_H + 30)
            src = Image.open(EXT / (it["pf"] if it["k"] == "v" else it["f"])).convert("RGB")
            th = src.copy()
            th.thumbnail((320, ROW_H))
            sheet.paste(th, (0, y))
            s = it["s"]
            d.rectangle([s[0] * th.width, y + s[1] * th.height, s[2] * th.width, y + s[3] * th.height], outline=(255, 0, 255), width=2)
            d.text((0, y + ROW_H + 4), "%s  q%s  %s%s" % (it["id"], it["q"], it["by"][:30], "  FILM" if it["k"] == "v" else ""), fill="black", font=f)
            x = 340
            for w, h in SHAPES:
                scale = min(1, ROW_H / h)
                cw, ch = int(w * scale), int(h * scale)
                cut, (a, b, c, e) = crop(it, w / h)
                if cut <= 0.3:
                    W, H = src.size
                    piece = src.crop((int(a * W), int(b * H), int(c * W), int(e * H))).resize((cw, ch), Image.LANCZOS)
                    sheet.paste(piece, (x, y))
                    if cut > SLACK:
                        d.text((x + 3, y + 3), "fallback %.0f%%" % (cut * 100), fill="red", font=f)
                else:
                    d.line([x, y + ch // 2, x + cw, y + ch // 2], fill=(200, 200, 200), width=2)
                x += cw + 20
        sheet.save(out / ("review-%02d.jpg" % (s0 // PER_SHEET + 1)), quality=82)
    print("%d pictures on %d sheets in %s" % (len(items), (len(items) + PER_SHEET - 1) // PER_SHEET, out))


if __name__ == "__main__":
    main()
