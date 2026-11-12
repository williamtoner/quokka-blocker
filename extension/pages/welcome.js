(function () {
  'use strict';
  Array.prototype.forEach.call(document.querySelectorAll('[data-mark]'), function (m) { m.innerHTML = QB.MARK; });
  var used = [];
  var motion = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  function fill(slot) {
    var w = Number(slot.dataset.w) || Math.round(slot.getBoundingClientRect().width);
    var h = Number(slot.dataset.h);
    slot.style.width = slot.dataset.w !== '0' ? w + 'px' : '';
    slot.style.height = h + 'px';
    var choice = QBPick.choose(QB_LIBRARY, w, h, { avoid: used, motion: motion, quokkas: 'lots' });
    if (!choice) return;
    choice.tiles.forEach(function (t) { used.push(t.item.id); });
    var card = QB.renderCard(choice, { width: w, height: h }, {
      asset: function (p) { return '../' + p; },
      motion: motion,
      onAnother: function () { fill(slot); }
    });
    slot.textContent = '';
    slot.appendChild(card);
  }
  Array.prototype.forEach.call(document.querySelectorAll('.slot'), fill);
})();
