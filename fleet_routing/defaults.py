"""Default starter routing playbook."""

from __future__ import annotations

from fleet_routing.models import (
    ActionType,
    CompareOp,
    ConditionType,
    RoutingAction,
    RoutingCondition,
    RoutingRule,
    RoutingRuleSet,
    RulePhase,
)


def default_routing_rules() -> RoutingRuleSet:
    """Return the default operator playbook mirroring legacy fleet behavior."""
    return RoutingRuleSet(
        routing_enabled=True,
        rules=[
            RoutingRule(
                id="rule-serve-pending",
                name="Serve waiting riders",
                priority=10,
                phase=RulePhase.DISPATCH,
                conditions=[
                    RoutingCondition(
                        type=ConditionType.PENDING_TRIPS,
                        operator=CompareOp.GTE,
                        value=1.0,
                    ),
                ],
                action=RoutingAction(type=ActionType.ASSIGN_NEAREST_ELIGIBLE),
            ),
            RoutingRule(
                id="rule-post-trip-surplus",
                name="Leave crowded dropoff zone",
                priority=20,
                phase=RulePhase.REPOSITION,
                conditions=[
                    RoutingCondition(
                        type=ConditionType.ZONE_SURPLUS,
                        operator=CompareOp.GTE,
                        value=1.0,
                    ),
                ],
                action=RoutingAction(type=ActionType.REPOSITION_TO_BEST_DEFICIT),
            ),
            RoutingRule(
                id="rule-idle-relocate",
                name="Relocate if idle too long",
                priority=30,
                phase=RulePhase.REPOSITION,
                conditions=[
                    RoutingCondition(
                        type=ConditionType.IDLE_MINUTES,
                        operator=CompareOp.GTE,
                        value=15.0,
                    ),
                ],
                action=RoutingAction(type=ActionType.REPOSITION_TO_BEST_DEFICIT),
            ),
            RoutingRule(
                id="rule-peak-staging",
                name="Stage for forecast peak",
                priority=40,
                phase=RulePhase.REPOSITION,
                conditions=[
                    RoutingCondition(
                        type=ConditionType.FORECAST_RISING,
                        operator=CompareOp.GTE,
                        value=1.5,
                    ),
                ],
                action=RoutingAction(type=ActionType.REPOSITION_TO_BEST_DEFICIT),
            ),
            RoutingRule(
                id="rule-zone-cap-evict",
                name="Evict over zone cap",
                priority=50,
                phase=RulePhase.REPOSITION,
                conditions=[
                    RoutingCondition(
                        type=ConditionType.ZONE_SURPLUS,
                        operator=CompareOp.GTE,
                        value=1.0,
                    ),
                ],
                action=RoutingAction(type=ActionType.SEND_TO_DEPOT),
            ),
        ],
    )
