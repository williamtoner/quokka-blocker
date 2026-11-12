/*
 * Unit tests for the picker and the library. Run: node test/pick.test.js
 */
'use strict';
var assert = require('assert');
var fs = require('fs');
var path = require('path');

var ROOT = path.join(__dirname, '..');
require(path.join(ROOT, 'extension/src/library.js'));
var P = require(path.join(ROOT, 'extension/src/pick.js'));
var LIB = globalThis.QB_LIBRARY;

var failures = 0;
function test(name, fn) {
  try { fn(); console.log('ok   ' + name); } catch (e) { failures++; console.log('FAIL ' + name + '\n     ' + e.message); }
}

function seeded(seed) {
  return function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
}

// Standard IAB sizes plus some odd ones seen in the wild.
var SIZES = [[300, 250], [336, 280], [728, 90], [970, 90], [970, 250], [160, 600], [120, 600], [300, 600],
  [320, 50], [320, 100], [468, 60], [250, 250], [200, 200], [300, 1050], [640, 360], [1200, 280], [234, 60], [180, 150]];

test('crop keeps a centred subject in a square', function () {
  var it = { w: 1000, h: 500, s: [0.4, 0.2, 0.6, 0.8] };
  var c = P.crop(it, 1);
  assert(c.fit);
  assert.strictEqual(c.x, 50);
});

test('crop slides to an off-centre subject and clamps at the edge', function () {
  var it = { w: 1000, h: 500, s: [0.0, 0.2, 0.2, 0.8] };
  var c = P.crop(it, 1);
  assert(c.fit);
  assert.strictEqual(c.x, 0);
});

test('crop refuses a shape that would cut the subject', function () {
  var it = { w: 1000, h: 1000, s: [0.1, 0.1, 0.9, 0.9] };
  assert(!P.crop(it, 4).fit);
});

test('banners become rows, towers become columns', function () {
  assert.strictEqual(P.layouts(728, 90)[0].dir, 'row');
  assert.strictEqual(P.layouts(160, 600)[0].dir, 'col');
  assert.strictEqual(P.layouts(300, 250).length, 1);
  assert.strictEqual(P.layouts(300, 600)[0].dir, 'one');
  P.layouts(728, 90)[0].tiles.forEach(function (t) { assert(t.w >= 64); });
});

test('library entries are complete and their files exist', function () {
  assert(LIB.items.length > 0, 'empty library');
  var ids = {};
  LIB.items.forEach(function (i) {
    assert(!ids[i.id], 'duplicate id ' + i.id);
    ids[i.id] = true;
    ['id', 'a', 'n', 'k', 'f', 'w', 'h', 's', 'by', 'lic', 'src', 'c'].forEach(function (k) {
      assert(i[k] !== undefined && i[k] !== '', i.id + ' lacks ' + k);
    });
    assert(LIB.animals[i.a], i.id + ': unknown animal ' + i.a);
    assert(fs.existsSync(path.join(ROOT, 'extension', i.f)), i.id + ': missing ' + i.f);
    if (i.k === 'v') assert(fs.existsSync(path.join(ROOT, 'extension', i.pf)), i.id + ': missing poster');
    var s = i.s;
    assert(s.length === 4 && s[0] >= 0 && s[1] >= 0 && s[2] <= 1 && s[3] <= 1 && s[0] < s[2] && s[1] < s[3], i.id + ': bad subject box');
    assert(/^(CC0|CC BY(-SA)? \d\.\d|Public domain)/i.test(i.lic), i.id + ': licence ' + i.lic);
    assert(!/\bNC\b|\bND\b/.test(i.lic), i.id + ': licence ' + i.lic);
    assert(/^https:\/\//.test(i.src), i.id + ': source ' + i.src);
  });
});

test('pictures are never blown up past 1.6x', function () {
  var rand = seeded(17);
  [[318, 1427], [970, 250], [692, 713], [1200, 280]].forEach(function (sz) {
    for (var n = 0; n < 20; n++) {
      P.choose(LIB, sz[0], sz[1], { rand: rand }).tiles.forEach(function (t) {
        assert(Math.max(t.w / t.item.w, t.h / t.item.h) <= 1.6, sz.join('x') + ' ' + t.item.id);
      });
    }
  });
});

test('every common ad size gets animals, distinct within a slot, faces kept', function () {
  var rand = seeded(7);
  SIZES.forEach(function (sz) {
    for (var n = 0; n < 25; n++) {
      var c = P.choose(LIB, sz[0], sz[1], { rand: rand, motion: true });
      assert(c, 'nothing for ' + sz.join('x'));
      var seen = {};
      c.tiles.forEach(function (t) {
        assert(!seen[t.item.id], 'repeat in ' + sz.join('x'));
        seen[t.item.id] = true;
        assert(P.crop(t.item, t.w / t.h).cut <= 0.3, sz.join('x') + ': ' + t.item.id + ' loses too much');
        if (t.item.k === 'v') assert.strictEqual(c.dir, 'one', 'film in a tiled slot');
      });
    }
  });
});

test('films only with motion on, and never past two per page', function () {
  var rand = seeded(3);
  for (var n = 0; n < 200; n++) {
    var a = P.choose(LIB, 300, 250, { rand: rand, motion: false });
    a.tiles.forEach(function (t) { assert(t.item.k !== 'v'); });
    var b = P.choose(LIB, 300, 250, { rand: rand, motion: true, videos: 2 });
    b.tiles.forEach(function (t) { assert(t.item.k !== 'v'); });
  }
});

test('"only" means only quokkas; switched-off animals stay away', function () {
  var rand = seeded(11);
  var off = {};
  Object.keys(LIB.animals).forEach(function (a, i) { if (i % 2) off[a] = true; });
  for (var n = 0; n < 100; n++) {
    P.choose(LIB, 300, 250, { rand: rand, quokkas: 'only' }).tiles.forEach(function (t) { assert.strictEqual(t.item.a, 'quokka'); });
    P.choose(LIB, 728, 90, { rand: rand, animals: off, quokkas: 'some' }).tiles.forEach(function (t) { assert(!off[t.item.a], t.item.a); });
  }
});

test('avoid list is honoured when there is a choice', function () {
  var rand = seeded(5);
  var first = P.choose(LIB, 300, 250, { rand: rand, motion: false }).tiles[0].item.id;
  for (var n = 0; n < 50; n++) {
    var again = P.choose(LIB, 300, 250, { rand: rand, motion: false, avoid: [first] }).tiles[0].item.id;
    assert.notStrictEqual(again, first);
  }
});

test('variety: a 300x250 slot sees many animals', function () {
  var rand = seeded(13);
  var seen = {};
  for (var n = 0; n < 400; n++) seen[P.choose(LIB, 300, 250, { rand: rand }).tiles[0].item.a] = true;
  var want = Math.min(Object.keys(LIB.animals).length, 20);
  assert(Object.keys(seen).length >= want * 0.8, Object.keys(seen).length + ' of ' + Object.keys(LIB.animals).length);
});

if (failures) { console.log(failures + ' failed'); process.exit(1); }
console.log('all passed');
