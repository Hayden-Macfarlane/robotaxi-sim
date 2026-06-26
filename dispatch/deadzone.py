"""Deadzone detection and ratio-gated coverage filler repositioning."""

from __future__ import annotations

import random
from dataclasses import dataclass

from core_data.models import GeoPoint, NetworkPolicy, Vehicle, VehicleState
from dispatch.reposition import _all_zones, idle_patience_min, pick_staging_point, vehicle_zone
from routing.city_router import CityRouter
from routing.geo import haversine_km


@dataclass(frozen=True)
class Deadzone:
    """Geographic area lacking idle vehicle coverage within policy distance."""

    zone: str
    point: GeoPoint
    nearest_asset_km: float
    size_km: float


@dataclass(frozen=True)
class DeadzoneFillDecision:
    """Reposition move to improve coverage in an under-served area."""

    zone: str
    staging: GeoPoint
    travel_min: float
    travel_km: float
    deadzone_size_km: float
    fill_ratio: float


def nearest_idle_asset_km(
    lat: float,
    lon: float,
    vehicles: dict[str, Vehicle],
    *,
    exclude_id: str | None = None,
) -> float | None:
    """Return haversine km to the closest idle vehicle, or None if none exist."""
    best: float | None = None
    for vehicle in vehicles.values():
        if vehicle.id == exclude_id:
            continue
        if vehicle.state != VehicleState.IDLE:
            continue
        dist = haversine_km(lat, lon, vehicle.lat, vehicle.lon)
        if best is None or dist < best:
            best = dist
    return best


def deadzone_fill_ratio(
    deadzone_size_km: float,
    travel_km: float,
    policy: NetworkPolicy,
) -> float:
    """Return fill score: (size + adjustment) / (travel + adjustment). Higher = better fill."""
    numerator = deadzone_size_km + policy.deadzone_size_adjustment_km
    denominator = max(travel_km + policy.deadzone_travel_adjustment_km, 0.01)
    return numerator / denominator


def passes_deadzone_fill_ratio(
    deadzone_size_km: float,
    travel_km: float,
    policy: NetworkPolicy,
) -> bool:
    """Return True when the fill ratio meets the operator threshold."""
    return deadzone_fill_ratio(deadzone_size_km, travel_km, policy) >= policy.deadzone_fill_ratio_threshold


def zone_representative_point(router: CityRouter, zone: str) -> GeoPoint | None:
    """Return a snapped network point representing ``zone`` for coverage sampling."""
    bbox = router.zone_bounding_boxes().get(zone)
    if bbox is None:
        return None
    min_lat, max_lat, min_lon, max_lon = bbox
    lat = (min_lat + max_lat) / 2
    lon = (min_lon + max_lon) / 2
    snap = router.snap_to_network(lat, lon)
    if snap is not None:
        return snap.point
    return GeoPoint(lat=lat, lon=lon)


def find_deadzones(
    router: CityRouter,
    vehicles: dict[str, Vehicle],
    policy: NetworkPolicy,
) -> list[Deadzone]:
    """Return zones whose centroid lacks idle coverage within max asset distance."""
    if not policy.deadzone_filler_enabled:
        return []
    threshold = policy.max_distance_from_nearest_asset_km
    deadzones: list[Deadzone] = []
    for zone in _all_zones(router):
        point = zone_representative_point(router, zone)
        if point is None:
            continue
        nearest = nearest_idle_asset_km(point.lat, point.lon, vehicles)
        if nearest is None:
            continue
        if nearest <= threshold:
            continue
        size_km = nearest - threshold
        deadzones.append(
            Deadzone(
                zone=zone,
                point=point,
                nearest_asset_km=round(nearest, 3),
                size_km=round(size_km, 3),
            ),
        )
    deadzones.sort(key=lambda d: d.size_km, reverse=True)
    return deadzones


def pick_deadzone_fill_decision(
    vehicle: Vehicle,
    router: CityRouter,
    policy: NetworkPolicy,
    vehicles: dict[str, Vehicle],
    *,
    sim_time_h: float,
    claimed: set[tuple[float, float]],
    rng: random.Random,
) -> DeadzoneFillDecision | None:
    """Return best ratio-qualified deadzone fill for ``vehicle``, or None."""
    if not policy.deadzone_filler_enabled:
        return None
    if vehicle.state != VehicleState.IDLE:
        return None
    if vehicle.manual_hold_until_h is not None and sim_time_h < vehicle.manual_hold_until_h:
        return None
    vzone = vehicle_zone(vehicle, router)
    idle_min = max(0.0, (sim_time_h - vehicle.idle_since_h) * 60.0)
    if idle_min < idle_patience_min(policy, vzone):
        return None

    deadzones = find_deadzones(router, vehicles, policy)
    if not deadzones:
        return None

    best: DeadzoneFillDecision | None = None
    for dz in deadzones:
        if dz.zone == vzone:
            continue
        staging = pick_staging_point(router, dz.zone, claimed=claimed, rng=rng)
        if staging is None:
            staging = dz.point
        route = router.route_between(vehicle.lat, vehicle.lon, staging.lat, staging.lon)
        if route is None:
            continue
        if route.travel_time_min > policy.max_reposition_min:
            continue
        ratio = deadzone_fill_ratio(dz.size_km, route.distance_km, policy)
        if not passes_deadzone_fill_ratio(dz.size_km, route.distance_km, policy):
            continue
        candidate = DeadzoneFillDecision(
            zone=dz.zone,
            staging=staging,
            travel_min=route.travel_time_min,
            travel_km=route.distance_km,
            deadzone_size_km=dz.size_km,
            fill_ratio=round(ratio, 3),
        )
        if best is None or candidate.fill_ratio > best.fill_ratio:
            best = candidate
    return best
