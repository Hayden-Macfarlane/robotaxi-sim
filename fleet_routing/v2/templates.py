"""Curated rule templates for the rule engine UI."""

from __future__ import annotations

from fleet_routing.v2.defaults import default_playbook_v2
from fleet_routing.v2.models import (
    ActionSpec,
    ActionTypeV2,
    CompareOpV2,
    ExprNode,
    ExprOp,
    MetricRef,
    RulePhaseV2,
    RuleTemplate,
    RuleV2,
)


def _template_from_rule(rule: RuleV2, summary: str, category: str) -> RuleTemplate:
    """Build a RuleTemplate from an existing rule."""
    return RuleTemplate(
        id=f"tpl-{rule.id}",
        name=rule.name,
        summary=summary,
        category=category,
        phase=rule.phase,
        rule=rule.model_copy(deep=True),
    )


def _pickup_nearest_template() -> RuleTemplate:
    """Standalone dispatch template for blank playbooks."""
    rule = RuleV2(
        id="pickup-nearest-available",
        name="Pick up waiting riders (nearest car)",
        priority=10,
        phase=RulePhaseV2.DISPATCH,
        when=ExprNode(
            op=ExprOp.COMPARE,
            metric=MetricRef(id="zone.pending_demand"),
            operator=CompareOpV2.GTE,
            value=1.0,
        ),
        action=ActionSpec(type=ActionTypeV2.ASSIGN_NEAREST_AVAILABLE),
    )
    return RuleTemplate(
        id="tpl-pickup-nearest",
        name=rule.name,
        summary="When riders are waiting in a zone, send the nearest idle or repositioning eligible car.",
        category="dispatch",
        phase=rule.phase,
        rule=rule,
    )


def all_rule_templates() -> list[RuleTemplate]:
    """Return insertable rule templates."""
    pb = default_playbook_v2()
    by_id = {r.id: r for r in pb.rules}
    return [
        _pickup_nearest_template(),
        _template_from_rule(
            by_id["v2-serve-pending"],
            "When a zone has waiting riders, assign the best available vehicle (legacy assign_vehicle action).",
            "dispatch",
        ),
        _template_from_rule(
            by_id["v2-surplus-evict"],
            "When a zone has surplus vehicles, send one to a deficit zone.",
            "reposition",
        ),
        _template_from_rule(
            by_id["v2-idle-relocate"],
            "When a vehicle has been idle too long, reposition to the best deficit zone.",
            "reposition",
        ),
        _template_from_rule(
            by_id["v2-forecast-staging"],
            "When zone demand forecast is rising, stage vehicles ahead of the peak.",
            "reposition",
        ),
        _template_from_rule(
            by_id["v2-deadzone-fill"],
            "When a vehicle is in a coverage deadzone, reposition to nearest density floor.",
            "reposition",
        ),
        _template_from_rule(
            by_id["v2-break-clusters"],
            "When idle vehicles cluster too tightly, break up the most crowded cluster.",
            "reposition",
        ),
        _template_from_rule(
            by_id["v2-zone-cap-depot"],
            "When zone surplus exceeds cap, send excess vehicles to a facility.",
            "facility",
        ),
    ]
