"""Geographic data record for map and directory views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class DataPoint:
    id: str
    city: str
    lat: float
    lng: float
    value: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON / map bridge payloads."""
        return {
            "id": self.id,
            "city": self.city,
            "lat": self.lat,
            "lng": self.lng,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DataPoint:
        """Build from a mapping (e.g. parsed CSV row or API JSON)."""
        return cls(
            id=str(data["id"]),
            city=str(data["city"]),
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            value=float(data["value"]),
        )
