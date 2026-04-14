(function () {
  'use strict';

  var dm = window.__datamap;
  if (!dm) return;

  function fetchCityThumbUrl(city) {
    var key = dm.util.normCity(city);
    if (!key) return Promise.resolve(null);
    if (dm.cityThumbCache[key]) return Promise.resolve(dm.cityThumbCache[key]);
    var api = 'https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(String(city || '').trim());
    return fetch(api, { headers: { 'accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        var src = j && j.thumbnail && j.thumbnail.source ? String(j.thumbnail.source) : null;
        if (src) dm.cityThumbCache[key] = src;
        return src;
      })
      .catch(function () { return null; });
  }

  dm.util.applyThumbToContainer = function (containerEl, city) {
    if (!containerEl) return;
    var img = containerEl.querySelector && containerEl.querySelector('img.map-card-img');
    if (!img) return;
    var key = dm.util.normCity(city);
    if (!key) return;
    if (img.getAttribute('data-loaded') === '1') return;
    img.setAttribute('data-loaded', '1');
    fetchCityThumbUrl(city).then(function (src) {
      if (!src) {
        img.classList.add('is-hidden');
        return;
      }
      img.src = src;
      img.classList.remove('is-hidden');
    });
  };
})();

