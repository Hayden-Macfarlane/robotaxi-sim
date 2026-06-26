"""EvalContext — live simulation snapshot for metric evaluation."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from core_data.models import Facility, NetworkPolicy, SpecialEvent, TripRequest, TripStatus, Vehicle, VehicleState
from demand.generator import DemandGenerator
from dispatch.reposition import ZoneBalance, expected_demand_by_zone, vehicle_zone, zone_balances
from fleet_routing.context import RoutingContext, build_routing_context
from routing.city_router import CityRouter
from routing.geo import haversine_km


@dataclass(frozen=True)
class KpiSnapshot:
    """Global KPI values for rule evaluation."""

    pending_trips: int = 0
    avg_wait_min: float = 0.0
    p95_wait_min: float = 0.0
    fleet_utilization_pct: float = 0.0
    deadhead_ratio: float = 0.0
    profit: float = 0.0
    completion_rate: float = 0.0
    trips_per_vehicle_hour: float = 0.0
    vehicles_needing_service: int = 0
    avg_battery_pct: float = 100.0
    worst_zone_gap: float = 0.0
    surplus_zone_count: int = 0
    deficit_zone_count: int = 0
    on_street_count: int = 0
    at_facility_count: int = 0


@dataclass
class SpatialIndex:
    """Precomputed idle-vehicle neighborhood data."""

    idle_vehicles: list[Vehicle] = field(default_factory=list)
    all_vehicles: list[Vehicle] = field(default_factory=list)

    def nearest_idle_km(self, vehicle: Vehicle, *, rank: int = 1) -> float | None:
        """Return haversine km to the ``rank``-th nearest other idle vehicle."""
        dists: list[float] = []
        for other in self.idle_vehicles:
            if other.id == vehicle.id:
                continue
            dists.append(haversine_km(vehicle.lat, vehicle.lon, other.lat, other.lon))
        if not dists:
            return None
        dists.sort()
        idx = max(0, rank - 1)
        return dists[idx] if idx < len(dists) else None

    def idle_count_within_km(self, lat: float, lon: float, radius_km: float, *, exclude_id: str | None = None) -> int:
        """Count idle vehicles within ``radius_km`` of a point."""
        count = 0
        for v in self.idle_vehicles:
            if exclude_id and v.id == exclude_id:
                continue
            if haversine_km(lat, lon, v.lat, v.lon) <= radius_km:
                count += 1
        return count

    def fleet_count_within_km(self, lat: float, lon: float, radius_km: float, *, exclude_id: str | None = None) -> int:
        """Count all vehicles within ``radius_km``."""
        count = 0
        for v in self.all_vehicles:
            if exclude_id and v.id == exclude_id:
                continue
            if haversine_km(lat, lon, v.lat, v.lon) <= radius_km:
                count += 1
        return count

    def local_density(self, lat: float, lon: float, radius_km: float, *, idle_only: bool = True, exclude_id: str | None = None) -> float:
        """Return vehicles per km² within radius."""
        if radius_km <= 0:
            return 0.0
        count = (
            self.idle_count_within_km(lat, lon, radius_km, exclude_id=exclude_id)
            if idle_only
            else self.fleet_count_within_km(lat, lon, radius_km, exclude_id=exclude_id)
        )
        area = math.pi * radius_km * radius_km
        return count / max(area, 1e-9)

    def is_most_crowded(self, vehicle: Vehicle, radius_km: float) -> bool:
        """True if vehicle has minimum nearest-neighbor distance among idle in radius."""
        my_nearest = self.nearest_idle_km(vehicle, rank=1)
        if my_nearest is None:
            return False
        for other in self.idle_vehicles:
            if other.id == vehicle.id:
                continue
            if haversine_km(vehicle.lat, vehicle.lon, other.lat, other.lon) > radius_km:
                continue
            other_nearest = self.nearest_idle_km(other, rank=1)
            if other_nearest is not None and other_nearest < my_nearest - 1e-6:
                return False
        return True

    def nearest_unmatched_rider_km(self, vehicle: Vehicle, trips: dict[str, TripRequest]) -> float | None:
        """Return haversine km to the nearest pending (unmatched) trip pickup."""
        best: float | None = None
        for trip in trips.values():
            if trip.status != TripStatus.PENDING:
                continue
            dist = haversine_km(vehicle.lat, vehicle.lon, trip.origin.lat, trip.origin.lon)
            if best is None or dist < best:
                best = dist
        return best

    def unmatched_riders_within_km(
        self,
        vehicle: Vehicle,
        trips: dict[str, TripRequest],
        radius_km: float,
    ) -> int:
        """Count pending trip pickups within ``radius_km`` of ``vehicle``."""
        count = 0
        for trip in trips.values():
            if trip.status != TripStatus.PENDING:
                continue
            if haversine_km(vehicle.lat, vehicle.lon, trip.origin.lat, trip.origin.lon) <= radius_km:
                count += 1
        return count


@dataclass
class EvalContext:
    """Superset routing context with vehicles, trips, facilities, and spatial index."""

    routing: RoutingContext
    vehicles: dict[str, Vehicle]
    trips: dict[str, TripRequest]
    facilities: dict[str, Facility]
    kpis: KpiSnapshot
    spatial: SpatialIndex
    zone_row_by_name: dict[str, ZoneBalance] = field(default_factory=dict)
    forecast_t15: dict[str, float] = field(default_factory=dict)
    forecast_t30: dict[str, float] = field(default_factory=dict)
    forecast_t60: dict[str, float] = field(default_factory=dict)
    _pair_cache: dict[str, float | int | bool | str] = field(default_factory=dict)

    @property
    def sim_time_h(self) -> float:
        return self.routing.sim_time_h

    @property
    def router(self) -> CityRouter:
        return self.routing.router

    @property
    def policy(self) -> NetworkPolicy:
        return self.routing.policy

    @property
    def rng(self) -> random.Random:
        return self.routing.rng

    def const(self, playbook_constants: dict[str, float], name: str, default: float = 0.0) -> float:
        """Resolve playbook constant or fall back to policy field by name."""
        if name in playbook_constants:
            return playbook_constants[name]
        return default

    def zone_row(self, zone: str) -> ZoneBalance | None:
        return self.zone_row_by_name.get(zone)

    def resolve_zone(self, zone_param: str | None, *, vehicle: Vehicle | None = None, trip: TripRequest | None = None) -> str:
        """Resolve zone parameter from explicit name, vehicle, or trip."""
        if zone_param:
            return zone_param
        if vehicle is not None:
            return self.routing.vehicle_zone(vehicle)
        if trip is not None:
            return self.routing.trip_zone(trip)
        return ""


def build_eval_context(
    router: CityRouter,
    policy: NetworkPolicy,
    demand: DemandGenerator,
    *,
    sim_time_h: float,
    supply_by_zone: dict[str, int],
    pending_by_zone: dict[str, int],
    events: list[SpecialEvent],
    vehicles: dict[str, Vehicle],
    trips: dict[str, TripRequest],
    facilities: dict[str, Facility],
    kpis: KpiSnapshot,
    horizon_h: float = 0.5,
    rng: random.Random | None = None,
) -> EvalContext:
    """Build evaluation context with spatial index and multi-horizon forecast."""
    routing = build_routing_context(
        router,
        policy,
        demand,
        sim_time_h=sim_time_h,
        supply_by_zone=supply_by_zone,
        pending_by_zone=pending_by_zone,
        events=events,
        horizon_h=horizon_h,
        rng=rng,
    )
    idle = [v for v in vehicles.values() if v.state == VehicleState.IDLE]
    spatial = SpatialIndex(idle_vehicles=idle, all_vehicles=list(vehicles.values()))
    zone_row_by_name = {row.zone: row for row in routing.zone_rows}

    def _forecast(h: float) -> dict[str, float]:
        return expected_demand_by_zone(
            demand,
            router,
            sim_time_h=sim_time_h,
            pending_by_zone=pending_by_zone,
            horizon_h=h,
            events=events,
        )

    return EvalContext(
        routing=routing,
        vehicles=vehicles,
        trips=trips,
        facilities=facilities,
        kpis=kpis,
        spatial=spatial,
        zone_row_by_name=zone_row_by_name,
        forecast_t15=_forecast(0.25),
        forecast_t30=_forecast(0.5),
        forecast_t60=_forecast(1.0),
    )
