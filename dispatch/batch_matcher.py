"""Global batch dispatch: assign pending trips to vehicles without double-booking."""

from __future__ import annotations

from core_data.models import NetworkPolicy, TripRequest, Vehicle
from dispatch.matcher import DispatchZoneContext, rank_dispatch_candidates
from routing.city_router import CityRouter
from routing.zones import zone_for_point


def zone_dispatch_enabled(trip: TripRequest, policy: NetworkPolicy) -> bool:
    """Return True if auto-dispatch applies to the trip's origin zone."""
    if not policy.auto_dispatch_enabled:
        return False
    zone = zone_for_point(trip.origin.lat, trip.origin.lon)
    if zone in policy.auto_dispatch_by_zone:
        return policy.auto_dispatch_by_zone[zone]
    return True


def batch_assign_trips(
    pending_trips: list[TripRequest],
    vehicles: dict[str, Vehicle],
    router: CityRouter,
    policy: NetworkPolicy,
    *,
    include_repositioning: bool = False,
    zone_ctx: DispatchZoneContext | None = None,
    traffic_multiplier: float = 1.0,
) -> list[tuple[str, str]]:
    """Greedy global matching: return list of (trip_id, vehicle_id) pairs."""
    assigned_vehicles: set[str] = set()
    pairs: list[tuple[str, str]] = []
    dynamic_supply = dict(zone_ctx.supply_by_zone) if zone_ctx else {}
    sorted_trips = sorted(pending_trips, key=lambda t: t.requested_at_h)
    for trip in sorted_trips:
        if not zone_dispatch_enabled(trip, policy):
            continue
        available = {vid: v for vid, v in vehicles.items() if vid not in assigned_vehicles}
        ctx = zone_ctx
        if zone_ctx is not None:
            ctx = DispatchZoneContext(
                supply_by_zone=dynamic_supply,
                gap_by_zone=zone_ctx.gap_by_zone,
                cap_by_zone=zone_ctx.cap_by_zone,
            )
        ranked = rank_dispatch_candidates(
            trip,
            available,
            router,
            surge_multiplier=policy.surge_multiplier,
            policy=policy,
            include_repositioning=include_repositioning,
            limit=1,
            zone_ctx=ctx,
            traffic_multiplier=traffic_multiplier,
        )
        if not ranked:
            continue
        best = ranked[0]
        vehicle = vehicles.get(best.vehicle_id)
        if vehicle is None:
            continue
        pairs.append((trip.id, best.vehicle_id))
        assigned_vehicles.add(best.vehicle_id)
        if zone_ctx is not None:
            vehicle_zone = zone_for_point(vehicle.lat, vehicle.lon)
            dropoff_zone = zone_for_point(trip.destination.lat, trip.destination.lon)
            if dynamic_supply.get(vehicle_zone, 0) > 0:
                dynamic_supply[vehicle_zone] = dynamic_supply.get(vehicle_zone, 0) - 1
            dynamic_supply[dropoff_zone] = dynamic_supply.get(dropoff_zone, 0) + 1
    return pairs
