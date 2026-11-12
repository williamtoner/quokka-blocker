(function () {
  'use strict';

  var LIB = globalThis.QB_LIBRARY;
  var $ = function (id) { return document.getElementById(id); };
  var DEFAULTS = { enabled: true, pausedHosts: [], motion: true, quokkas: 'lots', animalsOff: {}, stats: null };
  var state = null;
  var host = '';

  $('mark').innerHTML = globalThis.QB.MARK;
  $('version').textContent = 'v' + chrome.runtime.getManifest().version;

  function save(patch) {
    for (var k in patch) state[k] = patch[k];
    chrome.storage.local.set(patch);
  }

  function centre(item) {
    return Math.round((item.s[0] + item.s[2]) * 50) + '% ' + Math.round((item.s[1] + item.s[3]) * 50) + '%';
  }

  // Where the subject sits in a crop of the given shape (as pick.js works it out, simplified).
  function position(item, aspect) {
    var ratio = item.w / item.h;
    var s = item.s;
    if (aspect >= ratio) {
      var vh = ratio / aspect;
      var top = Math.min(Math.max((s[1] + s[3]) / 2 - vh / 2, 0), 1 - vh);
      return '50% ' + (vh >= 1 ? 50 : top / (1 - vh) * 100) + '%';
    }
    var vw = aspect / ratio;
    var left = Math.min(Math.max((s[0] + s[2]) / 2 - vw / 2, 0), 1 - vw);
    return (vw >= 1 ? 50 : left / (1 - vw) * 100) + '% 50%';
  }

  function photosOf(animal) {
    return LIB.items.filter(function (i) { return i.a === animal; });
  }

  function heroPick() {
    var off = state.animalsOff || {};
    var pool = LIB.items.filter(function (i) {
      if (state.quokkas === 'only') return i.a === 'quokka';
      return !off[i.a] && i.q >= 8;
    });
    if (!pool.length) pool = LIB.items;
    // Fits a wide frame without losing the face.
    var wide = pool.filter(function (i) { return i.w / i.h >= 1.2 && (i.s[3] - i.s[1]) <= (i.w / i.h) / (328 / 188) + 0.04; });
    var list = wide.length ? wide : pool;
    if (state.quokkas !== 'some' && Math.random() < 0.5) {
      var q = list.filter(function (i) { return i.a === 'quokka'; });
      if (q.length) list = q;
    }
    return list[Math.floor(Math.random() * list.length)];
  }

  function drawHero() {
    var item = heroPick();
    if (!item) return;
    var img = $('hero-img');
    img.onload = function () { img.classList.add('in'); };
    img.style.objectPosition = position(item, 328 / 188);
    img.src = '../' + (item.k === 'v' ? item.pf : item.f);
    $('hero').style.background = item.c;
    $('hero-credit').textContent = item.n + ' · ' + item.by;
    $('hero-credit').title = (item.k === 'v' ? 'Film' : 'Photo') + ': ' + item.by + ', ' + item.lic;
  }

  function drawStats() {
    var s = state.stats || { total: 0, today: 0, day: '' };
    var total = s.total || 0;
    $('total').textContent = total.toLocaleString();
    $('total-label').textContent = total === 1 ? 'ad turned into an animal' : 'ads turned into animals';
    var d = new Date();
    var key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    var todayN = s.day === key ? s.today : 0;
    var bits = [];
    if (todayN) bits.push(todayN.toLocaleString() + ' today');
    var met = Object.keys(s.animals || {}).length;
    if (met) bits.push(met + (met === 1 ? ' kind of animal met' : ' kinds of animal met'));
    if (!total) bits.push('Ads you meet from now on become animals.');
    $('today').textContent = bits.join('  ·  ');
  }

  function drawToggles() {
    document.body.classList.toggle('disabled', !state.enabled);
    $('enabled').checked = state.enabled;
    $('motion').checked = state.motion;
    var paused = state.pausedHosts.indexOf(host) !== -1;
    $('site').checked = !paused;
    $('site').disabled = !host;
    $('host').textContent = host || 'this page';
    $('host-hint').textContent = !host ? 'Not available on this page'
      : paused ? 'Ads are left alone here' : 'Animals instead of ads here';
    Array.prototype.forEach.call(document.querySelectorAll('#quokkas button'), function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.v === state.quokkas));
    });
    $('animals-section').classList.toggle('only', state.quokkas === 'only');
  }

  function drawAnimals() {
    var grid = $('animals');
    grid.textContent = '';
    var ids = Object.keys(LIB.animals);
    var off = state.animalsOff || {};
    var on = ids.filter(function (a) { return !off[a]; }).length;
    $('animals-count').textContent = state.quokkas === 'only' ? 'Quokkas only' : on + ' of ' + ids.length + ' on';
    ids.forEach(function (a) {
      var items = photosOf(a).filter(function (i) { return i.k === 'p'; });
      if (!items.length) items = photosOf(a);
      // The portrait whose subject box is most nearly square makes the best round face.
      var face = items.slice().sort(function (x, y) {
        var sq = function (i) { var w = (i.s[2] - i.s[0]) * i.w, h = (i.s[3] - i.s[1]) * i.h; return Math.abs(Math.log(w / h)) - i.q * 0.08; };
        return sq(x) - sq(y);
      })[0];
      var b = document.createElement('button');
      b.className = 'pet' + (a === 'quokka' ? ' quokka' : '');
      b.setAttribute('aria-pressed', String(!off[a]));
      b.title = LIB.animals[a] + ' (' + photosOf(a).length + ')';
      var f = document.createElement('div');
      f.className = 'face';
      var img = document.createElement('img');
      img.alt = '';
      img.loading = 'lazy';
      img.src = '../' + (face.k === 'v' ? face.pf : face.f);
      img.style.objectPosition = centre(face);
      // zoom in on the subject so faces fill the circle
      var sw = face.s[2] - face.s[0], sh = (face.s[3] - face.s[1]) * face.h / face.w;
      var zoom = Math.min(3, Math.max(1, 0.8 / Math.max(sw, sh * (face.w / face.h > 1 ? 1 : face.w / face.h))));
      img.style.transform = 'scale(' + zoom.toFixed(2) + ')';
      img.style.transformOrigin = centre(face);
      f.appendChild(img);
      var label = document.createElement('span');
      label.textContent = LIB.animals[a];
      b.appendChild(f);
      b.appendChild(label);
      b.addEventListener('click', function () {
        var next = Object.assign({}, state.animalsOff || {});
        if (next[a]) delete next[a];
        else {
          if (on <= 1) return; // keep at least one
          next[a] = true;
        }
        save({ animalsOff: next });
        drawAnimals();
      });
      grid.appendChild(b);
    });
  }

  $('enabled').addEventListener('change', function (e) { save({ enabled: e.target.checked }); drawToggles(); });
  $('motion').addEventListener('change', function (e) { save({ motion: e.target.checked }); });
  $('site').addEventListener('change', function (e) {
    if (!host) return;
    var list = state.pausedHosts.filter(function (h) { return h !== host; });
    if (!e.target.checked) list.push(host);
    save({ pausedHosts: list });
    drawToggles();
  });
  Array.prototype.forEach.call(document.querySelectorAll('#quokkas button'), function (b) {
    b.addEventListener('click', function () { save({ quokkas: b.dataset.v }); drawToggles(); drawAnimals(); });
  });

  chrome.storage.onChanged.addListener(function (changes, area) {
    if (area === 'local' && changes.stats && state) { state.stats = changes.stats.newValue; drawStats(); }
  });

  chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    var tab = tabs && tabs[0];
    try {
      var u = new URL(tab.url);
      if (u.protocol === 'http:' || u.protocol === 'https:') host = u.hostname;
    } catch (e) { /* no address: a browser page */ }
    chrome.storage.local.get(DEFAULTS, function (stored) {
      state = stored;
      if (!Array.isArray(state.pausedHosts)) state.pausedHosts = [];
      drawHero();
      drawStats();
      drawToggles();
      drawAnimals();
    });
  });
})();
