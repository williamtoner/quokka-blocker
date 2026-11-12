/*
 * Finds ad slots on the page and puts animals in them.
 *
 * Unlike an ad blocker this does not stop ads from loading; it covers the
 * space they were given. That keeps pages laid out as their designers
 * intended (no collapsed gaps, no jumping text) and needs no filter lists:
 * the slots are found by the containers the big ad networks render into.
 *
 * A slot is swapped the moment it takes up space, usually before the ad in
 * it has finished loading, so the ad is rarely seen at all.
 */
(function () {
  'use strict';
  if (window.top !== window || globalThis.__qbStarted) return;
  globalThis.__qbStarted = true;

  var QB = globalThis.QB;

  // Containers the big ad networks render into. Deliberately no generic
  // ".ad" / ".banner" class guesses: a false positive here eats page content.
  var AD_HOSTS = [
    'doubleclick.net', 'googlesyndication.com', 'googleadservices.com', 'amazon-adsystem.com',
    'adnxs.com', 'criteo.com', 'criteo.net', 'taboola.com', 'outbrain.com', 'pubmatic.com',
    'rubiconproject.com', 'openx.net', 'adform.net', 'smartadserver.com', 'media.net',
    'teads.tv', 'sharethrough.com', '3lift.com', 'yieldmo.com', 'adsrvr.org', 'casalemedia.com',
    'yimg.jp/images/listing', 'yads.yahoo.co.jp', 'i-mobile.co.jp', 'microad.jp', 'logly.co.jp',
    'fluct.jp', 'adingo.jp', 'nend.net', 'gssprt.jp', 'ad-stir.com'
  ];
  var SLOT_SELECTOR = [
    'ins.adsbygoogle',
    '[id^="div-gpt-ad"]',
    '[id^="google_ads_iframe"]',
    'iframe[id^="aswift_"]',
    '[data-google-query-id]',
    '[data-ad-slot]',
    'amp-ad',
    'div[id^="taboola-"]',
    '.OUTBRAIN',
    'ins.yads_ad',
    '[id^="yads"]'
  ].concat(AD_HOSTS.map(function (h) { return 'iframe[src*="' + h + '"]'; })).join(',');

  var DEFAULTS = { enabled: true, pausedHosts: [], motion: true };

  var settings = DEFAULTS;
  var tracked = new WeakSet();
  var released = new WeakSet(); // slots whose real ad the reader asked to see again
  var promoted = new WeakSet(); // ad frames dealt with on their own, inside a bigger slot
  var watching = [];            // slots found but too small to fill yet
  var swaps = [];
  var shown = [];               // picture ids on this page, so they are not repeated
  var scanTimer = null;
  var sizer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(onResize) : null;
  var reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)');

  function isActive() {
    return settings.enabled && settings.pausedHosts.indexOf(location.hostname) === -1;
  }

  function motion() {
    return settings.motion !== false && !(reduceMotion && reduceMotion.matches);
  }

  function send(msg) {
    try {
      return chrome.runtime.sendMessage(msg).catch(function () { return null; });
    } catch (e) {
      return Promise.resolve(null); // extension was reloaded under this page
    }
  }

  function asset(path) {
    return chrome.runtime.getURL(path);
  }

  // ---- finding slots ---------------------------------------------------------

  function scan() {
    scanTimer = null;
    if (!isActive()) return;
    scanPartial();
    var found = document.querySelectorAll(SLOT_SELECTOR);
    for (var i = 0; i < found.length; i++) {
      var slot = found[i];
      if (tracked.has(slot) || released.has(slot)) continue;
      if (slot.closest('[data-quokka-blocker]')) continue;
      // Ad scripts tag containers as they go, so an outer box can become a
      // slot after the ad inside it was already swapped. That one is done.
      if (slot.querySelector('quokka-blocker, [data-quokka-blocked]')) { tracked.add(slot); continue; }
      // Only the outermost container: a GPT div holds a container div holds an iframe.
      if (slot.parentElement && slot.parentElement.closest(SLOT_SELECTOR)) continue;
      tracked.add(slot);
      consider(slot);
    }
  }

  // A slot whose card covers only one ad frame in it (see targetFor) may
  // gain more frames later, as a page builds: each is a separate ad.
  function scanPartial() {
    swaps.forEach(function (entry) {
      if (entry.target === entry.slot || !entry.slot.isConnected) return;
      visibleFrames(entry.slot).forEach(function (f) {
        if (tracked.has(f) || f === entry.target || entry.target.contains(f)) return;
        tracked.add(f);
        promoted.add(f);
        consider(f);
      });
    });
  }

  function scheduleScan() {
    if (scanTimer === null) scanTimer = setTimeout(scan, 50);
  }

  function bigEnough(rect) {
    return rect.width >= 60 && rect.height >= 30;
  }

  function isInterstitial(rect) {
    return rect.width > innerWidth * 0.9 && rect.height > innerHeight * 0.9;
  }

  function visibleFrames(slot) {
    var out = [];
    var frames = slot.querySelectorAll('iframe');
    for (var i = 0; i < frames.length; i++) {
      if (bigEnough(frames[i].getBoundingClientRect())) out.push(frames[i]);
    }
    return out;
  }

  // Look at a slot now; if it has no size yet, wait until it does.
  function consider(slot) {
    if (!isActive() || !slot.isConnected || released.has(slot) || slot.hasAttribute('data-quokka-blocked')) return;
    if (slot.querySelector('quokka-blocker, [data-quokka-blocked]') ||
        (!promoted.has(slot) && slot.parentElement && slot.parentElement.closest('[data-quokka-blocked]'))) { unwatch(slot); return; }
    if (splitSlot(slot)) return;
    var rect = targetFor(slot).getBoundingClientRect();
    if (bigEnough(rect) && !isInterstitial(rect)) {
      unwatch(slot);
      swap(slot);
    } else if (watching.indexOf(slot) === -1) {
      watching.push(slot);
      if (sizer) sizer.observe(slot);
    }
  }

  function unwatch(slot) {
    var at = watching.indexOf(slot);
    if (at !== -1) watching.splice(at, 1);
    if (sizer) sizer.unobserve(slot);
  }

  function onResize(entries) {
    entries.forEach(function (e) { consider(e.target); });
  }

  /*
   * Some "slots" are really a whole column holding several separate ads.
   * One card stretched over them all would be odd, so a slot with two or
   * more visible ad frames has each frame dealt with by itself. Returns true
   * if it did that.
   */
  function splitSlot(slot) {
    if (slot.matches('iframe')) return false;
    var frames = visibleFrames(slot);
    if (frames.length < 2) return false;
    frames.forEach(function (f) {
      if (tracked.has(f)) return;
      tracked.add(f);
      promoted.add(f);
      consider(f);
    });
    return true;
  }

  /*
   * What to actually cover. Usually the slot itself, but publishers often
   * mark a whole full-width band as the "slot" with a 970x250 ad centred
   * inside it. Covering the band would be wrong, so when the slot holds one
   * visible ad frame that is clearly smaller, cover just that (or the tight
   * wrapper around it).
   */
  function targetFor(slot) {
    if (slot.matches('iframe')) return slot;
    var slotRect = slot.getBoundingClientRect();
    var visible = visibleFrames(slot);
    if (visible.length !== 1) return slot;
    var frameRect = visible[0].getBoundingClientRect();
    var frameArea = frameRect.width * frameRect.height;
    if (slotRect.width * slotRect.height <= frameArea * 1.25) return slot;
    var target = visible[0];
    while (target.parentElement && target.parentElement !== slot) {
      var r = target.parentElement.getBoundingClientRect();
      if (r.width * r.height > frameArea * 1.25) break;
      target = target.parentElement;
    }
    return target;
  }

  // ---- swapping -----------------------------------------------------------------

  var COPIED = ['margin-top', 'margin-right', 'margin-bottom', 'margin-left', 'float', 'vertical-align', 'border-radius'];
  var POSITIONED = ['position', 'top', 'right', 'bottom', 'left', 'z-index'];

  function playingVideos() {
    var n = 0;
    swaps.forEach(function (s) { if (s.choice && s.choice.tiles.some(function (t) { return t.item.k === 'v'; })) n++; });
    return n;
  }

  function ask(w, h, avoid) {
    return send({
      type: 'qb-choose',
      w: w, h: h,
      motion: motion(),
      videos: playingVideos(),
      avoid: avoid
    });
  }

  function swap(slot) {
    var target = targetFor(slot);
    var rect = target.getBoundingClientRect();
    slot.setAttribute('data-quokka-blocked', '');
    var entry = { slot: slot, target: target, host: null, choice: null, size: { width: Math.round(rect.width), height: Math.round(rect.height) },
      display: target.style.getPropertyValue('display'), priority: target.style.getPropertyPriority('display') };
    swaps.push(entry);

    return ask(entry.size.width, entry.size.height, shown.slice(-60)).then(function (choice) {
      if (!choice || !isActive() || !target.isConnected || swaps.indexOf(entry) === -1) {
        slot.removeAttribute('data-quokka-blocked');
        drop(entry);
        return;
      }
      place(entry, choice);
      target.style.setProperty('display', 'none', 'important');
      send({ type: 'qb-swapped', animals: choice.tiles.map(function (t) { return t.item.a; }), count: swaps.length });
    });
  }

  function place(entry, choice) {
    var cs = getComputedStyle(entry.target);
    var host = QB.renderCard(choice, entry.size, {
      asset: asset,
      motion: motion(),
      onAnother: function () { another(entry); },
      onShowAd: function () { undo(entry); }
    });
    // Sit exactly where the ad sat.
    host.style.setProperty('display', cs.display.indexOf('inline') === 0 ? 'inline-block' : 'block', 'important');
    var props = COPIED;
    if (cs.position !== 'static' && cs.position !== 'relative') props = props.concat(POSITIONED);
    props.forEach(function (p) { host.style.setProperty(p, cs.getPropertyValue(p), 'important'); });

    if (entry.host) {
      if (entry.host.__qbStop) entry.host.__qbStop();
      entry.host.replaceWith(host);
    } else {
      entry.target.parentNode.insertBefore(host, entry.target);
    }
    entry.host = host;
    entry.choice = choice;
    choice.tiles.forEach(function (t) { shown.push(t.item.id); });
  }

  function another(entry) {
    var avoid = shown.slice(-60);
    ask(entry.size.width, entry.size.height, avoid).then(function (choice) {
      if (choice && swaps.indexOf(entry) !== -1) place(entry, choice);
    });
  }

  function drop(entry) {
    var at = swaps.indexOf(entry);
    if (at !== -1) swaps.splice(at, 1);
  }

  function undo(entry) {
    drop(entry);
    released.add(entry.slot);
    if (entry.host) {
      if (entry.host.__qbStop) entry.host.__qbStop();
      entry.host.remove();
    }
    entry.slot.removeAttribute('data-quokka-blocked');
    if (entry.display) entry.target.style.setProperty('display', entry.display, entry.priority);
    else entry.target.style.removeProperty('display');
    send({ type: 'qb-count', count: swaps.length });
  }

  // The page took an ad away (or rebuilt that part of itself): take the animal too.
  function tidy() {
    swaps.slice().forEach(function (entry) {
      if (entry.host && !entry.target.isConnected) {
        drop(entry);
        if (entry.host.__qbStop) entry.host.__qbStop();
        entry.host.remove();
      }
    });
  }

  function onMutations() {
    scheduleScan();
    if (swaps.length) tidy();
  }

  // ---- lifecycle ------------------------------------------------------------------

  function applySettings(next) {
    var wasActive = isActive();
    var motionWas = motion();
    settings = next;
    if (isActive() && !wasActive) {
      tracked = new WeakSet();
      released = new WeakSet();
      scan();
    } else if (!isActive() && wasActive) {
      watching.slice().forEach(unwatch);
      swaps.slice().forEach(function (entry) {
        undo(entry);
        released.delete(entry.slot);
      });
      send({ type: 'qb-count', count: 0 });
    } else if (motion() !== motionWas) {
      swaps.slice().forEach(function (entry) {
        if (!entry.host) return;
        var keep = entry.choice;
        if (!motion() && keep.tiles.some(function (t) { return t.item.k === 'v'; })) another(entry);
        else place(entry, keep);
      });
    }
  }

  function merged(stored) {
    var out = {};
    for (var k in DEFAULTS) out[k] = stored && stored[k] !== undefined ? stored[k] : DEFAULTS[k];
    return out;
  }

  chrome.storage.local.get(DEFAULTS, function (stored) {
    settings = merged(stored);
    scan();
    new MutationObserver(onMutations).observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['id', 'class', 'src', 'data-google-query-id', 'data-ad-slot']
    });
  });

  chrome.storage.onChanged.addListener(function (changes, area) {
    if (area !== 'local') return;
    var next = merged(settings);
    var touched = false;
    for (var k in DEFAULTS) {
      if (changes[k]) { next[k] = changes[k].newValue !== undefined ? changes[k].newValue : DEFAULTS[k]; touched = true; }
    }
    if (touched) applySettings(next);
  });
})();
