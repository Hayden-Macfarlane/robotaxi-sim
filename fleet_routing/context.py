"""Routing evaluation context built from live simulation state."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from core_data.models import NetworkPolicy, SpecialEvent, TripRequest, Vehicle
from demand.generator import DemandGenerator
from dispatch.reposition import expected_demand_by_zone, vehicle_zone, zone_balances
from dispatch.reposition import ZoneBalance
from routing.city_router import CityRouter


@dataclass
class RoutingContext:
    """Snapshot of zone metrics and simulation clock for rule evaluation."""

    sim_time_h: float
    router: CityRouter
    policy: NetworkPolicy
    demand: DemandGenerator
    supply_by_zone: dict[str, int]
    pending_by_zone: dict[str, int]
    events: list[SpecialEvent]
    horizon_h: float = 0.5
    rng: random.Random = field(default_factory=random.Random)
    zone_rows: list[ZoneBalance] = field(default_factory=list)
    zone_rows_future: list[ZoneBalance] = field(default_factory=list)
    demand_now_by_zone: dict[str, float] = field(default_factory=dict)
    demand_future_by_zone: dict[str, float] = field(default_factory=dict)

    @property
    def sim_hour_of_day(self) -> float:
        """Fractional hour-of-day for time-of-day conditions."""
        return self.sim_time_h % 24.0

    def gap_for_zone(self, zone: str) -> float:
        """Return demand gap for ``zone`` (positive = deficit)."""
        for row in self.zone_rows:
            if row.zone == zone:
                return row.gap
        return 0.0

    def surplus_for_zone(self, zone: str) -> float:
        """Return idle surplus above cap for ``zone``."""
        supply = self.supply_by_zone.get(zone, 0)
        cap = self._cap_for_zone(zone)
        return float(max(0, supply - cap))

    def forecast_rising(self, zone: str) -> float:
        """Return forecast demand delta T+horizon minus now for ``zone``."""
        now = self.demand_now_by_zone.get(zone, 0.0)
        future = self.demand_future_by_zone.get(zone, 0.0)
        return future - now

    def pending_in_zone(self, zone: str) -> int:
        """Return open trip count in ``zone``."""
        return self.pending_by_zone.get(zone, 0)

    def vehicle_zone(self, vehicle: Vehicle) -> str:
        """Resolve supply zone for ``vehicle``."""
        return vehicle_zone(vehicle, self.router)

    def trip_zone(self, trip: TripRequest) -> str:
        """Resolve pickup zone for ``trip``."""
        from routing.zones import zone_for_point

        node = self.router.get_node(trip.origin_snap_node_id)
        if node is not None and node.zone:
            return node.zone
        return zone_for_point(trip.origin.lat, trip.origin.lon)

    def _cap_for_zone(self, zone: str) -> int:
        if zone in self.policy.max_idle_by_zone:
            return self.policy.max_idle_by_zone[zone]
        return self.policy.max_idle_per_zone


def build_routing_context(
    router: CityRouter,
    policy: NetworkPolicy,
    demand: DemandGenerator,
    *,
    sim_time_h: float,
    supply_by_zone: dict[str, int],
    pending_by_zone: dict[str, int],
    events: list[SpecialEvent],
    horizon_h: float = 0.5,
    rng: random.Random | None = None,
) -> RoutingContext:
    """Build a routing context with current and forecast zone balances."""
    zone_rows = zone_balances(
        router,
        policy,
        demand,
        sim_time_h=sim_time_h,
        supply_by_zone=supply_by_zone,
        pending_by_zone=pending_by_zone,
        events=events,
    )
    zone_rows_future = zone_balances(
        router,
        policy,
        demand,
        sim_time_h=sim_time_h,
        supply_by_zone=supply_by_zone,
        pending_by_zone=pending_by_zone,
        horizon_h=horizon_h,
        events=events,
    )
    demand_now = expected_demand_by_zone(
        demand,
        router,
        sim_time_h=sim_time_h,
        pending_by_zone=pending_by_zone,
        events=events,
    )
    demand_future = expected_demand_by_zone(
        demand,
        router,
        sim_time_h=sim_time_h,
        pending_by_zone=pending_by_zone,
        horizon_h=horizon_h,
        events=events,
    )
    return RoutingContext(
        sim_time_h=sim_time_h,
        router=router,
        policy=policy,
        demand=demand,
        supply_by_zone=supply_by_zone,
        pending_by_zone=pending_by_zone,
        events=events,
        horizon_h=horizon_h,
        rng=rng or random.Random(),
        zone_rows=zone_rows,
        zone_rows_future=zone_rows_future,
        demand_now_by_zone=demand_now,
        demand_future_by_zone=demand_future,
    )
