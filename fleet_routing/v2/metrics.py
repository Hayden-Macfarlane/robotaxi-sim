"""MetricRegistry — catalog and compute functions for rule engine v2."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core_data.models import TripRequest, Vehicle, VehicleState
from dispatch.deadzone import deadzone_fill_ratio, nearest_idle_asset_km
from dispatch.matcher import MatchCandidate, pick_best_vehicle, dispatch_zone_context_from_rows
from dispatch.reposition import idle_patience_min, reposition_benefit, vehicle_zone, zone_cap
from fleet.health import is_dispatch_eligible
from fleet_routing.v2.context import EvalContext, KpiSnapshot
from fleet_routing.v2.metric_categories import METRIC_CATEGORIES
from fleet_routing.v2.models import MetricCategory, MetricMeta, MetricScope, MetricValueType, RulePhaseV2
from routing.geo import haversine_km
from routing.zones import zone_for_point

MetricValue = float | int | bool | str
MetricFn = Callable[..., MetricValue]


@dataclass(frozen=True)
class RegisteredMetric:
    """One metric definition in the registry."""

    meta: MetricMeta
    compute: MetricFn


class MetricRegistry:
    """Central catalog of rule variables."""

    def __init__(self) -> None:
        self._metrics: dict[str, RegisteredMetric] = {}
        self._register_all()

    def get(self, metric_id: str) -> RegisteredMetric | None:
        return self._metrics.get(metric_id)

    def all_meta(self) -> list[MetricMeta]:
        return [m.meta for m in self._metrics.values()]

    def compute(
        self,
        metric_id: str,
        ctx: EvalContext,
        *,
        vehicle: Vehicle | None = None,
        trip: TripRequest | None = None,
        other_vehicle: Vehicle | None = None,
        zone: str | None = None,
        constants: dict[str, float] | None = None,
        params: dict[str, Any] | None = None,
    ) -> MetricValue:
        """Evaluate a metric by id."""
        reg = self._metrics.get(metric_id)
        if reg is None:
            return 0.0
        return reg.compute(
            ctx,
            vehicle=vehicle,
            trip=trip,
            other_vehicle=other_vehicle,
            zone=zone,
            constants=constants or {},
            params=params or {},
        )

    def _register(self, meta: MetricMeta, fn: MetricFn) -> None:
        category = METRIC_CATEGORIES.get(meta.id, MetricCategory.OTHER)
        meta = meta.model_copy(update={"category": category})
        self._metrics[meta.id] = RegisteredMetric(meta=meta, compute=fn)

    def _register_all(self) -> None:
        """Register full metric catalog."""
        self._register_spatial_vehicle()
        self._register_zone()
        self._register_vehicle_state()
        self._register_projected_battery()
        self._register_trip()
        self._register_pairwise()
        self._register_facility()
        self._register_global()
        self._register_time_event()
        self._register_constants()

    def _register_spatial_vehicle(self) -> None:
        phases = [RulePhaseV2.DISPATCH, RulePhaseV2.REPOSITION]

        def _nearest_idle(ctx: EvalContext, vehicle: Vehicle | None = None, params: dict[str, Any] | None = None, **_: Any) -> MetricValue:
            if vehicle is None:
                return 9999.0
            p = params or {}
            rank = int(p.get("rank", 1))
            d = ctx.spatial.nearest_idle_km(vehicle, rank=rank)
            return d if d is not None else 9999.0

        self._register(
            MetricMeta(id="vehicle.nearest_idle_km", scope=MetricScope.VEHICLE, value_type=MetricValueType.FLOAT,
                       industry_label="Nearest idle distance", plain_label="Distance to nearest idle car",
                       description="Haversine km to closest other idle vehicle.", unit="km", phases=phases),
            _nearest_idle,
        )
        self._register(
            MetricMeta(id="vehicle.nearest_idle_km_rank", scope=MetricScope.VEHICLE, value_type=MetricValueType.FLOAT,
                       industry_label="Nth nearest idle", plain_label="Distance to Nth nearest idle",
                       description="Distance to rank-N nearest idle vehicle.", unit="km", phases=phases,
                       param_schema={"rank": "int"}),
            _nearest_idle,
        )

        def _nearest_fleet(ctx: EvalContext, vehicle: Vehicle | None = None, **_: Any) -> MetricValue:
            if vehicle is None:
                return 9999.0
            best = 9999.0
            for other in ctx.spatial.all_vehicles:
                if other.id == vehicle.id:
                    continue
                d = haversine_km(vehicle.lat, vehicle.lon, other.lat, other.lon)
                best = min(best, d)
            return best

        self._register(
            MetricMeta(id="vehicle.nearest_fleet_km", scope=MetricScope.VEHICLE, value_type=MetricValueType.FLOAT,
                       industry_label="Nearest fleet asset", plain_label="Distance to nearest vehicle",
                       description="Closest vehicle regardless of state.", unit="km", phases=phases),
            _nearest_fleet,
        )

        def _nearest_busy(ctx: EvalContext, vehicle: Vehicle | None = None, **_: Any) -> MetricValue:
            if vehicle is None:
                return 9999.0
            busy = {VehicleState.TO_PICKUP, VehicleState.WITH_RIDER, VehicleState.REPOSITIONING, VehicleState.TO_FACILITY}
            best = 9999.0
            for other in ctx.spatial.all_vehicles:
                if other.id == vehicle.id or other.state not in busy:
                    continue
                d = haversine_km(vehicle.lat, vehicle.lon, other.lat, other.lon)
                best = min(best, d)
            return best if best < 9999.0 else 9999.0

        self._register(
            MetricMeta(id="vehicle.nearest_busy_km", scope=MetricScope.VEHICLE, value_type=MetricValueType.FLOAT,
                       industry_label="Nearest busy vehicle", plain_label="Distance to nearest busy car",
                       description="Closest vehicle on trip or repositioning.", unit="km", phases=phases),
            _nearest_busy,
        )

        def _count_within(idle_only: bool) -> MetricFn:
            def fn(ctx: EvalContext, vehicle: Vehicle | None = None, params: dict[str, Any] | None = None, **_: Any) -> MetricValue:
                if vehicle is None:
                    return 0
                r = float((params or {}).get("radius_km", 1.0))
                if idle_only:
                    return ctx.spatial.idle_count_within_km(vehicle.lat, vehicle.lon, r, exclude_id=vehicle.id)
                return ctx.spatial.fleet_count_within_km(vehicle.lat, vehicle.lon, r, exclude_id=vehicle.id)
            return fn

        self._register(
            MetricMeta(id="vehicle.idle_count_within_km", scope=MetricScope.VEHICLE, value_type=MetricValueType.INT,
                       industry_label="Idle neighbors", plain_label="Idle cars within radius",
                       description="Idle vehicles within radius.", unit="count", phases=phases,
                       param_schema={"radius_km": "float"}),
            _count_within(True),
        )
        self._register(
            MetricMeta(id="vehicle.fleet_count_within_km", scope=MetricScope.VEHICLE, value_type=MetricValueType.INT,
                       industry_label="Fleet neighbors", plain_label="All cars within radius",
                       description="All vehicles within radius.", unit="count", phases=phases,
                       param_schema={"radius_km": "float"}),
            _count_within(False),
        )

        def _local_density(idle_only: bool) -> MetricFn:
            def fn(ctx: EvalContext, vehicle: Vehicle | None = None, params: dict[str, Any] | None = None, **_: Any) -> MetricValue:
                if vehicle is None:
                    return 0.0
                r = float((params or {}).get("radius_km", 1.0))
                return ctx.spatial.local_density(vehicle.lat, vehicle.lon, r, idle_only=idle_only, exclude_id=vehicle.id)
            return fn

        self._register(
            MetricMeta(id="vehicle.local_idle_density", scope=MetricScope.VEHICLE, value_type=MetricValueType.FLOAT,
                       industry_label="Local idle density", plain_label="Idle density nearby",
                       description="Idle vehicles per km² within radius.", unit="per_km2", phases=phases,
                       param_schema={"radius_km": "float"}),
            _local_density(True),
        )
        self._register(
            MetricMeta(id="vehicle.local_fleet_density", scope=MetricScope.VEHICLE, value_type=MetricValueType.FLOAT,
                       industry_label="Local fleet density", plain_label="Fleet density nearby",
                       description="All vehicles per km² within radius.", unit="per_km2", phases=phases,
                       param_schema={"radius_km": "float"}),
            _local_density(False),
        )

        def _most_crowded(ctx: EvalContext, vehicle: Vehicle | None = None, params: dict[str, Any] | None = None, **_: Any) -> MetricValue:
            if vehicle is None:
                return False
            r = float((params or {}).get("radius_km", 1.0))
            return ctx.spatial.is_most_crowded(vehicle, r)

        self._register(
            MetricMeta(id="vehicle.is_most_crowded_in_radius", scope=MetricScope.VEHICLE, value_type=MetricValueType.BOOL,
                       industry_label="Most crowded locally", plain_label="Most crowded in radius",
                       description="True if this vehicle has the smallest gap to its nearest idle neighbor.",
                       phases=phases, param_schema={"radius_km": "float"}),
            _most_crowded,
        )

        def _deadzone_size(ctx: EvalContext, vehicle: Vehicle | None = None, constants: dict[str, float] | None = None, **_: Any) -> MetricValue:
            if vehicle is None:
                return 0.0
            c = constants or {}
            max_dist = c.get("max_distance_from_nearest_asset_km", ctx.policy.max_distance_from_nearest_asset_km)
            nearest = nearest_idle_asset_km(vehicle.lat, vehicle.lon, ctx.vehicles, exclude_id=vehicle.id)
            if nearest is None:
                return max_dist
            return max(0.0, nearest - max_dist)

        self._register(
            MetricMeta(id="vehicle.deadzone_size_km", scope=MetricScope.VEHICLE, value_type=MetricValueType.FLOAT,
                       industry_label="Deadzone size", plain_label="Coverage gap beyond nearest car",
                       description="How far past the coverage radius the nearest idle car is.", unit="km",
                       phases=[RulePhaseV2.REPOSITION]),
            _deadzone_size,
        )

        def _nearest_unmatched(ctx: EvalContext, vehicle: Vehicle | None = None, **_: Any) -> MetricValue:
            if vehicle is None:
                return 9999.0
            d = ctx.spatial.nearest_unmatched_rider_km(vehicle, ctx.trips)
            return d if d is not None else 9999.0

        self._register(
            MetricMeta(
                id="vehicle.nearest_unmatched_rider_km",
                scope=MetricScope.VEHICLE,
                value_type=MetricValueType.FLOAT,
                industry_label="Nearest unmatched rider",
                plain_label="Distance to nearest waiting rider",
                description="Straight-line km to the closest unmatched trip pickup.",
                unit="km",
                phases=phases,
            ),
            _nearest_unmatched,
        )

        def _unmatched_within(ctx: EvalContext, vehicle: Vehicle | None = None, params: dict[str, Any] | None = None, **_: Any) -> MetricValue:
            if vehicle is None:
                return 0
            r = float((params or {}).get("radius_km", 2.0))
            return ctx.spatial.unmatched_riders_within_km(vehicle, ctx.trips, r)

        self._register(
            MetricMeta(
                id="vehicle.unmatched_riders_within_km",
                scope=MetricScope.VEHICLE,
                value_type=MetricValueType.INT,
                industry_label="Unmatched riders nearby",
                plain_label="Waiting riders within radius",
                description="Count of unmatched trip pickups within the given radius.",
                unit="count",
                phases=phases,
                param_schema={"radius_km": "float"},
            ),
            _unmatched_within,
        )

    def _register_zone(self) -> None:
        phases = [RulePhaseV2.DISPATCH, RulePhaseV2.REPOSITION, RulePhaseV2.FACILITY]

        def _zone_metric(field: str) -> MetricFn:
            def fn(ctx: EvalContext, zone: str | None = None, vehicle: Vehicle | None = None, trip: TripRequest | None = None, **_: Any) -> MetricValue:
                z = ctx.resolve_zone(zone, vehicle=vehicle, trip=trip)
                row = ctx.zone_row(z)
                if row is None:
                    return 0.0 if field != "active_event" else False
                if field == "supply":
                    return float(row.supply)
                if field == "pending_demand":
                    return float(row.pending_demand)
                if field == "expected_demand":
                    return row.expected_demand
                if field == "gap":
                    return row.gap
                if field == "surplus":
                    return ctx.routing.surplus_for_zone(z)
                if field == "target_supply":
                    return float(row.target_supply)
                if field == "supply_shortfall":
                    return float(max(0, row.target_supply - row.supply))
                if field == "max_idle":
                    return float(row.max_idle)
                if field == "headroom":
                    return float(max(0, row.max_idle - row.supply))
                if field == "demand_per_idle":
                    denom = max(row.supply, 1)
                    return (row.expected_demand + row.pending_demand) / denom
                if field == "forecast_now":
                    return ctx.routing.demand_now_by_zone.get(z, 0.0)
                if field == "forecast_rising":
                    return ctx.routing.forecast_rising(z)
                if field == "forecast_t15":
                    return ctx.forecast_t15.get(z, 0.0)
                if field == "forecast_t30":
                    return ctx.forecast_t30.get(z, 0.0)
                if field == "forecast_t60":
                    return ctx.forecast_t60.get(z, 0.0)
                if field == "active_event":
                    return any(ev.zone == z and ev.start_h <= ctx.sim_time_h < ev.end_h for ev in ctx.routing.events)
                if field == "event_multiplier":
                    for ev in ctx.routing.events:
                        if ev.zone == z and ev.start_h <= ctx.sim_time_h < ev.end_h:
                            return ev.demand_multiplier
                    return 1.0
                return 0.0
            return fn

        zone_fields = [
            ("zone.supply", "supply", "Idle supply", "Idle cars in zone", "Idle cars currently in this area"),
            ("zone.pending_demand", "pending_demand", "Pending demand", "Waiting riders in zone", "Unmatched trips waiting in this area"),
            ("zone.expected_demand", "expected_demand", "Expected demand", "Expected trip demand", "Forecast-weighted demand for this area"),
            ("zone.gap", "gap", "Zone gap", "Supply shortage score", "How undersupplied this zone is"),
            ("zone.surplus", "surplus", "Zone surplus", "Idle above cap", "Idle cars above the zone cap"),
            ("zone.target_supply", "target_supply", "Target supply", "Minimum idle target", "Target idle cars for this area"),
            ("zone.supply_shortfall", "supply_shortfall", "Supply shortfall", "Below target count", "How many idle cars below target"),
            ("zone.max_idle", "max_idle", "Max idle cap", "Idle cap", "Maximum idle cars allowed here"),
            ("zone.headroom", "headroom", "Headroom", "Cap minus supply", "Spare idle slots before hitting cap"),
            ("zone.demand_per_idle", "demand_per_idle", "Demand per idle", "Load per idle car", "Demand pressure per idle vehicle"),
            ("zone.forecast_now", "forecast_now", "Forecast now", "Current demand forecast", "Current forecast intensity"),
            ("zone.forecast_t15", "forecast_t15", "Forecast +15m", "Demand in 15 minutes", "Forecast demand in 15 minutes"),
            ("zone.forecast_t30", "forecast_t30", "Forecast +30m", "Demand in 30 minutes", "Forecast demand in 30 minutes"),
            ("zone.forecast_t60", "forecast_t60", "Forecast +60m", "Demand in 60 minutes", "Forecast demand in 60 minutes"),
            ("zone.forecast_rising", "forecast_rising", "Forecast rising", "Demand rising", "Expected demand increase vs now"),
        ]
        for mid, field, industry, plain, desc in zone_fields:
            vtype = MetricValueType.FLOAT
            self._register(
                MetricMeta(id=mid, scope=MetricScope.ZONE, value_type=vtype, industry_label=industry,
                           plain_label=plain, description=desc, phases=phases,
                           param_schema={"zone": "string"}),
                _zone_metric(field),
            )

        self._register(
            MetricMeta(id="zone.active_event", scope=MetricScope.ZONE, value_type=MetricValueType.BOOL,
                       industry_label="Event active", plain_label="Demand event active",
                       description="Special event running in zone.", phases=phases, param_schema={"zone": "string"}),
            _zone_metric("active_event"),
        )
        self._register(
            MetricMeta(id="zone.event_multiplier", scope=MetricScope.ZONE, value_type=MetricValueType.FLOAT,
                       industry_label="Event multiplier", plain_label="Event demand boost",
                       description="Active event demand multiplier.", phases=phases, param_schema={"zone": "string"}),
            _zone_metric("event_multiplier"),
        )

    def _register_vehicle_state(self) -> None:
        phases = [RulePhaseV2.DISPATCH, RulePhaseV2.REPOSITION, RulePhaseV2.FACILITY]

        def _veh(field: str) -> MetricFn:
            def fn(ctx: EvalContext, vehicle: Vehicle | None = None, **_: Any) -> MetricValue:
                if vehicle is None:
                    return 0.0 if field not in ("is_dispatch_eligible", "is_off_street", "needs_charge", "needs_cleaning", "needs_maintenance", "is_saturated_zone") else False
                pol = ctx.policy
                if field == "battery_pct":
                    return vehicle.battery_pct
                if field == "condition_pct":
                    return vehicle.condition_pct
                if field == "cleanliness_pct":
                    return vehicle.cleanliness_pct
                if field == "idle_minutes":
                    return max(0.0, (ctx.sim_time_h - vehicle.idle_since_h) * 60.0)
                if field == "manual_hold_remaining_min":
                    if vehicle.manual_hold_until_h is None:
                        return 0.0
                    return max(0.0, (vehicle.manual_hold_until_h - ctx.sim_time_h) * 60.0)
                if field == "leg_progress_pct":
                    if vehicle.leg_ends_at_h is None or vehicle.leg_started_at_h is None:
                        return 0.0
                    span = vehicle.leg_ends_at_h - vehicle.leg_started_at_h
                    if span <= 0:
                        return 1.0
                    return min(1.0, max(0.0, (ctx.sim_time_h - vehicle.leg_started_at_h) / span))
                if field == "leg_remaining_min":
                    if vehicle.leg_ends_at_h is None:
                        return 0.0
                    return max(0.0, (vehicle.leg_ends_at_h - ctx.sim_time_h) * 60.0)
                if field == "is_dispatch_eligible":
                    return is_dispatch_eligible(vehicle, pol)
                if field == "is_off_street":
                    return vehicle.state in {VehicleState.CHARGING, VehicleState.CLEANING, VehicleState.MAINTENANCE, VehicleState.AT_DEPOT}
                if field == "needs_charge":
                    return vehicle.battery_pct <= pol.low_battery_pct
                if field == "needs_cleaning":
                    return vehicle.cleanliness_pct <= pol.low_cleanliness_pct
                if field == "needs_maintenance":
                    return vehicle.condition_pct <= pol.low_condition_pct
                if field == "is_saturated_zone":
                    z = vehicle_zone(vehicle, ctx.router)
                    return ctx.routing.supply_by_zone.get(z, 0) >= zone_cap(pol, z)
                if field == "zone":
                    return vehicle_zone(vehicle, ctx.router)
                return 0.0
            return fn

        for mid, field, label in [
            ("vehicle.battery_pct", "battery_pct", "Battery %"),
            ("vehicle.condition_pct", "condition_pct", "Condition %"),
            ("vehicle.cleanliness_pct", "cleanliness_pct", "Cleanliness %"),
            ("vehicle.idle_minutes", "idle_minutes", "Idle minutes"),
            ("vehicle.manual_hold_remaining_min", "manual_hold_remaining_min", "Manual hold remaining"),
            ("vehicle.leg_progress_pct", "leg_progress_pct", "Leg progress"),
            ("vehicle.leg_remaining_min", "leg_remaining_min", "Leg remaining"),
            ("vehicle.is_dispatch_eligible", "is_dispatch_eligible", "Dispatch eligible"),
            ("vehicle.is_off_street", "is_off_street", "At facility"),
            ("vehicle.needs_charge", "needs_charge", "Needs charge"),
            ("vehicle.needs_cleaning", "needs_cleaning", "Needs cleaning"),
            ("vehicle.needs_maintenance", "needs_maintenance", "Needs maintenance"),
            ("vehicle.is_saturated_zone", "is_saturated_zone", "Zone saturated"),
        ]:
            vtype = MetricValueType.BOOL if field.startswith("is_") or field.startswith("needs_") else MetricValueType.FLOAT
            self._register(
                MetricMeta(id=mid, scope=MetricScope.VEHICLE, value_type=vtype, industry_label=label,
                           plain_label=label, description=label, phases=phases),
                _veh(field),
            )

    def _register_projected_battery(self) -> None:
        phases = [RulePhaseV2.DISPATCH, RulePhaseV2.REPOSITION]

        def _energy_km(ctx: EvalContext, vehicle: Vehicle, trip: TripRequest | None) -> float:
            if trip is None:
                return 0.0
            pickup = haversine_km(vehicle.lat, vehicle.lon, trip.origin.lat, trip.origin.lon) * 1.35
            ride = haversine_km(trip.origin.lat, trip.origin.lon, trip.destination.lat, trip.destination.lon) * 1.35
            return pickup + ride

        def _projected(ctx: EvalContext, vehicle: Vehicle | None = None, trip: TripRequest | None = None, params: dict[str, Any] | None = None, **_: Any) -> MetricValue:
            if vehicle is None:
                return 0.0
            pol = ctx.policy
            km = 0.0
            p = params or {}
            mode = p.get("mode", "after_trip")
            if mode == "after_pickup" and trip:
                km = haversine_km(vehicle.lat, vehicle.lon, trip.origin.lat, trip.origin.lon) * 1.35
            elif mode == "after_trip" and trip:
                km = _energy_km(ctx, vehicle, trip)
            elif mode == "after_reposition":
                lat = float(p.get("lat", vehicle.lat))
                lon = float(p.get("lon", vehicle.lon))
                km = haversine_km(vehicle.lat, vehicle.lon, lat, lon) * 1.35
            drain = km * pol.battery_drain_per_km
            return max(0.0, vehicle.battery_pct - drain)

        self._register(
            MetricMeta(id="vehicle.projected_battery_after_pickup", scope=MetricScope.PAIR, value_type=MetricValueType.FLOAT,
                       industry_label="Battery after pickup", plain_label="Projected battery after pickup",
                       description="SOC after deadhead to pickup.", unit="%", phases=[RulePhaseV2.DISPATCH]),
            lambda ctx, vehicle=None, trip=None, **kw: _projected(ctx, vehicle, trip, params={"mode": "after_pickup"}, **kw),
        )
        self._register(
            MetricMeta(id="vehicle.projected_battery_after_trip", scope=MetricScope.PAIR, value_type=MetricValueType.FLOAT,
                       industry_label="Battery after trip", plain_label="Projected battery after full trip",
                       description="SOC after pickup + ride.", unit="%", phases=[RulePhaseV2.DISPATCH]),
            lambda ctx, vehicle=None, trip=None, **kw: _projected(ctx, vehicle, trip, params={"mode": "after_trip"}, **kw),
        )
        self._register(
            MetricMeta(id="vehicle.energy_needed_for_trip_pct", scope=MetricScope.PAIR, value_type=MetricValueType.FLOAT,
                       industry_label="Energy for trip", plain_label="Battery needed for trip",
                       description="Estimated SOC drain for pickup + ride.", unit="%", phases=[RulePhaseV2.DISPATCH]),
            lambda ctx, vehicle=None, trip=None, **kw: (
                _energy_km(ctx, vehicle, trip) * ctx.policy.battery_drain_per_km if vehicle and trip else 0.0
            ),
        )
        self._register(
            MetricMeta(id="vehicle.can_complete_trip_on_charge", scope=MetricScope.PAIR, value_type=MetricValueType.BOOL,
                       industry_label="Can complete trip", plain_label="Enough charge for trip",
                       description="Projected battery stays above minimum after trip.", phases=[RulePhaseV2.DISPATCH]),
            lambda ctx, vehicle=None, trip=None, **kw: (
                float(_projected(ctx, vehicle, trip, params={"mode": "after_trip"}, **kw))
                >= ctx.policy.min_battery_pct_for_trip
                if vehicle and trip else False
            ),
        )

    def _register_trip(self) -> None:
        phases = [RulePhaseV2.DISPATCH]

        def _trip(field: str) -> MetricFn:
            def fn(ctx: EvalContext, trip: TripRequest | None = None, **_: Any) -> MetricValue:
                if trip is None:
                    return 0.0 if field not in ("is_cross_zone",) else False
                if field == "wait_minutes":
                    return max(0.0, (ctx.sim_time_h - trip.requested_at_h) * 60.0)
                if field == "sla_remaining_min":
                    wait = max(0.0, (ctx.sim_time_h - trip.requested_at_h) * 60.0)
                    return ctx.policy.max_wait_min - wait
                if field == "fare_estimate":
                    return trip.fare_estimate
                if field == "pickup_zone":
                    return ctx.routing.trip_zone(trip)
                if field == "dropoff_zone":
                    return ctx.routing.trip_dropoff_zone(trip)
                if field == "is_cross_zone":
                    return ctx.routing.trip_zone(trip) != ctx.routing.trip_dropoff_zone(trip)
                if field == "pickup_zone_gap":
                    return ctx.routing.gap_for_zone(ctx.routing.trip_zone(trip))
                if field == "dropoff_zone_gap":
                    return ctx.routing.gap_for_zone(ctx.routing.trip_dropoff_zone(trip))
                if field == "pickup_zone_forecast_rising":
                    return ctx.routing.forecast_rising(ctx.routing.trip_zone(trip))
                if field == "dropoff_zone_surplus":
                    return ctx.routing.surplus_for_zone(ctx.routing.trip_dropoff_zone(trip))
                return 0.0
            return fn

        for mid, field, label in [
            ("trip.wait_minutes", "wait_minutes", "Trip wait"),
            ("trip.sla_remaining_min", "sla_remaining_min", "SLA remaining"),
            ("trip.fare_estimate", "fare_estimate", "Fare estimate"),
            ("trip.is_cross_zone", "is_cross_zone", "Cross-zone trip"),
            ("trip.pickup_zone_gap", "pickup_zone_gap", "Pickup zone gap"),
            ("trip.dropoff_zone_gap", "dropoff_zone_gap", "Dropoff zone gap"),
            ("trip.pickup_zone_forecast_rising", "pickup_zone_forecast_rising", "Pickup forecast rising"),
            ("trip.dropoff_zone_surplus", "dropoff_zone_surplus", "Dropoff surplus"),
        ]:
            vtype = MetricValueType.BOOL if field == "is_cross_zone" else MetricValueType.FLOAT
            self._register(
                MetricMeta(id=mid, scope=MetricScope.TRIP, value_type=vtype, industry_label=label,
                           plain_label=label, description=label, phases=phases),
                _trip(field),
            )
        self._register(
            MetricMeta(id="trip.pickup_zone", scope=MetricScope.TRIP, value_type=MetricValueType.STRING,
                       industry_label="Pickup zone", plain_label="Pickup zone", description="Trip origin zone.",
                       phases=phases),
            _trip("pickup_zone"),
        )
        self._register(
            MetricMeta(id="trip.dropoff_zone", scope=MetricScope.TRIP, value_type=MetricValueType.STRING,
                       industry_label="Dropoff zone", plain_label="Dropoff zone", description="Trip destination zone.",
                       phases=phases),
            _trip("dropoff_zone"),
        )

    def _register_pairwise(self) -> None:
        def _match(ctx: EvalContext, vehicle: Vehicle | None, trip: TripRequest | None) -> MatchCandidate | None:
            if vehicle is None or trip is None:
                return None
            zone_ctx = dispatch_zone_context_from_rows(
                ctx.routing.supply_by_zone, ctx.routing.zone_rows, ctx.policy,
            )
            m = pick_best_vehicle(
                trip, {vehicle.id: vehicle}, ctx.router,
                surge_multiplier=ctx.policy.surge_multiplier,
                policy=ctx.policy,
                include_repositioning=True,
                zone_ctx=zone_ctx,
                traffic_multiplier=ctx.policy.global_traffic_multiplier,
            )
            return m

        def _pair(field: str) -> MetricFn:
            def fn(ctx: EvalContext, vehicle: Vehicle | None = None, trip: TripRequest | None = None, params: dict[str, Any] | None = None, **_: Any) -> MetricValue:
                p = params or {}
                if field.startswith("reposition_"):
                    if vehicle is None:
                        return 0.0
                    lat = float(p.get("lat", vehicle.lat))
                    lon = float(p.get("lon", vehicle.lon))
                    route = ctx.router.route_between(vehicle.lat, vehicle.lon, lat, lon)
                    if route is None:
                        return 9999.0 if "travel" in field else 0.0
                    if field == "reposition_travel_min":
                        return route.travel_time_min * ctx.policy.global_traffic_multiplier
                    if field == "reposition_travel_km":
                        return route.distance_km
                    target_zone = zone_for_point(lat, lon)
                    gap = ctx.routing.gap_for_zone(target_zone)
                    travel = route.travel_time_min * ctx.policy.global_traffic_multiplier
                    if field == "reposition_benefit":
                        return reposition_benefit(gap, travel, ctx.policy)
                    if field == "target_zone_gap":
                        return gap
                    origin_d = ctx.spatial.local_density(vehicle.lat, vehicle.lon, float(p.get("radius_km", 1.0)), idle_only=True, exclude_id=vehicle.id)
                    dest_d = ctx.spatial.local_density(lat, lon, float(p.get("radius_km", 1.0)), idle_only=True)
                    if field == "density_ratio_dest_over_origin":
                        return dest_d / max(origin_d, 1e-9)
                    if field == "deadzone_fill_ratio":
                        nearest = nearest_idle_asset_km(lat, lon, ctx.vehicles, exclude_id=vehicle.id)
                        size = max(0.0, (nearest or 0) - ctx.policy.max_distance_from_nearest_asset_km)
                        return deadzone_fill_ratio(size, route.distance_km, ctx.policy)
                    return 0.0
                m = _match(ctx, vehicle, trip)
                if m is None:
                    return 9999.0 if field == "eta_pickup_min" else 0.0
                if field == "eta_pickup_min":
                    return m.eta_min
                if field == "dispatch_score":
                    return m.score
                if field == "balance_adjustment":
                    return m.balance_adjustment
                if field == "cross_zone_dispatch":
                    vz = vehicle_zone(vehicle, ctx.router) if vehicle else ""
                    tz = ctx.routing.trip_zone(trip) if trip else ""
                    return vz != tz
                return 0.0
            return fn

        pairs = [
            ("pair.eta_pickup_min", "eta_pickup_min", "Pickup ETA", "Minutes for this car to reach the rider"),
            ("pair.dispatch_score", "dispatch_score", "Dispatch score", "Lower score means better match for this trip"),
            ("pair.balance_adjustment", "balance_adjustment", "Dropoff balance bonus", "Bonus for improving dropoff zone balance"),
            ("pair.cross_zone_dispatch", "cross_zone_dispatch", "Cross-zone dispatch", "True if car and pickup are in different zones"),
            ("pair.reposition_travel_min", "reposition_travel_min", "Reposition travel time", "Minutes to drive to staging point"),
            ("pair.reposition_travel_km", "reposition_travel_km", "Reposition distance", "Km to drive to staging point"),
            ("pair.reposition_benefit", "reposition_benefit", "Reposition benefit", "Expected value minus deadhead cost"),
            ("pair.target_zone_gap", "target_zone_gap", "Target zone shortage", "Demand gap at the staging zone"),
            ("pair.density_ratio_dest_over_origin", "density_ratio_dest_over_origin", "Destination density ratio", "Idle density at destination vs origin"),
            ("pair.deadzone_fill_ratio", "deadzone_fill_ratio", "Deadzone fill score", "Coverage gain vs travel cost for a fill move"),
        ]
        for mid, field, label, desc in pairs:
            vtype = MetricValueType.BOOL if field == "cross_zone_dispatch" else MetricValueType.FLOAT
            self._register(
                MetricMeta(id=mid, scope=MetricScope.PAIR, value_type=vtype, industry_label=label,
                           plain_label=label, description=desc,
                           phases=[RulePhaseV2.DISPATCH] if "dispatch" in field or field == "eta_pickup_min" or field == "cross_zone_dispatch" or field == "balance_adjustment" else [RulePhaseV2.REPOSITION],
                           param_schema={"lat": "float", "lon": "float", "radius_km": "float"}),
                _pair(field),
            )

    def _register_facility(self) -> None:
        def _fleet(ctx: EvalContext, field: str, **_: Any) -> MetricValue:
            off = sum(1 for v in ctx.vehicles.values() if v.state in {VehicleState.AT_DEPOT, VehicleState.CHARGING, VehicleState.CLEANING, VehicleState.MAINTENANCE})
            if field == "on_street_count":
                return len(ctx.vehicles) - off
            if field == "at_facility_count":
                return off
            return 0

        self._register(
            MetricMeta(id="fleet.on_street_count", scope=MetricScope.GLOBAL, value_type=MetricValueType.INT,
                       industry_label="On street", plain_label="Vehicles on street",
                       description="Vehicles not at a facility.", phases=[RulePhaseV2.FACILITY]),
            lambda ctx, **kw: _fleet(ctx, "on_street_count", **kw),
        )
        self._register(
            MetricMeta(id="fleet.at_facility_count", scope=MetricScope.GLOBAL, value_type=MetricValueType.INT,
                       industry_label="At facilities", plain_label="Vehicles at facilities",
                       description="Off-street vehicle count.", phases=[RulePhaseV2.FACILITY]),
            lambda ctx, **kw: _fleet(ctx, "at_facility_count", **kw),
        )

    def _register_global(self) -> None:
        def _kpi(field: str) -> MetricFn:
            def fn(ctx: EvalContext, **_: Any) -> MetricValue:
                k = ctx.kpis
                return getattr(k, field, 0)
            return fn

        for mid, field, label in [
            ("global.pending_trips", "pending_trips", "Pending trips"),
            ("global.avg_wait_min", "avg_wait_min", "Average wait"),
            ("global.p95_wait_min", "p95_wait_min", "P95 wait"),
            ("global.fleet_utilization_pct", "fleet_utilization_pct", "Fleet utilization"),
            ("global.deadhead_ratio", "deadhead_ratio", "Deadhead ratio"),
            ("global.profit", "profit", "Profit"),
            ("global.completion_rate", "completion_rate", "Completion rate"),
            ("global.trips_per_vehicle_hour", "trips_per_vehicle_hour", "Trips per vehicle hour"),
            ("global.vehicles_needing_service", "vehicles_needing_service", "Needs service count"),
            ("global.avg_battery_pct", "avg_battery_pct", "Average battery"),
            ("global.worst_zone_gap", "worst_zone_gap", "Worst zone gap"),
            ("global.surplus_zone_count", "surplus_zone_count", "Surplus zones"),
            ("global.deficit_zone_count", "deficit_zone_count", "Deficit zones"),
        ]:
            vtype = MetricValueType.INT if field in ("pending_trips", "vehicles_needing_service", "surplus_zone_count", "deficit_zone_count") else MetricValueType.FLOAT
            self._register(
                MetricMeta(id=mid, scope=MetricScope.GLOBAL, value_type=vtype, industry_label=label,
                           plain_label=label, description=label, phases=list(RulePhaseV2)),
                _kpi(field),
            )

        self._register(
            MetricMeta(id="global.traffic_multiplier", scope=MetricScope.GLOBAL, value_type=MetricValueType.FLOAT,
                       industry_label="Traffic multiplier", plain_label="Traffic slowdown",
                       description="Global network traffic multiplier.", phases=list(RulePhaseV2)),
            lambda ctx, **_: ctx.policy.global_traffic_multiplier,
        )
        self._register(
            MetricMeta(id="global.surge_multiplier", scope=MetricScope.GLOBAL, value_type=MetricValueType.FLOAT,
                       industry_label="Surge multiplier", plain_label="Surge pricing multiplier",
                       description="Current surge multiplier.", phases=list(RulePhaseV2)),
            lambda ctx, **_: ctx.policy.surge_multiplier,
        )

    def _register_time_event(self) -> None:
        self._register(
            MetricMeta(id="time.hour_of_day", scope=MetricScope.GLOBAL, value_type=MetricValueType.FLOAT,
                       industry_label="Hour of day", plain_label="Sim hour",
                       description="Fractional hour 0–24.", unit="h", phases=list(RulePhaseV2)),
            lambda ctx, **_: ctx.routing.sim_hour_of_day,
        )

    def _register_constants(self) -> None:
        self._register(
            MetricMeta(id="const.value", scope=MetricScope.CONSTANT, value_type=MetricValueType.FLOAT,
                       industry_label="Playbook constant", plain_label="Constant",
                       description="Named constant from playbook.", param_schema={"name": "string"},
                       phases=list(RulePhaseV2)),
            lambda ctx, constants=None, params=None, **_: ctx.const(constants or {}, str((params or {}).get("name", "")), 0.0),
        )


REGISTRY = MetricRegistry()
