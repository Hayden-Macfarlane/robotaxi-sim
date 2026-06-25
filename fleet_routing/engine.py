"""Evaluate routing rules and produce dispatch / reposition decisions."""

from __future__ import annotations

import random
from dataclasses import dataclass

from core_data.models import GeoPoint, NetworkPolicy, TripRequest, Vehicle, VehicleState
from dispatch import pick_best_vehicle
from fleet_routing.constraints import (
    best_deficit_zone,
    pick_staging_in_zone,
    reposition_passes_roi,
    reposition_within_max_travel,
    vehicle_eligible_for_dispatch,
    vehicle_eligible_for_reposition,
)
from fleet_routing.context import RoutingContext
from fleet_routing.models import (
    ActionType,
    CompareOp,
    ConditionType,
    RoutingRule,
    RoutingRuleHit,
    RoutingRuleSet,
    RulePhase,
)


@dataclass(frozen=True)
class DispatchDecision:
    """Trip assignment produced by the routing engine."""

    trip_id: str
    vehicle_id: str
    rule_id: str
    rule_name: str
    action: ActionType


@dataclass(frozen=True)
class RepositionDecision:
    """Idle vehicle move produced by the routing engine."""

    vehicle_id: str
    staging: GeoPoint
    zone: str
    rule_id: str
    rule_name: str
    action: ActionType
    send_to_depot: bool = False


class RuleEvaluator:
    """Evaluate operator routing rules against live simulation context."""

    def __init__(self, rule_set: RoutingRuleSet) -> None:
        self._rule_set = rule_set

    @property
    def rule_set(self) -> RoutingRuleSet:
        return self._rule_set

    def evaluate_dispatch(
        self,
        ctx: RoutingContext,
        trip: TripRequest,
        vehicles: dict[str, Vehicle],
        *,
        assigned_vehicle_ids: set[str],
    ) -> DispatchDecision | None:
        """Return a dispatch decision for ``trip``, or None."""
        if not self._rule_set.routing_enabled:
            return None
        trip_zone = ctx.trip_zone(trip)
        wait_min = max(0.0, (ctx.sim_time_h - trip.requested_at_h) * 60.0)
        for rule in self._rule_set.sorted_rules(RulePhase.DISPATCH):
            if not self._conditions_match(
                rule,
                ctx,
                vehicle=None,
                trip=trip,
                trip_zone=trip_zone,
                wait_min=wait_min,
            ):
                continue
            decision = self._apply_dispatch_action(
                rule,
                ctx,
                trip,
                vehicles,
                assigned_vehicle_ids=assigned_vehicle_ids,
            )
            if decision is not None:
                return decision
        return None

    def evaluate_reposition(
        self,
        ctx: RoutingContext,
        vehicle: Vehicle,
        *,
        claimed: set[tuple[float, float]],
    ) -> RepositionDecision | None:
        """Return a reposition decision for ``vehicle``, or None."""
        if not self._rule_set.routing_enabled:
            return None
        if not vehicle_eligible_for_reposition(
            vehicle,
            ctx.policy,
            sim_time_h=ctx.sim_time_h,
            manual_hold_until_h=vehicle.manual_hold_until_h,
        ):
            return None
        vzone = ctx.vehicle_zone(vehicle)
        idle_min = max(0.0, (ctx.sim_time_h - vehicle.idle_since_h) * 60.0)
        for rule in self._rule_set.sorted_rules(RulePhase.REPOSITION):
            if not self._conditions_match(
                rule,
                ctx,
                vehicle=vehicle,
                trip=None,
                trip_zone=vzone,
                wait_min=idle_min,
                vehicle_zone_name=vzone,
            ):
                continue
            decision = self._apply_reposition_action(rule, ctx, vehicle, vzone, claimed=claimed)
            if decision is not None:
                return decision
        return None

    def _conditions_match(
        self,
        rule: RoutingRule,
        ctx: RoutingContext,
        *,
        vehicle: Vehicle | None,
        trip: TripRequest | None,
        trip_zone: str,
        wait_min: float,
        vehicle_zone_name: str | None = None,
    ) -> bool:
        """Return True if every condition in ``rule`` matches."""
        vzone = vehicle_zone_name or (ctx.vehicle_zone(vehicle) if vehicle else trip_zone)
        for cond in rule.conditions:
            if not self._eval_condition(
                cond,
                ctx,
                vehicle_zone=vzone,
                trip_zone=trip_zone,
                wait_min=wait_min,
            ):
                return False
        return True

    def _eval_condition(
        self,
        cond,
        ctx: RoutingContext,
        *,
        vehicle_zone: str,
        trip_zone: str,
        wait_min: float,
    ) -> bool:
        """Evaluate a single condition against context."""
        zone = cond.zone or (trip_zone if cond.type in (
            ConditionType.PENDING_TRIPS,
            ConditionType.TRIP_WAIT_MINUTES,
            ConditionType.ACTIVE_EVENT,
        ) else vehicle_zone)

        if cond.type == ConditionType.ZONE_DEFICIT:
            metric = ctx.gap_for_zone(zone)
        elif cond.type == ConditionType.ZONE_SURPLUS:
            metric = ctx.surplus_for_zone(zone)
        elif cond.type == ConditionType.IDLE_MINUTES:
            metric = wait_min
        elif cond.type == ConditionType.FORECAST_RISING:
            if cond.zone:
                metric = ctx.forecast_rising(cond.zone)
            else:
                metric = max((ctx.forecast_rising(z) for z in ctx.demand_now_by_zone), default=0.0)
        elif cond.type == ConditionType.PENDING_TRIPS:
            metric = float(ctx.pending_in_zone(zone))
        elif cond.type == ConditionType.TRIP_WAIT_MINUTES:
            metric = wait_min
        elif cond.type == ConditionType.ACTIVE_EVENT:
            return any(
                ev.zone == zone and ev.start_h <= ctx.sim_time_h < ev.end_h
                for ev in ctx.events
            )
        elif cond.type == ConditionType.TIME_OF_DAY:
            hour = ctx.sim_hour_of_day
            end = cond.value_max if cond.value_max is not None else cond.value
            if cond.value_max is not None:
                return cond.value <= hour <= end
            return self._compare(hour, cond.operator, cond.value)
        else:
            metric = 0.0

        return self._compare(metric, cond.operator, cond.value)

    @staticmethod
    def _compare(metric: float, op: CompareOp, threshold: float) -> bool:
        if op == CompareOp.GTE:
            return metric >= threshold
        if op == CompareOp.GT:
            return metric > threshold
        if op == CompareOp.LTE:
            return metric <= threshold
        if op == CompareOp.LT:
            return metric < threshold
        return metric == threshold

    def _apply_dispatch_action(
        self,
        rule: RoutingRule,
        ctx: RoutingContext,
        trip: TripRequest,
        vehicles: dict[str, Vehicle],
        *,
        assigned_vehicle_ids: set[str],
    ) -> DispatchDecision | None:
        action = rule.action.type
        if action == ActionType.HOLD:
            return None
        eligible = {
            vid: v for vid, v in vehicles.items()
            if vid not in assigned_vehicle_ids and vehicle_eligible_for_dispatch(v, ctx.policy)
        }
        if action == ActionType.ASSIGN_NEAREST_ELIGIBLE:
            match = pick_best_vehicle(
                trip,
                eligible,
                ctx.router,
                surge_multiplier=ctx.policy.surge_multiplier,
                policy=ctx.policy,
                include_repositioning=False,
            )
            if match is None:
                return None
            return DispatchDecision(
                trip_id=trip.id,
                vehicle_id=match.vehicle_id,
                rule_id=rule.id,
                rule_name=rule.name,
                action=action,
            )
        if action == ActionType.ASSIGN_NEAREST_IDLE_OR_REPOSITIONING:
            eligible_ext = {
                vid: v for vid, v in vehicles.items()
                if vid not in assigned_vehicle_ids
                and vehicle_eligible_for_dispatch(v, ctx.policy, include_repositioning=True)
            }
            match = pick_best_vehicle(
                trip,
                eligible_ext,
                ctx.router,
                surge_multiplier=ctx.policy.surge_multiplier,
                policy=ctx.policy,
                include_repositioning=True,
            )
            if match is None:
                return None
            return DispatchDecision(
                trip_id=trip.id,
                vehicle_id=match.vehicle_id,
                rule_id=rule.id,
                rule_name=rule.name,
                action=action,
            )
        if action == ActionType.ASSIGN_PREFER_ZONE:
            trip_zone = ctx.trip_zone(trip)
            in_zone = {
                vid: v for vid, v in eligible.items()
                if ctx.vehicle_zone(v) == trip_zone
            }
            pool = in_zone if in_zone else eligible
            match = pick_best_vehicle(
                trip,
                pool,
                ctx.router,
                surge_multiplier=ctx.policy.surge_multiplier,
                policy=ctx.policy,
                include_repositioning=False,
            )
            if match is None:
                return None
            return DispatchDecision(
                trip_id=trip.id,
                vehicle_id=match.vehicle_id,
                rule_id=rule.id,
                rule_name=rule.name,
                action=action,
            )
        return None

    def _apply_reposition_action(
        self,
        rule: RoutingRule,
        ctx: RoutingContext,
        vehicle: Vehicle,
        vzone: str,
        *,
        claimed: set[tuple[float, float]],
    ) -> RepositionDecision | None:
        action = rule.action.type
        if action == ActionType.HOLD:
            return RepositionDecision(
                vehicle_id=vehicle.id,
                staging=GeoPoint(lat=vehicle.lat, lon=vehicle.lon),
                zone=vzone,
                rule_id=rule.id,
                rule_name=rule.name,
                action=action,
            )
        if action == ActionType.SEND_TO_DEPOT:
            return RepositionDecision(
                vehicle_id=vehicle.id,
                staging=GeoPoint(lat=vehicle.lat, lon=vehicle.lon),
                zone=vzone,
                rule_id=rule.id,
                rule_name=rule.name,
                action=action,
                send_to_depot=True,
            )
        target_zone: str | None = None
        if action == ActionType.REPOSITION_TO_ZONE:
            target_zone = rule.action.target_zone
            if not target_zone:
                return None
        elif action == ActionType.REPOSITION_TO_BEST_DEFICIT:
            best = best_deficit_zone(vzone, ctx.zone_rows, ctx.supply_by_zone)
            if best is None:
                return None
            target_zone = best.zone
        else:
            return None

        staging = pick_staging_in_zone(
            ctx.router,
            target_zone,
            claimed=claimed,
            rng=ctx.rng,
        )
        if staging is None:
            return None
        route = ctx.router.route_between(vehicle.lat, vehicle.lon, staging.lat, staging.lon)
        if route is None:
            return None
        if not reposition_within_max_travel(route.travel_time_min, ctx.policy):
            return None
        gap = ctx.gap_for_zone(target_zone)
        if not reposition_passes_roi(gap, route.travel_time_min, ctx.policy):
            return None
        return RepositionDecision(
            vehicle_id=vehicle.id,
            staging=staging,
            zone=target_zone,
            rule_id=rule.id,
            rule_name=rule.name,
            action=action,
        )

    @staticmethod
    def hit_from_dispatch(decision: DispatchDecision, timestamp_h: float) -> RoutingRuleHit:
        """Build audit hit from dispatch decision."""
        return RoutingRuleHit(
            timestamp_h=timestamp_h,
            rule_id=decision.rule_id,
            rule_name=decision.rule_name,
            phase=RulePhase.DISPATCH,
            subject_id=decision.trip_id,
            action=decision.action,
            detail=f"vehicle {decision.vehicle_id}",
        )

    @staticmethod
    def hit_from_reposition(decision: RepositionDecision, timestamp_h: float) -> RoutingRuleHit:
        """Build audit hit from reposition decision."""
        if decision.action == ActionType.HOLD:
            detail = "hold position"
        elif decision.send_to_depot:
            detail = "send to depot"
        else:
            detail = f"→ {decision.zone}"
        return RoutingRuleHit(
            timestamp_h=timestamp_h,
            rule_id=decision.rule_id,
            rule_name=decision.rule_name,
            phase=RulePhase.REPOSITION,
            subject_id=decision.vehicle_id,
            action=decision.action,
            detail=detail,
        )
