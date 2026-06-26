"""Tests for extended operator controls and policy wiring."""

from __future__ import annotations

import json

from core_data.models import NetworkPolicy, ScenarioPreset, TripStatus, VehicleState
from dispatch.matcher import estimate_trip_fare, rank_dispatch_candidates
from fixture_loader import load_fixture_router
from simulation_loop.fleet_ops import compute_operator_alerts
from simulation_loop.manager import SimulationManager
from simulation_loop.scenarios import scenario_policy_patch


def test_estimate_trip_fare_uses_per_minute_and_mile() -> None:
    """Fare reflects per-minute and per-mile policy levers."""
    pol = NetworkPolicy(base_fare=5.0, surge_multiplier=2.0, per_minute_fare=0.2, per_mile_fare=1.0)
    fare = estimate_trip_fare(10.0, 8.0, pol)
    assert fare == 5.0 * 2.0 + 10.0 * 0.2 + (8.0 / 1.60934) * 1.0


def test_cross_zone_penalty_affects_score() -> None:
    """Cross-zone dispatch penalty increases match score."""
    router = load_fixture_router()
    from core_data.models import GeoPoint, TripRequest, Vehicle

    trip = TripRequest(
        id="t1",
        origin=GeoPoint(lat=30.20, lon=-97.80),
        destination=GeoPoint(lat=30.21, lon=-97.79),
        origin_snap_node_id="n-a",
        destination_snap_node_id="n-b",
        requested_at_h=0.0,
    )
    vehicles = {
        "v1": Vehicle(id="v1", state=VehicleState.IDLE, lat=30.22, lon=-97.78, current_node_id="n-c"),
    }
    low_pen = rank_dispatch_candidates(trip, vehicles, router, policy=NetworkPolicy(cross_zone_dispatch_penalty_min=0))
    high_pen = rank_dispatch_candidates(trip, vehicles, router, policy=NetworkPolicy(cross_zone_dispatch_penalty_min=10))
    assert high_pen[0].score > low_pen[0].score


def test_cancel_trip_manual() -> None:
    """Operator can force-cancel a pending trip."""
    mgr = SimulationManager()
    mgr.reset(seed=3)
    mgr.set_operator_setup(dispatch_assignment_mode=__import__('core_data.models', fromlist=['DispatchAssignmentMode']).DispatchAssignmentMode.MANUAL)
    mgr._seed_initial_trips(1)
    trip = next(t for t in mgr.state.trips.values() if t.status == TripStatus.PENDING)
    assert mgr.cancel_trip(trip.id) is None
    assert trip.status == TripStatus.CANCELLED


def test_apply_scenario_updates_policy() -> None:
    """Scenario preset patches network policy."""
    mgr = SimulationManager()
    mgr.reset(seed=1)
    mgr.apply_scenario(ScenarioPreset.RUSH_HOUR)
    assert mgr.state.policy.base_trips_per_hour == 42.0
    assert mgr.state.policy.scenario_preset == ScenarioPreset.RUSH_HOUR


def test_fleet_resize_on_policy_change() -> None:
    """Changing fleet_size adds vehicles mid-simulation."""
    mgr = SimulationManager()
    mgr.reset(seed=1)
    before = len(mgr.state.vehicles)
    mgr.set_network_policy(fleet_size=before + 2)
    assert len(mgr.state.vehicles) == before + 2


def test_operator_alerts_in_snapshot() -> None:
    """Snapshot includes operator alerts when KPIs exceed thresholds."""
    mgr = SimulationManager()
    mgr.reset(seed=1)
    mgr.set_network_policy(alert_pending_queue=0, alert_avg_wait_min=0)
    snap = json.loads(mgr.build_ui_snapshot(is_running=False, speed_multiplier=1.0))
    assert "operator_alerts" in snap


def test_scenario_patch_rush_hour() -> None:
    """Rush hour scenario returns expected demand boost."""
    patch = scenario_policy_patch(ScenarioPreset.RUSH_HOUR)
    assert patch["base_trips_per_hour"] == 42.0


def test_compute_operator_alerts_pending_queue() -> None:
    """Alert fires when pending trips exceed threshold."""
    alerts = compute_operator_alerts(
        NetworkPolicy(alert_pending_queue=3),
        {"pending_trips": 5, "avg_wait_min": 0, "fleet_utilization_pct": 50, "vehicles_needing_service": 0},
        [],
    )
    assert any(a["code"] == "pending_queue" for a in alerts)
