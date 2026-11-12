# Curating the animals

Quokka Blocker replaces web adverts with beautiful photographs and short
looping videos of animals. It is meant to feel like a premium, editorial
product: think the photo desk of a nature magazine, or a calendar you would
actually pay for. Every image a user sees has to make them go "oh!". One
mediocre photo makes the whole product look cheap, so **quality beats
quantity: pick fewer rather than settle.**

## Tool

`tools/media/candidates.py` (run with `python3`, from the repo root):

```bash
python3 tools/media/candidates.py photos "red panda" --out DIR --limit 50 [--offset 50] [--flickr]
python3 tools/media/candidates.py photos "Ailurus fulgens" --out DIR --limit 50      # add to the same DIR
python3 tools/media/candidates.py videos "red panda" --out DIR --limit 30
python3 tools/media/candidates.py frames VIDEO_FILE_URL --out DIR --every 2 --max 12
python3 tools/media/candidates.py box DIR/007.jpg 0.30 0.15 0.70 0.80
```

- Each search adds to `DIR/meta.json` (numbered candidates, licence and author
  already worked out; only CC0 / public domain / CC BY / CC BY-SA get through)
  and redraws numbered contact sheets `DIR/sheet-N.jpg` (12 per sheet). Look
  at the sheets with the Read tool, then open promising previews (`DIR/007.jpg`)
  one by one to judge sharpness and expression.
- Search Commons with several terms: English name, Latin name, other
  languages, and `incategory:Quality_images` / `incategory:Featured_pictures_on_Wikimedia_Commons`
  variants. Use `--offset` to page deeper; the best shots are often not on page 1.
  `--flickr` also searches Flickr's Creative Commons pool (images max 1024px;
  only use them when clearly better than what Commons has).
- `box` draws a subject box on a preview so you can check it by eye.
- `frames` pulls stills from a video every N seconds so you can see what
  happens in it (labels are seconds from the start).

## What makes the cut

Keep only photos that would look at home in a premium nature calendar:

- Tack sharp on the eyes, good natural light, pleasing colour, clean or softly
  blurred background. The animal is clearly the subject and fills a good part
  of the frame.
- Charming: eye contact, a "smile", sleeping curled up, yawning, peeking,
  holding something, a mother with baby, fluffy young. Adorable, warm, happy.
- Variety within an animal: different poses, settings and framings
  (close-up portrait, full body, pairs).

Reject: soft focus, noise, harsh flash, blown highlights; cages, fences, glass,
concrete zoo enclosures, feeding bowls, signs; people or hands in frame (a
collar on a pet is fine); watermarks, borders, text; illustrations, museum
specimens; dead animals, prey, blood, aggression, mating, injury, anything
sad or gross; staged/odd props (e.g. a quokka "holding a microphone"); the
animal tiny in the frame; awkward crops that cut off ears or faces.

Minimum size: 1000 px on the long side (Commons search already asks for >1500 px wide).

## Subject box

For each pick, give `subject`: `[x0, y0, x1, y1]` as fractions of the full
image (0..1, origin top-left). It is the part that must stay visible when the
picture is cropped to fit an ad slot of any shape: the face and enough of the
body to read as the animal, nothing more. Tighter is better as long as the
face is whole (ears included). The extension centres crops on this box.
**Check every box with `box` and look at the result before writing it down.**

## Videos

Short clips that loop: one continuous shot (no cuts), steady camera, the
animal doing something lovely and staying in frame. Give `start` and
`duration` (5 to 12 s) of the best segment, chosen so the end flows back
to the start without a jarring jump (similar pose/position at both ends).
At least 960 px wide, ideally 1280+. `subject` covers where the animal is
throughout the segment.

## Output

Write a JSON array to the file you were given, one object per pick:

```json
{
  "animal": "red-panda",              // id from your list
  "name": "Red panda",                // display name, sentence case
  "kind": "photo",                    // or "video"
  "source": "commons",                // copy from meta.json
  "page": "https://commons.wikimedia.org/wiki/File:...",  // copy
  "file_url": "https://upload.wikimedia.org/...",         // copy
  "width": 4000, "height": 2667,      // copy
  "author": "Jane Doe",               // copy, tidy it: a plain human name or handle, no HTML, no "Own work"
  "license": "CC BY-SA 4.0",          // copy
  "license_url": "https://creativecommons.org/licenses/by-sa/4.0",  // copy
  "where": "Rottnest Island, Australia",  // short place, only if the description says so; else ""
  "subject": [0.31, 0.18, 0.72, 0.86],
  "score": 9,                         // 1-10, honest; 8+ only for genuinely gorgeous
  "note": "yawning, soft green bokeh",
  "start": 12.0, "duration": 8.0      // videos only
}
```

Order picks best first within each animal. Do not download full-size
originals; previews are enough. Work only inside your own scratch folder and
your output file.
