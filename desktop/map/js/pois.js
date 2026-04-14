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
    return { cls: 'tag-icon', label: '•' };
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

  function renderPois(items) {
    dm.poiLayer.clearLayers();
    dm.roadLayer.clearLayers();
    if (!items || !items.length) return;
    items.forEach(function (e) {
      var ll = elementLatLng(e);
      if (!ll) return;
      var tags = e.tags || {};
      var name = tags.name ? String(tags.name) : '';
      var kind = labelForPoi(tags);
      var spec = iconSpecForElement(e);
      var icon = divIconFor(spec);

      var layer = (e.type === 'way' && tags.ref) ? dm.roadLayer : dm.poiLayer;
      var m = L.marker(ll, { icon: icon, keyboard: false, riseOnHover: true }).addTo(layer);

      var html = '<div class="poi-tooltip">' +
        '<div class="poi-name">' + (name || kind) + '</div>' +
        (name ? '<div class="poi-kind">' + kind + '</div>' : '') +
      '</div>';
      m.bindTooltip(html, { sticky: true, direction: 'top', opacity: 1, className: 'map-tooltip-card', offset: [0, -10] });

      // Treat every icon like a button: click to zoom + show name/details.
      var pop = '<div style="font-family:Segoe UI,system-ui,sans-serif;font-size:13px">' +
        '<div style="font-weight:800;color:#111">' + (name || kind) + '</div>' +
        (name ? '<div style="margin-top:4px;color:#111;opacity:.75">' + kind + '</div>' : '') +
      '</div>';
      m.bindPopup(pop, { className: 'map-popup-card', maxWidth: 320, autoPan: true, autoPanPadding: [28, 28] });
      m.on('click', function () {
        var targetZoom = Math.max(dm.map.getZoom(), 16);
        dm.map.flyTo(ll, targetZoom, { duration: 1.2 });
        dm.map.once('moveend', function () {
          try { m.openPopup(); } catch (e2) { /* ignore */ }
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

