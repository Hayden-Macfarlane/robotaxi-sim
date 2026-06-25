"""Tests for Austin zone assignment and map overlay geometry."""

from __future__ import annotations

from routing.zones import (
    AUSTIN_BBOX,
    AUSTIN_ZONE_RECTS,
    all_zone_names,
    exclusive_zone_polygons,
    zone_for_point,
    zone_overlay_snapshot,
)

_POI_RECTS = AUSTIN_ZONE_RECTS[:3]


def test_all_zone_names_match_rect_labels() -> None:
    names = all_zone_names()
    assert "downtown" in names
    assert "campus" in names
    assert "kyle" in names
    assert "buda" in names
    assert "east_side" in names
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
            lats = [pt[0] for pt in ring]
            lons = [pt[1] for pt in ring]
            lat = (min(lats) + max(lats)) / 2
            lon = (min(lons) + max(lons)) / 2
            if any(rect.contains(lat, lon) for rect in _POI_RECTS):
                continue
            assert zone_for_point(lat, lon) == zone


def test_known_neighborhood_assignments() -> None:
    assert zone_for_point(30.205, -97.655) == "airport"
    assert zone_for_point(30.270, -97.742) == "downtown"
    assert zone_for_point(30.295, -97.730) == "campus"
    assert zone_for_point(30.245, -97.700) == "riverside"
    assert zone_for_point(30.300, -97.660) == "east_side"
    assert zone_for_point(30.235, -97.780) == "south_central"
    assert zone_for_point(30.250, -97.880) == "southwest"
    assert zone_for_point(30.160, -97.850) == "buda"
    assert zone_for_point(30.050, -97.870) == "kyle"
    assert zone_for_point(30.360, -97.750) == "domain"


def test_service_area_has_no_unassigned_gaps() -> None:
    """Every point in the Austin bbox should map to a named zone."""
    n, s, e, w = AUSTIN_BBOX["north"], AUSTIN_BBOX["south"], AUSTIN_BBOX["east"], AUSTIN_BBOX["west"]
    steps = 12
    for i in range(steps):
        lat = s + (n - s) * (i + 0.5) / steps
        for j in range(steps):
            lon = w + (e - w) * (j + 0.5) / steps
            assert zone_for_point(lat, lon) != "unknown"


def test_zone_overlay_snapshot_includes_neighborhoods() -> None:
    overlays = zone_overlay_snapshot()
    zones = {row["zone"] for row in overlays}
    assert "downtown" in zones
    assert "campus" in zones
    assert "east_side" in zones
    assert len(overlays) == len(all_zone_names())


def test_rects_are_declared_in_priority_order() -> None:
    assert AUSTIN_ZONE_RECTS[0].name == "airport"
    assert AUSTIN_ZONE_RECTS[1].name == "downtown"
