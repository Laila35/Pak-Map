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
)
_ID_KEYS = ("id",)
_TYPE_KEYS = ("category", "type", "place_type", "poi_type", "icon")
_NAME_KEYS = ("place_name", "title", "display_name")
_DESC_KEYS = ("description", "details", "notes", "summary")
_IMAGE_KEYS = ("image_url", "image", "photo", "picture", "thumbnail")
_ADDRESS_KEYS = ("address", "addr", "location_address")
_RATING_KEYS = ("rating", "stars", "score_display")
_HOURS_KEYS = ("hours", "opening_hours", "open_hours", "times")
_REVIEWS_KEYS = ("reviews", "review_count", "reviewcount", "num_reviews")
_STATUS_KEYS = ("open_status", "status", "hours_status", "opens")
_WEBSITE_KEYS = ("website", "url", "link", "web")
_SPONSORED_KEYS = ("sponsored", "ad", "promoted")
_IMAGE2_KEYS = ("image_url_2", "image2", "photo2", "thumbnail2")


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


def _extract_optional_str(row: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    raw = _get_first(row, keys)
    if raw is None:
        return ""
    return str(raw).strip()


def _normalize_place_type(raw: str) -> str:
    """Map CSV free text to a small set of icon keys used by the map."""
    if not raw:
        return "place"
    s = raw.strip().lower().replace(" ", "_")
    synonyms: dict[str, str] = {
        "restaurant": "restaurant",
        "food": "restaurant",
        "cafe": "restaurant",
        "café": "restaurant",
        "dining": "restaurant",
        "hospital": "hospital",
        "clinic": "hospital",
        "medical": "hospital",
        "pharmacy": "pharmacy",
        "university": "university",
        "college": "university",
        "school": "school",
        "airport": "airport",
        "park": "park",
        "garden": "park",
        "hotel": "hotel",
        "lodging": "hotel",
        "mosque": "mosque",
        "temple": "mosque",
        "church": "mosque",
        "worship": "mosque",
        "bank": "bank",
        "shop": "shop",
        "store": "shop",
        "mall": "mall",
        "hypermarket": "mall",
        "shopping_mall": "mall",
        "travel_agency": "travel_agency",
        "travelagency": "travel_agency",
        "travel_agencies": "travel_agency",
        "travel": "travel_agency",
        "tours": "travel_agency",
        "hall": "hall",
        "banquet": "hall",
        "banquet_hall": "hall",
        "marriage_hall": "hall",
        "wedding_hall": "hall",
        "museum": "museum",
        "stadium": "stadium",
        "parking": "parking",
        "gas": "gas_station",
        "fuel": "gas_station",
        "gas_station": "gas_station",
    }
    return synonyms.get(s, s if s else "place")


def _extract_place_type(row: Mapping[str, Any]) -> str:
    raw = _extract_optional_str(row, _TYPE_KEYS)
    return _normalize_place_type(raw)


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

    raw_id = _get_first(row, _ID_KEYS)
    id_str = str(raw_id).strip() if raw_id is not None else ""
    if not id_str:
        id_str = uuid.uuid4().hex[:12]

    place_name = _extract_optional_str(row, _NAME_KEYS)
    if not place_name:
        place_name = city

    return DataPoint(
        id=id_str,
        city=city,
        lat=lat,
        lng=lng,
        value=val,
        place_type=_extract_place_type(row),
        place_name=place_name,
        description=_extract_optional_str(row, _DESC_KEYS),
        image_url=_extract_optional_str(row, _IMAGE_KEYS),
        image_url_2=_extract_optional_str(row, _IMAGE2_KEYS),
        address=_extract_optional_str(row, _ADDRESS_KEYS),
        rating=_extract_optional_str(row, _RATING_KEYS),
        hours=_extract_optional_str(row, _HOURS_KEYS),
        reviews=_extract_optional_str(row, _REVIEWS_KEYS),
        open_status=_extract_optional_str(row, _STATUS_KEYS),
        website=_extract_optional_str(row, _WEBSITE_KEYS),
        sponsored=_extract_optional_str(row, _SPONSORED_KEYS),
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
