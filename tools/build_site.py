#!/usr/bin/env python3
"""Build the website into a folder (default: dist/site).

The site runs the extension's own library, picker, card renderer, fonts and
photos, so the demo on it is the real thing. It also carries fresh builds of
the extension for the download buttons, the test page, and a credits page.

    python3 tools/build_site.py [out-dir]
"""
import shutil
import sys
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist/site"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "site", out)
    qb = out / "qb"
    qb.mkdir()
    for name in ("library.js", "pick.js", "card.js"):
        shutil.copy(EXT / "src" / name, qb / name)
    shutil.copy(EXT / "pages/theme.css", qb / "theme.css")
    shutil.copy(EXT / "icons/icon128.png", qb / "icon128.png")
    shutil.copytree(EXT / "fonts", qb / "fonts")
    shutil.copytree(EXT / "media", qb / "media")
    # theme.css finds the fonts at ../fonts from extension/pages; the site keeps them at qb/fonts.
    css = (qb / "theme.css").read_text().replace("../fonts/", "fonts/")
    (qb / "theme.css").write_text(css)

    # Credits: the extension's own page, pointed at the site's copies.
    page = (EXT / "pages/credits.html").read_text()
    page = page.replace('href="theme.css"', 'href="qb/theme.css"').replace('href="pages.css"', 'href="qb/pages.css"')
    page = page.replace('src="../src/', 'src="qb/').replace('src="credits.js"', 'src="qb/credits.js"')
    page = page.replace('href="../icons/icon32.png"', 'href="qb/icon128.png"').replace('href="welcome.html"', 'href="./"')
    (out / "credits.html").write_text(page)
    shutil.copy(EXT / "pages/pages.css", qb / "pages.css")
    shutil.copy(EXT / "pages/credits.js", qb / "credits.js")
    js = (qb / "credits.js").read_text().replace("'../' + (i.k", "'qb/' + (i.k")
    (qb / "credits.js").write_text(js)

    shutil.copytree(ROOT / "demo", out / "test")
    build.build_all(out)
    print("site in", out)


if __name__ == "__main__":
    main()
