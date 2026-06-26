"""Subject selection for multi-match rules."""

from __future__ import annotations

from core_data.models import TripRequest, Vehicle, VehicleState
from fleet_routing.v2.context import EvalContext
from fleet_routing.v2.evaluator import resolve_metric
from fleet_routing.v2.metrics import REGISTRY
from fleet_routing.v2.models import MetricRef, RuleV2, SelectionMode


def select_vehicles(
    rule: RuleV2,
    ctx: EvalContext,
    candidates: list[Vehicle],
    *,
    constants: dict[str, float],
) -> list[Vehicle]:
    """Filter and select vehicles per rule selection mode."""
    if not candidates:
        return []
    mode = rule.selection
    if mode == SelectionMode.ALL_MATCHING:
        return candidates

    if mode == SelectionMode.MOST_CROWDED:
        radius = float(rule.selection_params.get("radius_km", 1.0))
        best: Vehicle | None = None
        best_dist = 9999.0
        for v in candidates:
            d = ctx.spatial.nearest_idle_km(v, rank=1)
            if d is not None and d < best_dist:
                best_dist = d
                best = v
        return [best] if best else []

    if mode == SelectionMode.LEAST_CROWDED:
        best: Vehicle | None = None
        best_dist = -1.0
        for v in candidates:
            d = ctx.spatial.nearest_idle_km(v, rank=1) or 9999.0
            if d > best_dist:
                best_dist = d
                best = v
        return [best] if best else []

    if mode == SelectionMode.ONE_PER_CLUSTER:
        radius = float(rule.selection_params.get("radius_km", 1.0))
        remaining = list(candidates)
        picked: list[Vehicle] = []
        while remaining:
            seed = remaining.pop(0)
            picked.append(seed)
            cluster = {seed.id}
            for other in remaining[:]:
                if haversine_pair(seed, other) <= radius:
                    cluster.add(other.id)
                    remaining.remove(other)
            _ = cluster
        return picked

    if mode in (SelectionMode.HIGHEST_METRIC, SelectionMode.LOWEST_METRIC):
        ref = rule.selection_metric
        if ref is None:
            return candidates[:1]
        best: Vehicle | None = None
        best_val = -1e18 if mode == SelectionMode.HIGHEST_METRIC else 1e18
        for v in candidates:
            val = REGISTRY.compute(ref.id, ctx, vehicle=v, constants=constants, params=dict(ref.params))
            num = float(val) if not isinstance(val, bool) else (1.0 if val else 0.0)
            if mode == SelectionMode.HIGHEST_METRIC and num > best_val:
                best_val = num
                best = v
            elif mode == SelectionMode.LOWEST_METRIC and num < best_val:
                best_val = num
                best = v
        return [best] if best else []

    if mode == SelectionMode.ROUND_ROBIN_ZONE:
        by_zone: dict[str, list[Vehicle]] = {}
        for v in candidates:
            z = ctx.routing.vehicle_zone(v)
            by_zone.setdefault(z, []).append(v)
        out: list[Vehicle] = []
        for vehicles in by_zone.values():
            out.append(min(vehicles, key=lambda x: x.idle_since_h))
        return out

    return candidates


def haversine_pair(a: Vehicle, b: Vehicle) -> float:
    """Haversine km between two vehicles."""
    from routing.geo import haversine_km

    return haversine_km(a.lat, a.lon, b.lat, b.lon)


def eligible_idle_vehicles(ctx: EvalContext) -> list[Vehicle]:
    """Return idle vehicles eligible for reposition."""
    from fleet_routing.constraints import vehicle_eligible_for_reposition

    return [
        v for v in ctx.vehicles.values()
        if vehicle_eligible_for_reposition(
            v, ctx.policy, sim_time_h=ctx.sim_time_h, manual_hold_until_h=v.manual_hold_until_h,
        )
    ]


def eligible_dispatch_vehicles(ctx: EvalContext, *, include_repositioning: bool = True) -> dict[str, Vehicle]:
    """Return vehicles eligible for dispatch."""
    from fleet_routing.constraints import vehicle_eligible_for_dispatch

    out: dict[str, Vehicle] = {}
    for vid, v in ctx.vehicles.items():
        if vehicle_eligible_for_dispatch(v, ctx.policy, include_repositioning=include_repositioning):
            out[vid] = v
    return out
