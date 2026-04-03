"""Parse CSV / JSON files into ``DataPoint`` lists (no UI coupling)."""

from __future__ import annotations

import csv
import json
import math
import uuid
from pathlib import Path
from typing import Any, Mapping, TextIO

from models.datapoint import DataPoint

# Lookup order matters when multiple columns exist (first match wins).
_CITY_KEYS = ("city", "location", "area", "name")
_LAT_KEYS = ("lat", "latitude")
_LNG_KEYS = ("lng", "lon", "longitude")
_VALUE_KEYS = (
    "value",
    "population",
    "score",
    "cgpa",
    "iq score total",
    "mustakbil score match",
)


def _row_key_map(row: Mapping[str, Any]) -> dict[str, Any]:
    """Map lowercased stripped keys to values (first wins on duplicates)."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        if k is None:
            continue
        key = str(k).strip().lower()
        if key not in out:
            out[key] = v
    return out


def _get_first(row: Mapping[str, Any], allowed: tuple[str, ...]) -> Any:
    m = _row_key_map(row)
    for k in allowed:
        if k in m:
            v = m[k]
            if v is None:
                continue
            if isinstance(v, str) and not v.strip():
                continue
            return v
    return None


def _parse_float(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        x = float(raw)
        return x if math.isfinite(x) else None
    s = str(raw).strip().replace(",", "")
    if not s:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except ValueError:
        return None


def parse_value_field(raw: Any) -> float | None:
    """Parse numeric value; supports suffix '%' (e.g. ``45%`` → ``45.0``)."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        x = float(raw)
        return x if math.isfinite(x) else None
    s = str(raw).strip().replace(",", "")
    if not s:
        return None
    if s.endswith("%"):
        s = s[:-1].strip()
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except ValueError:
        return None


def _extract_city(row: Mapping[str, Any]) -> str | None:
    raw = _get_first(row, _CITY_KEYS)
    if raw is None:
        return None
    text = str(raw).strip()
    return text if text else None


def _extract_lat(row: Mapping[str, Any]) -> float | None:
    return _parse_float(_get_first(row, _LAT_KEYS))


def _extract_lng(row: Mapping[str, Any]) -> float | None:
    return _parse_float(_get_first(row, _LNG_KEYS))


def _extract_value(row: Mapping[str, Any]) -> float | None:
    m = _row_key_map(row)
    for key in _VALUE_KEYS:
        if key not in m:
            continue
        parsed = parse_value_field(m[key])
        if parsed is not None:
            return parsed
    return None


def row_to_datapoint(row: Mapping[str, Any]) -> DataPoint | None:
    """
    Build one ``DataPoint`` from a dict-like row (e.g. CSV ``DictReader`` row).

    Returns ``None`` if required fields are missing or invalid.
    """
    city = _extract_city(row)
    if city is None:
        return None

    lat = _extract_lat(row)
    lng = _extract_lng(row)
    if lat is None or lng is None:
        return None

    val = _extract_value(row)
    if val is None:
        return None

    return DataPoint(
        id=uuid.uuid4().hex[:12],
        city=city,
        lat=lat,
        lng=lng,
        value=val,
    )


def parse_csv_rows(rows: list[Mapping[str, Any]]) -> list[DataPoint]:
    """Convert already-parsed tabular rows to ``DataPoint`` list; skips bad rows."""
    out: list[DataPoint] = []
    for row in rows:
        try:
            p = row_to_datapoint(row)
            if p is not None:
                out.append(p)
        except (TypeError, ValueError, KeyError):
            continue
    return out


def parse_csv(source: str | Path | TextIO, *, encoding: str = "utf-8-sig") -> list[DataPoint]:
    """
    Parse a CSV file or text stream.

    Uses the first row as headers. Rows that cannot be converted are skipped.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        with path.open(newline="", encoding=encoding) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    else:
        reader = csv.DictReader(source)
        rows = list(reader)

    return parse_csv_rows(rows)


def _json_to_row_list(data: Any) -> list[Mapping[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, Mapping)]
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, Mapping)]
        return [data]
    return []


def parse_json(source: str | Path | TextIO, *, encoding: str = "utf-8") -> list[DataPoint]:
    """
    Parse JSON: a list of objects, a single object, or ``{\"data\": [ ... ]}``.

    Invalid elements are skipped.
    """
    if isinstance(source, (str, Path)):
        raw_text = Path(source).read_text(encoding=encoding)
    else:
        raw_text = source.read()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return []

    rows = _json_to_row_list(data)
    out: list[DataPoint] = []
    for row in rows:
        try:
            p = row_to_datapoint(row)
            if p is not None:
                out.append(p)
        except (TypeError, ValueError, KeyError):
            continue
    return out
