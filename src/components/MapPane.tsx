import { useEffect, useRef } from 'react';
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import type { DataPoint } from '../types';
import { radiusForValue, tierFor } from '../lib/dataset';

const ESRI_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const ESRI_ATTR =
  '&copy; Esri, Maxar, Earthstar Geographics, GIS User Community';

function displayTitle(p: DataPoint): string {
  const c = p.city.trim();
  if (c) return c;
  return p.id.length >= 4 ? `Target ${p.id.slice(0, 8)}` : `Target ${p.id}`;
}

function CardBody({
  p,
  vmin,
  vmax,
}: {
  p: DataPoint;
  vmin: number;
  vmax: number;
}) {
  const lat = p.lat.toFixed(4);
  const lng = p.lng.toFixed(4);
  const val = Number.isFinite(p.value) ? p.value.toLocaleString() : '—';
  const tier = tierFor(p.value, vmin, vmax);
  return (
    <div className="map-card-inner">
      <div className="map-card-tier">{tier}</div>
      <div className="map-card-title">{displayTitle(p)}</div>
      <div className="map-card-coords">
        Lat: {lat} &nbsp;·&nbsp; Lng: {lng}
      </div>
      <div className="map-card-value">{val}</div>
    </div>
  );
}

function TooltipBody({ p }: { p: DataPoint }) {
  const lat = p.lat.toFixed(4);
  const lng = p.lng.toFixed(4);
  const val = Number.isFinite(p.value) ? p.value.toLocaleString() : '—';
  return (
    <div className="map-tooltip-inner">
      <div className="map-tooltip-title">{displayTitle(p)}</div>
      <div className="map-tooltip-coords">
        Lat: {lat} &nbsp; Lng: {lng}
      </div>
      <div className="map-tooltip-value-row">
        Value: <strong className="map-tooltip-value">{val}</strong>
      </div>
    </div>
  );
}

function FitBounds({ points }: { points: DataPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    const b = L.latLngBounds(
      points.map((p) => [p.lat, p.lng] as [number, number]),
    );
    map.fitBounds(b, { padding: [48, 48], maxZoom: 14, animate: true });
  }, [map, points]);
  return null;
}

function FlyToSelected({
  selectedId,
  points,
}: {
  selectedId: string | null;
  points: DataPoint[];
}) {
  const map = useMap();
  useEffect(() => {
    if (!selectedId) return;
    const p = points.find((x) => x.id === selectedId);
    if (!p) return;
    map.flyTo([p.lat, p.lng], Math.max(map.getZoom(), 8), { duration: 0.85 });
  }, [map, selectedId, points]);
  return null;
}

function MarkerDot({
  p,
  vmin,
  vmax,
  selected,
  onSelect,
}: {
  p: DataPoint;
  vmin: number;
  vmax: number;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const ref = useRef<L.CircleMarker | null>(null);
  const r = radiusForValue(p.value, vmin, vmax);

  useEffect(() => {
    if (selected) ref.current?.openPopup();
  }, [selected]);

  return (
    <CircleMarker
      ref={ref}
      center={[p.lat, p.lng]}
      radius={r}
      pathOptions={{
        color: selected ? '#ffffff' : '#D4AF37',
        weight: selected ? 3 : 2,
        fillColor: '#D4AF37',
        fillOpacity: selected ? 0.5 : 0.28,
      }}
      eventHandlers={{
        click: () => onSelect(p.id),
      }}
    >
      <Tooltip
        direction="top"
        offset={[0, -10]}
        opacity={1}
        sticky
        className="map-tooltip-card"
      >
        <TooltipBody p={p} />
      </Tooltip>
      <Popup className="map-popup-card">
        <CardBody p={p} vmin={vmin} vmax={vmax} />
      </Popup>
    </CircleMarker>
  );
}

export function MapPane({
  points,
  selectedId,
  onSelectMarker,
}: {
  points: DataPoint[];
  selectedId: string | null;
  onSelectMarker: (id: string) => void;
}) {
  const vals = points.map((p) => p.value).filter(Number.isFinite);
  const vmin = vals.length ? Math.min(...vals) : 0;
  const vmax = vals.length ? Math.max(...vals) : 1;

  return (
    <div className="map-pane">
      <MapContainer
        center={[20, 0]}
        zoom={2}
        className="map-leaflet"
        zoomControl={false}
        style={{ height: '100%', width: '100%', background: '#050505' }}
      >
        <TileLayer attribution={ESRI_ATTR} url={ESRI_URL} maxZoom={19} />
        <FitBounds points={points} />
        <FlyToSelected selectedId={selectedId} points={points} />
        {points.map((p) => (
          <MarkerDot
            key={p.id}
            p={p}
            vmin={vmin}
            vmax={vmax}
            selected={selectedId === p.id}
            onSelect={onSelectMarker}
          />
        ))}
      </MapContainer>
    </div>
  );
}
