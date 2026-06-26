"""Apply rule engine v2 decisions to simulation state."""

from __future__ import annotations

from core_data.models import TripRequest, Vehicle
from fleet.health import is_dispatch_eligible
from fleet_routing.v2.context import EvalContext, KpiSnapshot, build_eval_context
from fleet_routing.v2.engine import EnginePlan, RuleEngineV2
from fleet_routing.v2.models import RuleHitV2
from simulation_loop.state import SimulationState


def kpi_snapshot_from_dict(kpis: dict[str, float], *, zone_rows: list) -> KpiSnapshot:
    """Build KpiSnapshot from manager KPI dict and zone balance rows."""
    worst_gap = max((row.gap for row in zone_rows), default=0.0)
    surplus = sum(1 for row in zone_rows if row.supply >= row.max_idle)
    deficit = sum(1 for row in zone_rows if row.gap > 0.5)
    return KpiSnapshot(
        pending_trips=int(kpis.get("pending_trips", 0)),
        avg_wait_min=float(kpis.get("avg_wait_min", 0)),
        p95_wait_min=float(kpis.get("p95_wait_min", 0)),
        fleet_utilization_pct=float(kpis.get("fleet_utilization_pct", 0)),
        deadhead_ratio=float(kpis.get("deadhead_ratio", 0)),
        profit=float(kpis.get("profit", 0)),
        completion_rate=float(kpis.get("completion_rate", 0)),
        trips_per_vehicle_hour=float(kpis.get("trips_per_vehicle_hour", 0)),
        vehicles_needing_service=int(kpis.get("vehicles_needing_service", 0)),
        avg_battery_pct=float(kpis.get("avg_battery_pct", 100)),
        worst_zone_gap=worst_gap,
        surplus_zone_count=surplus,
        deficit_zone_count=deficit,
        on_street_count=int(kpis.get("vehicles_on_street", 0)),
        at_facility_count=int(kpis.get("vehicles_at_depot", 0)),
    )


def build_manager_eval_context(
    state: SimulationState,
    *,
    router,
    demand,
    sim_time_h: float,
    supply_by_zone: dict[str, int],
    pending_by_zone: dict[str, int],
    kpis: dict[str, float],
    horizon_h: float,
    rng,
) -> EvalContext:
    """Build EvalContext from live simulation state."""
    from dispatch.reposition import zone_balances

    zone_rows = zone_balances(
        router,
        state.policy,
        demand,
        sim_time_h=sim_time_h,
        supply_by_zone=supply_by_zone,
        pending_by_zone=pending_by_zone,
        events=state.special_events,
    )
    return build_eval_context(
        router,
        state.policy,
        demand,
        sim_time_h=sim_time_h,
        supply_by_zone=supply_by_zone,
        pending_by_zone=pending_by_zone,
        events=state.special_events,
        vehicles=state.vehicles,
        trips=state.trips,
        facilities=state.facilities,
        kpis=kpi_snapshot_from_dict(kpis, zone_rows=zone_rows),
        horizon_h=horizon_h,
        rng=rng,
    )


def record_hits_v2(state: SimulationState, hits: list[RuleHitV2], *, max_len: int = 200) -> None:
    """Append v2 rule hits with cap."""
    state.rule_hits_v2.extend(hits)
    if len(state.rule_hits_v2) > max_len * 2:
        state.rule_hits_v2 = state.rule_hits_v2[-max_len:]
