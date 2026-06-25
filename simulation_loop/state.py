"""Simulation state container."""

from __future__ import annotations

from dataclasses import dataclass, field

from core_data.models import DispatchAction, Facility, NetworkPolicy, SpecialEvent, TripRequest, Vehicle
from fleet_routing.defaults import default_routing_rules
from fleet_routing.models import RoutingRuleHit, RoutingRuleSet


@dataclass
class SimulationState:
    """Mutable world state for the robotaxi manager."""

    vehicles: dict[str, Vehicle] = field(default_factory=dict)
    trips: dict[str, TripRequest] = field(default_factory=dict)
    policy: NetworkPolicy = field(default_factory=NetworkPolicy)
    facilities: dict[str, Facility] = field(default_factory=dict)
    special_events: list[SpecialEvent] = field(default_factory=list)
    dispatch_log: list[DispatchAction] = field(default_factory=list)
    routing_rules: RoutingRuleSet = field(default_factory=default_routing_rules)
    routing_rule_hits: list[RoutingRuleHit] = field(default_factory=list)
    revenue: float = 0.0
    trips_completed: int = 0
    trips_cancelled: int = 0
    wait_times_min: list[float] = field(default_factory=list)
    reposition_km: float = 0.0
    reposition_min: float = 0.0
    revenue_km: float = 0.0
