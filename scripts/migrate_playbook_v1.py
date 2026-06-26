#!/usr/bin/env python3
"""Migrate legacy routing rules and policy knobs into v2 playbook constants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core_data.models import NetworkPolicy
from fleet_routing.models import RoutingRuleSet
from fleet_routing.v2.migrate import migrate_policy_to_playbook


def main() -> None:
    """CLI entrypoint for playbook migration."""
    parser = argparse.ArgumentParser(description="Migrate v1 rules + policy to v2 playbook JSON.")
    parser.add_argument("--policy", type=Path, help="NetworkPolicy JSON file")
    parser.add_argument("--rules", type=Path, help="RoutingRuleSet JSON file")
    parser.add_argument("-o", "--output", type=Path, default=Path("playbook_v2.json"))
    args = parser.parse_args()

    policy = NetworkPolicy.model_validate(json.loads(args.policy.read_text())) if args.policy else NetworkPolicy()
    rules = (
        RoutingRuleSet.model_validate(json.loads(args.rules.read_text()))
        if args.rules
        else None
    )
    pb = migrate_policy_to_playbook(policy, rules)
    args.output.write_text(json.dumps(pb.model_dump(), indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
