(function () {
  'use strict';

  // Namespace to avoid globals leaking everywhere
  window.__datamap = window.__datamap || {};
  var dm = window.__datamap;

  dm.cfg = window.__MAP_CONFIG__ || {};

  dm.map = L.map('map', { zoomControl: false }).setView([30.3753, 69.3451], 6);
  L.control.zoom({ position: 'bottomright' }).addTo(dm.map);
  L.control.scale({ metric: true, imperial: false, position: 'bottomright' }).addTo(dm.map);

  dm.baseLayer = null;
  dm.markerLayer = L.layerGroup().addTo(dm.map);
  dm.poiLayer = L.layerGroup().addTo(dm.map);
  dm.roadLayer = L.layerGroup().addTo(dm.map);
  dm.boundaryLayer = null;

  dm.markers = {}; // id -> L.Marker

  // Default marker accent for body/shading
  dm.ACCENT = dm.cfg.markerAccent || '#ff0000';

  dm.cityThumbCache = {}; // normalizedCity -> url

  dm.poisEnabled = true;
  dm.poiReqId = 0;
  dm.poiCache = {}; // key -> {ts, items}
  dm.poiDebounce = null;

  dm.util = dm.util || {};
  dm.util.clamp01 = function (x) { return Math.max(0, Math.min(1, x)); };
  dm.util.normCity = function (city) { return String(city || '').trim().toLowerCase(); };

  dm.util.pinColorForValue = function (v, vmin, vmax) {
    // Uniform marker fill: always the same dark accent color.
    // (User requested all pins be identical dark blue + white.)
    return String(dm.ACCENT || '#000080');
  };

  dm.util.pinSvg = function (fill, selected) {
    // Red body, black outline, black center dot for a bold marker style.
    var body = String(fill || dm.ACCENT || '#ff0000');
    var stroke = '#000000';
    var strokeW = selected ? 3.0 : 2.4;
    var dotOpacity = selected ? 0.98 : 0.88;
    return (
      '<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 64 64" aria-hidden="true">' +
        '<path d="M32 2c-11.6 0-21 9.4-21 21 0 15.8 21 39 21 39s21-23.2 21-39C53 11.4 43.6 2 32 2z" ' +
          'fill="' + body + '" stroke="' + stroke + '" stroke-width="' + strokeW + '"/>' +
        '<circle cx="32" cy="23" r="8.8" fill="#000000" fill-opacity="' + dotOpacity + '"/>' +
      '</svg>'
    );
  };

  dm.util.placePinDivIcon = function (selected, fillColor) {
    var size = selected ? 42 : 36;
    var html =
      '<div style="' +
        'width:' + size + 'px;height:' + size + 'px;transform:translate3d(0,0,0);' +
        'filter:drop-shadow(0 6px 14px rgba(0,0,0,0.32));' +
      '">' +
        dm.util.pinSvg(fillColor, selected) +
      '</div>';
    return L.divIcon({
      className: 'map-type-icon-wrap',
      html: html,
      iconSize: [size, size],
      iconAnchor: [size / 2, size],
      popupAnchor: [0, -size + 6]
    });
  };

  dm.util.addOsmBasemapWithFallback = function () {
    var map = dm.map;
    var cfg = dm.cfg;

    var attrOsmCarto =
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' +
      ' &copy; <a href="https://carto.com/attributions">CARTO</a>';
    var voyager = L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      { attribution: attrOsmCarto, subdomains: 'abcd', maxZoom: 20 }
    );
    var cartoLight = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: attrOsmCarto,
      subdomains: 'abcd',
      maxZoom: 20
    });
    var osmRaster = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      subdomains: 'abc',
      maxZoom: 19,
      crossOrigin: true
    });

    // Terrain / Topo (contours + relief). Keep as a base layer option.
    var topoAttr =
      'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors ' +
      '&mdash; Style: &copy; <a href="https://opentopomap.org/">OpenTopoMap</a>';
    var openTopo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      attribution: topoAttr,
      subdomains: 'abc',
      maxZoom: 17,
      crossOrigin: true
    });
    // Optional hillshade overlay to enhance terrain readability.
    var hillshade = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}',
      { attribution: esriAttr, maxZoom: 19, opacity: 0.35, crossOrigin: true }
    );
    var terrain = L.layerGroup([openTopo, hillshade]);

    // Satellite (free) with WHITE labels for clear city names.
    var esriAttr =
      'Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community';
    var esriImagery = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { attribution: esriAttr, maxZoom: 19, crossOrigin: true }
    );
    // Labels overlay: use a transparent "roads + labels" tileset so names show on imagery.
    // Primary: voyager_only_labels (roads + place names). Fallback: dark_only_labels (place names).
    var cartoLabelsAttr = '&copy; <a href="https://carto.com/attributions">CARTO</a>';
    var voyagerLabels = L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png',
      {
        attribution: attrOsmCarto + ' ' + cartoLabelsAttr,
        subdomains: 'abcd',
        maxZoom: 20,
        opacity: 0.98,
        crossOrigin: true
      }
    );
    var whiteLabelsFallback = L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png',
      {
        attribution: attrOsmCarto + ' ' + cartoLabelsAttr,
        subdomains: 'abcd',
        maxZoom: 20,
        opacity: 0.95,
        crossOrigin: true
      }
    );
    var satellite = L.layerGroup([esriImagery, voyagerLabels]);

    // If the primary labels tileset fails, swap in the fallback.
    var lblErr = 0;
    voyagerLabels.on('tileerror', function () {
      lblErr += 1;
      if (lblErr === 6) {
        try { satellite.removeLayer(voyagerLabels); } catch (e) { /* ignore */ }
        try { satellite.addLayer(whiteLabelsFallback); } catch (e2) { /* ignore */ }
      }
    });

    dm.baseLayer = voyager.addTo(map);
    var tileErrors = 0;
    dm.baseLayer.on('tileerror', function () {
      tileErrors += 1;
      if (tileErrors === 8) {
        try { map.removeLayer(dm.baseLayer); } catch (e) { /* ignore */ }
        dm.baseLayer = cartoLight.addTo(map);
      }
    });

    var bases = {
      Streets: voyager,
      'OSM standard': osmRaster,
      Light: cartoLight,
      'Satellite (Esri)': satellite,
      Terrain: terrain
    };
    if (cfg.thunderforestApiKey) {
      bases['Cycling (Thunderforest)'] = L.tileLayer(
        'https://{s}.tile.thunderforest.com/cycle/{z}/{x}/{y}.png?apikey=' +
          encodeURIComponent(cfg.thunderforestApiKey),
        {
          subdomains: 'abc',
          maxZoom: 22,
          attribution:
            '&copy; <a href="https://www.thunderforest.com/">Thunderforest</a> ' +
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }
      );
    }

    function mapOverlays() {
      var sea = L.tileLayer('https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openseamap.org/">OpenSeaMap</a> contributors',
        maxZoom: 18,
        opacity: 0.92
      });
      return { 'Sea marks (OpenSeaMap)': sea };
    }

    L.control.layers(bases, mapOverlays(), { position: 'bottomleft', collapsed: true }).addTo(map);
  };

  dm.util.addGoogleBasemap = function (apiKey) {
    var map = dm.map;

    window.__datamapGmInit = function () {
      var s2 = document.createElement('script');
      s2.src = 'https://unpkg.com/leaflet.gridlayer.googlemutant@0.14.1/dist/Leaflet.GoogleMutant.js';
      s2.onload = function () {
        try {
          if (dm.baseLayer) {
            try { map.removeLayer(dm.baseLayer); } catch (e2) { /* ignore */ }
            dm.baseLayer = null;
          }
          var roads = L.gridLayer.googleMutant({ type: 'roadmap' });
          var sat = L.gridLayer.googleMutant({ type: 'satellite' });
          var hybrid = L.gridLayer.googleMutant({ type: 'hybrid' });
          dm.baseLayer = roads.addTo(map);
          L.control.layers(
            { Map: roads, Satellite: sat, Hybrid: hybrid },
            {},
            { position: 'bottomleft', collapsed: true }
          ).addTo(map);
        } catch (err) {
          dm.util.addOsmBasemapWithFallback();
        }
      };
      s2.onerror = function () { dm.util.addOsmBasemapWithFallback(); };
      document.head.appendChild(s2);
    };

    var s = document.createElement('script');
    s.src = 'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(apiKey) + '&callback=__datamapGmInit';
    s.async = true;
    s.defer = true;
    s.onerror = function () { dm.util.addOsmBasemapWithFallback(); };
    document.head.appendChild(s);
  };

  if (dm.cfg.mapProvider === 'google' && dm.cfg.googleMapsApiKey) {
    dm.util.addGoogleBasemap(dm.cfg.googleMapsApiKey);
  } else {
    dm.util.addOsmBasemapWithFallback();
  }
})();

