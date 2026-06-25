"""City router pathfinding tests."""

from __future__ import annotations

import pytest

from routing.city_loader import load_city_graph
from routing.city_router import CityRouter
from fixture_loader import load_fixture_router


@pytest.mark.slow
@pytest.mark.timeout(120)
def test_path_between_random_nodes() -> None:
    """Any two grid nodes should have a finite travel time."""
    nodes, edges = load_city_graph("austin")
    router = CityRouter(nodes, edges)
    origin = nodes[0].id
    dest = nodes[-1].id
    result = router.find_shortest_path(origin, dest)
    assert result is not None
    path, minutes = result
    assert len(path) >= 2
    assert minutes > 0.0


@pytest.mark.slow
@pytest.mark.timeout(120)
def test_same_node_zero_travel() -> None:
    """Origin equal to destination costs zero."""
    nodes, edges = load_city_graph("austin")
    router = CityRouter(nodes, edges)
    nid = nodes[0].id
    result = router.find_shortest_path(nid, nid)
    assert result is not None
    assert result[1] == 0.0


@pytest.mark.slow
@pytest.mark.timeout(120)
def test_snap_point_returns_nearest_node() -> None:
    """Snap should return a valid graph vertex when far from streets."""
    nodes, edges = load_city_graph("austin")
    router = CityRouter(nodes, edges)
    node = nodes[0]
    snap_id, geo = router.snap_point(node.lat, node.lon)
    assert snap_id == node.id
    assert abs(geo.lat - node.lat) < 0.01


def test_route_between_returns_route_leg() -> None:
    """Route between coordinates should return a RouteLeg with geometry."""
    router = load_fixture_router()
    a = router.nodes["n-a"]
    b = router.nodes["n-d"]
    leg = router.route_between(a.lat, a.lon, b.lat, b.lon)
    assert leg is not None
    assert len(leg.node_path) >= 2
    assert leg.travel_time_min > 0.0
    assert len(leg.geometry) >= 2


def test_position_along_polyline_endpoints() -> None:
    """Interpolation at 0 and 1 should return polyline endpoints."""
    from core_data.models import GeoPoint

    router = load_fixture_router()
    polyline = [
        GeoPoint(lat=30.20, lon=-97.80),
        GeoPoint(lat=30.21, lon=-97.79),
    ]
    start = router.position_along_polyline(polyline, 0.0)
    end = router.position_along_polyline(polyline, 1.0)
    assert start.lat == polyline[0].lat
    assert end.lat == polyline[-1].lat
