"""Simple local boundary cache.

Stores per-city GeoJSON at ``desktop/boundaries/<slug>.geojson``.
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return Path(__file__).resolve().parent.parent


_BOUNDARIES_DIR = _resource_root() / "boundaries"


def _slug_city(city: str) -> str:
    s = (city or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _path_for_city(city: str) -> Path | None:
    slug = _slug_city(city)
    if not slug:
        return None
    return _BOUNDARIES_DIR / f"{slug}.geojson"


def ensure_boundaries_dir() -> None:
    try:
        _BOUNDARIES_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return


def _is_geojson_like(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    t = obj.get("type")
    if t in {"Feature", "FeatureCollection"}:
        return True
    if t in {"Polygon", "MultiPolygon"}:
        return True
    return False


@lru_cache(maxsize=256)
def load_boundary_geojson_for_city(city: str) -> dict[str, Any] | None:
    path = _path_for_city(city)
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if _is_geojson_like(data) else None


def save_boundary_geojson_for_city(city: str, geojson_obj: dict[str, Any]) -> bool:
    if not _is_geojson_like(geojson_obj):
        return False
    ensure_boundaries_dir()
    path = _path_for_city(city)
    if path is None:
        return False
    try:
        path.write_text(json.dumps(geojson_obj, ensure_ascii=False), encoding="utf-8")
        load_boundary_geojson_for_city.cache_clear()
        return True
    except OSError:
        return False

