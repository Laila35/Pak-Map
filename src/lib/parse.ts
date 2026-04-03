/**
 * CSV / JSON parsing aligned with desktop ``utils/parser.py`` (same column aliases).
 */
import type { DataPoint } from '../types';

const CITY_KEYS = ['city', 'location', 'area', 'name'] as const;
const LAT_KEYS = ['lat', 'latitude'] as const;
const LNG_KEYS = ['lng', 'lon', 'longitude'] as const;
const VALUE_KEYS = [
  'value',
  'population',
  'score',
  'cgpa',
  'iq score total',
  'mustakbil score match',
] as const;

function normalizeKeys(row: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(row)) {
    if (k == null) continue;
    const key = String(k).trim().toLowerCase();
    if (!(key in out)) out[key] = v;
  }
  return out;
}

function getFirst(
  row: Record<string, unknown>,
  keys: readonly string[],
): unknown {
  const m = normalizeKeys(row);
  for (const k of keys) {
    if (k in m) {
      const v = m[k];
      if (v == null) continue;
      if (typeof v === 'string' && !v.trim()) continue;
      return v;
    }
  }
  return undefined;
}

function parseFloatRaw(raw: unknown): number | null {
  if (raw == null || typeof raw === 'boolean') return null;
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : null;
  let s = String(raw).trim().replace(/,/g, '');
  if (!s) return null;
  try {
    const x = parseFloat(s);
    return Number.isFinite(x) ? x : null;
  } catch {
    return null;
  }
}

function parseValueField(raw: unknown): number | null {
  if (raw == null || typeof raw === 'boolean') return null;
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : null;
  let s = String(raw).trim().replace(/,/g, '');
  if (!s) return null;
  if (s.endsWith('%')) s = s.slice(0, -1).trim();
  try {
    const x = parseFloat(s);
    return Number.isFinite(x) ? x : null;
  } catch {
    return null;
  }
}

function extractCity(row: Record<string, unknown>): string | null {
  const raw = getFirst(row, CITY_KEYS);
  if (raw == null) return null;
  const text = String(raw).trim();
  return text || null;
}

function extractValue(row: Record<string, unknown>): number | null {
  const m = normalizeKeys(row);
  for (const key of VALUE_KEYS) {
    if (key in m) {
      const parsed = parseValueField(m[key]);
      if (parsed != null) return parsed;
    }
  }
  return null;
}

function newId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 12);
  }
  return String(Math.random()).slice(2, 14);
}

export function rowToPoint(row: Record<string, unknown>): DataPoint | null {
  const city = extractCity(row);
  if (city == null) return null;
  const lat = parseFloatRaw(getFirst(row, LAT_KEYS));
  const lng = parseFloatRaw(getFirst(row, LNG_KEYS));
  if (lat == null || lng == null) return null;
  const val = extractValue(row);
  if (val == null) return null;
  return {
    id: newId(),
    city,
    lat,
    lng,
    value: val,
  };
}

export function parseJsonText(text: string): DataPoint[] {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return [];
  }
  let rows: Record<string, unknown>[] = [];
  if (Array.isArray(data)) {
    rows = data.filter((x): x is Record<string, unknown> => x != null && typeof x === 'object');
  } else if (data != null && typeof data === 'object') {
    const inner = (data as { data?: unknown }).data;
    if (Array.isArray(inner)) {
      rows = inner.filter((x): x is Record<string, unknown> => x != null && typeof x === 'object');
    } else {
      rows = [data as Record<string, unknown>];
    }
  }
  const out: DataPoint[] = [];
  for (const row of rows) {
    const p = rowToPoint(row);
    if (p) out.push(p);
  }
  return out;
}
