"""Hard constraints applied after a routing rule matches."""

from __future__ import annotations

from core_data.models import GeoPoint, NetworkPolicy, Vehicle, VehicleState
from dispatch.reposition import reposition_benefit
from dispatch.reposition import ZoneBalance
from fleet.health import is_dispatch_eligible
from routing.city_router import CityRouter


def reposition_passes_roi(
    gap: float,
    travel_min: float,
    policy: NetworkPolicy,
) -> bool:
    """Return True if deadhead ROI meets policy minimum."""
    return reposition_benefit(gap, travel_min, policy) >= policy.min_reposition_benefit


def reposition_within_max_travel(travel_min: float, policy: NetworkPolicy) -> bool:
    """Return True if deadhead duration is within policy limit."""
    return travel_min <= policy.max_reposition_min


def vehicle_eligible_for_dispatch(
    vehicle: Vehicle,
    policy: NetworkPolicy,
    *,
    include_repositioning: bool = False,
) -> bool:
    """Return True if vehicle can accept a trip assignment."""
    allowed = {VehicleState.IDLE}
    if include_repositioning:
        allowed.add(VehicleState.REPOSITIONING)
    return vehicle.state in allowed and is_dispatch_eligible(vehicle, policy)


def vehicle_eligible_for_reposition(
    vehicle: Vehicle,
    policy: NetworkPolicy,
    *,
    sim_time_h: float,
    manual_hold_until_h: float | None,
) -> bool:
    """Return True if vehicle may be auto-repositioned."""
    if vehicle.state != VehicleState.IDLE:
        return False
    if manual_hold_until_h is not None and sim_time_h < manual_hold_until_h:
        return False
    return True


def best_deficit_zone(
    vehicle_zone_name: str,
    zone_rows: list[ZoneBalance],
    supply_by_zone: dict[str, int],
) -> ZoneBalance | None:
    """Return highest-gap zone excluding the vehicle's current zone."""
    best: ZoneBalance | None = None
    for row in zone_rows:
        if row.zone == vehicle_zone_name:
            continue
        if supply_by_zone.get(row.zone, 0) >= row.max_idle:
            continue
        if row.gap <= 0.0:
            continue
        if best is None or row.gap > best.gap:
            best = row
    return best


def pick_staging_in_zone(
    router: CityRouter,
    zone: str,
    *,
    claimed: set[tuple[float, float]],
    rng,
) -> GeoPoint | None:
    """Pick an unclaimed staging coordinate inside ``zone``."""
    from dispatch.reposition import pick_staging_point

    return pick_staging_point(router, zone, claimed=claimed, rng=rng)
