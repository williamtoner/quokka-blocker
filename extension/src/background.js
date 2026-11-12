/*
 * The background worker chooses the animals (so the library is loaded once,
 * not into every page), keeps the counts, and draws the toolbar badge.
 * Nothing leaves the browser.
 */
if (typeof importScripts === 'function') importScripts('library.js', 'pick.js'); // Firefox lists them in the manifest

var LIB = globalThis.QB_LIBRARY;
var PICK = globalThis.QBPick;

var PREFS = { quokkas: 'lots', animalsOff: {} };
var prefs = { quokkas: PREFS.quokkas, animalsOff: {} };
var recent = []; // pictures shown lately anywhere, so the same few do not keep coming round
var RECENT_MAX = 90;

chrome.storage.local.get(PREFS, function (stored) {
  prefs.quokkas = stored.quokkas || PREFS.quokkas;
  prefs.animalsOff = stored.animalsOff || {};
});

chrome.storage.onChanged.addListener(function (changes, area) {
  if (area !== 'local') return;
  if (changes.quokkas) prefs.quokkas = changes.quokkas.newValue || PREFS.quokkas;
  if (changes.animalsOff) prefs.animalsOff = changes.animalsOff.newValue || {};
});

function today() {
  var d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

// Counts are written one at a time so two pages swapping at once never lose one.
var queue = Promise.resolve();
function record(animals) {
  queue = queue.then(function () {
    return chrome.storage.local.get({ stats: null }).then(function (got) {
      var s = got.stats || { total: 0, day: today(), today: 0, since: today(), animals: {}, last: null };
      if (s.day !== today()) { s.day = today(); s.today = 0; }
      s.total += 1;
      s.today += 1;
      animals.forEach(function (a) { s.animals[a] = (s.animals[a] || 0) + 1; });
      return chrome.storage.local.set({ stats: s });
    });
  }).catch(function () { /* storage unavailable; the count is not worth an error */ });
}

function setBadge(tabId, count) {
  var text = count > 0 ? (count > 99 ? '99+' : String(count)) : '';
  chrome.action.setBadgeText({ tabId: tabId, text: text }).catch(function () {});
  chrome.action.setBadgeBackgroundColor({ tabId: tabId, color: '#2F5D50' }).catch(function () {});
  if (chrome.action.setBadgeTextColor) chrome.action.setBadgeTextColor({ tabId: tabId, color: '#FFFFFF' }).catch(function () {});
}

function choose(msg) {
  var w = Math.max(1, Math.min(4000, Number(msg.w) || 0));
  var h = Math.max(1, Math.min(4000, Number(msg.h) || 0));
  var avoid = (Array.isArray(msg.avoid) ? msg.avoid.slice(-120).map(String) : []).concat(recent);
  var choice = PICK.choose(LIB, w, h, {
    animals: prefs.animalsOff,
    quokkas: prefs.quokkas,
    motion: msg.motion !== false,
    videos: Number(msg.videos) || 0,
    avoid: avoid
  });
  if (!choice) return null;
  choice.tiles.forEach(function (t) {
    recent.push(t.item.id);
    if (recent.length > RECENT_MAX) recent.shift();
  });
  return choice;
}

chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
  if (!msg || !sender.tab) return;
  if (msg.type === 'qb-choose') {
    sendResponse(choose(msg));
    return;
  }
  if (msg.type === 'qb-swapped') {
    var animals = (Array.isArray(msg.animals) ? msg.animals : []).filter(function (a) { return typeof a === 'string'; }).slice(0, 8);
    record(animals);
    setBadge(sender.tab.id, msg.count | 0);
    return;
  }
  if (msg.type === 'qb-count') {
    setBadge(sender.tab.id, msg.count | 0);
  }
});

chrome.runtime.onInstalled.addListener(function (details) {
  if (details.reason === 'install') {
    chrome.tabs.create({ url: chrome.runtime.getURL('pages/welcome.html') });
  }
});
