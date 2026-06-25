"""Unit tests for the fleet routing rule engine."""

from __future__ import annotations

import random

from core_data.models import GeoPoint, NetworkPolicy, SpecialEvent, TripRequest, TripStatus, Vehicle, VehicleState
from demand.generator import DemandGenerator
from fleet_routing.context import build_routing_context
from fleet_routing.defaults import default_routing_rules
from fleet_routing.engine import RuleEvaluator
from fleet_routing.models import (
    ActionType,
    CompareOp,
    ConditionType,
    RoutingAction,
    RoutingCondition,
    RoutingRule,
    RoutingRuleSet,
    RulePhase,
)
from fixture_loader import load_fixture_router


def _ctx(*, supply: dict[str, int] | None = None, pending: dict[str, int] | None = None):
    router = load_fixture_router()
    demand = DemandGenerator()
    policy = NetworkPolicy(fleet_size=6, max_idle_per_zone=3)
    return build_routing_context(
        router,
        policy,
        demand,
        sim_time_h=17.0,
        supply_by_zone=supply or {},
        pending_by_zone=pending or {},
        events=[],
        rng=random.Random(0),
    )


def test_default_rules_include_dispatch_and_reposition() -> None:
    """Default playbook covers dispatch and reposition phases."""
    rules = default_routing_rules()
    phases = {r.phase for r in rules.rules}
    assert RulePhase.DISPATCH in phases
    assert RulePhase.REPOSITION in phases


def test_dispatch_rule_matches_pending_trip() -> None:
    """Serve waiting riders rule assigns nearest eligible vehicle."""
    router = load_fixture_router()
    ctx = _ctx(pending={"southwest": 1})
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
        "v-1": Vehicle(
            id="v-1",
            state=VehicleState.IDLE,
            lat=30.20,
            lon=-97.80,
            current_node_id="n-a",
        ),
    }
    ev = RuleEvaluator(default_routing_rules())
    decision = ev.evaluate_dispatch(ctx, trip, vehicles, assigned_vehicle_ids=set())
    assert decision is not None
    assert decision.vehicle_id == "v-1"
    assert decision.action == ActionType.ASSIGN_NEAREST_ELIGIBLE


def test_reposition_idle_rule_fires() -> None:
    """Idle timeout rule triggers reposition when idle long enough."""
    router = load_fixture_router()
    ctx = _ctx(supply={"central": 0, "downtown": 0}, pending={"downtown": 2})
    vehicle = Vehicle(
        id="v-1",
        state=VehicleState.IDLE,
        lat=30.20,
        lon=-97.80,
        current_node_id="n-a",
        idle_since_h=16.0,
    )
    ev = RuleEvaluator(default_routing_rules())
    decision = ev.evaluate_reposition(ctx, vehicle, claimed=set())
    assert decision is not None
    assert decision.action == ActionType.REPOSITION_TO_BEST_DEFICIT


def test_rule_priority_first_match_wins() -> None:
    """Lower priority number wins when multiple rules could match."""
    rules = RoutingRuleSet(
        rules=[
            RoutingRule(
                id="hold-first",
                name="Hold",
                priority=1,
                phase=RulePhase.REPOSITION,
                conditions=[
                    RoutingCondition(type=ConditionType.IDLE_MINUTES, operator=CompareOp.GTE, value=1.0),
                ],
                action=RoutingAction(type=ActionType.HOLD),
            ),
            RoutingRule(
                id="move-second",
                name="Move",
                priority=2,
                phase=RulePhase.REPOSITION,
                conditions=[
                    RoutingCondition(type=ConditionType.IDLE_MINUTES, operator=CompareOp.GTE, value=1.0),
                ],
                action=RoutingAction(type=ActionType.REPOSITION_TO_BEST_DEFICIT),
            ),
        ],
    )
    ctx = _ctx()
    vehicle = Vehicle(
        id="v-1",
        state=VehicleState.IDLE,
        lat=30.20,
        lon=-97.80,
        current_node_id="n-a",
        idle_since_h=16.0,
    )
    ev = RuleEvaluator(rules)
    decision = ev.evaluate_reposition(ctx, vehicle, claimed=set())
    assert decision is not None
    assert decision.action == ActionType.HOLD


def test_active_event_condition() -> None:
    """Active event condition matches during event window."""
    router = load_fixture_router()
    events = [
        SpecialEvent(
            id="ev-1",
            label="Concert",
            zone="east_side",
            start_h=16.0,
            end_h=20.0,
            demand_multiplier=2.0,
        ),
    ]
    ctx = build_routing_context(
        router,
        NetworkPolicy(),
        DemandGenerator(),
        sim_time_h=17.0,
        supply_by_zone={},
        pending_by_zone={},
        events=events,
    )
    rule = RoutingRule(
        id="event-rule",
        name="Event",
        priority=1,
        phase=RulePhase.REPOSITION,
        conditions=[RoutingCondition(type=ConditionType.ACTIVE_EVENT, zone="east_side")],
        action=RoutingAction(type=ActionType.HOLD),
    )
    vehicle = Vehicle(
        id="v-1",
        state=VehicleState.IDLE,
        lat=30.20,
        lon=-97.80,
        current_node_id="n-a",
    )
    ev = RuleEvaluator(RoutingRuleSet(rules=[rule]))
    decision = ev.evaluate_reposition(ctx, vehicle, claimed=set())
    assert decision is not None
    assert decision.action == ActionType.HOLD
