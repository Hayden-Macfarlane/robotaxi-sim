"""Tests for manual-first operator setup flow."""

from __future__ import annotations

import json
import random

import pytest

from core_data.models import (
    DispatchAssignmentMode,
    GeoPoint,
    NetworkPolicy,
    TripRequest,
    TripStatus,
    Vehicle,
    VehicleState,
)
from demand.generator import DemandGenerator
from dispatch.matcher import pick_best_vehicle, rank_dispatch_candidates
from event_engine.engine import Event, EventType, SimulationEngine
from fleet_routing.context import build_routing_context
from fleet_routing.defaults import dispatch_only_rules, manual_first_routing_rules
from fleet_routing.engine import RuleEvaluator
from fleet_routing.models import ActionType
from fixture_loader import load_fixture_router
from simulation_loop.manager import SimulationManager


@pytest.fixture
def mgr() -> SimulationManager:
    """Manager reset with a stable seed for setup tests."""
    from routing.city_loader import clear_city_graph_cache

    clear_city_graph_cache()
    manager = SimulationManager()
    manager.reset(seed=3)
    return manager


def test_reset_starts_with_blank_playbook(mgr: SimulationManager) -> None:
    """Reset starts with no rules, no auto-dispatch, and no seeded trips."""
    assert not mgr.state.policy.auto_dispatch_enabled
    assert not mgr.state.routing_rules.routing_enabled
    assert mgr.state.operator_setup.dispatch_assignment_mode == DispatchAssignmentMode.MANUAL
    assert mgr.state.playbook_v2.rules == []
    assert mgr.state.playbook_v2.constants == {}
    assert mgr.state.playbook_v2.enabled
    assert len(mgr.state.trips) == 0


def test_setup_enables_closest_idle_or_repositioning(mgr: SimulationManager) -> None:
    """Operator setup applies auto-dispatch with extended vehicle pool."""
    mgr.set_operator_setup(
        dispatch_assignment_mode=DispatchAssignmentMode.CLOSEST_IDLE_OR_REPOSITIONING,
    )
    assert mgr.setup_complete
    assert mgr.state.policy.auto_dispatch_enabled
    assert mgr.state.routing_rules.routing_enabled
    assert len(mgr.state.routing_rules.rules) == 1
    assert mgr.state.routing_rules.rules[0].action.type == ActionType.ASSIGN_NEAREST_IDLE_OR_REPOSITIONING


def test_setup_manual_keeps_automation_off(mgr: SimulationManager) -> None:
    """Manual mode leaves auto-dispatch and routing disabled."""
    mgr.set_operator_setup(dispatch_assignment_mode=DispatchAssignmentMode.MANUAL)
    assert mgr.setup_complete
    assert not mgr.state.policy.auto_dispatch_enabled
    assert not mgr.state.routing_rules.routing_enabled


def test_snapshot_includes_dispatch_candidates(mgr: SimulationManager) -> None:
    """Pending trips expose ranked vehicle options after setup."""
    mgr.set_operator_setup(dispatch_assignment_mode=DispatchAssignmentMode.MANUAL)
    snap = json.loads(mgr.build_ui_snapshot(is_running=False, speed_multiplier=1.0))
    assert "dispatch_candidates" in snap
    assert isinstance(snap["dispatch_candidates"], dict)
    pending = [t for t in mgr.state.trips.values() if t.status == TripStatus.PENDING]
    if pending:
        assert pending[0].id in snap["dispatch_candidates"]


def test_dispatch_repositioning_vehicle() -> None:
    """Manual dispatch can assign a trip to a repositioning vehicle."""
    from routing.city_loader import clear_city_graph_cache

    clear_city_graph_cache()
    mgr = SimulationManager()
    mgr.reset(seed=5)
    mgr.set_operator_setup(dispatch_assignment_mode=DispatchAssignmentMode.MANUAL)
    trip = TripRequest(
        id="trip-manual",
        origin=GeoPoint(lat=30.20, lon=-97.80),
        destination=GeoPoint(lat=30.21, lon=-97.79),
        origin_snap_node_id="n-a",
        destination_snap_node_id="n-b",
        requested_at_h=0.0,
    )
    mgr.state.trips[trip.id] = trip
    vehicle = next(
        v for v in mgr.state.vehicles.values()
        if v.state == VehicleState.IDLE and (round(v.lat, 2), round(v.lon, 2)) != (30.20, -97.80)
    )
    err = mgr.reposition_vehicle_to_point(vehicle.id, 30.20, -97.80, manual=True)
    assert err is None
    assert mgr.state.vehicles[vehicle.id].state == VehicleState.REPOSITIONING
    err = mgr.dispatch_vehicle(vehicle.id, trip.id)
    assert err is None
    assert mgr.state.vehicles[vehicle.id].state == VehicleState.TO_PICKUP
    assert mgr.state.trips[trip.id].status == TripStatus.MATCHED


def test_pick_best_includes_repositioning() -> None:
    """Extended matcher considers repositioning vehicles."""
    router = load_fixture_router()
    trip = TripRequest(
        id="trip-1",
        origin=GeoPoint(lat=30.20, lon=-97.80),
        destination=GeoPoint(lat=30.21, lon=-97.79),
        origin_snap_node_id="n-a",
        destination_snap_node_id="n-b",
        requested_at_h=0.0,
    )
    vehicles = {
        "idle-far": Vehicle(
            id="idle-far",
            state=VehicleState.IDLE,
            lat=30.50,
            lon=-97.50,
            current_node_id="n-a",
        ),
        "repo-near": Vehicle(
            id="repo-near",
            state=VehicleState.REPOSITIONING,
            lat=30.20,
            lon=-97.80,
            current_node_id="n-a",
        ),
    }
    match_idle = pick_best_vehicle(trip, vehicles, router, include_repositioning=False)
    assert match_idle is not None
    assert match_idle.vehicle_id == "idle-far"
    match_ext = pick_best_vehicle(trip, vehicles, router, include_repositioning=True)
    assert match_ext is not None
    assert match_ext.vehicle_id == "repo-near"


def test_idle_or_repositioning_rule_action() -> None:
    """Dispatch-only rule with extended action picks repositioning vehicle."""
    router = load_fixture_router()
    ctx = build_routing_context(
        router,
        NetworkPolicy(),
        DemandGenerator(),
        sim_time_h=17.0,
        supply_by_zone={},
        pending_by_zone={"southwest": 1},
        events=[],
        rng=random.Random(0),
    )
    trip = TripRequest(
        id="trip-1",
        origin=GeoPoint(lat=30.20, lon=-97.80),
        destination=GeoPoint(lat=30.21, lon=-97.79),
        origin_snap_node_id="n-a",
        destination_snap_node_id="n-b",
        requested_at_h=16.9,
        status=TripStatus.PENDING,
    )
    vehicles = {
        "idle-far": Vehicle(
            id="idle-far",
            state=VehicleState.IDLE,
            lat=30.50,
            lon=-97.50,
            current_node_id="n-a",
        ),
        "repo-near": Vehicle(
            id="repo-near",
            state=VehicleState.REPOSITIONING,
            lat=30.20,
            lon=-97.80,
            current_node_id="n-a",
        ),
    }
    rules = dispatch_only_rules(DispatchAssignmentMode.CLOSEST_IDLE_OR_REPOSITIONING)
    ev = RuleEvaluator(rules)
    decision = ev.evaluate_dispatch(ctx, trip, vehicles, assigned_vehicle_ids=set())
    assert decision is not None
    assert decision.vehicle_id == "repo-near"
    assert decision.action == ActionType.ASSIGN_NEAREST_IDLE_OR_REPOSITIONING


def test_cancel_events_for_entity() -> None:
    """Leg interrupt removes stale arrive events from the queue."""
    engine = SimulationEngine(initial_time=0.0)
    engine.schedule_event(
        Event(timestamp=1.0, event_type=EventType.VEHICLE_ARRIVE, entity_id="v-1", payload={}),
    )
    engine.schedule_event(
        Event(timestamp=2.0, event_type=EventType.DEMAND_TICK, entity_id="world", payload={}),
    )
    removed = engine.cancel_events_for_entity("v-1", event_type=EventType.VEHICLE_ARRIVE)
    assert removed == 1
    assert engine.peek_next_time() == 2.0


def test_manual_first_routing_rules_empty() -> None:
    """Manual-first playbook has routing disabled and no rules."""
    rules = manual_first_routing_rules()
    assert not rules.routing_enabled
    assert rules.rules == []


def test_rank_dispatch_candidates_sorted() -> None:
    """Candidates are returned in ETA order."""
    router = load_fixture_router()
    trip = TripRequest(
        id="trip-1",
        origin=GeoPoint(lat=30.20, lon=-97.80),
        destination=GeoPoint(lat=30.21, lon=-97.79),
        origin_snap_node_id="n-a",
        destination_snap_node_id="n-b",
        requested_at_h=0.0,
    )
    vehicles = {
        "v-far": Vehicle(id="v-far", state=VehicleState.IDLE, lat=30.50, lon=-97.50, current_node_id="n-a"),
        "v-near": Vehicle(id="v-near", state=VehicleState.IDLE, lat=30.20, lon=-97.80, current_node_id="n-a"),
    }
    ranked = rank_dispatch_candidates(trip, vehicles, router, limit=2)
    assert len(ranked) == 2
    assert ranked[0].vehicle_id == "v-near"
    assert ranked[0].eta_min <= ranked[1].eta_min
