import Papa from 'papaparse';
import type { DataPoint } from '../types';
import { rowToPoint } from './parse';

export function parseCsvText(text: string): DataPoint[] {
  const res = Papa.parse<Record<string, unknown>>(text, {
    header: true,
    skipEmptyLines: true,
  });
  if (res.errors.length && !res.data.length) return [];
  const out: DataPoint[] = [];
  for (const row of res.data) {
    if (!row || typeof row !== 'object') continue;
    const p = rowToPoint(row as Record<string, unknown>);
    if (p) out.push(p);
  }
  return out;
}

export function parseCsvFile(file: File): Promise<DataPoint[]> {
  return new Promise((resolve, reject) => {
    Papa.parse<Record<string, unknown>>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (res) => {
        const out: DataPoint[] = [];
        for (const row of res.data) {
          if (!row || typeof row !== 'object') continue;
          const p = rowToPoint(row as Record<string, unknown>);
          if (p) out.push(p);
        }
        resolve(out);
      },
      error: (err) => reject(err),
    });
  });
}
