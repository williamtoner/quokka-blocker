/*
 * Draws the animal card that takes an ad's place. It lives in a closed
 * shadow root so the page's CSS cannot restyle it.
 *
 * At rest a card is just the photograph (or film) and a small mark in the
 * corner. Hovering brings up the animal's name, where the picture was taken
 * and who took it, and two buttons: another animal, or the original ad.
 *
 * Used by the extension's content script and by the website's demo, so it
 * takes everything environment-specific (where files live, what the buttons
 * do) as arguments.
 */
(function (root) {
  'use strict';

  var SERIF = 'QB Fraunces';
  var SANS = 'QB Inter';
  var SANS_STACK = '"' + SANS + '",ui-sans-serif,system-ui,-apple-system,"Segoe UI","Hiragino Sans","Yu Gothic UI",sans-serif';
  var SERIF_STACK = '"' + SERIF + '",ui-serif,Georgia,"Hiragino Mincho ProN",serif';
  var EASE = 'cubic-bezier(.2,.75,.2,1)';

  var MARK = '<svg viewBox="0 0 64 64" aria-hidden="true"><g fill="currentColor">' +
    '<path d="M21 58.5C14 58.8 8.5 59.6 4.2 60.6c-1.6.4-2-.9-.6-1.6 4.3-2.3 9.6-4.3 15.4-5.6z"/>' +
    '<ellipse cx="27.5" cy="42.6" rx="16" ry="16" transform="rotate(-12 27.5 42.6)"/>' +
    '<ellipse cx="35.5" cy="30" rx="9" ry="9"/><circle cx="40" cy="21.6" r="9.8"/>' +
    '<ellipse cx="48" cy="25.2" rx="6" ry="5" transform="rotate(12 48 25.2)"/>' +
    '<ellipse cx="35.4" cy="12.2" rx="4" ry="4.6" transform="rotate(-20 35.4 12.2)"/>' +
    '<ellipse cx="33.5" cy="57.6" rx="9" ry="2.8"/>' +
    '<ellipse cx="43.8" cy="39.2" rx="3.7" ry="2.4" transform="rotate(35 43.8 39.2)"/></g></svg>';
  var ICON_SHUFFLE = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 4.5h2.3c1.3 0 2.1.6 2.8 1.6l1.8 3.8c.7 1 1.5 1.6 2.8 1.6H14M2 11.5h2.3c1.3 0 2.1-.6 2.8-1.6M9 6.1c.7-1 1.5-1.6 2.8-1.6H14M12 2.5l2 2-2 2M12 9.5l2 2-2 2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var ICON_AD = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.75" y="3.25" width="12.5" height="9.5" rx="2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M4.6 10.2 6 5.8h.3l1.4 4.4M5 8.9h1.9M9.4 5.8v4.4h.9c1.2 0 1.9-.8 1.9-2.2s-.7-2.2-1.9-2.2z" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  var CSS = [
    ':host{all:initial;}',
    '*{box-sizing:border-box;margin:0;padding:0;}',
    '.card{position:relative;width:100%;height:100%;overflow:hidden;display:flex;gap:2px;background:#15110e;',
    '  font-family:' + SANS_STACK + ';font-synthesis:none;-webkit-font-smoothing:antialiased;color:#fff;line-height:1.25;',
    '  contain:strict;isolation:isolate;}',
    '.row{flex-direction:row;}.col{flex-direction:column;}',
    '.tile{position:relative;flex:none;overflow:hidden;background:var(--c);}',
    '.pan{position:absolute;inset:0;transform-origin:var(--ox) var(--oy);}',
    '.media{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:var(--x) var(--y);display:block;',
    '  opacity:0;transform:scale(1.045);filter:blur(14px) saturate(1.2);',
    '  transition:opacity .75s ' + EASE + ',transform 1.4s ' + EASE + ',filter .9s ' + EASE + ';transition-delay:var(--d);}',
    '.tile.in .media.still{opacity:1;transform:none;filter:none;}',
    'video.media{transition-duration:.9s;transition-delay:0s;}',
    '.tile.playing video.media{opacity:1;transform:none;filter:none;}',
    // a slow drift brings stills to life without asking for attention
    '.drift .pan{animation:qb-drift var(--dur) ease-in-out var(--dd) infinite alternate;}',
    '@keyframes qb-drift{from{transform:scale(1);}to{transform:scale(1.075);}}',
    '.paused .pan{animation-play-state:paused;}',
    '@media (prefers-reduced-motion:reduce){.drift .pan{animation:none;}.media{transform:none!important;filter:none!important;transition:opacity .4s linear;}}',

    // corner mark
    '.mark{position:absolute;z-index:2;top:8px;left:8px;height:24px;min-width:24px;padding:0 4.5px;border-radius:12px;display:flex;align-items:center;gap:6px;',
    '  background:rgba(22,17,13,.34);-webkit-backdrop-filter:blur(10px) saturate(1.4);backdrop-filter:blur(10px) saturate(1.4);',
    '  box-shadow:0 0 0 .5px rgba(255,255,255,.18) inset;color:#fff;opacity:.9;transition:opacity .3s,background .3s;}',
    '.mark svg{width:15px;height:15px;flex:none;}',
    '.mark span{font-size:11px;font-weight:600;letter-spacing:.01em;white-space:nowrap;max-width:0;overflow:hidden;opacity:0;',
    '  transition:max-width .45s ' + EASE + ',opacity .3s,margin .45s;margin-right:0;}',
    '.roomy:hover .mark span{max-width:120px;opacity:1;margin-right:4px;}',
    '.card:hover .mark{background:rgba(22,17,13,.5);opacity:1;}',

    // buttons
    '.tools{position:absolute;z-index:2;top:8px;right:8px;display:flex;gap:6px;opacity:0;transform:translateY(-3px);',
    '  transition:opacity .25s,transform .35s ' + EASE + ';}',
    '.card:hover .tools,.card:focus-within .tools{opacity:1;transform:none;}',
    'button{all:unset;box-sizing:border-box;height:26px;padding:0 10px 0 8px;border-radius:13px;display:flex;align-items:center;gap:5px;cursor:pointer;',
    '  background:rgba(22,17,13,.44);-webkit-backdrop-filter:blur(10px) saturate(1.4);backdrop-filter:blur(10px) saturate(1.4);',
    '  box-shadow:0 0 0 .5px rgba(255,255,255,.2) inset;color:#fff;font:500 11.5px/1 ' + SANS_STACK + ';white-space:nowrap;transition:background .2s;}',
    'button svg{width:14px;height:14px;flex:none;}',
    'button:hover{background:rgba(22,17,13,.68);}',
    'button:focus-visible{outline:2px solid #fff;outline-offset:1px;}',
    '.narrow button{padding:0;width:26px;justify-content:center;}',
    '.narrow button span{display:none;}',

    // captions
    '.cap{position:absolute;z-index:1;left:0;right:0;bottom:0;padding:28px 12px 10px;pointer-events:none;',
    '  background:linear-gradient(to top,rgba(12,9,7,.66),rgba(12,9,7,.28) 55%,rgba(12,9,7,0));',
    '  opacity:0;transform:translateY(5px);transition:opacity .3s,transform .4s ' + EASE + ';}',
    '.one:hover .cap,.tile:hover .cap,.card:focus-within .cap{opacity:1;transform:none;}',
    '.nm{display:block;font-family:' + SERIF_STACK + ';font-weight:500;font-size:var(--nm,17px);letter-spacing:-.01em;line-height:1.1;',
    '  font-variation-settings:"opsz" 36;text-shadow:0 1px 12px rgba(0,0,0,.25);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
    '.wh{display:block;margin-top:2px;font-size:11.5px;opacity:.86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
    '.cr{display:block;margin-top:5px;font-size:10.5px;opacity:.72;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;pointer-events:auto;}',
    '.cr a{color:inherit;text-decoration:none;border-bottom:1px solid rgba(255,255,255,.35);}',
    '.cr a:hover{border-bottom-color:#fff;}',
    '.short .cap{padding:16px 8px 6px;}',
    '.short .wh,.short .cr{display:none;}',
    '.tiny .cap,.tiny .mark{display:none;}',
    '.tiny .tools{top:4px;right:4px;}',
    '.tiny button{height:22px;width:22px;}'
  ].join('\n');

  var sheet = null;
  function getSheet() {
    if (!sheet) {
      sheet = new CSSStyleSheet();
      sheet.replaceSync(CSS);
    }
    return sheet;
  }

  // Our two typefaces, registered once per page under names no site uses.
  var fontsStarted = false;
  function loadFonts(asset) {
    if (fontsStarted || typeof FontFace === 'undefined' || !document.fonts) return;
    fontsStarted = true;
    [[SERIF, 'fonts/fraunces.woff2', { weight: '300 700' }], [SANS, 'fonts/inter.woff2', { weight: '400 700' }]].forEach(function (f) {
      fetch(asset(f[1]))
        .then(function (r) { return r.arrayBuffer(); })
        .then(function (bytes) { return new FontFace(f[0], bytes, f[2]).load(); })
        .then(function (face) { document.fonts.add(face); })
        .catch(function () { /* the system fonts will do */ });
    });
  }

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html) e.innerHTML = html;
    return e;
  }

  function credit(item) {
    var who = item.by || 'Unknown';
    var lic = item.lic || '';
    return { text: who + (lic ? ' · ' + lic : ''), href: item.src || '' };
  }

  function describe(item) {
    var c = credit(item);
    return item.n + (item.wh ? ', ' + item.wh : '') + '. ' + (item.k === 'v' ? 'Film' : 'Photo') + ': ' + c.text;
  }

  /*
   * Build a card.
   *   choice: { dir: 'one'|'row'|'col', tiles: [{ w, h, item, x, y }] }  (pick.js)
   *   size:   { width, height } in CSS px
   *   opts: {
   *     asset(path) -> URL of a file shipped with the extension
   *     motion:     false for no drift and no film
   *     onAnother(), onShowAd(): button actions (a button is left out if its action is)
   *   }
   * Returns the host element, ready to insert into the page.
   */
  function renderCard(choice, size, opts) {
    loadFonts(opts.asset);
    var host = document.createElement('quokka-blocker');
    host.setAttribute('data-quokka-blocker', '');
    host.style.setProperty('width', size.width + 'px', 'important');
    host.style.setProperty('height', size.height + 'px', 'important');
    host.style.setProperty('max-width', '100%', 'important');
    host.style.setProperty('overflow', 'hidden', 'important');
    host.style.setProperty('box-sizing', 'border-box', 'important');
    host.style.setProperty('padding', '0', 'important');
    host.style.setProperty('border', '0', 'important');

    var shadow = host.attachShadow({ mode: 'closed' });
    var motion = opts.motion !== false;
    try {
      shadow.adoptedStyleSheets = [getSheet()];
    } catch (e) {
      shadow.appendChild(el('style', '', '')).textContent = CSS; // older browsers
    }

    var card = el('div', 'card ' + choice.dir);
    var w = size.width, h = size.height;
    var tileH = choice.dir === 'col' ? choice.tiles[0].h : h;
    if (w < 230 || h < 60) card.classList.add('narrow');
    if (w >= 420) card.classList.add('roomy'); // room for the name beside the buttons
    if (tileH < 120 || choice.tiles[0].w < 150) card.classList.add('short');
    if (h < 46 || w < 100) card.classList.add('tiny');
    if (motion) card.classList.add('drift');
    card.setAttribute('role', 'group');
    card.setAttribute('aria-label', 'Quokka Blocker: animals in place of an advert');

    var videos = [];
    choice.tiles.forEach(function (t, i) {
      var it = t.item;
      var tile = el('figure', 'tile');
      tile.style.width = choice.dir === 'col' ? '100%' : t.w + 'px';
      tile.style.height = choice.dir === 'row' ? '100%' : t.h + 'px';
      if (choice.dir === 'one') { tile.style.width = '100%'; tile.style.height = '100%'; }
      tile.style.setProperty('--c', it.c || '#3a302a');
      tile.style.setProperty('--x', t.x + '%');
      tile.style.setProperty('--y', t.y + '%');
      tile.style.setProperty('--ox', Math.round(((it.s[0] + it.s[2]) / 2) * 100) + '%');
      tile.style.setProperty('--oy', Math.round(((it.s[1] + it.s[3]) / 2) * 100) + '%');
      tile.style.setProperty('--d', (i * 0.09) + 's');
      tile.style.setProperty('--dur', (22 + (i * 7) % 9) + 's');
      tile.style.setProperty('--dd', (-(i * 5.3) % 11) + 's');
      var nameSize = Math.max(12.5, Math.min(19, Math.min(t.w / 11, t.h / 6)));
      tile.style.setProperty('--nm', nameSize.toFixed(1) + 'px');
      tile.title = describe(it);

      var pan = el('div', 'pan');
      var img = el('img', 'media still');
      img.alt = '';
      img.decoding = 'async';
      img.draggable = false;
      var reveal = function () { tile.classList.add('in'); };
      img.addEventListener('load', reveal);
      img.addEventListener('error', reveal);
      img.src = opts.asset(it.k === 'v' ? it.pf : it.f);
      if (img.complete && img.naturalWidth) reveal();
      pan.appendChild(img);

      if (it.k === 'v' && motion) {
        var v = el('video', 'media');
        v.muted = true;
        v.defaultMuted = true;
        v.loop = true;
        v.playsInline = true;
        v.setAttribute('playsinline', '');
        v.setAttribute('muted', '');
        v.preload = 'auto';
        v.disablePictureInPicture = true;
        v.setAttribute('aria-hidden', 'true');
        v.addEventListener('playing', function () { tile.classList.add('playing'); });
        v.src = opts.asset(it.f);
        pan.appendChild(v);
        videos.push(v);
        tile.classList.add('film');
      }
      tile.appendChild(pan);

      var cap = el('figcaption', 'cap');
      var nm = el('span', 'nm');
      nm.textContent = it.n;
      cap.appendChild(nm);
      if (it.wh) {
        var wh = el('span', 'wh');
        wh.textContent = it.wh;
        cap.appendChild(wh);
      }
      var c = credit(it);
      var cr = el('span', 'cr');
      var link = el('a');
      link.href = c.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = (it.k === 'v' ? 'Film: ' : 'Photo: ') + c.text;
      cr.appendChild(link);
      cap.appendChild(cr);
      tile.appendChild(cap);
      card.appendChild(tile);
    });

    var mark = el('div', 'mark', MARK + '<span>Quokka Blocker</span>');
    card.appendChild(mark);

    var tools = el('div', 'tools');
    if (opts.onAnother) {
      var another = el('button', '', ICON_SHUFFLE + '<span>Another</span>');
      another.title = 'Show a different animal';
      another.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); opts.onAnother(); });
      tools.appendChild(another);
    }
    if (opts.onShowAd) {
      var ad = el('button', '', ICON_AD + '<span>Show ad</span>');
      ad.title = 'Put the original advert back';
      ad.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); opts.onShowAd(); });
      tools.appendChild(ad);
    }
    card.appendChild(tools);
    shadow.appendChild(card);

    // Only what is on screen moves: films play and stills drift while visible.
    if (typeof IntersectionObserver !== 'undefined') {
      card.classList.add('paused');
      var io = new IntersectionObserver(function (entries) {
        var on = entries[entries.length - 1].isIntersecting;
        card.classList.toggle('paused', !on);
        videos.forEach(function (v) {
          if (on) {
            var p = v.play();
            if (p && p.catch) p.catch(function () { /* autoplay refused: the still stays */ });
          } else {
            v.pause();
          }
        });
      }, { threshold: 0.35 });
      io.observe(host);
      host.__qbStop = function () { io.disconnect(); videos.forEach(function (v) { v.pause(); v.removeAttribute('src'); v.load(); }); };
    }
    return host;
  }

  var api = { renderCard: renderCard, describe: describe, MARK: MARK };
  root.QB = Object.assign(root.QB || {}, api);
})(typeof globalThis !== 'undefined' ? globalThis : this);
