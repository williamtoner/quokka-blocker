/*
 * Choosing animals for an ad slot. Pure functions, shared by the background
 * worker (which does the choosing for every page) and the website's demo.
 *
 * Every picture in the library carries a subject box: the part of the frame
 * that must stay in view (the face, the ears, enough body to read as the
 * animal). A picture can fill a slot only if cropping it to the slot's shape
 * keeps that box whole, and the crop is then centred on it.
 *
 * Slots come in every shape, from 320x50 strips to 160x600 towers. A slot
 * that no single picture can fill well is laid out as a row (or column) of
 * tiles, each its own animal.
 */
(function (root) {
  'use strict';

  var SLACK = 0.06;        // how much of the subject box a crop may shave off, as a fraction of it
  var BANNER = 2.4;        // wider than this (w/h) and a slot becomes a row of tiles...
  var TOWER = 0.56;        // ...narrower than this and it becomes a column
  var TILE_WIDE = 2.0;     // the shape tiles in a row aim for
  var TILE_TALL = 0.8;     // ...and in a column
  var MIN_TILE = 64;       // px, least tile size along the split
  var GAP = 2;             // px between tiles
  var QUOKKA = { some: 1, lots: 2.5, only: 1 };
  var ZOOM = 1.6;          // most a picture may be enlarged (CSS px per source px), so it stays sharp
  var ONE_MIN = 0.42;      // a single picture only for slots between these shapes; beyond, tiles look better
  var ONE_MAX = 2.8;

  /*
   * Where to put the crop window for a picture of shape `ratio` (w/h) in a
   * box of shape `aspect`, so the subject stays in view. Returns
   * { fit: bool, x: 0..100, y: 0..100, cut: fraction of the subject lost }
   * where x/y are CSS object-position percentages.
   */
  // How much a picture is enlarged when cropped to fill a box w x h.
  function zoom(item, w, h) {
    return Math.max(w / item.w, h / item.h);
  }

  function crop(item, aspect) {
    var s = item.s;
    var ratio = item.w / item.h;
    var x = 50, y = 50, cut = 0;
    if (aspect >= ratio) {
      // Full width shows; only a band of the height does.
      var vh = ratio / aspect;
      var sh = s[3] - s[1];
      cut = Math.max(0, (sh - vh) / sh);
      var cy = (s[1] + s[3]) / 2;
      var top = Math.min(Math.max(cy - vh / 2, 0), 1 - vh);
      // A subject taller than the window keeps its top (the face) in view.
      if (sh > vh) top = Math.min(Math.max(s[1] - vh * 0.02, 0), 1 - vh);
      y = vh >= 1 ? 50 : (top / (1 - vh)) * 100;
    } else {
      var vw = aspect / ratio;
      var sw = s[2] - s[0];
      cut = Math.max(0, (sw - vw) / sw);
      var cx = (s[0] + s[2]) / 2;
      var left = Math.min(Math.max(cx - vw / 2, 0), 1 - vw);
      x = vw >= 1 ? 50 : (left / (1 - vw)) * 100;
    }
    return { fit: cut <= SLACK, x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10, cut: cut };
  }

  function tileSizes(total, n) {
    var each = (total - GAP * (n - 1)) / n;
    var out = [];
    for (var i = 0; i < n; i++) out.push(Math.round(each * 100) / 100);
    return out;
  }

  /*
   * Ways to lay out a slot, best first: one picture if anything fits the
   * whole shape, else tiles.
   */
  function layouts(w, h) {
    var a = w / h;
    var out = a >= ONE_MIN && a <= ONE_MAX ? [{ dir: 'one', tiles: [{ w: w, h: h }] }] : [];
    var n, sizes;
    if (a > BANNER) {
      n = Math.min(Math.max(2, Math.round(a / TILE_WIDE)), Math.floor(w / MIN_TILE), 6);
      if (n >= 2) {
        sizes = tileSizes(w, n);
        out.push({ dir: 'row', tiles: sizes.map(function (tw) { return { w: tw, h: h }; }) });
      }
    } else if (a < TOWER) {
      n = Math.min(Math.max(2, Math.round((1 / a) / (1 / TILE_TALL))), Math.floor(h / MIN_TILE), 5);
      if (n >= 2) {
        sizes = tileSizes(h, n);
        out.push({ dir: 'col', tiles: sizes.map(function (th) { return { w: w, h: th }; }) });
      }
    }
    if (!out.length) out.push({ dir: 'one', tiles: [{ w: w, h: h }] }); // too few tiles fit: one picture after all
    return out;
  }

  function weightOf(item) {
    return Math.pow(Math.max(1, (item.q || 7) - 5), 1.4);
  }

  function pickWeighted(list, weight, rand) {
    var total = 0;
    for (var i = 0; i < list.length; i++) total += weight(list[i]);
    var r = rand() * total;
    for (var j = 0; j < list.length; j++) {
      r -= weight(list[j]);
      if (r <= 0) return list[j];
    }
    return list[list.length - 1];
  }

  /*
   * Choose pictures for a slot.
   *   lib:   { items: [...] }  (library.js)
   *   w, h:  slot size in CSS px
   *   opts:  {
   *     animals:  { id: false, ... }  animals switched off
   *     quokkas:  'some' | 'lots' | 'only'
   *     motion:   true to allow video
   *     videos:   how many videos the page already plays
   *     avoid:    ids not to repeat (shown recently or on this page)
   *     rand:     random source, default Math.random
   *   }
   * Returns { dir, tiles: [{ w, h, item, x, y }] } or null if nothing fits.
   */
  function choose(lib, w, h, opts) {
    opts = opts || {};
    var rand = opts.rand || Math.random;
    var off = opts.animals || {};
    var avoid = {};
    (opts.avoid || []).forEach(function (id) { avoid[id] = true; });
    var mode = QUOKKA[opts.quokkas] ? opts.quokkas : 'lots';

    var pool = lib.items.filter(function (it) {
      if (mode === 'only') return it.a === 'quokka';
      return !off[it.a];
    });
    if (!pool.length) pool = lib.items.filter(function (it) { return it.a === 'quokka'; });

    var videoOk = opts.motion !== false && (opts.videos || 0) < 2 && w >= 240 && h >= 150;
    var plans = layouts(w, h);

    for (var p = 0; p < plans.length; p++) {
      var plan = plans[p];
      var used = {};
      var tiles = [];
      for (var t = 0; t < plan.tiles.length; t++) {
        var tile = plan.tiles[t];
        var aspect = tile.w / tile.h;
        var fitting = [];
        pool.forEach(function (it) {
          if (used[it.id]) return;
          if (it.k === 'v' && !(videoOk && plan.dir === 'one')) return;
          if (zoom(it, tile.w, tile.h) > ZOOM) return;
          var c = crop(it, aspect);
          if (c.fit) fitting.push({ item: it, c: c });
        });
        if (!fitting.length) {
          // Nothing fits cleanly: take whatever loses least of its subject, within reason.
          // As a last resort a picture may appear twice in one slot.
          [true, false].forEach(function (fresh) {
            if (fitting.length) return;
            pool.forEach(function (it) {
              if ((fresh && used[it.id]) || it.k === 'v') return;
              var c = crop(it, aspect);
              if (c.cut <= 0.3) fitting.push({ item: it, c: c });
            });
          });
          fitting.sort(function (a, b) { return a.c.cut - b.c.cut; });
          fitting = fitting.slice(0, 3);
        }
        if (!fitting.length) break;
        var fresh = fitting.filter(function (f) { return !avoid[f.item.id]; });
        if (fresh.length) fitting = fresh;

        // Animal first, so animals with many pictures do not crowd out the rest;
        // a tile row also tries not to repeat an animal.
        var byAnimal = {};
        fitting.forEach(function (f) { (byAnimal[f.item.a] = byAnimal[f.item.a] || []).push(f); });
        var animals = Object.keys(byAnimal);
        var unseen = animals.filter(function (a) { return !used['animal:' + a]; });
        if (unseen.length) animals = unseen;
        var animal = pickWeighted(animals, function (a) { return a === 'quokka' ? QUOKKA[mode] : 1; }, rand);
        var choices = byAnimal[animal];

        // Videos are a treat, not the norm: about one single-picture slot in three.
        var vids = choices.filter(function (f) { return f.item.k === 'v'; });
        var stills = choices.filter(function (f) { return f.item.k !== 'v'; });
        if (vids.length && stills.length) choices = rand() < 0.34 ? vids : stills;

        var chosen = pickWeighted(choices, function (f) { return weightOf(f.item) * (1 - f.c.cut); }, rand);
        used[chosen.item.id] = true;
        used['animal:' + chosen.item.a] = true;
        tiles.push({ w: tile.w, h: tile.h, item: chosen.item, x: chosen.c.x, y: chosen.c.y });
      }
      if (tiles.length === plan.tiles.length) return { dir: plan.dir, tiles: tiles };
    }
    return null;
  }

  var api = { crop: crop, layouts: layouts, choose: choose, GAP: GAP };
  root.QBPick = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
