"""Tests for v2 dispatch action aliases and facility transit state."""

from __future__ import annotations

import random

from core_data.models import GeoPoint, NetworkPolicy, TripRequest, TripStatus, Vehicle, VehicleState
from demand.generator import DemandGenerator
from fleet_routing.v2.actions import execute_dispatch_action
from fleet_routing.v2.context import KpiSnapshot, build_eval_context
from fleet_routing.v2.models import ActionSpec, ActionTypeV2
from fixture_loader import load_fixture_router


def _eval_ctx(*, vehicles: dict[str, Vehicle], trips: dict[str, TripRequest]):
    router = load_fixture_router()
    demand = DemandGenerator()
    policy = NetworkPolicy(fleet_size=6, max_idle_per_zone=3)
    return build_eval_context(
        router,
        policy,
        demand,
        sim_time_h=0.0,
        supply_by_zone={},
        pending_by_zone={"southwest": 1},
        events=[],
        vehicles=vehicles,
        trips=trips,
        facilities={},
        kpis=KpiSnapshot(),
        rng=random.Random(0),
    )


def test_assign_nearest_idle_skips_repositioning_vehicle() -> None:
    """Idle-only alias must not pick a closer repositioning car."""
    router = load_fixture_router()
    origin = router.nodes["n-a"]
    far = router.nodes["n-d"]
    trip = TripRequest(
        id="t1",
        origin=GeoPoint(lat=origin.lat, lon=origin.lon),
        destination=GeoPoint(lat=far.lat, lon=far.lon),
        origin_snap_node_id=origin.id,
        destination_snap_node_id=far.id,
        status=TripStatus.PENDING,
        requested_at_h=0.0,
    )
    vehicles = {
        "repo-near": Vehicle(
            id="repo-near",
            state=VehicleState.REPOSITIONING,
            lat=origin.lat,
            lon=origin.lon,
            current_node_id=origin.id,
        ),
        "idle-far": Vehicle(
            id="idle-far",
            state=VehicleState.IDLE,
            lat=far.lat,
            lon=far.lon,
            current_node_id=far.id,
        ),
    }
    ctx = _eval_ctx(vehicles=vehicles, trips={"t1": trip})
    result = execute_dispatch_action(
        ActionSpec(type=ActionTypeV2.ASSIGN_NEAREST_IDLE),
        ctx,
        trip,
        vehicles,
        constants={},
        assigned=set(),
    )
    assert result is not None
    assert result.vehicle_id == "idle-far"


def test_assign_nearest_available_picks_repositioning_vehicle() -> None:
    """Available alias may redirect a closer repositioning car to the rider."""
    router = load_fixture_router()
    origin = router.nodes["n-a"]
    far = router.nodes["n-d"]
    trip = TripRequest(
        id="t1",
        origin=GeoPoint(lat=origin.lat, lon=origin.lon),
        destination=GeoPoint(lat=far.lat, lon=far.lon),
        origin_snap_node_id=origin.id,
        destination_snap_node_id=far.id,
        status=TripStatus.PENDING,
        requested_at_h=0.0,
    )
    vehicles = {
        "repo-near": Vehicle(
            id="repo-near",
            state=VehicleState.REPOSITIONING,
            lat=origin.lat,
            lon=origin.lon,
            current_node_id=origin.id,
        ),
        "idle-far": Vehicle(
            id="idle-far",
            state=VehicleState.IDLE,
            lat=far.lat,
            lon=far.lon,
            current_node_id=far.id,
        ),
    }
    ctx = _eval_ctx(vehicles=vehicles, trips={"t1": trip})
    result = execute_dispatch_action(
        ActionSpec(type=ActionTypeV2.ASSIGN_NEAREST_AVAILABLE),
        ctx,
        trip,
        vehicles,
        constants={},
        assigned=set(),
    )
    assert result is not None
    assert result.vehicle_id == "repo-near"


def test_pickup_nearest_template_is_insertable() -> None:
    """Library template uses nearest-available dispatch action."""
    from fleet_routing.v2.templates import all_rule_templates

    tpl = next(t for t in all_rule_templates() if t.id == "tpl-pickup-nearest")
    assert tpl.rule.action.type == ActionTypeV2.ASSIGN_NEAREST_AVAILABLE
    assert tpl.rule.when.metric is not None
    assert tpl.rule.when.metric.id == "zone.pending_demand"
