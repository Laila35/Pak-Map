import { useCallback, useMemo, useRef, useState } from 'react';
import { MapPane } from './components/MapPane';
import type { DataPoint } from './types';
import {
  filterPoints,
  maxValue,
  sortPoints,
  tierFor,
} from './lib/dataset';
import { parseCsvFile } from './lib/csv';
import { parseJsonText } from './lib/parse';

const DEMO: DataPoint[] = [
  { id: 'demo-1', city: 'London', lat: 51.5, lng: -0.09, value: 80 },
  { id: 'demo-2', city: 'New York', lat: 40.7, lng: -74.0, value: 60 },
];

function displayTitle(p: DataPoint): string {
  const c = p.city.trim();
  if (c) return c;
  return p.id.length >= 4 ? `Target ${p.id.slice(0, 8)}` : `Target ${p.id}`;
}

function formatValue(v: number): string {
  if (Number.isInteger(v)) return v.toLocaleString();
  const s = v.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return s.endsWith('.00') ? s.slice(0, -3) : s;
}

export default function App() {
  const [data, setData] = useState<DataPoint[]>([]);
  const [search, setSearch] = useState('');
  const [minVal, setMinVal] = useState(0);
  const [sliderMax, setSliderMax] = useState(100);
  const [sortIdx, setSortIdx] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const baseData = useMemo(() => (data.length ? data : DEMO), [data]);

  const filtered = useMemo(() => {
    let pts = filterPoints(baseData, search, minVal);
    if (sortIdx === 0) pts = sortPoints(pts, 'value', true);
    else if (sortIdx === 1) pts = sortPoints(pts, 'value', false);
    else if (sortIdx === 2) pts = sortPoints(pts, 'city', false);
    else pts = sortPoints(pts, 'city', true);
    return pts;
  }, [baseData, search, minVal, sortIdx]);

  const mapSelected =
    selectedId && filtered.some((p) => p.id === selectedId)
      ? selectedId
      : null;

  const vmin = useMemo(() => {
    const v = filtered.map((p) => p.value);
    return v.length ? Math.min(...v) : 0;
  }, [filtered]);
  const vmax = useMemo(() => {
    const v = filtered.map((p) => p.value);
    return v.length ? Math.max(...v) : 1;
  }, [filtered]);

  const onFile = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    setErr(null);
    try {
      let pts: DataPoint[] = [];
      if (f.name.toLowerCase().endsWith('.json')) {
        const text = await f.text();
        pts = parseJsonText(text);
      } else {
        pts = await parseCsvFile(f);
      }
      if (!pts.length) {
        setErr('No valid rows found.');
        return;
      }
      setData(pts);
      const m = maxValue(pts);
      const top = Math.max(1, Math.ceil(m));
      setSliderMax(top);
      setMinVal(0);
      setSelectedId(null);
    } catch {
      setErr('Could not read file.');
    }
  }, []);

  const useDemo = useCallback(() => {
    setData([]);
    setSliderMax(100);
    setMinVal(0);
    setSelectedId(null);
    setErr(null);
  }, []);

  return (
    <div className="app-root">
      <aside className="panel panel-left">
        <div className="brand">
          <span className="brand-deep">DEEP</span>
          <span className="brand-dive">DIVE</span>
        </div>
        <p className="tagline">Web · same data as desktop</p>

        <label className="lbl">Dataset</label>
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.json"
          hidden
          onChange={onFile}
        />
        <button
          type="button"
          className="btn"
          onClick={() => fileRef.current?.click()}
        >
          Upload CSV / JSON
        </button>
        <button type="button" className="btn btn-ghost" onClick={useDemo}>
          Use demo map
        </button>
        {err && <p className="err">{err}</p>}

        <label className="lbl">Search</label>
        <input
          className="input"
          placeholder="City…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <label className="lbl">Value threshold (≥ {minVal})</label>
        <input
          type="range"
          className="range"
          min={0}
          max={sliderMax}
          value={Math.min(minVal, sliderMax)}
          onChange={(e) => setMinVal(Number(e.target.value))}
        />

        <label className="lbl">Sort</label>
        <select
          className="select"
          value={sortIdx}
          onChange={(e) => setSortIdx(Number(e.target.value))}
        >
          <option value={0}>Value (high → low)</option>
          <option value={1}>Value (low → high)</option>
          <option value={2}>City (A → Z)</option>
          <option value={3}>City (Z → A)</option>
        </select>
      </aside>

      <main className="map-wrap">
        <MapPane
          points={filtered}
          selectedId={mapSelected}
          onSelectMarker={(id) => setSelectedId(id)}
        />
      </main>

      <aside className="panel panel-right">
        <h2 className="dir-title">Directory</h2>
        <p className="dir-count">
          {filtered.length.toLocaleString()} records
          {!data.length && ' · demo'}
        </p>
        <div className="dir-list">
          {filtered.length === 0 && data.length > 0 && (
            <p className="dir-empty">No records match filters.</p>
          )}
          {filtered.map((p) => (
            <button
              key={p.id}
              type="button"
              className={
                p.id === selectedId ? 'dir-card dir-card-active' : 'dir-card'
              }
              onClick={() => setSelectedId(p.id)}
            >
              <div className="dir-card-main">
                <div className="dir-card-title">{displayTitle(p)}</div>
                <div className="dir-card-coords">LAT: {p.lat.toFixed(2)}</div>
                <div className="dir-card-coords">LNG: {p.lng.toFixed(2)}</div>
              </div>
              <div className="dir-card-side">
                <span className="dir-tier">{tierFor(p.value, vmin, vmax)}</span>
                <span className="dir-val">{formatValue(p.value)}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>
    </div>
  );
}
