#!/usr/bin/env python3
"""Turn the curated picks into the files the extension ships.

Reads tools/media/picks/*.json (see CURATION.md), fetches each pick once
(cached in tools/media/cache/), and writes:

  extension/media/photos/<id>.avif    long edge 1280 px
  extension/media/films/<id>.webm     VP9, 960 px wide, silent, seamless loop
  extension/media/films/<id>.webp     its first frame, shown while it loads
  extension/src/library.js            what the extension knows about each one

    python3 tools/media/build_media.py [--only ID ...] [--force]

Picks can be dropped from the build without deleting them by listing their
"page" in tools/media/rejects.txt (one per line, # for comments).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidates  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PICKS = ROOT / "tools/media/picks"
CACHE = ROOT / "tools/media/cache"
OVERRIDES = ROOT / "tools/media/overrides.json"
REJECTS = ROOT / "tools/media/rejects.txt"
EXT = ROOT / "extension"
PHOTO_EDGE = 1280
PHOTO_Q = 52  # AVIF
FILM_W = 960
FILM_CRF = 37
FADE = 0.8  # s of crossfade that hides the loop point

# Animal id -> the name shown in the popup's animal list. Cards use each
# picture's own, more specific name ("Ezo squirrel", "Harp seal pup").
GROUP_NAMES = {
    "dormouse": "Dormouse", "flying-squirrel": "Flying squirrel", "otter": "Otter", "owl": "Owl",
    "penguin": "Penguin", "pika": "Pika", "puffin": "Puffin", "red-squirrel": "Red squirrel",
    "seal-pup": "Seal pup", "tanuki": "Tanuki", "shiba-inu": "Shiba inu", "pallas-cat": "Pallas's cat",
    "duckling": "Duckling", "rabbit": "Rabbit", "snow-monkey": "Snow monkey", "wallaby": "Wallaby",
}
NAMES = dict(GROUP_NAMES)  # animal id -> display name; the rest come from the picks


def ff():
    return candidates.ffmpeg()


def commons_thumb(titles, width):
    """Ask Commons for a resized copy of each file, so we never pull 50 MB originals."""
    out = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        params = {"action": "query", "format": "json", "titles": "|".join(chunk), "prop": "imageinfo",
                  "iiprop": "url|size", "iiurlwidth": width}
        data = json.loads(candidates.get(candidates.API + "?" + urllib.parse.urlencode(params)))
        norm = {n["to"]: n["from"] for n in data.get("query", {}).get("normalized", [])}
        for p in data.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            title = norm.get(p["title"], p["title"])
            out[title] = (ii.get("thumburl") or ii.get("url") or "").split("?")[0]
    return out


def thumb_url(file_url, width):
    """Commons serves resized copies at a path derived from the original's:
    .../commons/a/ab/Name.jpg -> .../commons/thumb/a/ab/Name.jpg/1920px-Name.jpg"""
    head, name = file_url.rsplit("/", 1)
    return "%s/%dpx-%s" % (head.replace("/wikipedia/commons/", "/wikipedia/commons/thumb/", 1) + "/" + name, width, name)


def fetch_photo(p):
    """A copy no bigger than needed: a 1920 px Commons thumbnail when the original is
    larger than that, else the original itself (Flickr files are 1024 px already)."""
    url = p["file_url"]
    if p["source"] == "commons" and "/wikipedia/commons/" in url and max(p.get("width") or 0, p.get("height") or 0) > 2000:
        try:
            return cached(thumb_url(url, 1920), ".img")
        except Exception:  # noqa: BLE001  some files have no thumbnail at that size
            pass
    return cached(url, ".img")


def cached(url, suffix):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (hashlib.sha1(url.encode()).hexdigest()[:16] + suffix)
    if not path.exists() or path.stat().st_size == 0:
        path.write_bytes(candidates.get(url))
    return path


def title_of(page):
    return urllib.parse.unquote(page.rsplit("/wiki/", 1)[-1]).replace("_", " ")


def hexcolour(rgb):
    return "#%02x%02x%02x" % tuple(int(v) for v in rgb[:3])


def subject_colour(im, s):
    """The average colour around the subject: what shows while the picture loads."""
    w, h = im.size
    box = (int(s[0] * w), int(s[1] * h), max(int(s[2] * w), int(s[0] * w) + 1), max(int(s[3] * h), int(s[1] * h) + 1))
    small = im.crop(box).resize((8, 8))
    mean = ImageStat.Stat(small).mean
    return hexcolour([v * 0.8 for v in mean])  # a touch darker, so the fade-in reads as light arriving


def build_photo(pick, src, force):
    out = EXT / "media/photos" / (pick["id"] + ".avif")
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    if force or not out.exists():
        im2 = im.copy()
        im2.thumbnail((PHOTO_EDGE, PHOTO_EDGE), Image.LANCZOS)
        im2.save(out, "AVIF", quality=PHOTO_Q, speed=4)
    done = Image.open(out)
    return {"f": "media/photos/%s.avif" % pick["id"], "w": done.width, "h": done.height,
            "c": subject_colour(im, pick["subject"])}


def build_film(pick, src, force):
    out = EXT / "media/films" / (pick["id"] + ".webm")
    poster = EXT / "media/films" / (pick["id"] + ".webp")
    start, dur = float(pick["start"]), float(pick["duration"])
    if force or not out.exists():
        # Take FADE more than needed and lay the tail over the head, so the
        # last frame flows into the first.
        edge = ""
        if pick.get("crop"):  # trim letterbox bars or a stray edge: fractions x0 y0 x1 y1
            x0, y0, x1, y1 = pick["crop"]
            edge = "crop=iw*%.4f:ih*%.4f:iw*%.4f:ih*%.4f," % (x1 - x0, y1 - y0, x0, y0)
        graph = ("[0:v]" + edge + "fps=30,scale=%d:-2:flags=lanczos,format=yuv420p,setsar=1,split[a][b];"
                 "[a]trim=0:%.3f,setpts=PTS-STARTPTS,fps=30[main];"
                 "[b]trim=%.3f:%.3f,setpts=PTS-STARTPTS,fps=30[tail];"
                 "[tail][main]xfade=transition=fade:duration=%.3f:offset=0,format=yuv420p[v]") % (
            FILM_W, dur, dur, dur + FADE, FADE)
        cmd = [ff(), "-v", "error", "-y", "-ss", "%.3f" % start, "-t", "%.3f" % (dur + FADE + 0.2), "-i", str(src),
               "-filter_complex", graph, "-map", "[v]", "-an", "-c:v", "libvpx-vp9", "-b:v", "900k", "-crf", str(FILM_CRF),  # constrained quality: CRF, capped
               "-pix_fmt", "yuv420p", "-row-mt", "1", "-deadline", "good", "-cpu-used", "4", "-g", "240", str(out)]
        subprocess.run(cmd, check=True)
    if force or not poster.exists():
        tmp = poster.with_suffix(".png")
        subprocess.run([ff(), "-v", "error", "-y", "-i", str(out), "-frames:v", "1", str(tmp)], check=True)
        Image.open(tmp).convert("RGB").save(poster, "WEBP", quality=82, method=6)
        tmp.unlink()
    im = Image.open(poster)
    return {"f": "media/films/%s.webm" % pick["id"], "pf": "media/films/%s.webp" % pick["id"],
            "w": im.width, "h": im.height, "c": subject_colour(im.convert("RGB"), pick["subject"])}


def tidy_author(a):
    a = re.sub(r"\s+", " ", a or "").strip()
    a = re.sub(r"^(own work|photo by|photograph by)[:,]?\s*", "", a, flags=re.I)
    a = re.sub(r"\s*\(talk\)|\s*\(talk · contribs\)", "", a)
    return a[:80] or "Unknown"


def load_picks():
    rejects = set()
    if REJECTS.exists():
        for line in REJECTS.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                rejects.add(line)
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    picks, seen = [], set()
    for f in sorted(PICKS.glob("*.json")):
        for p in json.loads(f.read_text()):
            key = (p["page"], p.get("start"))  # one video can give two clips
            if p["page"] in rejects or key in seen:
                continue
            seen.add(key)
            p.update(overrides.get(p["page"], {}))
            p["group"] = f.stem
            picks.append(p)
    # Stable ids: animal plus a short hash of the source, so re-curating does not renumber everything.
    for p in picks:
        h = hashlib.sha1((p["page"] + ("@%s" % p["start"] if p.get("start") else "")).encode()).hexdigest()[:5]
        p["id"] = "%s-%s%s" % (p["animal"], "f" if p["kind"] == "video" else "", h)
        NAMES.setdefault(p["animal"], p["name"])
    return picks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--films", action="store_true", help="re-encode the films (not the photos)")
    args = ap.parse_args()

    (EXT / "media/photos").mkdir(parents=True, exist_ok=True)
    (EXT / "media/films").mkdir(parents=True, exist_ok=True)
    picks = load_picks()
    if args.only:
        picks = [p for p in picks if p["id"] in args.only or p["animal"] in args.only]


    def one(p):
        try:
            if p["kind"] == "photo":
                src = fetch_photo(p)
                info = build_photo(p, src, args.force)
                kind = "p"
            else:
                src = cached(p["file_url"], Path(urllib.parse.urlparse(p["file_url"]).path).suffix or ".video")
                info = build_film(p, src, args.force or args.films)
                kind = "v"
        except Exception as e:  # noqa: BLE001
            print("FAILED %s %s: %s" % (p["id"], p["page"], e), file=sys.stderr)
            return None
        rec = {"id": p["id"], "a": p["animal"], "n": p["name"], "k": kind}
        rec.update(info)
        rec.update({
            "s": [round(float(v), 3) for v in p["subject"]],
            "q": p.get("score", 7),
            "by": tidy_author(p.get("author")),
            "lic": p.get("license", ""),
            "lu": p.get("license_url", ""),
            "src": p["page"],
            "wh": p.get("where", "") or "",
        })
        print("ok", rec["id"], rec["w"], "x", rec["h"])
        return rec

    with ThreadPoolExecutor(6) as ex:
        items = [r for r in ex.map(one, picks) if r]

    if args.only:
        # Merge into the existing library rather than replacing it.
        old = json.loads(re.search(r"=\s*(\{.*\});", (EXT / "src/library.js").read_text(), re.S).group(1))
        keep = {i["id"]: i for i in old["items"]}
        for i in items:
            keep[i["id"]] = i
        items = list(keep.values())
        for k, v in old.get("animals", {}).items():
            NAMES.setdefault(k, v)

    # Stray files from picks that were dropped.
    wanted = {i["f"] for i in items} | {i.get("pf") for i in items}
    for sub in ("photos", "films"):
        for f in (EXT / "media" / sub).iterdir():
            if "media/%s/%s" % (sub, f.name) not in wanted and not args.only:
                f.unlink()

    items.sort(key=lambda i: (i["a"] != "quokka", i["a"], -i["q"], i["id"]))
    animals = {}
    for i in items:
        animals.setdefault(i["a"], NAMES.get(i["a"], i["n"]))
    lib = {"animals": animals, "items": items}
    body = json.dumps(lib, ensure_ascii=False, separators=(",", ":"))
    (EXT / "src/library.js").write_text(
        "/* Generated by tools/media/build_media.py from tools/media/picks/. Do not edit by hand. */\n"
        "globalThis.QB_LIBRARY = " + body + ";\n")
    size = sum(f.stat().st_size for f in (EXT / "media").rglob("*") if f.is_file())
    print("%d pictures (%d films) of %d animals, %.1f MB" % (
        len(items), sum(1 for i in items if i["k"] == "v"), len(animals), size / 1e6))


if __name__ == "__main__":
    main()
