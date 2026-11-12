#!/usr/bin/env python3
"""Package the extension for Chrome and Firefox.

    python3 tools/build.py [out-dir]     (default: dist/)

writes quokka-blocker-chrome.zip and quokka-blocker-firefox.zip.

Firefox runs the same code; only the manifest differs. Its background code is
an event page rather than a service worker, so it is given, in order, the
files Chrome's worker pulls in with importScripts(). Media files are already
compressed, so they are stored rather than deflated.
"""
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
ADDON_ID = "quokka-blocker@williamtoner.net"
MIN_FIREFOX = "128.0"
STORED = {".avif", ".webp", ".webm", ".png", ".woff2"}


def background_scripts(worker):
    source = (EXT / worker).read_text()
    call = re.search(r"importScripts\((.*?)\);", source, re.S)
    if not call:
        raise SystemExit("%s no longer calls importScripts()" % worker)
    folder = Path(worker).parent
    return [(folder / name).as_posix() for name in re.findall(r"'([^']+)'", call.group(1))] + [worker]


def firefox_manifest():
    m = json.loads((EXT / "manifest.json").read_text())
    m.pop("minimum_chrome_version", None)
    m["background"] = {"scripts": background_scripts(m["background"]["service_worker"])}
    m["browser_specific_settings"] = {"gecko": {
        "id": ADDON_ID,
        "strict_min_version": MIN_FIREFOX,
        "data_collection_permissions": {"required": ["none"]},
    }}
    return m


def pack(out, manifest):
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n", zipfile.ZIP_DEFLATED)
        for path in sorted(EXT.rglob("*")):
            if not path.is_file() or path.name in (".DS_Store", "manifest.json"):
                continue
            how = zipfile.ZIP_STORED if path.suffix in STORED else zipfile.ZIP_DEFLATED
            zf.write(path, path.relative_to(EXT).as_posix(), compress_type=how)
    return out


def build_all(out):
    out.mkdir(parents=True, exist_ok=True)
    chrome = json.loads((EXT / "manifest.json").read_text())
    for name, manifest in (("chrome", chrome), ("firefox", firefox_manifest())):
        path = pack(out / ("quokka-blocker-%s.zip" % name), manifest)
        print("%s  %.1f MB" % (path, path.stat().st_size / 1e6))


def main():
    build_all(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist")


if __name__ == "__main__":
    main()
