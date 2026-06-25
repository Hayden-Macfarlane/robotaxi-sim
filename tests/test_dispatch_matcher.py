"""Dispatch matcher tests."""

from __future__ import annotations

from core_data.models import GeoPoint, TripRequest, TripStatus, Vehicle, VehicleState
from dispatch.matcher import pick_best_vehicle
from fixture_loader import load_fixture_router


def test_picks_nearest_idle_vehicle() -> None:
    """Matcher should prefer the vehicle closest to trip origin."""
    router = load_fixture_router()
    origin_node = router.nodes["n-a"]
    far_node = router.nodes["n-d"]
    trip = TripRequest(
        id="t1",
        origin=GeoPoint(lat=origin_node.lat, lon=origin_node.lon),
        destination=GeoPoint(lat=far_node.lat, lon=far_node.lon),
        origin_snap_node_id=origin_node.id,
        destination_snap_node_id=far_node.id,
        status=TripStatus.PENDING,
        requested_at_h=0.0,
    )
    vehicles = {
        "near": Vehicle(
            id="near",
            state=VehicleState.IDLE,
            lat=origin_node.lat,
            lon=origin_node.lon,
            current_node_id=origin_node.id,
        ),
        "far": Vehicle(
            id="far",
            state=VehicleState.IDLE,
            lat=far_node.lat,
            lon=far_node.lon,
            current_node_id=far_node.id,
        ),
    }
    match = pick_best_vehicle(trip, vehicles, router)
    assert match is not None
    assert match.vehicle_id == "near"
