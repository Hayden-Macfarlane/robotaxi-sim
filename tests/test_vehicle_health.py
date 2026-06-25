"""Tests for vehicle health wear and service logic."""

from __future__ import annotations

import random

from core_data.models import NetworkPolicy, Vehicle, VehicleState
from dispatch.matcher import pick_best_vehicle
from fleet.health import (
    apply_movement_wear,
    apply_trip_complete_wear,
    health_alert,
    is_dispatch_eligible,
    restore_after_service,
    service_duration_min,
)
from core_data.models import GeoPoint, TripRequest
from fixture_loader import load_fixture_router


def test_movement_wear_reduces_battery_and_condition() -> None:
    policy = NetworkPolicy(battery_drain_per_km=1.0, condition_drain_per_km=0.5)
    vehicle = Vehicle(id="v1", lat=0, lon=0, current_node_id="n-a")
    apply_movement_wear(vehicle, 10.0, policy)
    assert vehicle.battery_pct == 90.0
    assert vehicle.condition_pct == 95.0


def test_trip_complete_wear_reduces_cleanliness() -> None:
    policy = NetworkPolicy(cleanliness_drain_per_trip=2.0, cleanliness_spill_chance=0.0)
    vehicle = Vehicle(id="v1", lat=0, lon=0, current_node_id="n-a", cleanliness_pct=100.0)
    spilled = apply_trip_complete_wear(vehicle, policy, random.Random(0))
    assert not spilled
    assert vehicle.cleanliness_pct == 98.0


def test_spill_forces_ineligible() -> None:
    policy = NetworkPolicy(
        cleanliness_spill_chance=1.0,
        cleanliness_spill_floor_pct=8.0,
        low_cleanliness_pct=20.0,
    )
    vehicle = Vehicle(id="v1", lat=0, lon=0, current_node_id="n-a", state=VehicleState.IDLE)
    apply_trip_complete_wear(vehicle, policy, random.Random(0))
    assert vehicle.cleanliness_pct == 8.0
    assert not is_dispatch_eligible(vehicle, policy)
    assert health_alert(vehicle, policy) == "needs_cleaning"


def test_service_duration_scales_with_battery_deficit() -> None:
    policy = NetworkPolicy(charge_minutes_to_full=40.0)
    vehicle = Vehicle(id="v1", lat=0, lon=0, current_node_id="n-a", battery_pct=50.0)
    assert service_duration_min(vehicle, "charger", policy) == 20.0


def test_restore_after_service() -> None:
    vehicle = Vehicle(
        id="v1",
        lat=0,
        lon=0,
        current_node_id="n-a",
        battery_pct=10.0,
        cleanliness_pct=5.0,
        condition_pct=15.0,
    )
    restore_after_service(vehicle, "charger")
    assert vehicle.battery_pct == 100.0
    restore_after_service(vehicle, "cleaning")
    assert vehicle.cleanliness_pct == 100.0
    restore_after_service(vehicle, "maintenance")
    assert vehicle.condition_pct == 100.0


def test_matcher_excludes_unfit_vehicle() -> None:
    router = load_fixture_router()
    trip = TripRequest(
        id="t1",
        origin=GeoPoint(lat=30.20, lon=-97.80),
        destination=GeoPoint(lat=30.22, lon=-97.78),
        origin_snap_node_id="n-a",
        destination_snap_node_id="n-c",
        requested_at_h=0.0,
    )
    policy = NetworkPolicy(low_battery_pct=50.0)
    vehicles = {
        "v-fit": Vehicle(id="v-fit", state=VehicleState.IDLE, lat=30.20, lon=-97.80, current_node_id="n-a", battery_pct=80.0),
        "v-low": Vehicle(id="v-low", state=VehicleState.IDLE, lat=30.20, lon=-97.80, current_node_id="n-a", battery_pct=10.0),
    }
    match = pick_best_vehicle(trip, vehicles, router, policy=policy)
    assert match is not None
    assert match.vehicle_id == "v-fit"
