"""Snap-to-street spatial index tests."""

from __future__ import annotations

from fixture_loader import load_fixture_router


def test_snap_projects_onto_segment_not_node() -> None:
    """A point near a curve should snap onto the street segment."""
    router = load_fixture_router()
    snap = router.snap_to_network(30.2065, -97.7935)
    assert snap is not None
    assert snap.distance_km < 0.02
    assert snap.edge_id in router.edges


def test_snap_point_uses_street_geometry() -> None:
    """snap_point should return on-street coordinates."""
    router = load_fixture_router()
    _, point = router.snap_point(30.205, -97.792)
    assert 30.19 < point.lat < 30.23
    assert -97.81 < point.lon < -97.76
