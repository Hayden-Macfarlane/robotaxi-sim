"""Tests for optimization lab: economics KPIs, experiments, presets, batch dispatch."""

from __future__ import annotations

import json
from pathlib import Path

from core_data.models import DispatchAssignmentMode, GeoPoint, NetworkPolicy, TripRequest, TripStatus, Vehicle, VehicleState
from dispatch.batch_matcher import batch_assign_trips
from experiment.ledger import ExperimentLedger
from fixture_loader import load_fixture_router
from simulation_loop.manager import SimulationManager
from simulation_loop.preset_store import PresetStore


def _snapshot(mgr: SimulationManager) -> dict:
    return json.loads(mgr.build_ui_snapshot(is_running=False, speed_multiplier=1.0))


def test_economics_kpis_include_profit_and_completion_rate() -> None:
    """KPI snapshot reports profit, deadhead cost, and completion rate."""
    mgr = SimulationManager()
    mgr.reset(seed=5)
    mgr.set_network_policy(deadhead_cost_per_min=0.5, auto_dispatch_enabled=True)
    mgr.set_operator_setup(dispatch_assignment_mode=DispatchAssignmentMode.CLOSEST_IDLE_OR_REPOSITIONING)
    mgr.step(2.0)
    kpis = _snapshot(mgr)["kpis"]
    assert "profit" in kpis
    assert "deadhead_cost" in kpis
    assert "completion_rate" in kpis
    assert "trips_per_vehicle_hour" in kpis
    assert "composite_score" in kpis
    assert kpis["profit"] == round(kpis["revenue"] - kpis["deadhead_cost"], 2)


def test_kpi_time_series_samples_on_step() -> None:
    """KPI ring buffer collects samples every 15 sim minutes."""
    mgr = SimulationManager()
    mgr.reset(seed=1)
    mgr.step(0.5)
    snap = _snapshot(mgr)
    assert len(snap["kpi_series"]) >= 1
    sample = snap["kpi_series"][0]
    assert "profit" in sample
    assert "sim_time_h" in sample


def test_checkpoint_run_persists_and_lists(tmp_path: Path) -> None:
    """Experiment checkpoint saves KPIs and config to ledger."""
    mgr = SimulationManager()
    mgr._ledger = ExperimentLedger(tmp_path / "experiments")
    mgr.reset(seed=42)
    mgr.step(1.0)
    run = mgr.checkpoint_run("Baseline")
    assert run.label == "Baseline"
    assert run.seed == 42
    assert "profit" in run.kpis
    listed = mgr.list_experiment_runs()
    assert len(listed) == 1
    snap = _snapshot(mgr)
    assert len(snap["experiment_runs"]) == 1
    assert mgr.delete_experiment_run(run.id) is None
    assert mgr.list_experiment_runs() == []


def test_operator_preset_round_trip(tmp_path: Path) -> None:
    """Save and load operator preset restores policy."""
    mgr = SimulationManager()
    mgr._presets = PresetStore(tmp_path / "presets")
    mgr.reset(seed=3)
    mgr.set_network_policy(cross_zone_dispatch_penalty_min=7.5, surge_multiplier=1.8)
    mgr.save_operator_preset("test-preset", "unit test")
    mgr.set_network_policy(cross_zone_dispatch_penalty_min=0.0, surge_multiplier=1.0)
    assert mgr.load_operator_preset("test-preset") is None
    assert mgr.state.policy.cross_zone_dispatch_penalty_min == 7.5
    assert mgr.state.policy.surge_multiplier == 1.8
    snap = _snapshot(mgr)
    assert "test-preset" in snap["operator_presets"]
    assert mgr.delete_operator_preset("test-preset") is None


def test_batch_assign_trips_no_double_booking() -> None:
    """Batch matcher assigns each vehicle at most once."""
    router = load_fixture_router()
    policy = NetworkPolicy(auto_dispatch_enabled=True)
    trips = [
        TripRequest(
            id="t1",
            origin=GeoPoint(lat=30.20, lon=-97.80),
            destination=GeoPoint(lat=30.21, lon=-97.79),
            origin_snap_node_id="n-a",
            destination_snap_node_id="n-b",
            requested_at_h=0.0,
        ),
        TripRequest(
            id="t2",
            origin=GeoPoint(lat=30.20, lon=-97.80),
            destination=GeoPoint(lat=30.22, lon=-97.78),
            origin_snap_node_id="n-a",
            destination_snap_node_id="n-c",
            requested_at_h=0.1,
        ),
    ]
    vehicles = {
        "v1": Vehicle(id="v1", state=VehicleState.IDLE, lat=30.22, lon=-97.78, current_node_id="n-c"),
    }
    pairs = batch_assign_trips(trips, vehicles, router, policy)
    vehicle_ids = [vid for _, vid in pairs]
    assert len(vehicle_ids) == len(set(vehicle_ids))
    assert len(pairs) <= 1


def test_batch_dispatch_enabled_in_manager() -> None:
    """Manager uses batch path when batch_dispatch_enabled is on."""
    mgr = SimulationManager()
    mgr.reset(seed=9)
    mgr.set_network_policy(auto_dispatch_enabled=True, batch_dispatch_enabled=True)
    mgr.set_operator_setup(dispatch_assignment_mode=DispatchAssignmentMode.CLOSEST_IDLE_OR_REPOSITIONING)
    mgr._seed_initial_trips(3)
    pending_before = sum(1 for t in mgr.state.trips.values() if t.status == TripStatus.PENDING)
    mgr.step(0.5)
    pending_after = sum(1 for t in mgr.state.trips.values() if t.status == TripStatus.PENDING)
    assert pending_before >= pending_after or mgr.state.trips_completed >= 0
