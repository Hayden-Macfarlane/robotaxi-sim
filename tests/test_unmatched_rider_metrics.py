"""Tests for unmatched-rider distance metrics."""

from __future__ import annotations

from core_data.models import GeoPoint, TripRequest, TripStatus, Vehicle, VehicleState
from fleet_routing.v2.context import SpatialIndex
from fleet_routing.v2.metrics import REGISTRY


def test_nearest_unmatched_rider_km() -> None:
    """Pending trip pickup distance is computed from vehicle position."""
    vehicle = Vehicle(id="v1", state=VehicleState.IDLE, lat=30.20, lon=-97.80, current_node_id="n-a")
    trips = {
        "t1": TripRequest(
            id="t1",
            origin=GeoPoint(lat=30.21, lon=-97.79),
            destination=GeoPoint(lat=30.22, lon=-97.78),
            origin_snap_node_id="n-b",
            destination_snap_node_id="n-c",
            requested_at_h=0.0,
            status=TripStatus.PENDING,
        ),
        "t2": TripRequest(
            id="t2",
            origin=GeoPoint(lat=30.50, lon=-97.50),
            destination=GeoPoint(lat=30.51, lon=-97.49),
            origin_snap_node_id="n-d",
            destination_snap_node_id="n-e",
            requested_at_h=0.0,
            status=TripStatus.MATCHED,
        ),
    }
    idx = SpatialIndex()
    dist = idx.nearest_unmatched_rider_km(vehicle, trips)
    assert dist is not None
    assert 0.0 < dist < 20.0


def test_unmatched_riders_within_km() -> None:
    """Only pending trips within radius are counted."""
    vehicle = Vehicle(id="v1", state=VehicleState.IDLE, lat=30.20, lon=-97.80, current_node_id="n-a")
    trips = {
        "near": TripRequest(
            id="near",
            origin=GeoPoint(lat=30.201, lon=-97.801),
            destination=GeoPoint(lat=30.22, lon=-97.78),
            origin_snap_node_id="n-b",
            destination_snap_node_id="n-c",
            requested_at_h=0.0,
            status=TripStatus.PENDING,
        ),
        "far": TripRequest(
            id="far",
            origin=GeoPoint(lat=30.50, lon=-97.50),
            destination=GeoPoint(lat=30.51, lon=-97.49),
            origin_snap_node_id="n-d",
            destination_snap_node_id="n-e",
            requested_at_h=0.0,
            status=TripStatus.PENDING,
        ),
    }
    idx = SpatialIndex()
    assert idx.unmatched_riders_within_km(vehicle, trips, radius_km=5.0) == 1
    assert idx.unmatched_riders_within_km(vehicle, trips, radius_km=100.0) == 2


def test_registry_exposes_unmatched_rider_metrics() -> None:
    """New metrics appear in catalog with demand category."""
    ids = {m.id for m in REGISTRY.all_meta()}
    assert "vehicle.nearest_unmatched_rider_km" in ids
    assert "vehicle.unmatched_riders_within_km" in ids
    nearest = REGISTRY.get("vehicle.nearest_unmatched_rider_km")
    assert nearest is not None
    assert nearest.meta.category.value == "demand"
