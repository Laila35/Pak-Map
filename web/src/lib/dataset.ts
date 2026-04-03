import type { DataPoint } from '../types';

export function maxValue(points: DataPoint[]): number {
  if (!points.length) return 0;
  return Math.max(...points.map((p) => p.value));
}

export function filterPoints(
  points: DataPoint[],
  search: string,
  minVal: number,
): DataPoint[] {
  const q = search.trim().toLowerCase();
  return points.filter((p) => {
    if (q && !p.city.toLowerCase().includes(q)) return false;
    if (p.value < minVal) return false;
    return true;
  });
}

export function sortPoints(
  points: DataPoint[],
  field: 'city' | 'value',
  descending: boolean,
): DataPoint[] {
  const copy = [...points];
  if (field === 'city') {
    copy.sort((a, b) => {
      const c = a.city.toLowerCase().localeCompare(b.city.toLowerCase());
      return descending ? -c : c;
    });
  } else {
    copy.sort((a, b) => (descending ? b.value - a.value : a.value - b.value));
  }
  return copy;
}

export function tierFor(value: number, vmin: number, vmax: number): string {
  if (vmax <= vmin) return 'TIER II';
  const t = (value - vmin) / (vmax - vmin);
  if (t >= 0.66) return 'TIER I';
  if (t >= 0.33) return 'TIER II';
  return 'TIER III';
}

export function radiusForValue(
  v: number,
  vmin: number,
  vmax: number,
): number {
  if (!Number.isFinite(v)) return 12;
  if (vmax <= vmin) return 14;
  const t = (v - vmin) / (vmax - vmin);
  return 6 + t * 22;
}
