"""Tests for depot release valve and facility routing."""

from __future__ import annotations

from core_data.models import Facility, NetworkPolicy, NodeKind, Vehicle, VehicleState
from dispatch.matcher import pick_best_vehicle
from simulation_loop.manager import SimulationManager
from simulation_loop.state import SimulationState


def test_depot_vehicles_excluded_from_dispatch() -> None:
    from core_data.models import GeoPoint, TripRequest, TripStatus
    from fixture_loader import load_fixture_router

    router = load_fixture_router()
    trip = TripRequest(
        id="t1",
        origin=GeoPoint(lat=30.20, lon=-97.80),
        destination=GeoPoint(lat=30.22, lon=-97.78),
        origin_snap_node_id="n-a",
        destination_snap_node_id="n-c",
        requested_at_h=0.0,
    )
    vehicles = {
        "v-street": Vehicle(id="v-street", state=VehicleState.IDLE, lat=30.20, lon=-97.80, current_node_id="n-a"),
        "v-depot": Vehicle(
            id="v-depot",
            state=VehicleState.AT_DEPOT,
            lat=30.20,
            lon=-97.80,
            current_node_id="n-a",
            facility_id="depot-mini",
        ),
    }
    match = pick_best_vehicle(trip, vehicles, router)
    assert match is not None
    assert match.vehicle_id == "v-street"


def test_release_from_facility_returns_idle(sim_manager: SimulationManager) -> None:
    vehicle = next(iter(sim_manager.state.vehicles.values()))
    vehicle.state = VehicleState.AT_DEPOT
    vehicle.facility_id = "depot-main"
    err = sim_manager.release_from_facility(vehicle.id)
    assert err is None
    assert vehicle.state == VehicleState.IDLE
    assert vehicle.facility_id is None


def test_manual_hold_blocks_auto_reposition(sim_manager: SimulationManager) -> None:
    vehicle = next(v for v in sim_manager.state.vehicles.values() if v.state == VehicleState.IDLE)
    vehicle.manual_hold_until_h = sim_manager.current_time + 10.0
    vehicle.idle_since_h = sim_manager.current_time - 1.0
    before = vehicle.lat
    sim_manager._apply_routing_rules()
    assert vehicle.lat == before
