"""Pydantic schemas for operator routing rules."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RulePhase(StrEnum):
    """Whether a rule applies to trip dispatch or idle repositioning."""

    DISPATCH = "dispatch"
    REPOSITION = "reposition"


class ConditionType(StrEnum):
    """Routing rule condition kinds."""

    ZONE_DEFICIT = "zone_deficit"
    ZONE_SURPLUS = "zone_surplus"
    IDLE_MINUTES = "idle_minutes"
    FORECAST_RISING = "forecast_rising"
    PENDING_TRIPS = "pending_trips"
    TRIP_WAIT_MINUTES = "trip_wait_minutes"
    ACTIVE_EVENT = "active_event"
    TIME_OF_DAY = "time_of_day"


class ActionType(StrEnum):
    """Routing rule action kinds."""

    ASSIGN_NEAREST_ELIGIBLE = "assign_nearest_eligible"
    ASSIGN_PREFER_ZONE = "assign_prefer_zone"
    REPOSITION_TO_BEST_DEFICIT = "reposition_to_best_deficit"
    REPOSITION_TO_ZONE = "reposition_to_zone"
    SEND_TO_DEPOT = "send_to_depot"
    HOLD = "hold"


class CompareOp(StrEnum):
    """Numeric comparison operator for conditions."""

    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"
    EQ = "eq"


class RoutingCondition(BaseModel):
    """Single AND condition within a rule."""

    type: ConditionType
    operator: CompareOp = CompareOp.GTE
    value: float = 0.0
    value_max: float | None = Field(
        default=None,
        description="Upper bound for time_of_day hour range.",
    )
    zone: str | None = Field(
        default=None,
        description="Target zone; None uses vehicle or trip zone in context.",
    )


class RoutingAction(BaseModel):
    """Action executed when all rule conditions match."""

    type: ActionType
    target_zone: str | None = Field(
        default=None,
        description="Explicit zone for reposition_to_zone.",
    )


class RoutingRule(BaseModel):
    """One prioritized routing playbook entry."""

    id: str
    name: str
    enabled: bool = True
    priority: int = Field(default=0, ge=0)
    phase: RulePhase
    conditions: list[RoutingCondition] = Field(default_factory=list)
    action: RoutingAction


class RoutingRuleSet(BaseModel):
    """Ordered collection of routing rules."""

    rules: list[RoutingRule] = Field(default_factory=list)
    routing_enabled: bool = True

    def sorted_rules(self, phase: RulePhase) -> list[RoutingRule]:
        """Return enabled rules for ``phase`` sorted by priority ascending."""
        items = [r for r in self.rules if r.enabled and r.phase == phase]
        return sorted(items, key=lambda r: r.priority)


class RoutingRuleHit(BaseModel):
    """Audit entry when a routing rule fires."""

    timestamp_h: float
    rule_id: str
    rule_name: str
    phase: RulePhase
    subject_id: str
    action: ActionType
    detail: str = ""
