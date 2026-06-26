"""Simulation state container."""

from __future__ import annotations

from dataclasses import dataclass, field

from core_data.models import (
    DispatchAction,
    ExperimentRun,
    Facility,
    KpiSample,
    NetworkPolicy,
    OperatorPreset,
    OperatorSetup,
    SpecialEvent,
    TripRequest,
    Vehicle,
)
from fleet_routing.defaults import manual_first_routing_rules
from fleet_routing.models import RoutingRuleHit, RoutingRuleSet
from fleet_routing.v2.defaults import manual_playbook_v2
from fleet_routing.v2.models import PlaybookV2, RuleHitV2


@dataclass
class SimulationState:
    """Mutable world state for the robotaxi manager."""

    vehicles: dict[str, Vehicle] = field(default_factory=dict)
    trips: dict[str, TripRequest] = field(default_factory=dict)
    policy: NetworkPolicy = field(default_factory=NetworkPolicy)
    facilities: dict[str, Facility] = field(default_factory=dict)
    special_events: list[SpecialEvent] = field(default_factory=list)
    dispatch_log: list[DispatchAction] = field(default_factory=list)
    routing_rules: RoutingRuleSet = field(default_factory=manual_first_routing_rules)
    routing_rule_hits: list[RoutingRuleHit] = field(default_factory=list)
    playbook_v2: PlaybookV2 = field(default_factory=manual_playbook_v2)
    rule_hits_v2: list[RuleHitV2] = field(default_factory=list)
    operator_setup: OperatorSetup = field(default_factory=OperatorSetup)
    revenue: float = 0.0
    trips_completed: int = 0
    trips_cancelled: int = 0
    wait_times_min: list[float] = field(default_factory=list)
    reposition_km: float = 0.0
    reposition_min: float = 0.0
    revenue_km: float = 0.0
    kpi_series: list[KpiSample] = field(default_factory=list)
    last_kpi_sample_h: float = -1.0
