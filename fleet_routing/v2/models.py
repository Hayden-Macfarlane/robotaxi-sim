"""Pydantic schemas for rule engine v2."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RulePhaseV2(StrEnum):
    """Rule evaluation phase."""

    DISPATCH = "dispatch"
    REPOSITION = "reposition"
    FACILITY = "facility"


class CompareOpV2(StrEnum):
    """Numeric comparison operators."""

    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    BETWEEN = "between"


class ExprOp(StrEnum):
    """Expression tree node operators."""

    AND = "and"
    OR = "or"
    NOT = "not"
    COMPARE = "compare"
    METRIC = "metric"
    CONST = "const"


class MetricScope(StrEnum):
    """Metric subject scope."""

    VEHICLE = "vehicle"
    TRIP = "trip"
    ZONE = "zone"
    PAIR = "pairwise"
    GLOBAL = "global"
    FACILITY = "facility"
    CONSTANT = "constant"


class MetricValueType(StrEnum):
    """Return type of a metric."""

    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STRING = "string"


class MetricCategory(StrEnum):
    """UI grouping for constraint pickers."""

    DEMAND = "demand"
    DISTANCE = "distance"
    TIMING = "timing"
    ZONE = "zone"
    VEHICLE = "vehicle"
    DISPATCH = "dispatch"
    FLEET = "fleet"
    OTHER = "other"


class SelectionMode(StrEnum):
    """How to pick subjects when multiple match a rule."""

    ALL_MATCHING = "all_matching"
    MOST_CROWDED = "most_crowded"
    LEAST_CROWDED = "least_crowded"
    ONE_PER_CLUSTER = "one_per_cluster"
    HIGHEST_METRIC = "highest_metric"
    LOWEST_METRIC = "lowest_metric"
    BEST_DISPATCH_SCORE = "best_dispatch_score"
    ROUND_ROBIN_ZONE = "round_robin_zone"


class ActionTypeV2(StrEnum):
    """Parameterized rule actions."""

    ASSIGN_VEHICLE = "assign_vehicle"
    ASSIGN_NEAREST_IDLE = "assign_nearest_idle"
    ASSIGN_NEAREST_AVAILABLE = "assign_nearest_available"
    HOLD = "hold"
    REPOSITION_TO_POINT = "reposition_to_point"
    REPOSITION_TO_ZONE = "reposition_to_zone"
    REPOSITION_TO_BEST_DEFICIT = "reposition_to_best_deficit"
    REPOSITION_TO_NEAREST_DENSITY_FLOOR = "reposition_to_nearest_density_floor"
    SEND_TO_FACILITY = "send_to_facility"
    RELEASE_FROM_FACILITY = "release_from_facility"
    CANCEL_TRIP = "cancel_trip"


class MetricRef(BaseModel):
    """Reference to a registered metric with optional parameters."""

    id: str
    params: dict[str, float | str | int | bool] = Field(default_factory=dict)


class ExprNode(BaseModel):
    """Composable boolean/numeric expression tree."""

    op: ExprOp
    metric: MetricRef | None = None
    operator: CompareOpV2 | None = None
    value: float | None = None
    value_max: float | None = None
    right_metric: MetricRef | None = None
    children: list[ExprNode] = Field(default_factory=list)


class ActionSpec(BaseModel):
    """THEN action with typed parameters."""

    type: ActionTypeV2
    params: dict[str, Any] = Field(default_factory=dict)
    constraints: ExprNode | None = None
    rank_by: MetricRef | None = None
    filter: ExprNode | None = None


class RuleV2(BaseModel):
    """One prioritized playbook rule."""

    id: str
    name: str
    enabled: bool = True
    priority: int = Field(default=0, ge=0)
    phase: RulePhaseV2
    when: ExprNode
    selection: SelectionMode = SelectionMode.ALL_MATCHING
    selection_metric: MetricRef | None = None
    selection_params: dict[str, float | str | int | bool] = Field(default_factory=dict)
    action: ActionSpec
    rank_by: MetricRef | None = None


class PlaybookV2(BaseModel):
    """Operator playbook: constants + ordered rules."""

    enabled: bool = True
    constants: dict[str, float] = Field(default_factory=dict)
    rules: list[RuleV2] = Field(default_factory=list)

    def sorted_rules(self, phase: RulePhaseV2) -> list[RuleV2]:
        """Return enabled rules for ``phase`` sorted by priority ascending."""
        items = [r for r in self.rules if r.enabled and r.phase == phase]
        return sorted(items, key=lambda r: r.priority)


class MetricMeta(BaseModel):
    """UI and documentation metadata for a registered metric."""

    id: str
    scope: MetricScope
    value_type: MetricValueType
    industry_label: str
    plain_label: str
    description: str
    unit: str = ""
    category: MetricCategory = MetricCategory.OTHER
    phases: list[RulePhaseV2] = Field(default_factory=list)
    param_schema: dict[str, str] = Field(default_factory=dict)


class ParamFieldMeta(BaseModel):
    """Typed parameter field metadata for actions and selection modes."""

    type: str
    plain_label: str
    industry_label: str = ""
    description: str = ""
    default: float | int | bool | str | None = None
    unit: str = ""


class ConstantMeta(BaseModel):
    """UI metadata for a named playbook constant."""

    id: str
    plain_label: str
    industry_label: str
    description: str
    unit: str = ""
    default: float = 0.0
    min: float | None = None
    max: float | None = None
    related_metrics: list[str] = Field(default_factory=list)
    related_rules: list[str] = Field(default_factory=list)


class ActionMeta(BaseModel):
    """UI metadata for a rule action type."""

    id: str
    plain_label: str
    industry_label: str
    description: str
    phases: list[RulePhaseV2] = Field(default_factory=list)
    param_schema: dict[str, ParamFieldMeta] = Field(default_factory=dict)
    requires_selection: bool = False


class SelectionMeta(BaseModel):
    """UI metadata for a subject selection mode."""

    id: str
    plain_label: str
    industry_label: str
    description: str
    requires_metric: bool = False
    phases: list[RulePhaseV2] = Field(default_factory=list)
    param_schema: dict[str, ParamFieldMeta] = Field(default_factory=dict)


class RuleTemplate(BaseModel):
    """Insertable rule preset for the UI library."""

    id: str
    name: str
    summary: str
    category: str
    phase: RulePhaseV2
    rule: RuleV2


class RuleHitV2(BaseModel):
    """Audit entry when a v2 rule fires or is evaluated."""

    timestamp_h: float
    rule_id: str
    rule_name: str
    phase: RulePhaseV2
    subject_id: str
    action: ActionTypeV2
    matched: bool = True
    detail: str = ""
    metric_values: dict[str, float | int | bool | str] = Field(default_factory=dict)
    selection_reason: str = ""
    destination_search: dict[str, Any] = Field(default_factory=dict)
    shadow_only: bool = False


class RoutingEngineVersion(StrEnum):
    """Which routing engine executes decisions."""

    V1 = "v1"
    V2 = "v2"
    SHADOW = "shadow"
