"""Tests for Austin zone assignment and map overlay geometry."""

from __future__ import annotations

from routing.austin_zones_geo import AUSTIN_POI_ZONE_RINGS
from routing.zones import (
    AUSTIN_BBOX,
    AUSTIN_ZONE_POLYGONS,
    all_zone_names,
    exclusive_zone_polygons,
    sample_interior_point,
    zone_for_point,
    zone_overlay_snapshot,
    _point_in_polygon,
)
from routing.austin_zones_geo import AUSTIN_BASE_ZONE_POLYGONS


def test_all_zone_names_include_neighborhoods() -> None:
    names = all_zone_names()
    assert "downtown" in names
    assert "campus" in names
    assert "south_central" in names
    assert "kyle" in names
    assert len(names) == len(set(names))


def test_exclusive_polygons_stay_in_bbox() -> None:
    polys = exclusive_zone_polygons()
    n, s, e, w = AUSTIN_BBOX["north"], AUSTIN_BBOX["south"], AUSTIN_BBOX["east"], AUSTIN_BBOX["west"]
    for rings in polys.values():
        for ring in rings:
            lats = [pt[0] for pt in ring]
            lons = [pt[1] for pt in ring]
            assert min(lats) >= s - 1e-9
            assert max(lats) <= n + 1e-9
            assert min(lons) >= w - 1e-9
            assert max(lons) <= e + 1e-9


def test_overlay_points_match_zone_for_point() -> None:
    polys = exclusive_zone_polygons()
    for zone, rings in polys.items():
        for ring in rings:
            lat, lon = sample_interior_point(tuple(ring))
            if any(_point_in_polygon(lat, lon, poi_ring) for poi_ring in AUSTIN_POI_ZONE_RINGS.values()):
                continue
            assert zone_for_point(lat, lon) == zone


def test_south_central_is_between_mopac_i35_and_ben_white() -> None:
    """South central interior sits between Loop 1, I-35, and the Ben White corridor."""
    assert zone_for_point(30.22, -97.75) == "south_central"
    assert zone_for_point(30.234, -97.757) == "south_central"
    assert zone_for_point(30.245, -97.735) == "south_central"


def test_known_neighborhood_assignments() -> None:
    assert zone_for_point(30.205, -97.655) == "airport"
    assert zone_for_point(30.270, -97.742) == "downtown"
    assert zone_for_point(30.295, -97.730) == "campus"
    assert zone_for_point(30.245, -97.705) == "riverside"
    assert zone_for_point(30.300, -97.660) == "east_side"
    assert zone_for_point(30.250, -97.880) == "southwest"
    assert zone_for_point(30.160, -97.850) == "buda"
    assert zone_for_point(30.050, -97.870) == "kyle"
    assert zone_for_point(30.360, -97.750) == "westlake"


def test_service_area_has_no_unassigned_gaps() -> None:
    """Every point in the Austin bbox should map to a named zone."""
    n, s, e, w = AUSTIN_BBOX["north"], AUSTIN_BBOX["south"], AUSTIN_BBOX["east"], AUSTIN_BBOX["west"]
    steps = 20
    for i in range(steps):
        lat = s + (n - s) * (i + 0.5) / steps
        for j in range(steps):
            lon = w + (e - w) * (j + 0.5) / steps
            assert zone_for_point(lat, lon) != "unknown"


def test_base_partition_has_no_overlaps() -> None:
    n, s, e, w = AUSTIN_BBOX["north"], AUSTIN_BBOX["south"], AUSTIN_BBOX["east"], AUSTIN_BBOX["west"]
    for i in range(24):
        lat = s + (n - s) * (i + 0.5) / 24
        for j in range(24):
            lon = w + (e - w) * (j + 0.5) / 24
            hits = [name for name, ring in AUSTIN_BASE_ZONE_POLYGONS if _point_in_polygon(lat, lon, ring)]
            assert len(hits) <= 1


def test_zone_overlay_snapshot_includes_neighborhoods() -> None:
    overlays = zone_overlay_snapshot()
    zones = {row["zone"] for row in overlays}
    assert "downtown" in zones
    assert "south_central" in zones
    assert len(overlays) == len(all_zone_names())


def test_polygons_are_declared_in_priority_order() -> None:
    assert AUSTIN_ZONE_POLYGONS[0].name == "airport"
    assert AUSTIN_ZONE_POLYGONS[1].name == "downtown"
