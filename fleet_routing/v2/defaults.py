"""Default v2 playbooks and parity presets."""

from __future__ import annotations

import json
from pathlib import Path

from fleet_routing.v2.constants import default_constants
from fleet_routing.v2.models import (
    ActionSpec,
    ActionTypeV2,
    CompareOpV2,
    ExprNode,
    ExprOp,
    MetricRef,
    PlaybookV2,
    RulePhaseV2,
    RuleV2,
    SelectionMode,
)


def _compare(metric_id: str, op: CompareOpV2, value: float, **params: float | str) -> ExprNode:
    return ExprNode(
        op=ExprOp.COMPARE,
        metric=MetricRef(id=metric_id, params=dict(params)),
        operator=op,
        value=value,
    )


def _compare_const(const_name: str, op: CompareOpV2, metric_id: str, **params: float | str) -> ExprNode:
    """Compare a metric against a named playbook constant."""
    return ExprNode(
        op=ExprOp.COMPARE,
        metric=MetricRef(id=metric_id, params=dict(params)),
        operator=op,
        right_metric=MetricRef(id="const.value", params={"name": const_name}),
    )


def _and(*children: ExprNode) -> ExprNode:
    return ExprNode(op=ExprOp.AND, children=list(children))


def default_playbook_v2() -> PlaybookV2:
    """Return parity playbook mirroring legacy default_routing_rules behavior."""
    return PlaybookV2(
        enabled=True,
        constants=default_constants(),
        rules=[
            RuleV2(
                id="v2-serve-pending",
                name="Serve waiting riders",
                priority=10,
                phase=RulePhaseV2.DISPATCH,
                when=_compare("zone.pending_demand", CompareOpV2.GTE, 1.0),
                action=ActionSpec(type=ActionTypeV2.ASSIGN_VEHICLE, params={"preempt_reposition": True}),
            ),
            RuleV2(
                id="v2-surplus-evict",
                name="Leave crowded zone",
                priority=20,
                phase=RulePhaseV2.REPOSITION,
                when=_compare("zone.surplus", CompareOpV2.GTE, 1.0),
                action=ActionSpec(type=ActionTypeV2.REPOSITION_TO_BEST_DEFICIT),
            ),
            RuleV2(
                id="v2-idle-relocate",
                name="Relocate if idle too long",
                priority=30,
                phase=RulePhaseV2.REPOSITION,
                when=_compare_const("idle_patience_min", CompareOpV2.GTE, "vehicle.idle_minutes"),
                action=ActionSpec(type=ActionTypeV2.REPOSITION_TO_BEST_DEFICIT),
            ),
            RuleV2(
                id="v2-forecast-staging",
                name="Stage for forecast peak",
                priority=40,
                phase=RulePhaseV2.REPOSITION,
                when=_compare_const("forecast_rising_threshold", CompareOpV2.GTE, "zone.forecast_rising"),
                action=ActionSpec(type=ActionTypeV2.REPOSITION_TO_BEST_DEFICIT),
            ),
            RuleV2(
                id="v2-deadzone-fill",
                name="Fill coverage deadzone",
                priority=45,
                phase=RulePhaseV2.REPOSITION,
                when=_compare("vehicle.deadzone_size_km", CompareOpV2.GT, 0.0),
                action=ActionSpec(
                    type=ActionTypeV2.REPOSITION_TO_NEAREST_DENSITY_FLOOR,
                    params={"min_density_ratio": 0.0, "radius_km": 1.0},
                ),
            ),
            RuleV2(
                id="v2-break-clusters",
                name="Break idle clusters",
                priority=50,
                phase=RulePhaseV2.REPOSITION,
                when=_and(
                    _compare_const("cluster_radius_km", CompareOpV2.LT, "vehicle.nearest_idle_km"),
                    _compare(
                        "vehicle.is_most_crowded_in_radius",
                        CompareOpV2.EQ,
                        1.0,
                        radius_km=0.8,
                    ),
                ),
                selection=SelectionMode.MOST_CROWDED,
                selection_params={"radius_km": 0.8},
                action=ActionSpec(
                    type=ActionTypeV2.REPOSITION_TO_NEAREST_DENSITY_FLOOR,
                    params={"min_density_ratio": 0.5, "radius_km": 1.0},
                ),
            ),
            RuleV2(
                id="v2-zone-cap-depot",
                name="Evict over zone cap to depot",
                priority=60,
                phase=RulePhaseV2.REPOSITION,
                when=_compare("zone.surplus", CompareOpV2.GTE, 1.0),
                action=ActionSpec(type=ActionTypeV2.SEND_TO_FACILITY),
            ),
        ],
    )


def manual_playbook_v2() -> PlaybookV2:
    """Empty playbook for manual-first reset — no rules or thresholds."""
    return PlaybookV2(enabled=True, constants={}, rules=[])


def load_playbook_v2(path: Path | None = None) -> PlaybookV2:
    """Load playbook JSON from disk or return default."""
    if path is None:
        path = Path(__file__).resolve().parents[2] / "data" / "playbooks" / "default_v2.json"
    if path.is_file():
        data = json.loads(path.read_text())
        return PlaybookV2.model_validate(data)
    return default_playbook_v2()
