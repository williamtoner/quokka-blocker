(function () {
  'use strict';
  var LIB = globalThis.QB_LIBRARY;
  var motion = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  var used = [];
  function asset(p) { return 'qb/' + p; }

  Array.prototype.forEach.call(document.querySelectorAll('[data-mark]'), function (m) { m.innerHTML = QB.MARK; });

  var animals = Object.keys(LIB.animals).length;
  document.getElementById('n-pictures').textContent = String(LIB.items.length);
  document.getElementById('n-animals').textContent = String(animals);

  function card(w, h, opts) {
    opts = opts || {};
    var choice = QBPick.choose(LIB, w, h, { avoid: used, motion: motion, quokkas: opts.quokkas || 'lots' });
    if (!choice) return null;
    choice.tiles.forEach(function (t) { used.push(t.item.id); });
    if (used.length > LIB.items.length - 12) used = used.slice(-12);
    return QB.renderCard(choice, { width: w, height: h }, { asset: asset, motion: motion, onAnother: opts.onAnother });
  }

  // Hero: three cards in a loose stack.
  var mosaic = document.getElementById('hero-mosaic');
  function hero() {
    mosaic.textContent = '';
    var W = mosaic.clientWidth, H = mosaic.clientHeight;
    var spots = [
      { x: 0.16, y: 0.02, w: 0.62, h: 0.56, q: 'only' },
      { x: 0.0, y: 0.52, w: 0.5, h: 0.42 },
      { x: 0.46, y: 0.44, w: 0.54, h: 0.52 }
    ];
    spots.forEach(function (s, i) {
      var w = Math.round(s.w * W), h = Math.round(s.h * H);
      var holder = document.createElement('div');
      holder.className = 'tile';
      holder.style.cssText = 'left:' + s.x * W + 'px;top:' + s.y * H + 'px;width:' + w + 'px;height:' + h + 'px;z-index:' + (i === 0 ? 1 : 2);
      var refill = function () {
        var c = card(w, h, { quokkas: s.q, onAnother: refill });
        if (c) { holder.textContent = ''; holder.appendChild(c); }
      };
      refill();
      mosaic.appendChild(holder);
    });
  }

  // Demo: the same mock page with ads or with animals.
  var mode = 'animals';
  function fakeAd(slot) {
    var ad = document.createElement('div');
    ad.className = 'fake-ad';
    ad.innerHTML = '<b></b><i>BUY NOW ›</i>';
    ad.querySelector('b').textContent = slot.dataset.ad;
    return ad;
  }
  function demo() {
    Array.prototype.forEach.call(document.querySelectorAll('.page-mock .slot'), function (slot) {
      slot.textContent = '';
      slot.style.height = slot.dataset.h + 'px';
      if (slot.dataset.w !== '0') slot.style.width = slot.dataset.w + 'px';
      if (!slot.offsetParent) return; // hidden on small screens
      var w = Math.round(slot.getBoundingClientRect().width), h = Number(slot.dataset.h);
      if (mode === 'ads') { slot.appendChild(fakeAd(slot)); return; }
      var refill = function () {
        var c = card(w, h, { onAnother: refill });
        if (c) { slot.textContent = ''; slot.appendChild(c); }
      };
      refill();
    });
  }
  Array.prototype.forEach.call(document.querySelectorAll('.demo .seg button'), function (b) {
    b.addEventListener('click', function () {
      mode = b.dataset.mode;
      Array.prototype.forEach.call(document.querySelectorAll('.demo .seg button'), function (o) { o.setAttribute('aria-pressed', String(o === b)); });
      demo();
    });
  });

  // The animals, rolling past.
  function marquee() {
    var best = {};
    LIB.items.forEach(function (i) {
      if (i.k !== 'p' || i.q < 8) return;
      (best[i.a] = best[i.a] || []).push(i);
    });
    var picks = [];
    Object.keys(best).forEach(function (a) { picks = picks.concat(best[a].slice(0, a === 'quokka' ? 3 : 1)); });
    picks.sort(function () { return Math.random() - 0.5; });
    picks = picks.slice(0, 28);
    var track = document.querySelector('.track');
    picks.concat(picks).forEach(function (i) {
      var fig = document.createElement('figure');
      var wide = i.w / i.h > 1.25 && (i.s[3] - i.s[1]) < 0.8;
      fig.className = 'pic' + (wide ? ' wide' : '');
      fig.style.background = i.c;
      var img = document.createElement('img');
      img.loading = 'lazy';
      img.alt = i.n;
      img.src = asset(i.f);
      img.style.objectPosition = Math.round((i.s[0] + i.s[2]) * 50) + '% ' + Math.round((i.s[1] + i.s[3]) * 50) + '%';
      var cap = document.createElement('figcaption');
      cap.innerHTML = '<b></b><span></span>';
      cap.querySelector('b').textContent = i.n;
      cap.querySelector('span').textContent = 'Photo: ' + i.by + ' · ' + i.lic;
      fig.appendChild(img);
      fig.appendChild(cap);
      track.appendChild(fig);
    });
  }

  hero();
  demo();
  marquee();
  var lastW = innerWidth, t = null;
  addEventListener('resize', function () {
    if (Math.abs(innerWidth - lastW) < 40) return;
    lastW = innerWidth;
    clearTimeout(t);
    t = setTimeout(function () { hero(); demo(); }, 250);
  });
})();
