(function () {
  'use strict';

  var dm = window.__datamap;
  if (!dm) return;

  function fetchCityThumbUrl(city) {
    var key = dm.util.normCity(city);
    if (!key) return Promise.resolve(null);
    if (dm.cityThumbCache[key]) return Promise.resolve(dm.cityThumbCache[key]);
    var q = String(city || '').trim();
    if (q && !/pakistan/i.test(q)) q = q + ' Pakistan';
    var api = 'https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(q);
    return fetch(api, { headers: { 'accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        var src = j && j.thumbnail && j.thumbnail.source ? String(j.thumbnail.source) : null;
        if (src) {
          dm.cityThumbCache[key] = src;
          return src;
        }
        // Fallback image so the popup still has a hero image.
        var fb = 'https://source.unsplash.com/600x400/?' + encodeURIComponent(String(city || '').trim() || 'city') + ',pakistan';
        dm.cityThumbCache[key] = fb;
        return fb;
      })
      .catch(function () {
        // Final fallback (no network / blocked).
        var fb = 'https://source.unsplash.com/600x400/?city,pakistan';
        dm.cityThumbCache[key] = fb;
        return fb;
      });
  }

  dm.util.applyThumbToContainer = function (containerEl, city) {
    if (!containerEl) return;
    var imgs = [];
    if (containerEl.querySelectorAll) {
      imgs = Array.prototype.slice.call(containerEl.querySelectorAll('img.map-card-img, img.map-card-hero'));
    }
    if (!imgs.length) return;
    var key = dm.util.normCity(city);
    if (!key) return;
    // Only fetch once per popup container.
    if (containerEl.getAttribute && containerEl.getAttribute('data-thumb-loaded') === '1') return;
    if (containerEl.setAttribute) containerEl.setAttribute('data-thumb-loaded', '1');
    fetchCityThumbUrl(city).then(function (src) {
      if (!src) return;
      imgs.forEach(function (img) {
        try {
          img.src = src;
          img.classList.remove('is-hidden');
        } catch (e) { /* ignore */ }
      });
    });
  };
})();

