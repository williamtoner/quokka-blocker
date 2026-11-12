# Chrome Web Store listing

Everything to paste into the [developer dashboard](https://chrome.google.com/webstore/devconsole), field by field. The texts' source is `fields.json`; the site turns it into an unlisted page with a Copy button per field, <https://williamtoner.net/quokka-blocker/store/>, and a download with the package and every image. `FLYINGFISH_TASK.md` is the same submission written as a task for the FlyingFish computer-use app. Images are in this folder; they are rebuilt by `tools/make_store_assets.py`. The package is `dist/quokka-blocker-chrome.zip` (from `python3 tools/build.py`), the same file the website offers.

## Package

Upload `quokka-blocker-chrome.zip`. Name, version, summary and icon come from its manifest:

- **Name:** Quokka Blocker
- **Summary (132 max):** Replaces web adverts with beautiful photographs and films of quokkas, otters, red pandas and friends.

## Store listing tab

**Description:**

```
Every ad, now an animal.

Quokka Blocker replaces the adverts on the web with photographs and short films of quokkas, otters, red pandas and their friends. Each one is fitted to the space the advert was given, so pages keep their layout: no gaps, no jumping text, just something lovely where an advert used to be.

• 190 hand-picked pictures of 41 kinds of animal, from snow monkeys and shima-enaga to capybaras, sea otters and, of course, quokkas.
• Every picture is marked with where its animal is, so a crop never cuts off a face. Long banners become filmstrips; tall columns stack up.
• Now and then a short, silent film plays instead: a red fox kit at its den, a puffin on a misty cliff. Films only play while on screen, and you can switch them off.
• Hover any animal to see what it is, where it was photographed and who took the picture. Ask for another, or put the original advert back.
• Choose your animals in the toolbar popup, pause Quokka Blocker on any site, or go all in with "Quokkas only".

Private by design. Every photo and film ships inside the extension. Quokka Blocker makes no network requests of its own, collects no data, and has no accounts, tracking or ads. Your count of ads turned into animals stays in your browser.

Every picture is shared under an open licence (Creative Commons or public domain) by the photographer credited beside it, on Wikimedia Commons or Flickr. Full credits are in the extension.

Open source: https://github.com/williamtoner/quokka-blocker
Website: https://williamtoner.net/quokka-blocker/
```

- **Category:** Fun (under Lifestyle). Well-being is the alternative.
- **Language:** English
- **Store icon:** `extension/icons/icon128.png`
- **Screenshots (1280x800):** `1-page.png`, `2-before-after.png`, `3-hover.png`, `4-popup.png`, `5-welcome.png`, in that order
- **Small promo tile (440x280):** `promo-440x280.png`
- **Marquee promo tile (1400x560):** `marquee-1400x560.png`
- **Official URL:** none (it needs a verified domain; can be added later)
- **Homepage URL:** https://williamtoner.net/quokka-blocker/
- **Support URL:** https://github.com/williamtoner/quokka-blocker/issues
- **Mature content:** No

## Privacy practices tab

**Single purpose:**

```
Quokka Blocker has one purpose: where a web page shows an advert, it shows a photograph or short film of an animal instead, sized to the advert's space. Everything it shows is bundled with the extension.
```

**Permission justifications:**

- **storage:** `Saves the user's settings (on/off, sites where it is paused, films on or off, which animals to show) and a count of how many adverts it has replaced, in the browser only.`
- **activeTab:** `Lets the toolbar popup read the current tab's address so the user can pause Quokka Blocker on that site with one switch.`
- **Host permission (content script on all http/https pages):** `Adverts appear on any website, so the content script runs on every page to find the containers the major ad networks render into and cover each one with a bundled animal photograph. It reads no page content beyond the size and position of those ad containers, and sends nothing anywhere.`

**Are you using remote code?** No, I am not using remote code.

**Data usage:** tick none of the data types (it collects none). Tick all three certifications:

- I do not sell or transfer user data to third parties, outside of the approved use cases
- I do not use or transfer user data for purposes that are unrelated to my item's single purpose
- I do not use or transfer user data to determine creditworthiness or for lending purposes

**Privacy policy URL:** https://williamtoner.net/quokka-blocker/privacy.html

## Distribution tab

- **Visibility:** Public
- **Regions:** All regions
- **Payment:** Free

## Notes for the reviewer (if asked)

```
Quokka Blocker does not block network requests; it covers advert containers (Google Publisher Tag and AdSense slots, Amazon, Criteo, Taboola, Outbrain and similar, matched by element id or frame source) with locally bundled images. To see it working, open https://williamtoner.net/quokka-blocker/test/, a test page full of fake adverts in common sizes. Source: https://github.com/williamtoner/quokka-blocker
```

## After the first submission

Review usually takes a few days; extensions that run on all sites can take longer. Once it is live, put the store link on the website (the "Add to your browser" button and the Chrome install box in `site/index.html`). Each new version needs a higher `version` in `extension/manifest.json` and a new upload of the zip.
