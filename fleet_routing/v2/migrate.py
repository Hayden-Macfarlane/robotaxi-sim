"""Migrate v1 routing rules and policy knobs into v2 playbook constants."""

from __future__ import annotations

from core_data.models import NetworkPolicy
from fleet_routing.models import RoutingRuleSet
from fleet_routing.v2.defaults import default_playbook_v2
from fleet_routing.v2.models import PlaybookV2


def migrate_policy_to_playbook(policy: NetworkPolicy, rules_v1: RoutingRuleSet | None = None) -> PlaybookV2:
    """Build a v2 playbook from legacy policy fields and optional v1 rules."""
    pb = default_playbook_v2()
    pb.constants.update({
        "idle_patience_min": policy.reposition_idle_min,
        "forecast_rising_threshold": policy.forecast_rising_threshold,
        "max_reposition_min": policy.max_reposition_min,
        "min_reposition_benefit": policy.min_reposition_benefit,
        "max_distance_from_nearest_asset_km": policy.max_distance_from_nearest_asset_km,
        "deadzone_fill_ratio_threshold": policy.deadzone_fill_ratio_threshold,
        "max_deadhead_to_pickup_min": policy.max_deadhead_to_pickup_min,
    })
    if rules_v1 is not None:
        pb.enabled = rules_v1.routing_enabled
    return pb
