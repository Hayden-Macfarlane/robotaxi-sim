"""Street geometry routing tests."""

from __future__ import annotations

from routing.geo import polyline_length_km
from fixture_loader import load_fixture_router


def test_route_geometry_has_multiple_points() -> None:
    """Route polyline should follow curved edge geometry, not single chord."""
    router = load_fixture_router()
    leg = router.route_between(30.20, -97.80, 30.21, -97.77)
    assert leg is not None
    assert len(leg.geometry) >= 3
    assert len(leg.edge_ids) >= 2


def test_route_geometry_length_matches_edges() -> None:
    """Concatenated geometry length should be positive and plausible."""
    router = load_fixture_router()
    leg = router.route_between(30.20, -97.80, 30.22, -97.78)
    assert leg is not None
    geom_km = polyline_length_km(leg.geometry)
    assert geom_km > 0.5
    assert leg.travel_time_min > 0.0


def test_position_on_route_midpoint() -> None:
    """Mid-route progress should land between endpoints."""
    router = load_fixture_router()
    leg = router.route_between(30.20, -97.80, 30.22, -97.78)
    assert leg is not None
    start, _ = router.position_on_leg(leg, 0.0)
    mid, heading = router.position_on_leg(leg, 0.5)
    end, _ = router.position_on_leg(leg, 1.0)
    assert start.lat != end.lat or start.lon != end.lon
    assert 0.0 <= heading <= 360.0
    assert min(start.lat, end.lat) <= mid.lat <= max(start.lat, end.lat)
