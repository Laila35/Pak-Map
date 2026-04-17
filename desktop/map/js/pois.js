(function () {
  'use strict';

  var dm = window.__datamap;
  if (!dm || !dm.map) return;

  function poiKey(bounds, zoom) {
    function r(x) { return Math.round(x * 200) / 200; } // ~0.005 deg
    return [
      Math.floor(zoom),
      r(bounds.getSouth()),
      r(bounds.getWest()),
      r(bounds.getNorth()),
      r(bounds.getEast())
    ].join('|');
  }

  function labelForPoi(tags) {
    if (!tags) return 'POI';
    if (tags.amenity === 'hospital') return 'Hospital';
    if (tags.amenity === 'school') return 'School';
    if (tags.office) return 'Office';
    if (tags.tourism) return 'Explore';
    return 'POI';
  }

  function iconSpecForElement(e) {
    var tags = (e && e.tags) || {};
    // Motorways / National highways from ways
    var ref = tags.ref ? String(tags.ref) : '';
    if (ref && /^M-/i.test(ref)) return { cls: 'tag-icon tag-m', label: ref.toUpperCase() };
    if (ref && /^N/i.test(ref)) return { cls: 'tag-icon tag-n', label: ref.toUpperCase() };

    // Hospitals as H
    if (tags.amenity === 'hospital') return { cls: 'tag-icon tag-h is-round', label: 'H' };

    // Exploring points in purple
    if (tags.tourism && /^(attraction|viewpoint|museum|zoo|theme_park)$/i.test(String(tags.tourism))) {
      return { cls: 'tag-icon tag-exp is-round', label: 'E' };
    }
    if (tags.office) return { cls: 'tag-icon tag-exp is-round', label: 'E' };

    // Default small dot-like tag (grey) if needed
    return { cls: 'tag-icon is-round tag-generic', label: '📍' };
  }

  function divIconFor(spec) {
    return L.divIcon({
      className: 'tag-icon-wrap',
      html: '<div class="' + spec.cls + '">' + String(spec.label || '') + '</div>',
      iconSize: [1, 1],
      iconAnchor: [14, 11],
      popupAnchor: [0, -14]
    });
  }

  function elementLatLng(e) {
    if (!e) return null;
    if (e.type === 'node' && isFinite(e.lat) && isFinite(e.lon)) return L.latLng(e.lat, e.lon);
    if (e.type === 'way' && e.center && isFinite(e.center.lat) && isFinite(e.center.lon)) return L.latLng(e.center.lat, e.center.lon);
    return null;
  }

  // ---- Wikipedia thumbnail fetch (cached) for POI popups ----
  var wikiSummaryCache = {}; // lower(query) -> { imgUrl: string|null, extract: string|null }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function titleMixHtml(title) {
    var t = String(title || '').trim();
    if (!t) return '';
    var parts = t.split(/\s+/);
    if (parts.length === 1) {
      return '<span class="dm-popup-title-gold">' + escapeHtml(t) + '</span>';
    }
    var first = parts.shift();
    var rest = parts.join(' ');
    return (
      '<span class="dm-popup-title-gold">' + escapeHtml(first) + '</span>' +
      ' ' +
      '<span class="dm-popup-title-white">' + escapeHtml(rest) + '</span>'
    );
  }

  async function getWikiSummary(query) {
    try {
      var raw = String(query || '').trim();
      if (!raw) return { imgUrl: null, extract: null };

      var key = raw.toLowerCase();
      if (wikiSummaryCache[key]) return wikiSummaryCache[key];

      var url = 'https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(raw);
      var res = await fetch(url, { headers: { accept: 'application/json' } });
      if (!res || !res.ok) {
        wikiSummaryCache[key] = { imgUrl: null, extract: null };
        return wikiSummaryCache[key];
      }
      var data = await res.json();
      var imgUrl =
        data && data.thumbnail && typeof data.thumbnail.source === 'string'
          ? String(data.thumbnail.source)
          : null;
      var extract = data && typeof data.extract === 'string' ? String(data.extract) : null;
      if (extract && extract.length > 220) extract = extract.slice(0, 217) + '...';

      wikiSummaryCache[key] = { imgUrl: imgUrl, extract: extract };
      return wikiSummaryCache[key];
    } catch (err) {
      return { imgUrl: null, extract: null };
    }
  }

  function poiPopupHtml(placeName, kind, wiki, isLoading, ll, tags) {
    wiki = wiki || {};
    var imgTop = isLoading
      ? '<div class="dm-popup-noimg">Loading image...</div>'
      : (wiki.imgUrl
          ? '<img class="dm-popup-img" src="' + escapeHtml(wiki.imgUrl) + '" alt="" referrerpolicy="no-referrer" />'
          : '<div class="dm-popup-noimg">No image available</div>');
    var desc = wiki.extract ? String(wiki.extract) : '';

    var lat = ll && isFinite(ll.lat) ? Number(ll.lat).toFixed(4) : '';
    var lng = ll && isFinite(ll.lng) ? Number(ll.lng).toFixed(4) : '';
    var addrParts = [];
    if (tags) {
      if (tags['addr:housenumber']) addrParts.push(String(tags['addr:housenumber']));
      if (tags['addr:street']) addrParts.push(String(tags['addr:street']));
      if (tags['addr:suburb']) addrParts.push(String(tags['addr:suburb']));
      if (tags['addr:city']) addrParts.push(String(tags['addr:city']));
      if (tags['addr:district']) addrParts.push(String(tags['addr:district']));
      if (tags['addr:state']) addrParts.push(String(tags['addr:state']));
    }
    var address = addrParts.length ? addrParts.join(', ') : '';
    var hours = tags && tags.opening_hours ? String(tags.opening_hours) : '';
    var phone = tags && (tags.phone || tags['contact:phone']) ? String(tags.phone || tags['contact:phone']) : '';
    var website = tags && (tags.website || tags['contact:website']) ? String(tags.website || tags['contact:website']) : '';

    function row(label, value, isLink) {
      if (!value) return '';
      var v = escapeHtml(value);
      if (isLink) {
        var href = value;
        if (!/^https?:\/\//i.test(href)) href = 'https://' + href;
        v = '<a href="' + escapeHtml(href) + '" target="_blank" rel="noreferrer noopener" style="color:#FFD700;text-decoration:none">' + v + '</a>';
      }
      return '<div class="dm-popup-meta">' + escapeHtml(label) + ': <span class="dm-popup-meta-strong">' + v + '</span></div>';
    }

    return (
      '<div class="dm-popup">' +
        '<div class="dm-popup-pad">' +
          '<div class="dm-popup-media">' + imgTop + '</div>' +
          '<div class="dm-popup-title">' + titleMixHtml(placeName) + '</div>' +
          (desc ? '<div class="dm-popup-desc">' + escapeHtml(desc) + '</div>' : '<div class="dm-popup-desc dm-popup-desc-muted">No description available</div>') +
          (kind ? '<div class="dm-popup-meta">Type: <span class="dm-popup-meta-strong">' + escapeHtml(kind) + '</span></div>' : '') +
          row('Lat', lat, false) +
          row('Lng', lng, false) +
          row('Address', address, false) +
          row('Hours', hours, false) +
          row('Phone', phone, false) +
          row('Website', website, true) +
        '</div>' +
      '</div>'
    );
  }

  function renderPois(items) {
    dm.poiLayer.clearLayers();
    dm.roadLayer.clearLayers();
    if (!items || !items.length) return;
    items.forEach(function (e) {
      var ll = elementLatLng(e);
      if (!ll) return;
      var tags = e.tags || {};
      var name =
        (tags.name ? String(tags.name) : '') ||
        (tags['name:en'] ? String(tags['name:en']) : '') ||
        (tags.official_name ? String(tags.official_name) : '') ||
        (tags.operator ? String(tags.operator) : '') ||
        (tags.brand ? String(tags.brand) : '');
      var kind = labelForPoi(tags);
      var spec = iconSpecForElement(e);
      var icon = divIconFor(spec);

      var layer = (e.type === 'way' && tags.ref) ? dm.roadLayer : dm.poiLayer;
      var m = L.marker(ll, { icon: icon, keyboard: false, riseOnHover: true }).addTo(layer);

      // Treat every icon like a button: click to zoom + show details.
      var placeName = (name || kind);
      // Improve Wikipedia hit-rate: "CMH Hospital Rawalpindi, Pakistan"
      var cityHint =
        (tags['addr:city'] ? String(tags['addr:city']) : '') ||
        (tags['is_in:city'] ? String(tags['is_in:city']) : '') ||
        (tags['addr:district'] ? String(tags['addr:district']) : '');
      var wikiQuery = placeName;
      if (cityHint && cityHint.trim()) wikiQuery += ' ' + cityHint.trim();
      wikiQuery += ' Pakistan';

      m.bindPopup(
        poiPopupHtml(placeName, kind, null, true, ll, tags),
        { className: 'map-popup-card', maxWidth: 320, autoPan: true, autoPanPadding: [28, 28], closeButton: true }
      );

      m.on('mouseover', function () { try { this.openPopup(); } catch(e) {} });
      m.on('mouseout', function () { if (!this.__sticky) { try { this.closePopup(); } catch(e) {} } });
      m.on('popupclose', function () { this.__sticky = false; });

      m.on('click', function () {
        this.__sticky = true;
        var targetZoom = Math.max(dm.map.getZoom(), 16);
        dm.map.flyTo(ll, targetZoom, { duration: 1.2 });
        dm.map.once('moveend', function () {
          try { m.openPopup(); } catch (e2) { /* ignore */ }
        });

        // Fetch and update image once per marker (plus global cache across markers).
        if (m.__wikiImgApplied) return;
        if (!m.__wikiImgPromise) {
          m.__wikiImgPromise = getWikiSummary(wikiQuery);
        }
        m.__wikiImgPromise
          .then(function (wiki) {
            m.setPopupContent(poiPopupHtml(placeName, kind, wiki, false, ll, tags));
            m.__wikiImgApplied = true;
          })
          .catch(function () {
            // leave placeholder/fallback silently
          });
      });
    });
  }

  function updatePois() {
    if (!dm.poisEnabled) {
      dm.poiLayer.clearLayers();
      dm.roadLayer.clearLayers();
      return;
    }
    var zoom = dm.map.getZoom();
    if (zoom < 13) {
      dm.poiLayer.clearLayers();
      dm.roadLayer.clearLayers();
      return;
    }
    var b = dm.map.getBounds();
    var key = poiKey(b, zoom);
    var now = Date.now();
    var cached = dm.poiCache[key];
    if (cached && (now - cached.ts) < 60 * 1000) {
      renderPois(cached.items);
      return;
    }

    var reqId = ++dm.poiReqId;
    var south = b.getSouth();
    var west = b.getWest();
    var north = b.getNorth();
    var east = b.getEast();
    var query =
      '[out:json][timeout:12];(' +
        'node["amenity"="school"](' + south + ',' + west + ',' + north + ',' + east + ');' +
        'node["amenity"="hospital"](' + south + ',' + west + ',' + north + ',' + east + ');' +
        'node["office"](' + south + ',' + west + ',' + north + ',' + east + ');' +
        'node["tourism"~"^(attraction|viewpoint|museum|zoo|theme_park)$"](' + south + ',' + west + ',' + north + ',' + east + ');' +
        'way["highway"]["ref"~"^M-"](' + south + ',' + west + ',' + north + ',' + east + ');' +
        'way["highway"]["ref"~"^N"](' + south + ',' + west + ',' + north + ',' + east + ');' +
      ');out body center 250;';

    fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8' },
      body: 'data=' + encodeURIComponent(query)
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j || reqId !== dm.poiReqId) return;
        var items = (j.elements || []).filter(function (e) {
          if (!e) return false;
          if (e.type === 'node') return isFinite(e.lat) && isFinite(e.lon);
          if (e.type === 'way') return !!(e.center && isFinite(e.center.lat) && isFinite(e.center.lon));
          return false;
        });
        dm.poiCache[key] = { ts: Date.now(), items: items };
        renderPois(items);
      })
      .catch(function () { /* ignore */ });
  }

  window.__datamapSchedulePoisUpdate = function () {
    if (dm.poiDebounce) clearTimeout(dm.poiDebounce);
    dm.poiDebounce = setTimeout(updatePois, 220);
  };

  window.setPoisEnabled = function (enabled) {
    dm.poisEnabled = !!enabled;
    if (!dm.poisEnabled) {
      dm.poiLayer.clearLayers();
      return;
    }
    window.__datamapSchedulePoisUpdate();
  };

  dm.map.on('moveend zoomend', function () {
    window.__datamapSchedulePoisUpdate();
  });
})();

