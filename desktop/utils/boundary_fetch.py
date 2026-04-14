"""Boundary fetch + fallback polygon generator (GeoJSON).

We try to fetch a boundary polygon from Nominatim. If unavailable, we generate
an approximate circular polygon around the city's lat/lng so boundaries always
render.
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from map_config import NOMINATIM_EMAIL

_NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"


def _ua() -> str:
    agent = "datamap-explorer/1.0 (boundary-fetch)"
    if NOMINATIM_EMAIL:
        agent = f"{agent} ({NOMINATIM_EMAIL})"
    return agent


def _as_feature(geom: dict[str, Any], props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "Feature", "properties": props, "geometry": geom}


def _queries_for_city(city: str) -> list[str]:
    """
    Nominatim often returns a POINT for "City, Pakistan" (no polygon).
    Administrative boundaries are frequently indexed under "District/Division/Tehsil".
    """
    c = (city or "").strip()
    if not c:
        return []
    if "pakistan" in c.lower():
        base = c
    else:
        base = f"{c}, Pakistan"

    return [
        base,
        f"{c} District, Pakistan",
        f"{c} Division, Pakistan",
        f"{c} Tehsil, Pakistan",
        f"{c} Cantonment, Pakistan",
    ]


def generate_fallback_polygon(lat: float, lng: float, radius_km: float = 4.0) -> dict[str, Any]:
    """Generate a circular GeoJSON Polygon Feature around a point.

    Uses 36 points; geometry coordinates are in [lng, lat] order.
    """
    lat = float(lat)
    lng = float(lng)
    radius_km = float(radius_km)

    r_earth_km = 6371.0088
    ang_dist = radius_km / r_earth_km

    lat1 = math.radians(lat)
    lng1 = math.radians(lng)
    coords: list[list[float]] = []

    for i in range(36 + 1):
        bearing = math.radians(i * (360.0 / 36.0))
        sin_lat1 = math.sin(lat1)
        cos_lat1 = math.cos(lat1)
        sin_ad = math.sin(ang_dist)
        cos_ad = math.cos(ang_dist)

        lat2 = math.asin(sin_lat1 * cos_ad + cos_lat1 * sin_ad * math.cos(bearing))
        lng2 = lng1 + math.atan2(
            math.sin(bearing) * sin_ad * cos_lat1,
            cos_ad - sin_lat1 * math.sin(lat2),
        )
        coords.append([math.degrees(lng2), math.degrees(lat2)])

    geom = {"type": "Polygon", "coordinates": [coords]}
    props = {"fallback": True, "radius_km": radius_km}
    return _as_feature(geom, props)


def _bbox_polygon(points: list[tuple[float, float]], padding_deg: float = 0.01) -> dict[str, Any] | None:
    """
    Build a GeoJSON Polygon Feature representing a padded bbox around points.

    points: [(lat, lng), ...]
    """
    if not points:
        return None
    lats = [p[0] for p in points if math.isfinite(p[0])]
    lngs = [p[1] for p in points if math.isfinite(p[1])]
    if not lats or not lngs:
        return None
    south = min(lats) - padding_deg
    north = max(lats) + padding_deg
    west = min(lngs) - padding_deg
    east = max(lngs) + padding_deg
    coords = [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
    ]
    geom = {"type": "Polygon", "coordinates": [coords]}
    props = {"fallback": True, "source": "dataset_bbox"}
    return _as_feature(geom, props)


def _convex_hull_polygon(points: list[tuple[float, float]], padding_scale: float = 1.02) -> dict[str, Any] | None:
    """
    Build a GeoJSON Polygon Feature representing the convex hull of points.

    points: [(lat, lng), ...]
    padding_scale: expands hull slightly around centroid so edge points aren't on the border.
    """
    if not points:
        return None
    pts: list[tuple[float, float]] = []
    for lat, lng in points:
        if not (math.isfinite(lat) and math.isfinite(lng)):
            continue
        pts.append((float(lng), float(lat)))  # hull in (x=lng, y=lat)
    # de-dupe
    pts = sorted(set(pts))
    if len(pts) < 3:
        return None

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: list[tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return None

    # Expand slightly around centroid for padding.
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)
    if not math.isfinite(cx) or not math.isfinite(cy):
        return None
    scale = float(padding_scale) if padding_scale and padding_scale > 1 else 1.0
    ring: list[list[float]] = []
    for x, y in hull:
        xx = cx + (x - cx) * scale
        yy = cy + (y - cy) * scale
        ring.append([xx, yy])
    ring.append(ring[0])

    geom = {"type": "Polygon", "coordinates": [ring]}
    props = {"fallback": True, "source": "dataset_hull"}
    return _as_feature(geom, props)


def _point_in_ring(lng: float, lat: float, ring: list[list[float]]) -> bool:
    """Ray casting for a single ring. ring coords are [lng, lat]."""
    inside = False
    n = len(ring)
    if n < 4:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersect = ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside


def _point_in_geojson(lng: float, lat: float, geom: dict[str, Any]) -> bool:
    """Supports Polygon + MultiPolygon only."""
    t = geom.get("type")
    if t == "Polygon":
        rings = geom.get("coordinates") or []
        if not rings:
            return False
        outer = rings[0]
        if not _point_in_ring(lng, lat, outer):
            return False
        # holes
        for hole in rings[1:]:
            if _point_in_ring(lng, lat, hole):
                return False
        return True
    if t == "MultiPolygon":
        polys = geom.get("coordinates") or []
        for rings in polys:
            if not rings:
                continue
            outer = rings[0]
            if not _point_in_ring(lng, lat, outer):
                continue
            in_hole = False
            for hole in rings[1:]:
                if _point_in_ring(lng, lat, hole):
                    in_hole = True
                    break
            if not in_hole:
                return True
        return False
    return False


def count_points_inside_boundary(feature: dict[str, Any], points_latlng: list[tuple[float, float]]) -> int:
    """Count how many (lat,lng) points fall inside a GeoJSON Feature boundary."""
    if not points_latlng:
        return 0
    if not isinstance(feature, dict):
        return 0
    geom = feature.get("geometry")
    if not isinstance(geom, dict):
        return 0
    inside = 0
    for lat, lng in points_latlng:
        if _point_in_geojson(float(lng), float(lat), geom):
            inside += 1
    return inside


def boundary_covers_points(feature: dict[str, Any], points_latlng: list[tuple[float, float]], min_fraction: float = 0.85) -> bool:
    """True if boundary contains at least min_fraction of points."""
    if not points_latlng:
        return True
    total = len(points_latlng)
    if total <= 0:
        return True
    inside = count_points_inside_boundary(feature, points_latlng)
    return (inside / total) >= float(min_fraction)


def _choose_best_candidate(
    candidates: list[dict[str, Any]],
    points_latlng: list[tuple[float, float]] | None,
) -> dict[str, Any] | None:
    polys = []
    for f in candidates:
        if not isinstance(f, dict) or f.get("type") != "Feature":
            continue
        geom = f.get("geometry")
        if not isinstance(geom, dict) or geom.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        props = f.get("properties") or {}
        class_ = str(props.get("class") or "")
        type_ = str(props.get("type") or "")
        score = 0
        if class_ == "boundary" and type_ == "administrative":
            score += 50
        if class_ == "place" and type_ in {"city", "town"}:
            score += 30
        if props.get("osm_type") == "relation":
            score += 10
        polys.append((score, f))
    if not polys:
        return None

    polys.sort(key=lambda x: x[0], reverse=True)
    if not points_latlng:
        return polys[0][1]

    # Prefer candidate that contains the most dataset points.
    best = None
    best_hits = -1
    for _, f in polys:
        geom = f["geometry"]
        hits = 0
        for lat, lng in points_latlng:
            if _point_in_geojson(lng, lat, geom):
                hits += 1
        if hits > best_hits:
            best_hits = hits
            best = f

    return best


def fetch_city_boundary_candidates(city: str) -> list[dict[str, Any]]:
    queries = _queries_for_city(city)
    if not queries:
        return []

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for q in queries:
        params = {
            "q": q,
            "format": "jsonv2",
            "limit": "10",
            "countrycodes": "pk",
            "polygon_geojson": "1",
            "addressdetails": "1",
            "dedupe": "0",
            "extratags": "1",
        }
        url = f"{_NOMINATIM_SEARCH}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": _ua(), "Accept": "application/json"},
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=18) as resp:
                raw = resp.read().decode("utf-8")
        except (urllib.error.URLError, OSError):
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, list) or not data:
            continue

        for hit in data:
            if not isinstance(hit, dict):
                continue
            geom = hit.get("geojson")
            if not isinstance(geom, dict) or geom.get("type") not in {"Polygon", "MultiPolygon"}:
                continue
            osm_type = str(hit.get("osm_type") or "")
            osm_id = str(hit.get("osm_id") or "")
            key = (osm_type, osm_id)
            if osm_id and key in seen:
                continue
            if osm_id:
                seen.add(key)
            props = {
                "display_name": hit.get("display_name"),
                "osm_type": hit.get("osm_type"),
                "osm_id": hit.get("osm_id"),
                "class": hit.get("class"),
                "type": hit.get("type"),
                "name": hit.get("name"),
                "query": q,
            }
            out.append(_as_feature(geom, props))

        # If we already found good polygon candidates, no need to keep trying weaker queries.
        if out:
            break

    return out


def fetch_city_boundary_geojson(
    city: str,
    *,
    points_latlng: list[tuple[float, float]] | None = None,
    fallback_center: tuple[float, float] | None = None,
) -> dict[str, Any] | None:
    """
    Fetch the best available boundary for a city.

    - Pull multiple candidates from Nominatim.
    - If dataset points are provided, pick the polygon that contains the most points.
    - If no polygon matches but points exist, fall back to a bbox that guarantees all points are inside.
    - Else fall back to a 4km circle at fallback_center.
    """
    candidates = fetch_city_boundary_candidates(city)
    best = _choose_best_candidate(candidates, points_latlng)
    if best is not None:
        return best

    if points_latlng:
        hull = _convex_hull_polygon(points_latlng, padding_scale=1.02)
        if hull is not None:
            return hull
        bbox = _bbox_polygon(points_latlng, padding_deg=0.01)
        if bbox is not None:
            return bbox

    if fallback_center is not None:
        lat, lng = fallback_center
        return generate_fallback_polygon(lat, lng, radius_km=4.0)
    return None

