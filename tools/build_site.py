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
    store_kit(out)
    print("site in", out)


FIELDS = [  # (key in fields.json, label on the page, where it goes in the dashboard)
    ("summary", "Summary", "Comes from the package; shown for checking"),
    ("description", "Description", "Store listing → Description"),
    ("category", "Category", "Store listing → Category"),
    ("language", "Language", "Store listing → Language"),
    ("homepage", "Homepage URL", "Store listing → Homepage URL"),
    ("support", "Support URL", "Store listing → Support URL"),
    ("single_purpose", "Single purpose", "Privacy → Single purpose description"),
    ("justify_storage", "storage justification", "Privacy → Permission justification: storage"),
    ("justify_activeTab", "activeTab justification", "Privacy → Permission justification: activeTab"),
    ("justify_host", "Host permission justification", "Privacy → Permission justification: host permissions"),
    ("remote_code", "Remote code", "Privacy → Are you using remote code? (choose this answer)"),
    ("privacy_policy", "Privacy policy URL", "Privacy → Privacy policy URL"),
    ("reviewer_notes", "Notes for the reviewer", "Only if the dashboard asks for test instructions"),
]


def store_kit(out):
    """An unlisted page with every Chrome Web Store field and a Copy button for
    each, and one zip with the package and the listing images, so the
    submission can be done from a browser on any computer."""
    import html
    import json
    import zipfile
    src = ROOT / "listing/chrome"
    fields = json.loads((src / "fields.json").read_text())
    dest = out / "store"
    dest.mkdir()
    images = fields["screenshots"] + [fields["promo_small"], fields["promo_marquee"]]
    for name in images:
        shutil.copy(src / name, dest / name)
    shutil.copy(EXT / "icons/icon128.png", dest / "icon128.png")
    kit = dest / "quokka-blocker-store-kit.zip"
    with zipfile.ZipFile(kit, "w") as zf:
        zf.write(out / "quokka-blocker-chrome.zip", "quokka-blocker-store-kit/quokka-blocker-chrome.zip")
        for name in images + ["icon128.png"]:
            zf.write(dest / name, "quokka-blocker-store-kit/" + name)
        zf.writestr("quokka-blocker-store-kit/fields.json", json.dumps(fields, indent=1, ensure_ascii=False))

    rows = []
    for key, label, where in FIELDS:
        rows.append(
            '<section class="f"><div class="h"><h2>%s</h2><button type="button" data-copy="%s">Copy %s</button></div>'
            '<p class="w">%s</p><pre id="%s">%s</pre></section>'
            % (html.escape(label), key, html.escape(label[0].lower() + label[1:]), html.escape(where), key, html.escape(fields[key])))
    shots = "".join('<figure><img src="%s" alt=""><figcaption>%s</figcaption></figure>' % (n, n) for n in images)
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Chrome Web Store kit · Quokka Blocker</title>
<link rel="icon" href="../qb/icon128.png"><link rel="stylesheet" href="../qb/theme.css"><style>
body{padding:32px 24px 80px}main{max-width:860px;margin:0 auto}
h1{font:480 40px/1.1 var(--serif);letter-spacing:-.02em}h2{font:600 16px var(--sans)}
.lede{margin:10px 0 26px;color:var(--ink-2)}
.dl{display:inline-flex;align-items:center;height:44px;padding:0 20px;border-radius:999px;background:var(--green);color:var(--green-ink);font-weight:600;text-decoration:none}
.f{margin-top:22px;padding:18px 20px;border-radius:14px;background:var(--raised);box-shadow:var(--shadow)}
.h{display:flex;align-items:center;justify-content:space-between;gap:12px}
.w{margin-top:2px;font-size:13px;color:var(--ink-3)}
pre{margin-top:10px;white-space:pre-wrap;font:400 14px/1.55 var(--sans);color:var(--ink)}
button{border:0;border-radius:999px;padding:8px 14px;background:var(--green-soft);color:var(--green);font-weight:600;cursor:pointer}
button.done{background:var(--green);color:var(--green-ink)}
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-top:14px}
.shots img{width:100%%;border-radius:8px;display:block;box-shadow:var(--shadow)}figcaption{margin-top:6px;font-size:13px;color:var(--ink-2)}
</style></head><body><main>
<h1>Chrome Web Store kit</h1>
<p class="lede">Everything for submitting Quokka Blocker. Download the kit (the extension package and every image), then copy each field below into the developer dashboard.</p>
<a class="dl" href="quokka-blocker-store-kit.zip" download>Download the store kit</a>
%s
<section class="f"><h2>Images</h2><p class="w">Screenshots in this order, then the small promo tile (440×280) and the marquee (1400×560). All are in the kit.</p><div class="shots">%s</div></section>
</main><script src="store.js"></script></body></html>""" % ("".join(rows), shots)
    (dest / "index.html").write_text(page)
    (dest / "store.js").write_text("""document.querySelectorAll('[data-copy]').forEach(function (b) {
  b.addEventListener('click', function () {
    var text = document.getElementById(b.dataset.copy).textContent;
    var done = function () { var was = b.textContent; b.textContent = 'Copied'; b.classList.add('done');
      setTimeout(function () { b.textContent = was; b.classList.remove('done'); }, 1600); };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () { fallback(text); done(); });
    else { fallback(text); done(); }
  });
});
function fallback(text) {
  var t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select();
  document.execCommand('copy'); t.remove();
}
""")
    print("store kit: %s (%.1f MB)" % (kit, kit.stat().st_size / 1e6))


if __name__ == "__main__":
    main()
