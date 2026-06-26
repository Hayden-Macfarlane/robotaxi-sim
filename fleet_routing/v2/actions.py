"""Parameterized rule actions and destination search."""

from __future__ import annotations

import random
from dataclasses import dataclass

from core_data.models import GeoPoint, TripRequest, Vehicle
from dispatch.matcher import dispatch_zone_context_from_rows, pick_best_vehicle
from dispatch.deadzone import zone_representative_point
from dispatch.reposition import _all_zones, pick_staging_point, reposition_benefit
from fleet_routing.constraints import best_deficit_zone, reposition_passes_roi, reposition_within_max_travel
from fleet_routing.v2.context import EvalContext
from fleet_routing.v2.evaluator import evaluate_expr, resolve_metric
from fleet_routing.v2.metrics import REGISTRY
from fleet_routing.v2.models import ActionSpec, ActionTypeV2, MetricRef


@dataclass(frozen=True)
class DispatchActionResult:
    """Dispatch assignment from v2 action."""

    trip_id: str
    vehicle_id: str
    detail: str = ""


@dataclass(frozen=True)
class RepositionActionResult:
    """Reposition move from v2 action."""

    vehicle_id: str
    staging: GeoPoint
    zone: str
    send_to_depot: bool = False
    detail: str = ""
    destination_search: dict[str, object] | None = None


def _const(spec: ActionSpec, constants: dict[str, float], key: str, default: float) -> float:
    if key in spec.params:
        return float(spec.params[key])
    if key in constants:
        return constants[key]
    return default


def execute_dispatch_action(
    spec: ActionSpec,
    ctx: EvalContext,
    trip: TripRequest,
    vehicles: dict[str, Vehicle],
    *,
    constants: dict[str, float],
    assigned: set[str],
) -> DispatchActionResult | None:
    """Execute a dispatch-phase action."""
    if spec.type == ActionTypeV2.HOLD:
        return None
    dispatch_types = (
        ActionTypeV2.ASSIGN_VEHICLE,
        ActionTypeV2.ASSIGN_NEAREST_IDLE,
        ActionTypeV2.ASSIGN_NEAREST_AVAILABLE,
    )
    if spec.type not in dispatch_types:
        return None
    if spec.type == ActionTypeV2.ASSIGN_NEAREST_IDLE:
        preempt = False
    elif spec.type == ActionTypeV2.ASSIGN_NEAREST_AVAILABLE:
        preempt = True
    else:
        preempt = bool(spec.params.get("preempt_reposition", True))
    pool = {
        vid: v for vid, v in vehicles.items()
        if vid not in assigned
    }
    if spec.filter is not None:
        pool = {
            vid: v for vid, v in pool.items()
            if evaluate_expr(spec.filter, ctx, vehicle=v, trip=trip, constants=constants)
        }
    if not pool:
        return None
    zone_ctx = dispatch_zone_context_from_rows(ctx.routing.supply_by_zone, ctx.routing.zone_rows, ctx.policy)
    match = pick_best_vehicle(
        trip,
        pool,
        ctx.router,
        surge_multiplier=ctx.policy.surge_multiplier,
        policy=ctx.policy,
        include_repositioning=preempt,
        zone_ctx=zone_ctx,
        traffic_multiplier=ctx.policy.global_traffic_multiplier,
    )
    if match is None:
        return None
    if spec.rank_by is not None:
        score = REGISTRY.compute(spec.rank_by.id, ctx, vehicle=pool[match.vehicle_id], trip=trip, constants=constants, params=dict(spec.rank_by.params))
        _ = score
    return DispatchActionResult(trip_id=trip.id, vehicle_id=match.vehicle_id, detail=f"eta {match.eta_min:.1f}m score {match.score:.2f}")


def execute_reposition_action(
    spec: ActionSpec,
    ctx: EvalContext,
    vehicle: Vehicle,
    *,
    constants: dict[str, float],
    claimed: set[tuple[float, float]],
) -> RepositionActionResult | None:
    """Execute a reposition-phase action."""
    if spec.type == ActionTypeV2.HOLD:
        return RepositionActionResult(
            vehicle_id=vehicle.id,
            staging=GeoPoint(lat=vehicle.lat, lon=vehicle.lon),
            zone=ctx.routing.vehicle_zone(vehicle),
            detail="hold",
        )
    if spec.type == ActionTypeV2.SEND_TO_FACILITY:
        return RepositionActionResult(
            vehicle_id=vehicle.id,
            staging=GeoPoint(lat=vehicle.lat, lon=vehicle.lon),
            zone=ctx.routing.vehicle_zone(vehicle),
            send_to_depot=True,
            detail="send_to_facility",
        )
    if spec.type == ActionTypeV2.REPOSITION_TO_BEST_DEFICIT:
        vzone = ctx.routing.vehicle_zone(vehicle)
        best = best_deficit_zone(vzone, ctx.routing.zone_rows, ctx.routing.supply_by_zone)
        if best is None:
            return None
        return _reposition_to_zone(ctx, vehicle, best.zone, constants=constants, claimed=claimed, spec=spec)
    if spec.type == ActionTypeV2.REPOSITION_TO_ZONE:
        target = str(spec.params.get("target_zone", ""))
        if not target:
            return None
        return _reposition_to_zone(ctx, vehicle, target, constants=constants, claimed=claimed, spec=spec)
    if spec.type == ActionTypeV2.REPOSITION_TO_NEAREST_DENSITY_FLOOR:
        return _reposition_density_floor(ctx, vehicle, spec, constants=constants, claimed=claimed)
    if spec.type == ActionTypeV2.REPOSITION_TO_POINT:
        lat = float(spec.params.get("lat", vehicle.lat))
        lon = float(spec.params.get("lon", vehicle.lon))
        return _reposition_to_point(ctx, vehicle, lat, lon, constants=constants, spec=spec)
    return None


def _reposition_to_zone(
    ctx: EvalContext,
    vehicle: Vehicle,
    zone: str,
    *,
    constants: dict[str, float],
    claimed: set[tuple[float, float]],
    spec: ActionSpec,
) -> RepositionActionResult | None:
    staging = pick_staging_point(ctx.router, zone, claimed=claimed, rng=ctx.rng)
    if staging is None:
        return None
    return _reposition_to_point(ctx, vehicle, staging.lat, staging.lon, zone=zone, constants=constants, spec=spec, claimed=claimed)


def _reposition_to_point(
    ctx: EvalContext,
    vehicle: Vehicle,
    lat: float,
    lon: float,
    *,
    constants: dict[str, float],
    spec: ActionSpec,
    zone: str | None = None,
    claimed: set[tuple[float, float]] | None = None,
) -> RepositionActionResult | None:
    route = ctx.router.route_between(vehicle.lat, vehicle.lon, lat, lon)
    if route is None:
        return None
    travel = route.travel_time_min * ctx.policy.global_traffic_multiplier
    max_travel = _const(spec, constants, "max_travel_min", ctx.policy.max_reposition_min)
    if travel > max_travel:
        return None
    target_zone = zone or ctx.routing.vehicle_zone(vehicle)
    gap = ctx.routing.gap_for_zone(target_zone)
    min_benefit = _const(spec, constants, "min_reposition_benefit", ctx.policy.min_reposition_benefit)
    benefit = reposition_benefit(gap, travel, ctx.policy)
    if benefit < min_benefit and spec.type != ActionTypeV2.REPOSITION_TO_NEAREST_DENSITY_FLOOR:
        return None
    if spec.constraints is not None:
        params = {"lat": lat, "lon": lon, "radius_km": spec.params.get("radius_km", 1.0)}
        if not evaluate_expr(
            spec.constraints, ctx, vehicle=vehicle, constants=constants,
        ):
            ref = MetricRef(id="pair.density_ratio_dest_over_origin", params=params)
            ratio = REGISTRY.compute(ref.id, ctx, vehicle=vehicle, constants=constants, params=params)
            if not evaluate_expr(spec.constraints, ctx, vehicle=vehicle, constants=constants):
                _ = ratio
                pass
    if claimed is not None:
        claimed.add((round(lat, 4), round(lon, 4)))
    return RepositionActionResult(
        vehicle_id=vehicle.id,
        staging=GeoPoint(lat=lat, lon=lon),
        zone=target_zone,
        detail=f"travel {travel:.1f}m benefit {benefit:.2f}",
    )


def _reposition_density_floor(
    ctx: EvalContext,
    vehicle: Vehicle,
    spec: ActionSpec,
    *,
    constants: dict[str, float],
    claimed: set[tuple[float, float]],
) -> RepositionActionResult | None:
    """Search zone staging points meeting minimum density ratio."""
    min_ratio = _const(spec, constants, "min_density_ratio", 0.5)
    radius = float(spec.params.get("radius_km", 1.0))
    origin_density = ctx.spatial.local_density(vehicle.lat, vehicle.lon, radius, idle_only=True, exclude_id=vehicle.id)
    min_density = origin_density * min_ratio
    max_travel = _const(spec, constants, "max_travel_min", ctx.policy.max_reposition_min)

    candidates: list[tuple[float, float, float, str]] = []
    for zone in _all_zones(ctx.router):
        staging = pick_staging_point(ctx.router, zone, claimed=claimed, rng=ctx.rng)
        if staging is None:
            staging = zone_representative_point(ctx.router, zone)
        if staging is None:
            continue
        key = (round(staging.lat, 4), round(staging.lon, 4))
        if key in claimed:
            continue
        density = ctx.spatial.local_density(staging.lat, staging.lon, radius, idle_only=True)
        if density < min_density:
            continue
        route = ctx.router.route_between(vehicle.lat, vehicle.lon, staging.lat, staging.lon)
        if route is None:
            continue
        travel = route.travel_time_min * ctx.policy.global_traffic_multiplier
        if travel > max_travel:
            continue
        candidates.append((travel, staging.lat, staging.lon, zone))

    search_info: dict[str, object] = {"candidates": len(candidates), "min_density_ratio": min_ratio}
    if not candidates:
        search_info["failed_constraints"] = ["no_staging_meets_density"]
        return None
    candidates.sort(key=lambda x: x[0])
    travel, lat, lon, zone = candidates[0]
    claimed.add((round(lat, 4), round(lon, 4)))
    search_info["picked"] = {"lat": lat, "lon": lon, "zone": zone}
    return RepositionActionResult(
        vehicle_id=vehicle.id,
        staging=GeoPoint(lat=lat, lon=lon),
        zone=zone,
        detail=f"density floor ratio>={min_ratio} travel {travel:.1f}m",
        destination_search=search_info,
    )
