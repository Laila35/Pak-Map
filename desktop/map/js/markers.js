(function () {
  'use strict';

  var dm = window.__datamap;
  if (!dm || !dm.map) return;

  function __escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function displayTitle(p) {
    var c = String(p.city || '').trim();
    if (c) return c;
    var id = String(p.id || '');
    return id.length >= 4 ? 'Target ' + id.substring(0, 8) : 'Target ' + id;
  }

  function tierFor(v, vmin, vmax) {
    v = Number(v);
    if (!isFinite(v) || vmax <= vmin) return 'TIER II';
    var t = (v - vmin) / (vmax - vmin);
    if (t >= 0.66) return 'TIER I';
    if (t >= 0.33) return 'TIER II';
    return 'TIER III';
  }

  function formatVal(p) {
    if (p.value == null || p.value === '') return '—';
    return Number(p.value).toLocaleString();
  }

  // ---- Wikipedia summary fetch (image + short extract; cached) ----
  var __wikiSummaryMem = {}; // lower(title) -> { imgUrl: string|null, extract: string|null }
  function __wikiKey(t) { return String(t || '').trim().toLowerCase(); }
  async function getWikiSummary(title) {
    var raw = String(title || '').trim();
    if (!raw) return { imgUrl: null, extract: null };
    var k = __wikiKey(raw);
    if (__wikiSummaryMem[k]) return __wikiSummaryMem[k];

    try {
      var url = 'https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(raw);
      var res = await fetch(url, { headers: { accept: 'application/json' } });
      if (!res || !res.ok) {
        __wikiSummaryMem[k] = { imgUrl: null, extract: null };
        return __wikiSummaryMem[k];
      }
      var data = await res.json();
      var imgUrl =
        data && data.thumbnail && typeof data.thumbnail.source === 'string'
          ? String(data.thumbnail.source)
          : null;
      var extract = data && typeof data.extract === 'string' ? String(data.extract) : null;
      // Keep it short inside a Leaflet popup.
      if (extract && extract.length > 220) extract = extract.slice(0, 217) + '...';

      __wikiSummaryMem[k] = { imgUrl: imgUrl, extract: extract };
      return __wikiSummaryMem[k];
    } catch (e) {
      __wikiSummaryMem[k] = { imgUrl: null, extract: null };
      return __wikiSummaryMem[k];
    }
  }

  function titleMixHtml(title) {
    var t = String(title || '').trim();
    if (!t) return '';
    var parts = t.split(/\s+/);
    if (parts.length === 1) {
      return '<span class="dm-popup-title-gold">' + __escapeHtml(t) + '</span>';
    }
    var first = parts.shift();
    var rest = parts.join(' ');
    return (
      '<span class="dm-popup-title-gold">' + __escapeHtml(first) + '</span>' +
      ' ' +
      '<span class="dm-popup-title-white">' + __escapeHtml(rest) + '</span>'
    );
  }

  function popupHtml(p, vmin, vmax, wiki) {
    wiki = wiki || {};
    var lat = Number(p.lat).toFixed(4);
    var lng = Number(p.lng).toFixed(4);
    var val = formatVal(p);
    var tier = tierFor(Number(p.value), vmin, vmax);
    var title = displayTitle(p);
    var imgTop = (function () {
      if (wiki && wiki.imgUrl) {
        return (
          '<img class="dm-popup-img" src="' + __escapeHtml(wiki.imgUrl) + '" alt="" referrerpolicy="no-referrer" />'
        );
      }
      return '<div class="dm-popup-noimg">No image available</div>';
    })();
    var desc = wiki && wiki.extract ? String(wiki.extract) : '';
    return (
      '<div class="dm-popup">' +
        '<div class="dm-popup-pad">' +
          '<div class="dm-popup-tier">' + __escapeHtml(tier) + '</div>' +
          '<div class="dm-popup-media">' + imgTop + '</div>' +
          '<div class="dm-popup-title">' + titleMixHtml(title) + '</div>' +
          (desc ? '<div class="dm-popup-desc">' + __escapeHtml(desc) + '</div>' : '<div class="dm-popup-desc dm-popup-desc-muted">No description available</div>') +
          '<div class="dm-popup-meta">Lat: ' + __escapeHtml(lat) + ' &nbsp;·&nbsp; Lng: ' + __escapeHtml(lng) + '</div>' +
          '<div class="dm-popup-value">Population: <span class="dm-popup-value-num">' + __escapeHtml(val) + '</span></div>' +
        '</div>' +
      '</div>'
    );
  }

  function schedulePoisUpdate() {
    if (typeof window.__datamapSchedulePoisUpdate === 'function') {
      window.__datamapSchedulePoisUpdate();
    }
  }

  // ---- Search result popup (Wikipedia image + caching) ----
  function searchPopupHtml(title, kind, lat, lng, wiki, loading) {
    wiki = wiki || {};
    var imgTop = loading
      ? '<div class="dm-popup-noimg">Loading image...</div>'
      : (wiki.imgUrl
          ? '<img class="dm-popup-img" src="' + __escapeHtml(wiki.imgUrl) + '" alt="" referrerpolicy="no-referrer" />'
          : '<div class="dm-popup-noimg">No image available</div>');
    var desc = wiki.extract ? String(wiki.extract) : '';
    return (
      '<div class="dm-popup">' +
        '<div class="dm-popup-pad">' +
          '<div class="dm-popup-media">' + imgTop + '</div>' +
          '<div class="dm-popup-title">' + titleMixHtml(title) + '</div>' +
          (desc ? '<div class="dm-popup-desc">' + __escapeHtml(desc) + '</div>' : '<div class="dm-popup-desc dm-popup-desc-muted">No description available</div>') +
          '<div class="dm-popup-meta">Lat: ' + __escapeHtml(Number(lat).toFixed(4)) + ' &nbsp;·&nbsp; Lng: ' + __escapeHtml(Number(lng).toFixed(4)) + '</div>' +
          (kind ? '<div class="dm-popup-meta">Type: <span class="dm-popup-meta-strong">' + __escapeHtml(kind) + '</span></div>' : '') +
        '</div>' +
      '</div>'
    );
  }

  // Exposed: called by Python after geocoding a query.
  window.showSearchResult = function (lat, lng, query, kind) {
    lat = Number(lat); lng = Number(lng);
    if (!isFinite(lat) || !isFinite(lng)) return;
    var title = String(query || '').trim() || 'Search result';
    var k = String(kind || '').trim();

    if (!dm.__searchMarker) {
      dm.__searchMarker = L.marker([lat, lng], {
        icon: dm.util.placePinDivIcon(true, dm.ACCENT),
        keyboard: false,
        riseOnHover: true
      }).addTo(dm.markerLayer);
    } else {
      dm.__searchMarker.setLatLng([lat, lng]);
      dm.__searchMarker.setIcon(dm.util.placePinDivIcon(true, dm.ACCENT));
    }

    var m = dm.__searchMarker;
    m.__wikiApplied = false;
    m.__wikiPromise = null;

    m.bindPopup(searchPopupHtml(title, k, lat, lng, null, true), {
      className: 'map-popup-card',
      maxWidth: 340,
      autoPan: true,
      autoPanPadding: [28, 28]
    });
    try { m.openPopup(); } catch (e) { /* ignore */ }

    m.__wikiPromise = getWikiSummary(title);
    m.__wikiPromise.then(function (wiki) {
      m.setPopupContent(searchPopupHtml(title, k, lat, lng, wiki, false));
      m.__wikiApplied = true;
    }).catch(function () { /* ignore */ });
  };

  /**
   * @param {Array} data - [{ id, city, lat, lng, value }, ...]
   * @param {string|null|undefined} selectedId
   */
  window.addMarkers = function (data, selectedId) {
    dm.markerLayer.clearLayers();
    dm.markers = {};
    if (!data || !data.length) return;

    var vals = data.map(function (p) { return Number(p.value); }).filter(isFinite);
    var vmin = vals.length ? Math.min.apply(null, vals) : 0;
    var vmax = vals.length ? Math.max.apply(null, vals) : 1;

    var sel = selectedId != null && String(selectedId) !== '' ? String(selectedId) : null;
    var bounds = L.latLngBounds([]);

    data.forEach(function (p) {
      var pid = String(p.id);
      var lat = Number(p.lat);
      var lng = Number(p.lng);
      if (!isFinite(lat) || !isFinite(lng)) return;

      var isSel = sel && pid === sel;
      var fill = dm.util.pinColorForValue(p.value, vmin, vmax);

      var m = L.marker([lat, lng], {
        icon: dm.util.placePinDivIcon(!!isSel, fill),
        keyboard: false,
        riseOnHover: true
      }).addTo(dm.markerLayer);

      m.__pinFill = fill;
      m.__wikiApplied = false;
      m.__wikiPromise = null;
      bounds.extend([lat, lng]);

      // Bind exactly once. We update content in-place after fetching Wikipedia.
      m.bindPopup(popupHtml(p, vmin, vmax, null), {
        className: 'map-popup-card',
        maxWidth: 340,
        autoPan: true,
        autoPanPadding: [28, 28]
      });
      m.on('popupopen', function (e) {
        // Fetch once per marker; update this same popup (no duplicate bind/open).
        if (m.__wikiApplied) return;
        if (!m.__wikiPromise) {
          m.__wikiPromise = getWikiSummary(displayTitle(p));
        }
        m.__wikiPromise.then(function (wiki) {
          // Only update if this marker still has a popup instance.
          try { m.setPopupContent(popupHtml(p, vmin, vmax, wiki)); } catch (e2) { /* ignore */ }
          m.__wikiApplied = true;
        }).catch(function () { /* ignore */ });
      });

      m.on('click', function () {
        window.focusMarker(pid, { fly: true });
        if (window.bridge && typeof window.bridge.markerClicked === 'function') {
          window.bridge.markerClicked(pid);
        }
      });

      dm.markers[pid] = m;
    });

    if (bounds.isValid()) {
      dm.map.flyToBounds(bounds, { padding: [52, 52], duration: 1.5, maxZoom: 16 });
    }
    schedulePoisUpdate();
  };

  window.highlightMarkerOnMap = function (id, options) {
    options = options || {};
    var fly = options.fly !== false;
    var sel = id != null && id !== '' ? String(id) : null;
    Object.keys(dm.markers).forEach(function (k) {
      var m = dm.markers[k];
      var isSel = sel && k === sel;
      var fill = m.__pinFill || dm.ACCENT;
      m.setIcon(dm.util.placePinDivIcon(!!isSel, fill));
    });
    if (!sel) {
      dm.map.closePopup();
      return;
    }
    if (dm.markers[sel] && fly) {
      window.focusMarker(sel, { fly: true });
    } else if (dm.markers[sel]) {
      try { dm.markers[sel].bringToFront(); } catch (e) { /* ignore */ }
    }
  };

  window.focusMarker = function (id, opts) {
    opts = opts || {};
    var fly = opts.fly !== false;
    var key = String(id);
    var m = dm.markers[key];
    if (!m) return;
    if (fly) {
      var targetZoom = Math.max(dm.map.getZoom(), 17);
      dm.map.flyTo(m.getLatLng(), targetZoom, { duration: 1.5 });
      dm.map.once('moveend', function () { m.openPopup(); });
    } else {
      m.openPopup();
    }
  };

  window.flyToLocation = function (lat, lng, zoom) {
    zoom = zoom == null ? 17 : Number(zoom);
    if (!isFinite(zoom)) zoom = 17;
    dm.map.flyTo([lat, lng], zoom, { duration: 1.5 });
    schedulePoisUpdate();
  };

  window.fitMapToBounds = function (south, west, north, east) {
    var b = L.latLngBounds(L.latLng(south, west), L.latLng(north, east));
    if (!b.isValid()) return;
    dm.map.flyToBounds(b, { padding: [48, 48], duration: 1.5, maxZoom: 16 });
    schedulePoisUpdate();
  };
})();

