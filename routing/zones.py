"""Austin neighborhood zones for demand, fleet balance, and map overlays."""

from __future__ import annotations

from dataclasses import dataclass

from routing.austin_zones_geo import (
    AUSTIN_BASE_ZONE_POLYGONS,
    AUSTIN_POI_ZONE_RINGS,
    AUSTIN_ZONE_LOOKUP_ORDER,
)

# Greater Austin service area (includes Kyle / Buda south of city proper).
AUSTIN_BBOX = {"north": 30.52, "south": 30.00, "east": -97.55, "west": -97.95}


@dataclass(frozen=True)
class ZonePolygon:
    """Named polygon zone in WGS-84 degrees."""

    name: str
    ring: tuple[tuple[float, float], ...]
    kind: str = "grid"

    def contains(self, lat: float, lon: float) -> bool:
        """Return True when ``(lat, lon)`` lies inside this polygon ring."""
        return _point_in_polygon(lat, lon, self.ring)

    def bounding_box(self) -> tuple[float, float, float, float]:
        """Return ``(min_lat, max_lat, min_lon, max_lon)`` for the ring."""
        lats = [pt[0] for pt in self.ring]
        lons = [pt[1] for pt in self.ring]
        return min(lats), max(lats), min(lons), max(lons)


def _point_in_polygon(lat: float, lon: float, ring: tuple[tuple[float, float], ...]) -> bool:
    """Winding-number point-in-polygon test using lon/lat as x/y."""
    x, y = lon, lat
    winding = 0
    for i in range(len(ring)):
        y1, x1 = ring[i]
        y2, x2 = ring[(i + 1) % len(ring)]
        if y1 <= y:
            if y2 > y and (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1) > 0:
                winding += 1
        else:
            if y2 <= y and (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1) < 0:
                winding -= 1
    return winding != 0


def _build_zone_polygons() -> tuple[ZonePolygon, ...]:
    """Materialize lookup polygons from geo definitions."""
    by_name: dict[str, ZonePolygon] = {}
    for name, ring in AUSTIN_POI_ZONE_RINGS.items():
        by_name[name] = ZonePolygon(name=name, ring=ring, kind="poi")
    for name, ring in AUSTIN_BASE_ZONE_POLYGONS:
        if name in AUSTIN_POI_ZONE_RINGS:
            continue
        by_name[name] = ZonePolygon(name=name, ring=ring, kind="grid")
    ordered: list[ZonePolygon] = []
    for name in AUSTIN_ZONE_LOOKUP_ORDER:
        zone = by_name.get(name)
        if zone is not None:
            ordered.append(zone)
    for name, zone in by_name.items():
        if name not in AUSTIN_ZONE_LOOKUP_ORDER:
            ordered.append(zone)
    return tuple(ordered)


AUSTIN_ZONE_POLYGONS: tuple[ZonePolygon, ...] = _build_zone_polygons()

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

POI_ZONE_NAMES: frozenset[str] = frozenset(AUSTIN_POI_ZONE_RINGS)


def all_zone_names() -> list[str]:
    """Return canonical zone labels for operator controls."""
    seen: set[str] = set()
    names: list[str] = []
    for zone in AUSTIN_ZONE_POLYGONS:
        if zone.name not in seen:
            seen.add(zone.name)
            names.append(zone.name)
    return sorted(names)


def zone_for_point(lat: float, lon: float, fallback: str = "unknown") -> str:
    """Return demand zone for a WGS-84 coordinate using highway-aligned polygons."""
    for poi_name, ring in AUSTIN_POI_ZONE_RINGS.items():
        if _point_in_polygon(lat, lon, ring):
            return poi_name
    for name, ring in AUSTIN_BASE_ZONE_POLYGONS:
        if _point_in_polygon(lat, lon, ring):
            return name
    return fallback


def exclusive_zone_polygons() -> dict[str, list[list[tuple[float, float]]]]:
    """Highway-aligned polygons grouped by zone name for map overlays."""
    polys: dict[str, list[list[tuple[float, float]]]] = {}
    for name, ring in AUSTIN_BASE_ZONE_POLYGONS:
        polys.setdefault(name, []).append(list(ring))
    return polys


def poi_zone_polygons() -> dict[str, list[tuple[float, float]]]:
    """POI core polygons drawn with higher emphasis on the map."""
    return {name: list(ring) for name, ring in AUSTIN_POI_ZONE_RINGS.items()}


def zone_bounding_boxes() -> dict[str, tuple[float, float, float, float]]:
    """Return merged ``(min_lat, max_lat, min_lon, max_lon)`` per zone label."""
    boxes: dict[str, list[float]] = {}
    for name, ring in [*AUSTIN_BASE_ZONE_POLYGONS, *((n, r) for n, r in AUSTIN_POI_ZONE_RINGS.items())]:
        lats = [pt[0] for pt in ring]
        lons = [pt[1] for pt in ring]
        if name not in boxes:
            boxes[name] = [min(lats), max(lats), min(lons), max(lons)]
            continue
        b = boxes[name]
        b[0] = min(b[0], min(lats))
        b[1] = max(b[1], max(lats))
        b[2] = min(b[2], min(lons))
        b[3] = max(b[3], max(lons))
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


def sample_interior_point(ring: tuple[tuple[float, float], ...]) -> tuple[float, float]:
    """Return a point likely inside ``ring`` for tests and diagnostics."""
    min_lat, max_lat, min_lon, max_lon = ZonePolygon(name="", ring=ring).bounding_box()
    for _ in range(32):
        lat = (min_lat + max_lat) / 2
        lon = (min_lon + max_lon) / 2
        if _point_in_polygon(lat, lon, ring):
            return lat, lon
        min_lat = (min_lat + lat) / 2
        max_lat = (max_lat + lat) / 2
        min_lon = (min_lon + lon) / 2
        max_lon = (max_lon + lon) / 2
    lats = [pt[0] for pt in ring]
    lons = [pt[1] for pt in ring]
    return (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
