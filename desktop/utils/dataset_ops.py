"""Pure functions: filter, sort, and tier labels for ``DataPoint`` lists."""

from __future__ import annotations

from typing import Literal

from models.datapoint import DataPoint

SortField = Literal["city", "value"]


def max_value(points: list[DataPoint]) -> float:
    if not points:
        return 0.0
    return max(p.value for p in points)


def tier_label(value: float, max_val: float) -> str:
    """
    Tier by position in the current value range (same rule as the web app).

    Top third → ``I``, middle → ``II``, bottom → ``III``.
    """
    if max_val <= 0:
        return "III"
    if value > max_val * (2.0 / 3.0):
        return "I"
    if value > max_val * (1.0 / 3.0):
        return "II"
    return "III"


def _search_blob(p: DataPoint) -> str:
    parts = (
        p.city,
        p.place_name,
        p.description,
        p.address,
        p.place_type,
        p.rating,
        p.hours,
        p.open_status,
        p.website,
        p.reviews,
    )
    return " ".join(x for x in parts if x).lower()


def filter_points(
    points: list[DataPoint],
    *,
    search_query: str,
    min_value: float,
) -> list[DataPoint]:
    """Substring match on city / place fields (case-insensitive) and minimum ``value``."""
    q = search_query.strip().lower()
    out: list[DataPoint] = []
    for p in points:
        if q and q not in _search_blob(p):
            continue
        if p.value < min_value:
            continue
        out.append(p)
    return out


def sort_points(
    points: list[DataPoint],
    field: SortField,
    *,
    descending: bool,
) -> list[DataPoint]:
    if field == "city":
        return sorted(points, key=lambda p: p.city.lower(), reverse=descending)
    return sorted(points, key=lambda p: p.value, reverse=descending)
