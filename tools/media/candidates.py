#!/usr/bin/env python3
"""Gather candidate animal photos and videos for curation.

Searches Wikimedia Commons (and, for photos, Flickr's Creative Commons pool
through Openverse), keeps only files whose licence lets us ship them in a free
extension (CC0, public domain, CC BY, CC BY-SA), downloads small previews and
lays them out on numbered contact sheets so a person can pick the best.

    candidates.py photos "quokka" --out DIR [--limit 40] [--flickr]
    candidates.py videos "otter" --out DIR [--limit 20]
    candidates.py frames URL --out DIR [--every 2] [--max 12]   # stills from a video
    candidates.py box PREVIEW.jpg x0 y0 x1 y1   # draw a subject box to check it

Each run writes DIR/meta.json (one record per numbered candidate, with the
licence and author already worked out) and DIR/sheet-*.jpg.
Search terms use Commons search syntax, e.g. 'quokka incategory:Quality_images'.
"""
import argparse
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

UA = "QuokkaBlocker-curation/0.1 (https://github.com/williamtoner)"
API = "https://commons.wikimedia.org/w/api.php"
OPENVERSE = "https://api.openverse.org/v1/images/"
PREVIEW = 640

OK_LICENCE = re.compile(r"^(cc0|cc[- ]zero|public domain|pd\b|pdm|cc[- ]by(?:[- ]sa)?(?:[- ]\d\.\d)?(?:[- ][a-z]{2,3})?)", re.I)


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def get(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(2 + 3 * attempt)


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def licence_ok(name):
    name = (name or "").strip()
    if re.search(r"\bnc\b|\bnd\b|non-?commercial|noderivs|gfdl only", name, re.I):
        return False
    return bool(OK_LICENCE.match(name))


def commons(query, limit, kind, offset=0):
    ftype = "bitmap" if kind == "photos" else "video"
    extra = " filew:>1500" if kind == "photos" else ""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": "%s filetype:%s%s" % (query, ftype, extra), "gsrnamespace": 6,
        "gsrlimit": min(limit, 50), "gsroffset": offset, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata|mime|mediatype", "iiurlwidth": PREVIEW,
        "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|Credit|ImageDescription|Restrictions|AttributionRequired|DateTimeOriginal",
    }
    data = json.loads(get(API + "?" + urllib.parse.urlencode(params)))
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        val = lambda k: (meta.get(k) or {}).get("value", "")  # noqa: E731
        lic = strip_html(val("LicenseShortName"))
        if not licence_ok(lic):
            continue
        rec = {
            "source": "commons",
            "title": p["title"],
            "page": ii.get("descriptionurl"),
            "file_url": (ii.get("url") or "").split("?")[0],
            "preview_url": (ii.get("thumburl") or "").split("?")[0],
            "width": ii.get("width"), "height": ii.get("height"),
            "duration": ii.get("duration"),
            "mime": ii.get("mime"),
            "author": strip_html(val("Artist"))[:160],
            "credit": strip_html(val("Credit"))[:200],
            "license": lic,
            "license_url": strip_html(val("LicenseUrl")),
            "restrictions": strip_html(val("Restrictions")),
            "description": strip_html(val("ImageDescription"))[:400],
        }
        out.append(rec)
    return out


def flickr(query, limit):
    params = {"q": query, "license": "by,by-sa,cc0,pdm", "source": "flickr",
              "page_size": min(limit, 50), "mature": "false"}
    data = json.loads(get(OPENVERSE + "?" + urllib.parse.urlencode(params)))
    out = []
    for r in data.get("results", []):
        if (r.get("width") or 0) < 1000 and (r.get("height") or 0) < 1000 and r.get("width"):
            continue
        lic = ("CC " + r["license"].upper() + " " + (r.get("license_version") or "")).strip()
        if r["license"] in ("cc0",):
            lic = "CC0"
        if r["license"] == "pdm":
            lic = "Public domain"
        out.append({
            "source": "flickr",
            "title": r.get("title") or "",
            "page": r.get("foreign_landing_url"),
            "file_url": r.get("url"),
            "preview_url": r.get("url"),
            "width": r.get("width"), "height": r.get("height"),
            "author": r.get("creator") or "",
            "credit": r.get("creator_url") or "",
            "license": lic,
            "license_url": r.get("license_url"),
            "restrictions": "",
            "description": ", ".join(t["name"] for t in (r.get("tags") or [])[:12]),
        })
    return out


def font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def sheets(out_dir, items, cols=4, rows=3, cell=360):
    """Numbered contact sheets, 12 previews each."""
    f = font(30)
    per = cols * rows
    names = []
    for s in range(0, len(items), per):
        page = items[s:s + per]
        sheet = Image.new("RGB", (cols * cell, rows * cell), "white")
        d = ImageDraw.Draw(sheet)
        for i, rec in enumerate(page):
            path = out_dir / rec["preview"]
            if not path.exists():
                continue
            im = Image.open(path).convert("RGB")
            im.thumbnail((cell - 8, cell - 8))
            x = (i % cols) * cell + (cell - im.width) // 2
            y = (i // cols) * cell + (cell - im.height) // 2
            sheet.paste(im, (x, y))
            cx, cy = (i % cols) * cell + 6, (i // cols) * cell + 6
            label = str(rec["n"])
            d.rectangle([cx, cy, cx + 22 + 18 * len(label), cy + 40], fill="black")
            d.text((cx + 8, cy + 3), label, fill="yellow", font=f)
        name = "sheet-%d.jpg" % (s // per + 1)
        sheet.save(out_dir / name, quality=85)
        names.append(name)
    return names


def fetch_previews(out_dir, items):
    def one(rec):
        path = out_dir / rec["preview"]
        if path.exists():
            return
        try:
            raw = get(rec["preview_url"])
            path.write_bytes(raw)
            im = Image.open(path)
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((PREVIEW, PREVIEW))
            im.save(path, quality=88)
        except Exception as e:  # noqa: BLE001
            print("preview failed", rec["n"], rec["title"], e, file=sys.stderr)
            if path.exists():
                path.unlink()
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(one, items))


def cmd_search(args):
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "meta.json"
    items = json.loads(meta_path.read_text()) if meta_path.exists() else []
    seen = {r["page"] for r in items}
    found = commons(args.query, args.limit, args.kind, args.offset)
    if args.flickr and args.kind == "photos":
        found += flickr(args.flickr_query or args.query.split(" incategory")[0], args.limit)
    added = []
    for rec in found:
        if rec["page"] in seen or not rec.get("preview_url"):
            continue
        seen.add(rec["page"])
        rec["n"] = len(items) + 1
        rec["query"] = args.query
        rec["preview"] = "%03d.jpg" % rec["n"]
        items.append(rec)
        added.append(rec)
    fetch_previews(out_dir, added)
    meta_path.write_text(json.dumps(items, indent=1, ensure_ascii=False))
    names = sheets(out_dir, [r for r in items if (out_dir / r["preview"]).exists()])
    print("%d new, %d total in %s; sheets: %s" % (len(added), len(items), out_dir, " ".join(names)))
    for rec in added:
        dur = " %.0fs" % rec["duration"] if rec.get("duration") else ""
        print("%3d %s %sx%s%s %s | %s" % (rec["n"], rec["source"], rec["width"], rec["height"], dur, rec["license"], rec["title"][:70]))


def cmd_box(args):
    """Draw a subject box (fractions x0 y0 x1 y1) on a preview, to check it by eye."""
    im = Image.open(args.image).convert("RGB")
    x0, y0, x1, y1 = args.box
    d = ImageDraw.Draw(im)
    w, h = im.size
    for k in range(3):
        d.rectangle([x0 * w - k, y0 * h - k, x1 * w + k, y1 * h + k], outline=(255, 0, 255))
    out = Path(args.image).with_name(Path(args.image).stem + "-box.jpg")
    im.save(out, quality=88)
    print(out)


def cmd_frames(args):
    """Stills from a video, every N seconds, on one numbered sheet (numbers are seconds)."""
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "f-%03d.jpg"
    for old in out_dir.glob("f-*.jpg"):
        old.unlink()
    src = args.url
    if src.startswith("http"):
        local = out_dir / ("video" + Path(urllib.parse.urlparse(src).path).suffix)
        local.write_bytes(get(src))
        src = str(local)
    subprocess.run([ffmpeg(), "-v", "error", "-i", src, "-vf",
                    "fps=1/%g,scale=480:-2" % args.every, "-frames:v", str(args.max), str(pattern)], check=True)
    frames = sorted(out_dir.glob("f-*.jpg"))
    items = [{"n": int(round((i) * args.every)), "preview": f.name} for i, f in enumerate(frames)]
    names = sheets(out_dir, items, cols=4, rows=3, cell=360)
    for old, new in zip(names, names):
        (out_dir / old).rename(out_dir / ("frames-" + new))
    print("%d stills; sheets: %s (label = seconds from start)" % (len(frames), " ".join("frames-" + n for n in names)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for kind in ("photos", "videos"):
        p = sub.add_parser(kind)
        p.add_argument("query")
        p.add_argument("--out", required=True)
        p.add_argument("--limit", type=int, default=40)
        p.add_argument("--offset", type=int, default=0, help="skip this many Commons results (next page)")
        p.add_argument("--flickr", action="store_true", help="also search Flickr CC photos via Openverse")
        p.add_argument("--flickr-query", help="plain words for the Flickr search (defaults to the query)")
        p.set_defaults(kind=kind, fn=cmd_search)
    p = sub.add_parser("box")
    p.add_argument("image")
    p.add_argument("box", type=float, nargs=4)
    p.set_defaults(fn=cmd_box)
    p = sub.add_parser("frames")
    p.add_argument("url")
    p.add_argument("--out", required=True)
    p.add_argument("--every", type=float, default=2)
    p.add_argument("--max", type=int, default=12)
    p.set_defaults(fn=cmd_frames)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
