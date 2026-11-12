(function () {
  'use strict';
  var LIB = globalThis.QB_LIBRARY;
  Array.prototype.forEach.call(document.querySelectorAll('[data-mark]'), function (m) { m.innerHTML = globalThis.QB.MARK; });

  var list = document.getElementById('list');
  var people = {};
  LIB.items.forEach(function (i) { people[i.by] = true; });
  document.getElementById('intro').textContent =
    'All ' + LIB.items.length + ' pictures in Quokka Blocker were shared under open licences by the ' +
    Object.keys(people).length + ' photographers and film-makers named here, on Wikimedia Commons and Flickr. ' +
    'Thank you all. Each links to its original and its licence.';

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }

  function link(href, text) {
    var a = el('a', '', text);
    a.href = href;
    a.target = '_blank';
    a.rel = 'noopener';
    return a;
  }

  Object.keys(LIB.animals).forEach(function (animal) {
    var items = LIB.items.filter(function (i) { return i.a === animal; });
    var sec = el('section', 'animal');
    var h = el('h2', '', LIB.animals[animal]);
    h.appendChild(el('small', '', items.length === 1 ? '1 picture' : items.length + ' pictures'));
    sec.appendChild(h);
    var grid = el('div', 'shots');
    items.forEach(function (i) {
      var card = el('div', 'shot');
      var fig = el('figure');
      fig.style.background = i.c;
      var img = el('img');
      img.loading = 'lazy';
      img.alt = i.n;
      img.src = '../' + (i.k === 'v' ? i.pf : i.f);
      img.style.objectPosition = Math.round((i.s[0] + i.s[2]) * 50) + '% ' + Math.round((i.s[1] + i.s[3]) * 50) + '%';
      fig.appendChild(img);
      if (i.k === 'v') fig.appendChild(el('span', 'film', 'Film'));
      card.appendChild(fig);
      var meta = el('div', 'meta');
      meta.appendChild(el('div', 'who', i.by));
      if (i.wh) meta.appendChild(el('div', '', i.wh));
      var line = el('div');
      line.appendChild(i.lu ? link(i.lu, i.lic) : document.createTextNode(i.lic));
      line.appendChild(document.createTextNode(' · '));
      line.appendChild(link(i.src, 'Original'));
      meta.appendChild(line);
      card.appendChild(meta);
      grid.appendChild(card);
    });
    sec.appendChild(grid);
    list.appendChild(sec);
  });
})();
