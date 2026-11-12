# Quokka Blocker

A browser extension that replaces web adverts with beautiful photographs and short films of quokkas, otters, red pandas and their friends.

It does not stop ads from loading. It covers the spaces they were given, so pages keep the layout their designers intended (no collapsed gaps, no jumping text) and it needs no filter lists.

## Try it

1. Open `chrome://extensions`, switch on **Developer mode**, click **Load unpacked** and pick the `extension/` folder. Works in Chrome, Edge, Brave, Arc and other Chromium browsers. For Firefox, see [below](#firefox).
2. Open the test page, a mock newspaper full of fake ads in every common shape:

   ```bash
   python3 -m http.server 8377 --bind 127.0.0.1 --directory demo
   ```

   then <http://localhost:8377/>.

Hover an animal to see what it is, where the picture was taken and who took it, and to ask for **Another** or **Show ad**. The toolbar popup keeps count and lets you pause it per site, switch films off, choose your animals, or go all in with *Quokkas only*.

## How it works

- **Finding ad spaces.** `content.js` watches the page for the containers the big ad networks render into (Google's GPT and AdSense slots, Amazon, Criteo, Taboola, Outbrain, Yahoo! JAPAN and others). Deliberately no guessing from class names like `.ad`: a false positive would eat page content. A space is swapped the moment it takes up room, usually before its advert has loaded. A space holding several ad frames has each one dealt with separately; a full-width band with a smaller ad centred in it has just the ad covered; full-screen interstitials are left alone, so nothing traps the reader.
- **Choosing animals.** `pick.js` lays out the space. Every picture in the library carries a *subject box* marking where the animal is, and a picture may fill a space only if cropping it to that shape keeps the box whole; the crop is then centred on it. Boxes and squares take one picture; long banners become a filmstrip of tiles and tall towers a stack. Animals are chosen first and pictures second, so animals with many pictures do not crowd out the rest, and recent pictures are not repeated.
- **Drawing the card.** `card.js` builds it in a closed shadow root so page styles cannot touch it. Stills drift very slowly; films play only while on screen, at most two to a page, and never with *reduce motion* set.
- **Nothing leaves the browser.** Every photo, film and font ships inside the extension. There is no server, no analytics and no network request of its own.

## The pictures

Every picture is shared under an open licence (CC0, CC BY or CC BY-SA) on Wikimedia Commons or Flickr, and every one is credited: on the card when you hover, and in full on the extension's credits page (`pages/credits.html`).

They were chosen by hand against the brief in [tools/media/CURATION.md](tools/media/CURATION.md): sharp, warm, charming, no cages or people, nothing sad. The picks, with their sources, licences and subject boxes, live in `tools/media/picks/*.json`. To rebuild the shipped files from them:

```bash
python3 tools/media/build_media.py
```

That fetches each original once (cached in `tools/media/cache/`), writes 1280 px AVIF stills and 960 px VP9 films (trimmed, silent, with the end cross-faded into the start so they loop without a jump), and regenerates `extension/src/library.js`. List a picture's page in `tools/media/rejects.txt` to drop it, or correct its fields in `tools/media/overrides.json`.

`tools/media/candidates.py` is the curation tool: it searches Commons and Openverse, keeps only usable licences, and lays candidates out on numbered contact sheets.

## Tests

```bash
node test/pick.test.js                                   # picker and library
QB_CHROMIUM=/path/to/chrome python3 test/e2e.py --shots out/   # the real extension on the test page
```

The end-to-end test needs Python Playwright. It checks that every fake ad becomes animals, the editorial photo is left alone, a slot added late is swapped within 400 ms, and **Show ad** works.

## Firefox

The same code runs in Firefox; only the manifest differs, and `tools/build.py` writes both:

```bash
python3 tools/build.py        # dist/quokka-blocker-chrome.zip and dist/quokka-blocker-firefox.zip
```

Until Mozilla signs it, load the Firefox zip from `about:debugging#/runtime/this-firefox` with **Load Temporary Add-on…**.

## The website

`site/` is the public page. It runs the extension's own library, picker and card renderer, so its demo is the real thing. `python3 tools/build_site.py` builds it into `dist/site` with fresh downloads, the credits page and the test page.

## Licence

Code: MIT. Typefaces: Fraunces and Inter, SIL Open Font License (`extension/fonts/OFL.txt`). Pictures: each under its own Creative Commons licence or public domain dedication, as credited; the cropped, resized and looped copies here are shared under the same terms as their originals.
