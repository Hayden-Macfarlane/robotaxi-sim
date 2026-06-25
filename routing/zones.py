"""Austin neighborhood zones for demand, fleet balance, and map overlays."""

from __future__ import annotations

from dataclasses import dataclass

# Greater Austin service area (includes Kyle / Buda south of city proper).
AUSTIN_BBOX = {"north": 30.52, "south": 30.00, "east": -97.55, "west": -97.95}

# Grid split lines — rows south→north, columns west→east.
_LAT_BREAKS: tuple[float, ...] = (30.00, 30.12, 30.20, 30.26, 30.285, 30.32, 30.38, 30.52)
_LON_BREAKS: tuple[float, ...] = (-97.95, -97.80, -97.755, -97.715, -97.68, -97.65, -97.55)

# Neighborhood labels for each grid cell (must match lat/lon break dimensions).
_GRID_NAMES: tuple[tuple[str, ...], ...] = (
    ("kyle", "kyle", "kyle", "kyle", "kyle", "kyle"),
    ("buda", "buda", "airport", "airport", "airport", "east_side"),
    ("southwest", "south_central", "south_central", "riverside", "riverside", "east_side"),
    ("southwest", "central", "downtown", "downtown", "riverside", "east_side"),
    ("westlake", "central", "campus", "campus", "east_side", "east_side"),
    ("westlake", "domain", "domain", "domain", "east_side", "east_side"),
    ("northwest", "northwest", "northwest", "northeast", "northeast", "northeast"),
)


@dataclass(frozen=True)
class ZoneRect:
    """Named axis-aligned zone rectangle in WGS-84 degrees."""

    name: str
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

    def contains(self, lat: float, lon: float) -> bool:
        """Return True when ``(lat, lon)`` lies inside this rectangle."""
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon

    def ring(self) -> list[tuple[float, float]]:
        """Return closed polygon ring for map overlays."""
        return [
            (self.min_lat, self.min_lon),
            (self.max_lat, self.min_lon),
            (self.max_lat, self.max_lon),
            (self.min_lat, self.max_lon),
        ]


def _grid_zone_rects() -> tuple[ZoneRect, ...]:
    """Build one rectangle per grid cell so the city bbox is fully tiled."""
    rects: list[ZoneRect] = []
    for row_idx, row in enumerate(_GRID_NAMES):
        min_lat = _LAT_BREAKS[row_idx]
        max_lat = _LAT_BREAKS[row_idx + 1]
        for col_idx, name in enumerate(row):
            rects.append(ZoneRect(
                name,
                min_lat,
                max_lat,
                _LON_BREAKS[col_idx],
                _LON_BREAKS[col_idx + 1],
            ))
    return tuple(rects)


# POI cores first, then full grid partition (most-specific wins on overlap).
AUSTIN_ZONE_RECTS: tuple[ZoneRect, ...] = (
    ZoneRect("airport", 30.18, 30.235, -97.685, -97.625),
    ZoneRect("downtown", 30.262, 30.278, -97.748, -97.732),
    ZoneRect("campus", 30.288, 30.308, -97.742, -97.718),
    *_grid_zone_rects(),
)

# Display colors (hex) for map overlays — mirrored in frontend.
ZONE_COLORS: dict[str, str] = {
    "airport": "#06b6d4",
    "buda": "#14b8a6",
    "campus": "#f97316",
    "central": "#64748b",
    "domain": "#a855f7",
    "downtown": "#8b5cf6",
    "east_side": "#ec4899",
    "kyle": "#84cc16",
    "northeast": "#0ea5e9",
    "northwest": "#22c55e",
    "riverside": "#eab308",
    "south_central": "#fb7185",
    "southwest": "#3b82f6",
    "westlake": "#6366f1",
    "unknown": "#475569",
}

# POI-sized cores rendered with slightly higher opacity on the map.
POI_ZONE_NAMES: frozenset[str] = frozenset({"airport", "downtown", "campus"})


def all_zone_names() -> list[str]:
    """Return canonical zone labels for operator controls."""
    seen: set[str] = set()
    names: list[str] = []
    for rect in AUSTIN_ZONE_RECTS:
        if rect.name not in seen:
            seen.add(rect.name)
            names.append(rect.name)
    return sorted(names)


def zone_for_point(lat: float, lon: float, fallback: str = "unknown") -> str:
    """Return demand zone for a WGS-84 coordinate using neighborhood rectangles."""
    for rect in AUSTIN_ZONE_RECTS:
        if rect.contains(lat, lon):
            return rect.name
    return fallback


def exclusive_zone_polygons() -> dict[str, list[list[tuple[float, float]]]]:
    """Non-overlapping polygons grouped by zone name for map overlays."""
    polys: dict[str, list[list[tuple[float, float]]]] = {}
    for rect in _grid_zone_rects():
        polys.setdefault(rect.name, []).append(rect.ring())
    return polys


def poi_zone_polygons() -> dict[str, list[tuple[float, float]]]:
    """POI core rectangles drawn with higher emphasis on the map."""
    return {
        rect.name: rect.ring()
        for rect in AUSTIN_ZONE_RECTS[:3]
    }


def zone_bounding_boxes() -> dict[str, tuple[float, float, float, float]]:
    """Return merged ``(min_lat, max_lat, min_lon, max_lon)`` per zone label."""
    boxes: dict[str, list[float]] = {}
    for rect in _grid_zone_rects():
        if rect.name not in boxes:
            boxes[rect.name] = [rect.min_lat, rect.max_lat, rect.min_lon, rect.max_lon]
            continue
        b = boxes[rect.name]
        b[0] = min(b[0], rect.min_lat)
        b[1] = max(b[1], rect.max_lat)
        b[2] = min(b[2], rect.min_lon)
        b[3] = max(b[3], rect.max_lon)
    return {name: (b[0], b[1], b[2], b[3]) for name, b in boxes.items()}


def zone_overlay_snapshot() -> list[dict[str, object]]:
    """Serialize zone overlay geometry for the UI map."""
    overlays: list[dict[str, object]] = []
    for zone, rings in exclusive_zone_polygons().items():
        overlays.append({
            "zone": zone,
            "kind": "poi" if zone in POI_ZONE_NAMES else "grid",
            "color": ZONE_COLORS.get(zone, ZONE_COLORS["unknown"]),
            "polygons": [[[lat, lon] for lat, lon in ring] for ring in rings],
        })
    return overlays
