"""Tests for rule engine v2 metrics and evaluation."""

from __future__ import annotations

from core_data.models import Vehicle, VehicleState
from fleet_routing.v2.context import SpatialIndex
from fleet_routing.v2.defaults import default_playbook_v2
from fleet_routing.v2.engine import RuleEngineV2
from fleet_routing.v2.metrics import REGISTRY
from fleet_routing.v2.models import CompareOpV2, ExprNode, ExprOp, MetricRef
from fleet_routing.v2.evaluator import evaluate_expr
from simulation_loop.routing_v2 import build_manager_eval_context
from simulation_loop.manager import SimulationManager


def test_metric_registry_size() -> None:
    """Catalog exposes a broad operator variable set."""
    assert len(REGISTRY.all_meta()) >= 80


def test_nearest_idle_km_metric() -> None:
    """Spatial index returns distance to closest idle neighbor."""
    a = Vehicle(id="a", state=VehicleState.IDLE, lat=30.20, lon=-97.80, current_node_id="n-a")
    b = Vehicle(id="b", state=VehicleState.IDLE, lat=30.21, lon=-97.79, current_node_id="n-b")
    idx = SpatialIndex(idle_vehicles=[a, b], all_vehicles=[a, b])
    d = idx.nearest_idle_km(a, rank=1)
    assert d is not None
    assert 0.0 < d < 20.0


def test_playbook_cluster_rule_expression(sim_manager: SimulationManager) -> None:
    """Cluster-break rule metrics evaluate on fixture fleet."""
    sim_manager.state.operator_setup = sim_manager.state.operator_setup.model_copy(
        update={"routing_engine_version": "v2"},
    )
    sim_manager.state.playbook_v2 = default_playbook_v2()
    supply, pending = sim_manager._zone_heatmaps()
    ctx = build_manager_eval_context(
        sim_manager.state,
        router=sim_manager._router,
        demand=sim_manager._demand,
        sim_time_h=sim_manager.current_time,
        supply_by_zone=supply,
        pending_by_zone=pending,
        kpis=sim_manager._compute_kpis(),
        horizon_h=0.5,
        rng=sim_manager._rng,
    )
    vehicle = next(v for v in sim_manager.state.vehicles.values() if v.state == VehicleState.IDLE)
    expr = ExprNode(
        op=ExprOp.COMPARE,
        metric=MetricRef(id="vehicle.nearest_idle_km"),
        operator=CompareOpV2.LT,
        value=999.0,
    )
    assert evaluate_expr(expr, ctx, vehicle=vehicle, constants=sim_manager.state.playbook_v2.constants)


def test_v2_engine_produces_plan(sim_manager: SimulationManager) -> None:
    """V2 engine returns dispatch/reposition plan without error."""
    sim_manager.state.operator_setup = sim_manager.state.operator_setup.model_copy(
        update={"routing_engine_version": "v2"},
    )
    sim_manager.state.playbook_v2 = default_playbook_v2()
    supply, pending = sim_manager._zone_heatmaps()
    ctx = build_manager_eval_context(
        sim_manager.state,
        router=sim_manager._router,
        demand=sim_manager._demand,
        sim_time_h=sim_manager.current_time,
        supply_by_zone=supply,
        pending_by_zone=pending,
        kpis=sim_manager._compute_kpis(),
        horizon_h=0.5,
        rng=sim_manager._rng,
    )
    plan = RuleEngineV2(sim_manager.state.playbook_v2).plan(ctx, timestamp_h=sim_manager.current_time)
    assert isinstance(plan.hits, list)
