(function () {
  'use strict';

  var dm = window.__datamap;
  if (!dm || !dm.map) return;

  function boundaryStyle() {
    // Pure red + dotted stroke + light transparent fill
    return {
      color: '#ff0000',
      weight: 4,
      opacity: 1,
      fillColor: '#ff0000',
      fillOpacity: 0,
      dashArray: '2 8',
      lineCap: 'round',
      lineJoin: 'round'
    };
  }

  function ensureBoundaryLayer() {
    if (dm.boundaryLayer) return dm.boundaryLayer;
    dm.boundaryLayer = L.geoJSON(null, {
      style: boundaryStyle,
      interactive: false,
      filter: function (feature) {
        try {
          var t = feature && feature.geometry && feature.geometry.type ? String(feature.geometry.type) : '';
          return t === 'Polygon' || t === 'MultiPolygon';
        } catch (e) {
          return false;
        }
      }
    }).addTo(dm.map);
    return dm.boundaryLayer;
  }

  window.clearCityBoundary = function () {
    if (!dm.boundaryLayer) return;
    dm.boundaryLayer.clearLayers();
  };

  window.setCityBoundary = function (geojson, opts) {
    opts = opts || {};
    var fit = opts.fit === true;
    var layer = ensureBoundaryLayer();
    layer.clearLayers();
    if (!geojson) return;
    try {
      layer.addData(geojson);
    } catch (e) {
      return;
    }
    try { layer.setStyle(boundaryStyle()); } catch (e2) { /* ignore */ }

    if (fit) {
      try {
        var b = layer.getBounds && layer.getBounds();
        if (b && b.isValid && b.isValid()) {
          var maxZ = opts.maxZoom == null ? 13 : Number(opts.maxZoom);
          if (!isFinite(maxZ)) maxZ = 13;
          var pad = opts.padding || [64, 64];
          if (dm.map.flyToBounds) {
            dm.map.flyToBounds(b, { padding: pad, maxZoom: maxZ, duration: 1.5 });
          } else {
            dm.map.fitBounds(b, { padding: pad, maxZoom: maxZ, animate: true });
          }
        }
      } catch (e3) { /* ignore */ }
    }
  };
})();

