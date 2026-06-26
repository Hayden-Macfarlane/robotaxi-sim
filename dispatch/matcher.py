"""Vehicle–trip matching by ETA and operator scoring weights."""

from __future__ import annotations

from dataclasses import dataclass

from core_data.models import DispatchTieBreaker, NetworkPolicy, TripRequest, Vehicle, VehicleState
from dispatch.reposition import ZoneBalance, zone_cap
from fleet.health import is_dispatch_eligible
from routing.geo import haversine_km
from routing.city_router import CityRouter
from routing.zones import zone_for_point

# Approximate road-network factor for quick UI ETA ranking (not used for actual dispatch).
_STREET_FACTOR = 1.35
_AVG_SPEED_KMH = 32.0
_KM_PER_MILE = 1.60934


def _haversine_eta_min(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Estimate driving minutes from straight-line distance."""
    km = haversine_km(lat1, lon1, lat2, lon2) * _STREET_FACTOR
    return km / (_AVG_SPEED_KMH / 60.0)


@dataclass(frozen=True)
class DispatchZoneContext:
    """Live zone supply snapshot for dropoff-aware dispatch scoring."""

    supply_by_zone: dict[str, int]
    gap_by_zone: dict[str, float]
    cap_by_zone: dict[str, int]


def dispatch_zone_context_from_rows(
    supply_by_zone: dict[str, int],
    zone_rows: list[ZoneBalance],
    policy: NetworkPolicy,
) -> DispatchZoneContext:
    """Build zone context from routing context zone balance rows."""
    gap_by_zone = {row.zone: row.gap for row in zone_rows}
    cap_by_zone = {row.zone: row.max_idle for row in zone_rows}
    for zone in supply_by_zone:
        cap_by_zone.setdefault(zone, zone_cap(policy, zone))
        gap_by_zone.setdefault(zone, 0.0)
    return DispatchZoneContext(
        supply_by_zone=dict(supply_by_zone),
        gap_by_zone=gap_by_zone,
        cap_by_zone=cap_by_zone,
    )


@dataclass(frozen=True)
class MatchCandidate:
    """Scored vehicle assignment for a pending trip."""

    vehicle_id: str
    eta_min: float
    score: float
    state: VehicleState = VehicleState.IDLE
    dropoff_zone: str = ""
    balance_adjustment: float = 0.0


def _vehicle_dispatch_eligible(
    vehicle: Vehicle,
    policy: NetworkPolicy,
    *,
    include_repositioning: bool,
) -> bool:
    """Return True if vehicle may be considered for trip dispatch."""
    allowed = {VehicleState.IDLE}
    if include_repositioning and policy.allow_preempt_reposition:
        allowed.add(VehicleState.REPOSITIONING)
    if vehicle.state not in allowed:
        return False
    if not is_dispatch_eligible(vehicle, policy):
        return False
    if vehicle.active_route_edges and vehicle.state == VehicleState.REPOSITIONING:
        return include_repositioning and policy.allow_preempt_reposition
    return True


def _charge_sufficient(
    vehicle: Vehicle,
    trip: TripRequest,
    router: CityRouter,
    policy: NetworkPolicy,
    *,
    traffic_multiplier: float = 1.0,
) -> bool:
    """Return True if battery can likely serve pickup + ride when charge-aware dispatch is on."""
    if not policy.charge_aware_dispatch:
        return True
    pickup = router.route_between(vehicle.lat, vehicle.lon, trip.origin.lat, trip.origin.lon)
    ride = router.route_between(trip.origin.lat, trip.origin.lon, trip.destination.lat, trip.destination.lon)
    if pickup is None or ride is None:
        return False
    total_km = pickup.distance_km + ride.distance_km
    needed_pct = total_km / policy.km_per_soc_pct
    return vehicle.battery_pct >= max(policy.min_battery_pct_for_trip, needed_pct)


def _dropoff_balance_adjustment(
    vehicle: Vehicle,
    trip: TripRequest,
    policy: NetworkPolicy,
    zone_ctx: DispatchZoneContext | None,
) -> float:
    """Return score delta from dropoff zone balance (positive = worse rank)."""
    if not policy.dispatch_consider_dropoff_balance or zone_ctx is None:
        return 0.0
    vehicle_zone = zone_for_point(vehicle.lat, vehicle.lon)
    dropoff_zone = zone_for_point(trip.destination.lat, trip.destination.lon)
    projected = dict(zone_ctx.supply_by_zone)
    if projected.get(vehicle_zone, 0) > 0:
        projected[vehicle_zone] = projected.get(vehicle_zone, 0) - 1
    projected[dropoff_zone] = projected.get(dropoff_zone, 0) + 1

    adjustment = 0.0
    cap = zone_ctx.cap_by_zone.get(dropoff_zone, zone_cap(policy, dropoff_zone))
    over = projected.get(dropoff_zone, 0) - cap
    if over > 0 and policy.dispatch_penalty_dropoff_surplus_min > 0:
        adjustment += over * policy.dispatch_penalty_dropoff_surplus_min

    supply_delta = 0 if vehicle_zone == dropoff_zone else 1
    gap = zone_ctx.gap_by_zone.get(dropoff_zone, 0.0)
    if supply_delta > 0 and gap > 0 and policy.dispatch_weight_dropoff_balance > 0:
        adjustment -= policy.dispatch_weight_dropoff_balance * min(gap, float(cap), float(supply_delta))
    return adjustment


def _dispatch_score(
    vehicle: Vehicle,
    trip: TripRequest,
    eta_min: float,
    policy: NetworkPolicy,
    *,
    zone_ctx: DispatchZoneContext | None = None,
) -> tuple[float, float]:
    """Return ``(score, balance_adjustment)`` — lower score is better."""
    trip_zone = zone_for_point(trip.origin.lat, trip.origin.lon)
    vehicle_zone = zone_for_point(vehicle.lat, vehicle.lon)
    score = eta_min * policy.dispatch_weight_eta
    if policy.dispatch_weight_surge > 0:
        score -= policy.dispatch_weight_surge * policy.surge_multiplier
    if policy.cross_zone_dispatch_penalty_min > 0 and vehicle_zone != trip_zone:
        score += policy.cross_zone_dispatch_penalty_min
    if policy.dispatch_weight_zone_balance > 0:
        score -= policy.dispatch_weight_zone_balance * max(0.0, 1.0 if vehicle_zone == trip_zone else 0.0)
    balance_adj = _dropoff_balance_adjustment(vehicle, trip, policy, zone_ctx)
    score += balance_adj
    return score, balance_adj


def _tie_break_key(
    candidate: MatchCandidate,
    vehicles: dict[str, Vehicle],
    policy: NetworkPolicy,
) -> tuple[float, float, float]:
    """Secondary sort key when ETAs are close."""
    vehicle = vehicles[candidate.vehicle_id]
    if policy.dispatch_tie_breaker == DispatchTieBreaker.IDLE_LONGEST:
        return (candidate.eta_min, -vehicle.idle_since_h, vehicle.battery_pct)
    if policy.dispatch_tie_breaker == DispatchTieBreaker.LOWEST_BATTERY:
        return (candidate.eta_min, vehicle.battery_pct, -vehicle.idle_since_h)
    return (candidate.eta_min, -vehicle.idle_since_h, vehicle.battery_pct)


def rank_dispatch_candidates(
    trip: TripRequest,
    vehicles: dict[str, Vehicle],
    router: CityRouter,
    *,
    surge_multiplier: float = 1.0,
    policy: NetworkPolicy | None = None,
    include_repositioning: bool = False,
    limit: int | None = None,
    use_fast_eta: bool | None = None,
    zone_ctx: DispatchZoneContext | None = None,
    traffic_multiplier: float = 1.0,
) -> list[MatchCandidate]:
    """Return vehicles ranked by pickup ETA and operator scoring for ``trip``."""
    pol = policy or NetworkPolicy()
    candidate_limit = limit if limit is not None else pol.dispatch_candidate_limit
    fast_eta = use_fast_eta if use_fast_eta is not None else pol.dispatch_use_fast_eta
    dropoff_zone = zone_for_point(trip.destination.lat, trip.destination.lon)
    traffic = traffic_multiplier if traffic_multiplier > 0 else pol.global_traffic_multiplier
    candidates: list[MatchCandidate] = []
    for vehicle in vehicles.values():
        if not _vehicle_dispatch_eligible(vehicle, pol, include_repositioning=include_repositioning):
            continue
        if not _charge_sufficient(vehicle, trip, router, pol, traffic_multiplier=traffic):
            continue
        if fast_eta:
            eta = _haversine_eta_min(
                vehicle.lat,
                vehicle.lon,
                trip.origin.lat,
                trip.origin.lon,
            )
        else:
            raw_eta = router.travel_time_between_points(
                vehicle.lat,
                vehicle.lon,
                trip.origin.lat,
                trip.origin.lon,
            )
            eta = raw_eta * traffic if raw_eta is not None else None
        if eta is None:
            continue
        if pol.max_deadhead_to_pickup_min > 0 and eta > pol.max_deadhead_to_pickup_min:
            continue
        score, balance_adj = _dispatch_score(vehicle, trip, eta, pol, zone_ctx=zone_ctx)
        if surge_multiplier != 1.0 and pol.dispatch_weight_surge == 0:
            score = eta * pol.dispatch_weight_eta + balance_adj
        candidates.append(
            MatchCandidate(
                vehicle_id=vehicle.id,
                eta_min=eta,
                score=score,
                state=vehicle.state,
                dropoff_zone=dropoff_zone,
                balance_adjustment=balance_adj,
            ),
        )
    candidates.sort(key=lambda c: (c.score, *_tie_break_key(c, vehicles, pol)[1:]))
    return candidates[:candidate_limit]


def pick_best_vehicle(
    trip: TripRequest,
    vehicles: dict[str, Vehicle],
    router: CityRouter,
    *,
    surge_multiplier: float = 1.0,
    policy: NetworkPolicy | None = None,
    include_repositioning: bool = False,
    zone_ctx: DispatchZoneContext | None = None,
    traffic_multiplier: float = 1.0,
) -> MatchCandidate | None:
    """Return the best vehicle for ``trip``, or None."""
    ranked = rank_dispatch_candidates(
        trip,
        vehicles,
        router,
        surge_multiplier=surge_multiplier,
        policy=policy,
        include_repositioning=include_repositioning,
        limit=1,
        zone_ctx=zone_ctx,
        traffic_multiplier=traffic_multiplier,
    )
    return ranked[0] if ranked else None


def estimate_trip_fare(
    travel_time_min: float,
    distance_km: float,
    policy: NetworkPolicy,
) -> float:
    """Compute fare from policy pricing levers."""
    miles = distance_km / _KM_PER_MILE
    return (
        policy.base_fare * policy.surge_multiplier
        + travel_time_min * policy.per_minute_fare
        + miles * policy.per_mile_fare
    )
