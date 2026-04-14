"""Load optional map / geocoder settings from ``desktop/.env`` (see ``.env.example``)."""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)


_load_dotenv()

# ``auto`` (default): use Google basemap when GOOGLE_MAPS_API_KEY is set, else OSM/CARTO.
# ``osm``: always free tiles even if a key exists. ``google``: Google only when key is set.
_raw_provider = os.getenv("MAP_PROVIDER", "auto").strip().lower()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
THUNDERFOREST_API_KEY = os.getenv("THUNDERFOREST_API_KEY", "").strip()
NOMINATIM_EMAIL = os.getenv("NOMINATIM_EMAIL", "").strip()
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "").strip()
# auto: Geoapify when GEOAPIFY_API_KEY is set, else Nominatim. nominatim | geoapify to force one.
_raw_geocoder = os.getenv("GEOCODER_PROVIDER", "auto").strip().lower()
if _raw_geocoder == "geoapify":
    GEOCODER_PROVIDER: str = "geoapify" if GEOAPIFY_API_KEY else "nominatim"
elif _raw_geocoder == "nominatim":
    GEOCODER_PROVIDER = "nominatim"
else:
    GEOCODER_PROVIDER = "geoapify" if GEOAPIFY_API_KEY else "nominatim"

# auto: Google look when GOOGLE_MAPS_API_KEY is set; else OSM-style tiles.
# osm: always free tiles (even if a key is in .env). google: Google if key set.
MAP_PROVIDER: str
if _raw_provider == "osm":
    MAP_PROVIDER = "osm"
elif _raw_provider == "google":
    MAP_PROVIDER = "google" if GOOGLE_MAPS_API_KEY else "osm"
else:
    MAP_PROVIDER = "google" if GOOGLE_MAPS_API_KEY else "osm"


def map_boot_json() -> dict[str, str]:
    """Inject into ``window.__MAP_CONFIG__`` for ``map/index.html``."""
    # Keep a consistent modern accent across providers (no teal/green).
    accent = "#000080"
    return {
        "mapProvider": MAP_PROVIDER,
        "googleMapsApiKey": GOOGLE_MAPS_API_KEY,
        "thunderforestApiKey": THUNDERFOREST_API_KEY,
        "markerAccent": accent,
    }
