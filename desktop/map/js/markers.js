(function () {
  'use strict';

  var dm = window.__datamap;
  if (!dm || !dm.map) return;

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

  function popupHtml(p, vmin, vmax) {
    var lat = Number(p.lat).toFixed(4);
    var lng = Number(p.lng).toFixed(4);
    var val = formatVal(p);
    var tier = tierFor(Number(p.value), vmin, vmax);
    var title = displayTitle(p);
    return (
      '<div class="map-card-inner">' +
        '<div class="map-card-tier">' + tier + '</div>' +
        '<div class="map-card-media">' +
          '<img class="map-card-img is-hidden" alt="" referrerpolicy="no-referrer" />' +
          '<div class="map-card-head">' +
            '<div class="map-card-title">' + title + '</div>' +
            '<div class="map-card-coords">Lat: ' + lat + ' &nbsp;·&nbsp; Lng: ' + lng + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="map-card-value">' + val + '</div>' +
        '<div style="margin-top:10px;font-size:13px;color:#666">Population: <strong style="color:#111">' + val + '</strong></div>' +
      '</div>'
    );
  }

  function tooltipHtml(p, vmin, vmax) {
    var lat = Number(p.lat).toFixed(4);
    var lng = Number(p.lng).toFixed(4);
    var val = formatVal(p);
    var title = displayTitle(p);
    return (
      '<div class="map-tooltip-inner">' +
        '<div class="map-card-media" style="margin-bottom:6px">' +
          '<img class="map-card-img is-hidden" alt="" referrerpolicy="no-referrer" />' +
          '<div class="map-card-head">' +
            '<div style="font-weight:700;font-size:14px;color:#111;margin-bottom:4px">' + title + '</div>' +
            '<div style="font-size:12px;color:#666">Lat: ' + lat + ' &nbsp; Lng: ' + lng + '</div>' +
          '</div>' +
        '</div>' +
        '<div style="font-size:13px;color:#666">Population: <strong style="color:#111">' + val + '</strong></div>' +
      '</div>'
    );
  }

  function schedulePoisUpdate() {
    if (typeof window.__datamapSchedulePoisUpdate === 'function') {
      window.__datamapSchedulePoisUpdate();
    }
  }

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
      bounds.extend([lat, lng]);

      m.bindPopup(popupHtml(p, vmin, vmax), {
        className: 'map-popup-card',
        maxWidth: 340,
        autoPan: true,
        autoPanPadding: [28, 28]
      });
      m.bindTooltip(tooltipHtml(p, vmin, vmax), {
        sticky: true,
        direction: 'top',
        opacity: 1,
        className: 'map-tooltip-card',
        offset: [0, -10]
      });

      m.on('tooltipopen', function (e) {
        if (e && e.tooltip && dm.util.applyThumbToContainer) {
          dm.util.applyThumbToContainer(e.tooltip.getElement(), p.city);
        }
      });
      m.on('popupopen', function (e) {
        if (e && e.popup && dm.util.applyThumbToContainer) {
          dm.util.applyThumbToContainer(e.popup.getElement(), p.city);
        }
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

