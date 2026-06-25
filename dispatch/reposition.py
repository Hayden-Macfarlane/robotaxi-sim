"""Fleet repositioning, zone balancing, and ROI-gated staging."""

from __future__ import annotations

import random
from dataclasses import dataclass

from core_data.models import GeoPoint, NetworkPolicy, SpecialEvent, Vehicle, VehicleState
from demand.forecast import forecast_intensity
from demand.generator import ZONE_WEIGHTS, DemandGenerator
from routing.city_router import CityRouter
from routing.zones import zone_for_point


@dataclass(frozen=True)
class ZoneBalance:
    """Supply, demand, and gap metrics for one zone."""

    zone: str
    supply: int
    pending_demand: int
    expected_demand: float
    target_supply: int
    gap: float
    max_idle: int


@dataclass(frozen=True)
class RepositionDecision:
    """Scored reposition target for one vehicle."""

    zone: str
    gap: float
    travel_min: float
    benefit: float
    staging: GeoPoint


def zone_cap(policy: NetworkPolicy, zone: str) -> int:
    """Return max idle vehicles allowed in ``zone``."""
    if zone in policy.max_idle_by_zone:
        return policy.max_idle_by_zone[zone]
    return policy.max_idle_per_zone


def idle_patience_min(policy: NetworkPolicy, zone: str) -> float:
    """Return idle timeout before auto-reposition in ``zone``."""
    if zone in policy.reposition_idle_min_by_zone:
        return policy.reposition_idle_min_by_zone[zone]
    return policy.reposition_idle_min


def vehicle_zone(vehicle: Vehicle, router: CityRouter) -> str:
    """Resolve supply zone from live coordinates."""
    return zone_for_point(vehicle.lat, vehicle.lon)


def default_target_supply_by_zone(
    fleet_size: int,
    zones: list[str],
    policy_targets: dict[str, int],
) -> dict[str, int]:
    """Compute per-zone idle vehicle targets from policy or zone weights."""
    if policy_targets:
        return {z: policy_targets.get(z, 0) for z in zones}
    weights = {z: ZONE_WEIGHTS.get(z, 1.0) for z in zones}
    total_w = sum(weights.values()) or 1.0
    targets: dict[str, int] = {}
    assigned = 0
    for zone in zones:
        share = max(0, round(fleet_size * weights[zone] / total_w))
        targets[zone] = share
        assigned += share
    remainder = max(0, fleet_size - assigned)
    for zone in sorted(zones, key=lambda z: weights[z], reverse=True):
        if remainder <= 0:
            break
        targets[zone] = targets.get(zone, 0) + 1
        remainder -= 1
    return targets


def expected_demand_by_zone(
    demand: DemandGenerator,
    router: CityRouter,
    *,
    sim_time_h: float,
    pending_by_zone: dict[str, int],
    horizon_h: float = 0.0,
    events: list[SpecialEvent] | None = None,
) -> dict[str, float]:
    """Forecast-weighted demand score per zone at ``sim_time_h + horizon_h``."""
    zones = _all_zones(router)
    if not zones:
        return {}
    t = sim_time_h + horizon_h
    total_weight = sum(ZONE_WEIGHTS.get(z, 1.0) for z in zones)
    scores: dict[str, float] = {}
    for zone in zones:
        weight = ZONE_WEIGHTS.get(zone, 1.0)
        intensity = forecast_intensity(
            zone,
            t,
            base_weight=weight / total_weight,
            events=events,
        )
        base = intensity * demand.base_trips_per_hour
        pending = float(pending_by_zone.get(zone, 0))
        scores[zone] = base + pending * 2.0
    return scores


def zone_balances(
    router: CityRouter,
    policy: NetworkPolicy,
    demand: DemandGenerator,
    *,
    sim_time_h: float,
    supply_by_zone: dict[str, int],
    pending_by_zone: dict[str, int],
    horizon_h: float = 0.0,
    events: list[SpecialEvent] | None = None,
) -> list[ZoneBalance]:
    """Return zone balance rows sorted by descending gap."""
    zones = _all_zones(router)
    targets = default_target_supply_by_zone(
        policy.fleet_size,
        zones,
        policy.target_supply_by_zone,
    )
    expected = expected_demand_by_zone(
        demand,
        router,
        sim_time_h=sim_time_h,
        pending_by_zone=pending_by_zone,
        horizon_h=horizon_h,
        events=events,
    )
    rows: list[ZoneBalance] = []
    for zone in zones:
        supply = supply_by_zone.get(zone, 0)
        target = targets.get(zone, 0)
        exp = expected.get(zone, 0.0)
        pending = pending_by_zone.get(zone, 0)
        cap = zone_cap(policy, zone)
        supply_shortfall = max(0, target - supply)
        gap = (exp + float(pending)) - float(supply) + float(supply_shortfall)
        rows.append(
            ZoneBalance(
                zone=zone,
                supply=supply,
                pending_demand=pending,
                expected_demand=round(exp, 2),
                target_supply=target,
                gap=round(gap, 2),
                max_idle=cap,
            ),
        )
    rows.sort(key=lambda r: r.gap, reverse=True)
    return rows


def reposition_benefit(gap: float, travel_min: float, policy: NetworkPolicy) -> float:
    """Net benefit of repositioning: expected trip value vs deadhead cost."""
    return gap * policy.value_per_trip - travel_min * policy.deadhead_cost_per_min


def pick_staging_point(
    router: CityRouter,
    zone: str,
    *,
    claimed: set[tuple[float, float]],
    rng: random.Random,
) -> GeoPoint | None:
    """Pick an unclaimed staging coordinate inside ``zone``."""
    nodes_by_zone = router.nodes_by_zone()
    node_ids = list(nodes_by_zone.get(zone, []))
    rng.shuffle(node_ids)
    for nid in node_ids:
        node = router.get_node(nid)
        if node is None:
            continue
        key = (round(node.lat, 4), round(node.lon, 4))
        if key in claimed:
            continue
        return GeoPoint(lat=node.lat, lon=node.lon)
    for nid in router.node_ids:
        node = router.get_node(nid)
        if node is None:
            continue
        if zone_for_point(node.lat, node.lon) != zone:
            continue
        key = (round(node.lat, 4), round(node.lon, 4))
        if key in claimed:
            continue
        return GeoPoint(lat=node.lat, lon=node.lon)
    bbox = router.zone_bounding_boxes().get(zone)
    if bbox is None:
        return None
    min_lat, max_lat, min_lon, max_lon = bbox
    for _ in range(12):
        lat = rng.uniform(min_lat, max_lat)
        lon = rng.uniform(min_lon, max_lon)
        if zone_for_point(lat, lon) != zone:
            continue
        snap = router.snap_to_network(lat, lon)
        if snap is None:
            continue
        key = (round(snap.point.lat, 4), round(snap.point.lon, 4))
        if key in claimed:
            continue
        return snap.point
    return None


def pick_reposition_decision(
    vehicle: Vehicle,
    router: CityRouter,
    policy: NetworkPolicy,
    demand: DemandGenerator,
    *,
    sim_time_h: float,
    supply_by_zone: dict[str, int],
    pending_by_zone: dict[str, int],
    claimed: set[tuple[float, float]],
    rng: random.Random,
    horizon_h: float = 0.0,
    events: list[SpecialEvent] | None = None,
) -> RepositionDecision | None:
    """Return best ROI reposition target for ``vehicle``, or None."""
    if vehicle.state != VehicleState.IDLE:
        return None
    vzone = vehicle_zone(vehicle, router)
    balances = zone_balances(
        router,
        policy,
        demand,
        sim_time_h=sim_time_h,
        supply_by_zone=supply_by_zone,
        pending_by_zone=pending_by_zone,
        horizon_h=horizon_h,
        events=events,
    )
    current_supply = supply_by_zone.get(vzone, 0)
    cap = zone_cap(policy, vzone)
    best: RepositionDecision | None = None
    for row in balances:
        if row.zone == vzone:
            continue
        if supply_by_zone.get(row.zone, 0) >= row.max_idle:
            continue
        if current_supply <= cap:
            if row.gap <= 0.5:
                continue
        elif row.gap <= -0.5:
            continue
        staging = pick_staging_point(router, row.zone, claimed=claimed, rng=rng)
        if staging is None:
            continue
        route = router.route_between(vehicle.lat, vehicle.lon, staging.lat, staging.lon)
        if route is None:
            continue
        travel = route.travel_time_min
        if travel > policy.max_reposition_min:
            continue
        benefit = reposition_benefit(row.gap, travel, policy)
        if benefit < policy.min_reposition_benefit:
            continue
        if best is None or benefit > best.benefit:
            best = RepositionDecision(
                zone=row.zone,
                gap=row.gap,
                travel_min=travel,
                benefit=benefit,
                staging=staging,
            )
    return best


def pick_reposition_target_zone(
    vehicle: Vehicle,
    router: CityRouter,
    policy: NetworkPolicy,
    demand: DemandGenerator,
    *,
    sim_time_h: float,
    supply_by_zone: dict[str, int],
    pending_by_zone: dict[str, int],
    horizon_h: float = 0.0,
    events: list[SpecialEvent] | None = None,
) -> str | None:
    """Return the best deficit zone for ``vehicle``, or None if no move needed."""
    rng = random.Random(0)
    decision = pick_reposition_decision(
        vehicle,
        router,
        policy,
        demand,
        sim_time_h=sim_time_h,
        supply_by_zone=supply_by_zone,
        pending_by_zone=pending_by_zone,
        claimed=set(),
        rng=rng,
        horizon_h=horizon_h,
        events=events,
    )
    return decision.zone if decision else None


def surplus_idle_vehicles(
    vehicles: dict[str, Vehicle],
    router: CityRouter,
    policy: NetworkPolicy,
    supply_by_zone: dict[str, int],
) -> list[Vehicle]:
    """Return idle vehicles exceeding per-zone caps, longest-idle first per zone."""
    by_zone: dict[str, list[Vehicle]] = {}
    for vehicle in vehicles.values():
        if vehicle.state != VehicleState.IDLE:
            continue
        zone = vehicle_zone(vehicle, router)
        by_zone.setdefault(zone, []).append(vehicle)
    surplus: list[Vehicle] = []
    for zone, idle_list in by_zone.items():
        cap = zone_cap(policy, zone)
        count = supply_by_zone.get(zone, len(idle_list))
        excess = count - cap
        if excess <= 0:
            continue
        idle_list.sort(key=lambda v: v.idle_since_h)
        surplus.extend(idle_list[:excess])
    return surplus


def should_post_trip_reposition(
    dropoff_zone: str,
    router: CityRouter,
    policy: NetworkPolicy,
    demand: DemandGenerator,
    *,
    sim_time_h: float,
    supply_by_zone: dict[str, int],
    pending_by_zone: dict[str, int],
) -> bool:
    """Return True if dropoff zone is at or above idle cap."""
    if not policy.post_trip_reposition_enabled:
        return False
    cap = zone_cap(policy, dropoff_zone)
    supply = supply_by_zone.get(dropoff_zone, 0)
    return supply >= cap


def forecast_snapshot(
    demand: DemandGenerator,
    router: CityRouter,
    *,
    sim_time_h: float,
    pending_by_zone: dict[str, int],
    events: list[SpecialEvent] | None = None,
) -> list[dict[str, object]]:
    """Build forecast rows for UI: now, +30min, +60min."""
    rows: list[dict[str, object]] = []
    for zone in _all_zones(router):
        now = expected_demand_by_zone(
            demand, router, sim_time_h=sim_time_h, pending_by_zone=pending_by_zone, events=events,
        ).get(zone, 0.0)
        t30 = expected_demand_by_zone(
            demand, router, sim_time_h=sim_time_h, pending_by_zone=pending_by_zone,
            horizon_h=0.5, events=events,
        ).get(zone, 0.0)
        t60 = expected_demand_by_zone(
            demand, router, sim_time_h=sim_time_h, pending_by_zone=pending_by_zone,
            horizon_h=1.0, events=events,
        ).get(zone, 0.0)
        rows.append({
            "zone": zone,
            "now": round(now, 2),
            "t_plus_30": round(t30, 2),
            "t_plus_60": round(t60, 2),
        })
    rows.sort(key=lambda r: float(r["t_plus_30"]), reverse=True)
    return rows


def _all_zones(router: CityRouter) -> list[str]:
    """Union of graph zones and known POI zone names."""
    zones = set(router.nodes_by_zone().keys())
    zones.update(ZONE_WEIGHTS.keys())
    return sorted(zones)
