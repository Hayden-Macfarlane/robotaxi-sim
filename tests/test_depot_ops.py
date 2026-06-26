"""Tests for depot release valve and facility routing."""

from __future__ import annotations

import random

from core_data.models import GeoPoint, NetworkPolicy, TripRequest, TripStatus, Vehicle, VehicleState
from dispatch.matcher import pick_best_vehicle
from dispatch.reposition import pick_staging_point
from event_engine.engine import Event, EventType
from fixture_loader import load_fixture_router
from simulation_loop.manager import SimulationManager


def test_depot_vehicles_excluded_from_dispatch() -> None:
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


def test_release_from_facility_routes_to_zone(sim_manager: SimulationManager) -> None:
    vehicle = next(iter(sim_manager.state.vehicles.values()))
    router = sim_manager._router
    zones = list(router.zone_bounding_boxes().keys())
    assert zones
    target_zone = zones[0]
    vehicle.state = VehicleState.CHARGING
    vehicle.facility_id = "charger-mini"
    fac = sim_manager.state.facilities["charger-mini"]
    vehicle.lat = fac.lat
    vehicle.lon = fac.lon
    vehicle.current_node_id = fac.node_id
    sim_manager._engine.schedule_event(
        Event(
            timestamp=sim_manager.current_time + 1.0,
            event_type=EventType.VEHICLE_ARRIVE,
            entity_id=vehicle.id,
            payload={"leg": "service_complete", "facility_id": fac.id, "facility_kind": "charger"},
        ),
    )
    err = sim_manager.release_from_facility(vehicle.id, target_zone)
    assert err is None
    assert vehicle.facility_id is None
    assert vehicle.state in (VehicleState.IDLE, VehicleState.REPOSITIONING)
    removed = sim_manager._engine.cancel_events_for_entity(vehicle.id, event_type=EventType.VEHICLE_ARRIVE)
    assert removed == 0


def test_release_blocked_at_zone_cap(sim_manager: SimulationManager) -> None:
    vehicle = next(iter(sim_manager.state.vehicles.values()))
    router = sim_manager._router
    target_zone = list(router.zone_bounding_boxes().keys())[0]
    vehicle.state = VehicleState.AT_DEPOT
    vehicle.facility_id = "depot-mini"
    sim_manager._state.policy = sim_manager._state.policy.model_copy(
        update={"max_idle_per_zone": 0, "max_idle_by_zone": {target_zone: 0}},
    )
    err = sim_manager.release_from_facility(vehicle.id, target_zone)
    assert err is not None
    assert "cap" in err.lower()


def test_send_to_facility_all_kinds(sim_manager: SimulationManager) -> None:
    vehicle = next(v for v in sim_manager.state.vehicles.values() if v.state == VehicleState.IDLE)
    for fac in sim_manager.state.facilities.values():
        vehicle.state = VehicleState.IDLE
        vehicle.facility_id = None
        err = sim_manager.send_to_facility(vehicle.id, fac.id, manual=True)
        assert err is None, f"failed for {fac.kind}: {err}"
        assert vehicle.state == VehicleState.TO_FACILITY
        sim_manager._clear_leg(vehicle)
        sim_manager._engine.cancel_events_for_entity(vehicle.id, event_type=EventType.VEHICLE_ARRIVE)
        vehicle.state = VehicleState.IDLE


def test_manual_reposition_preempts_in_progress(sim_manager: SimulationManager) -> None:
    vehicle = next(v for v in sim_manager.state.vehicles.values() if v.state == VehicleState.IDLE)
    route = sim_manager._router.route_between(vehicle.lat, vehicle.lon, 30.22, -97.78)
    assert route is not None
    vehicle.state = VehicleState.REPOSITIONING
    sim_manager._start_leg(
        vehicle,
        route,
        leg="reposition",
        payload={"node_id": "n-c", "lat": 30.22, "lon": -97.78, "manual": True},
        track_deadhead=True,
    )
    assert vehicle.state == VehicleState.REPOSITIONING
    err = sim_manager.reposition_vehicle_to_point(vehicle.id, 30.21, -97.77, manual=True)
    assert err is None
    assert vehicle.state in (VehicleState.IDLE, VehicleState.REPOSITIONING)


def test_manual_hold_blocks_auto_reposition(sim_manager: SimulationManager) -> None:
    vehicle = next(v for v in sim_manager.state.vehicles.values() if v.state == VehicleState.IDLE)
    vehicle.manual_hold_until_h = sim_manager.current_time + 10.0
    vehicle.idle_since_h = sim_manager.current_time - 1.0
    before = vehicle.lat
    sim_manager._apply_routing_rules()
    assert vehicle.lat == before
