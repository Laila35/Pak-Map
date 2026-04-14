"""Geographic data record for map and directory views."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class DataPoint:
    id: str
    city: str
    lat: float
    lng: float
    value: float
    # Optional POI fields (CSV columns); drive map icons + hover / popup cards in Leaflet.
    place_type: str = "place"
    place_name: str = ""
    description: str = ""
    image_url: str = ""
    image_url_2: str = ""  # optional second photo (gallery strip)
    address: str = ""
    rating: str = ""
    hours: str = ""
    reviews: str = ""  # review count e.g. "96"
    open_status: str = ""  # e.g. "Closed · Opens 11AM Mon"
    website: str = ""
    sponsored: str = ""  # "yes" / "true" / "1" shows Sponsored label

    def display_name(self) -> str:
        n = (self.place_name or "").strip()
        if n:
            return n
        c = (self.city or "").strip()
        if c:
            return c
        return self.id[:8] if len(self.id) >= 4 else self.id

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON / map bridge payloads."""
        return {
            "id": self.id,
            "city": self.city,
            "lat": self.lat,
            "lng": self.lng,
            "value": self.value,
            "place_type": self.place_type,
            "place_name": self.place_name,
            "description": self.description,
            "image_url": self.image_url,
            "image_url_2": self.image_url_2,
            "address": self.address,
            "rating": self.rating,
            "hours": self.hours,
            "reviews": self.reviews,
            "open_status": self.open_status,
            "website": self.website,
            "sponsored": self.sponsored,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DataPoint:
        """Build from a mapping (e.g. parsed CSV row or API JSON)."""
        rid = str(data.get("id") or "").strip()
        if not rid:
            rid = uuid.uuid4().hex[:12]
        pt = str(data.get("place_type") or data.get("category") or "place").strip().lower() or "place"
        return cls(
            id=rid,
            city=str(data["city"]),
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            value=float(data["value"]),
            place_type=pt,
            place_name=str(data.get("place_name") or data.get("name") or "").strip(),
            description=str(data.get("description") or "").strip(),
            image_url=str(data.get("image_url") or data.get("image") or "").strip(),
            image_url_2=str(data.get("image_url_2") or data.get("image2") or "").strip(),
            address=str(data.get("address") or "").strip(),
            rating=str(data.get("rating") or "").strip(),
            hours=str(data.get("hours") or data.get("opening_hours") or "").strip(),
            reviews=str(data.get("reviews") or data.get("review_count") or "").strip(),
            open_status=str(data.get("open_status") or data.get("status") or "").strip(),
            website=str(data.get("website") or data.get("url") or "").strip(),
            sponsored=str(data.get("sponsored") or "").strip(),
        )
