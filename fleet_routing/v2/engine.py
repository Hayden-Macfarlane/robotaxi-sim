"""Rule engine v2 — evaluate playbook rules for dispatch and reposition."""

from __future__ import annotations

from dataclasses import dataclass

from core_data.models import TripRequest, TripStatus, Vehicle
from fleet_routing.v2.actions import DispatchActionResult, RepositionActionResult, execute_dispatch_action, execute_reposition_action
from fleet_routing.v2.context import EvalContext
from fleet_routing.v2.evaluator import collect_metric_snapshot, evaluate_expr
from fleet_routing.v2.models import ActionTypeV2, PlaybookV2, RuleHitV2, RulePhaseV2, RuleV2
from fleet_routing.v2.selection import eligible_dispatch_vehicles, eligible_idle_vehicles, select_vehicles


@dataclass(frozen=True)
class EnginePlan:
    """Batch of decisions produced by one engine tick."""

    dispatch: list[DispatchActionResult]
    reposition: list[RepositionActionResult]
    hits: list[RuleHitV2]


class RuleEngineV2:
    """Evaluate operator playbook rules."""

    def __init__(self, playbook: PlaybookV2) -> None:
        self._playbook = playbook

    @property
    def playbook(self) -> PlaybookV2:
        return self._playbook

    def plan(self, ctx: EvalContext, *, timestamp_h: float, shadow_only: bool = False) -> EnginePlan:
        """Produce dispatch and reposition decisions without mutating world state."""
        if not self._playbook.enabled:
            return EnginePlan(dispatch=[], reposition=[], hits=[])
        constants = dict(self._playbook.constants)
        dispatch_out: list[DispatchActionResult] = []
        reposition_out: list[RepositionActionResult] = []
        hits: list[RuleHitV2] = []
        assigned: set[str] = set()
        claimed: set[tuple[float, float]] = set()

        pending_trips = sorted(
            (t for t in ctx.trips.values() if t.status == TripStatus.PENDING),
            key=lambda t: t.requested_at_h,
        )
        for trip in pending_trips:
            decision = self._plan_dispatch(ctx, trip, assigned=assigned, constants=constants, timestamp_h=timestamp_h, shadow_only=shadow_only, hits=hits)
            if decision is not None:
                dispatch_out.append(decision)
                assigned.add(decision.vehicle_id)

        idle = [v for v in eligible_idle_vehicles(ctx) if v.id not in assigned]
        if timestamp_h <= 0.0:
            return EnginePlan(dispatch=dispatch_out, reposition=[], hits=hits)
        for vehicle in idle:
            if vehicle.id in assigned:
                continue
            for rule in self._playbook.sorted_rules(RulePhaseV2.REPOSITION):
                if not evaluate_expr(rule.when, ctx, vehicle=vehicle, constants=constants):
                    continue
                selected = select_vehicles(rule, ctx, [vehicle], constants=constants)
                if not selected:
                    continue
                result = execute_reposition_action(rule.action, ctx, vehicle, constants=constants, claimed=claimed)
                metrics = collect_metric_snapshot(rule.when, ctx, vehicle=vehicle, constants=constants)
                hits.append(
                    RuleHitV2(
                        timestamp_h=timestamp_h,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        phase=RulePhaseV2.REPOSITION,
                        subject_id=vehicle.id,
                        action=rule.action.type,
                        matched=result is not None,
                        detail=result.detail if result else "no_action",
                        metric_values=metrics,
                        selection_reason=rule.selection.value,
                        destination_search=result.destination_search if result and result.destination_search else {},
                        shadow_only=shadow_only,
                    ),
                )
                if result is None:
                    break
                if result.send_to_depot:
                    reposition_out.append(result)
                    assigned.add(vehicle.id)
                    break
                reposition_out.append(result)
                assigned.add(vehicle.id)
                break

        return EnginePlan(dispatch=dispatch_out, reposition=reposition_out, hits=hits)

    def _plan_dispatch(
        self,
        ctx: EvalContext,
        trip: TripRequest,
        *,
        assigned: set[str],
        constants: dict[str, float],
        timestamp_h: float,
        shadow_only: bool,
        hits: list[RuleHitV2],
    ) -> DispatchActionResult | None:
        vehicles = eligible_dispatch_vehicles(ctx, include_repositioning=True)
        for rule in self._playbook.sorted_rules(RulePhaseV2.DISPATCH):
            if not evaluate_expr(rule.when, ctx, trip=trip, constants=constants):
                continue
            result = execute_dispatch_action(rule.action, ctx, trip, vehicles, constants=constants, assigned=assigned)
            metrics = collect_metric_snapshot(rule.when, ctx, trip=trip, constants=constants)
            hits.append(
                RuleHitV2(
                    timestamp_h=timestamp_h,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    phase=RulePhaseV2.DISPATCH,
                    subject_id=trip.id,
                    action=rule.action.type,
                    matched=result is not None,
                    detail=result.detail if result else "no_match",
                    metric_values=metrics,
                    shadow_only=shadow_only,
                ),
            )
            if result is not None:
                return result
        return None
