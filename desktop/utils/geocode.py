"""Simple geocoding helpers for Pakistan cities (Nominatim).

Used by the sidebar search icon to move the map to a typed city.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from map_config import NOMINATIM_EMAIL

_NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"


def _ua() -> str:
    agent = "datamap-explorer/1.0 (geocode)"
    if NOMINATIM_EMAIL:
        agent = f"{agent} ({NOMINATIM_EMAIL})"
    return agent


def geocode_pk_city(city: str) -> tuple[float, float, str] | None:
    """
    Resolve a Pakistani city name to (lat, lng, display_name) using Nominatim.
    Returns None if not found.
    """
    q = (city or "").strip()
    if not q:
        return None
    if "pakistan" not in q.lower():
        q = f"{q}, Pakistan"

    params = {
        "q": q,
        "format": "jsonv2",
        "limit": "1",
        "countrycodes": "pk",
        "addressdetails": "1",
    }
    url = f"{_NOMINATIM_SEARCH}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _ua(), "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=14) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError):
        return None

    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    hit = data[0]
    if not isinstance(hit, dict):
        return None
    try:
        lat = float(hit.get("lat"))
        lng = float(hit.get("lon"))
    except (TypeError, ValueError):
        return None
    display = str(hit.get("display_name") or q)
    return lat, lng, display


def geocode_pk_query(query: str) -> tuple[float, float, str] | None:
    """
    Resolve a free-text Pakistan location query to (lat, lng, display_name).

    Examples:
    - "Saddar metro station Rawalpindi"
    - "CMH hospital Rawalpindi"
    """
    q = (query or "").strip()
    if not q:
        return None
    if "pakistan" not in q.lower():
        q = f"{q}, Pakistan"

    params = {
        "q": q,
        "format": "jsonv2",
        "limit": "1",
        "countrycodes": "pk",
        "addressdetails": "1",
    }
    url = f"{_NOMINATIM_SEARCH}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _ua(), "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=14) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError):
        return None

    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    hit = data[0]
    if not isinstance(hit, dict):
        return None
    try:
        lat = float(hit.get("lat"))
        lng = float(hit.get("lon"))
    except (TypeError, ValueError):
        return None
    display = str(hit.get("display_name") or q)
    return lat, lng, display

