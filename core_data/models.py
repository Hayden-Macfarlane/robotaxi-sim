"""Foundational Pydantic models for robotaxi network simulation.

Schemas and enums only — no routing, dispatch, or I/O logic.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class VehicleState(StrEnum):
    """Operational state of a robotaxi in the fleet."""

    IDLE = "idle"
    TO_PICKUP = "to_pickup"
    WITH_RIDER = "with_rider"
    REPOSITIONING = "repositioning"
    AT_DEPOT = "at_depot"
    CHARGING = "charging"
    MAINTENANCE = "maintenance"
    CLEANING = "cleaning"


class TripStatus(StrEnum):
    """Lifecycle state of a rider trip request."""

    PENDING = "pending"
    MATCHED = "matched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class NodeKind(StrEnum):
    """Operational classification for graph vertices."""

    INTERSECTION = "intersection"
    DEPOT = "depot"
    CHARGER = "charger"
    MAINTENANCE = "maintenance"
    CLEANING = "cleaning"


class GeoPoint(BaseModel):
    """WGS-84 coordinate for rider pickup, dropoff, or live vehicle position."""

    lat: float
    lon: float


class RoadNode(BaseModel):
    """Graph vertex — intersection or OSM node in the city road network."""

    id: str
    lat: float
    lon: float
    zone: str = Field(default="", description="Demand/supply zone label for heatmaps.")
    kind: NodeKind = NodeKind.INTERSECTION
    name: str = ""
    capacity: int = Field(default=0, ge=0)


class RoadEdge(BaseModel):
    """Directed road segment with travel time used as Dijkstra weight."""

    id: str
    origin_id: str
    destination_id: str
    distance_km: float = Field(..., gt=0.0)
    travel_time_min: float = Field(..., gt=0.0)
    weight_multiplier: float = Field(default=1.0, gt=0.0)
    geometry: list[GeoPoint] = Field(default_factory=list)
    name: str = ""
    highway: str = ""


class RouteLeg(BaseModel):
    """Street-following route between two snapped network points."""

    edge_ids: list[str]
    node_path: list[str]
    geometry: list[GeoPoint]
    distance_km: float = Field(..., ge=0.0)
    travel_time_min: float = Field(..., ge=0.0)


class Facility(BaseModel):
    """Operational anchor (depot, charger) snapped to the road network."""

    id: str
    kind: NodeKind
    node_id: str
    lat: float
    lon: float
    name: str = ""
    capacity: int = Field(default=20, ge=1)


class Vehicle(BaseModel):
    """Autonomous vehicle in the managed fleet."""

    id: str
    state: VehicleState = VehicleState.IDLE
    lat: float
    lon: float
    current_node_id: str
    assigned_trip_id: str | None = None
    battery_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    condition_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    cleanliness_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    idle_since_h: float = 0.0
    manual_hold_until_h: float | None = None
    facility_id: str | None = None
    active_route_edges: list[str] = Field(default_factory=list)
    active_route_geometry: list[GeoPoint] = Field(default_factory=list)
    leg_started_at_h: float | None = None
    leg_ends_at_h: float | None = None
    heading_deg: float = 0.0


class TripRequest(BaseModel):
    """Rider app trip request awaiting or undergoing service."""

    id: str
    origin: GeoPoint
    destination: GeoPoint
    origin_snap_node_id: str
    destination_snap_node_id: str
    status: TripStatus = TripStatus.PENDING
    requested_at_h: float
    matched_vehicle_id: str | None = None
    pickup_at_h: float | None = None
    completed_at_h: float | None = None
    fare_estimate: float = Field(default=0.0, ge=0.0)
    wait_min: float = Field(default=0.0, ge=0.0)


class SpecialEvent(BaseModel):
    """Temporary demand boost for concerts, sports, or airport surges."""

    id: str
    label: str
    zone: str
    start_h: float = Field(..., ge=0.0)
    end_h: float = Field(..., gt=0.0)
    demand_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)


class DispatchAction(BaseModel):
    """Audit log entry for manual or automatic fleet moves."""

    timestamp_h: float
    vehicle_id: str
    action: str
    source: str
    reason: str = ""
    from_lat: float | None = None
    from_lon: float | None = None
    to_lat: float | None = None
    to_lon: float | None = None


class DispatchAssignmentMode(StrEnum):
    """How pending trips are matched to vehicles after operator setup."""

    MANUAL = "manual"
    CLOSEST_IDLE_OR_REPOSITIONING = "closest_idle_or_repositioning"
    CLOSEST_IDLE = "closest_idle"


class OperatorSetup(BaseModel):
    """Required operator choices before the simulation may advance."""

    setup_complete: bool = False
    dispatch_assignment_mode: DispatchAssignmentMode | None = None
    advanced_automation_enabled: bool = False


class DispatchTieBreaker(StrEnum):
    """Tie-break strategy when dispatch ETAs are equal."""

    CLOSEST = "closest"
    IDLE_LONGEST = "idle_longest"
    LOWEST_BATTERY = "lowest_battery"


class ScenarioPreset(StrEnum):
    """Named operator scenario presets."""

    CUSTOM = "custom"
    RUSH_HOUR = "rush_hour"
    LOW_DEMAND = "low_demand"
    CONCERT_SURGE = "concert_surge"
    MAINTENANCE_HEAVY = "maintenance_heavy"
    AIRPORT_PEAK = "airport_peak"


class NetworkPolicy(BaseModel):
    """Manager-controlled network and pricing levers."""

    fleet_size: int = Field(default=14, ge=1, le=200)
    base_fare: float = Field(default=8.0, ge=0.0)
    surge_multiplier: float = Field(default=1.0, ge=0.5, le=5.0)
    reposition_idle_min: float = Field(default=15.0, ge=1.0)
    auto_dispatch_enabled: bool = True
    auto_reposition_enabled: bool = True
    post_trip_reposition_enabled: bool = True
    max_idle_per_zone: int = Field(default=3, ge=1, le=50)
    max_idle_by_zone: dict[str, int] = Field(default_factory=dict)
    reposition_idle_min_by_zone: dict[str, float] = Field(default_factory=dict)
    target_supply_by_zone: dict[str, int] = Field(default_factory=dict)
    max_wait_min: float = Field(default=12.0, ge=1.0)
    reposition_lead_min: float = Field(default=30.0, ge=5.0)
    min_reposition_benefit: float = Field(default=0.5, ge=0.0)
    max_reposition_min: float = Field(default=45.0, ge=1.0)
    deadhead_cost_per_min: float = Field(default=0.15, ge=0.0)
    value_per_trip: float = Field(default=2.0, ge=0.0)
    manual_hold_min: float = Field(default=60.0, ge=5.0)
    depot_release_enabled: bool = True
    min_depot_buffer: int = Field(default=0, ge=0)
    proactive_staging_enabled: bool = True
    battery_drain_per_km: float = Field(default=0.4, ge=0.0)
    low_battery_pct: float = Field(default=20.0, ge=5.0, le=50.0)
    condition_drain_per_km: float = Field(default=0.08, ge=0.0)
    condition_drain_per_trip: float = Field(default=0.5, ge=0.0)
    cleanliness_drain_per_trip: float = Field(default=1.5, ge=0.0)
    cleanliness_spill_chance: float = Field(default=0.04, ge=0.0, le=1.0)
    cleanliness_spill_floor_pct: float = Field(default=8.0, ge=0.0, le=50.0)
    low_condition_pct: float = Field(default=25.0, ge=5.0, le=50.0)
    low_cleanliness_pct: float = Field(default=20.0, ge=5.0, le=50.0)
    charge_minutes_to_full: float = Field(default=45.0, ge=1.0)
    cleaning_service_min: float = Field(default=20.0, ge=1.0)
    maintenance_service_min: float = Field(default=30.0, ge=1.0)
    # Demand tuning
    base_trips_per_hour: float = Field(default=24.0, ge=0.0, le=500.0)
    zone_demand_weights: dict[str, float] = Field(default_factory=dict)
    # Dispatch scoring & limits
    dispatch_candidate_limit: int = Field(default=5, ge=1, le=25)
    dispatch_use_fast_eta: bool = False
    dispatch_weight_eta: float = Field(default=1.0, ge=0.0)
    dispatch_weight_surge: float = Field(default=0.0, ge=0.0)
    dispatch_weight_zone_balance: float = Field(default=0.0, ge=0.0)
    dispatch_consider_dropoff_balance: bool = False
    dispatch_weight_dropoff_balance: float = Field(default=0.0, ge=0.0)
    dispatch_penalty_dropoff_surplus_min: float = Field(default=0.0, ge=0.0)
    cross_zone_dispatch_penalty_min: float = Field(default=0.0, ge=0.0)
    max_deadhead_to_pickup_min: float = Field(default=0.0, ge=0.0)
    allow_preempt_reposition: bool = True
    failover_pending_queue_max: int = Field(default=0, ge=0)
    failover_avg_wait_max_min: float = Field(default=0.0, ge=0.0)
    dispatch_tie_breaker: DispatchTieBreaker = DispatchTieBreaker.CLOSEST
    # Pricing
    per_minute_fare: float = Field(default=0.15, ge=0.0)
    per_mile_fare: float = Field(default=0.0, ge=0.0)
    # Reposition thresholds
    forecast_rising_threshold: float = Field(default=1.5, ge=0.0)
    # Charge-aware dispatch
    charge_aware_dispatch: bool = False
    min_battery_pct_for_trip: float = Field(default=25.0, ge=5.0, le=90.0)
    km_per_soc_pct: float = Field(default=0.6, gt=0.0)
    # Operator alerts (0 = disabled for utilization)
    alert_avg_wait_min: float = Field(default=8.0, ge=0.0)
    alert_pending_queue: int = Field(default=10, ge=0)
    alert_utilization_below_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    alert_vehicles_needing_service: int = Field(default=5, ge=0)
    alert_zone_deficit: int = Field(default=3, ge=0)
    # Network / traffic
    global_traffic_multiplier: float = Field(default=1.0, gt=0.0, le=3.0)
    scenario_preset: ScenarioPreset = ScenarioPreset.CUSTOM
    # Routing efficiency (Phase 5)
    batch_dispatch_enabled: bool = False
    auto_dispatch_by_zone: dict[str, bool] = Field(default_factory=dict)
    # Composite score weights (operator sets; sim reports only)
    score_weight_profit: float = Field(default=1.0, ge=0.0)
    score_weight_wait: float = Field(default=0.0, ge=0.0)
    score_weight_deadhead: float = Field(default=0.0, ge=0.0)
    score_weight_completion: float = Field(default=0.0, ge=0.0)
    # Deadzone coverage filler (distance from nearest idle asset)
    deadzone_filler_enabled: bool = False
    max_distance_from_nearest_asset_km: float = Field(default=2.0, ge=0.1, le=50.0)
    deadzone_fill_ratio_threshold: float = Field(default=1.0, ge=0.0, le=20.0)
    deadzone_size_adjustment_km: float = Field(default=0.0, ge=0.0, le=20.0)
    deadzone_travel_adjustment_km: float = Field(default=0.0, ge=0.0, le=20.0)

    @field_validator("fleet_size")
    @classmethod
    def _fleet_positive(cls, v: int) -> int:
        """Ensure at least one vehicle can operate."""
        return max(1, v)


class KpiSample(BaseModel):
    """Point-in-time KPI snapshot for time-series charts."""

    sim_time_h: float = Field(..., ge=0.0)
    profit: float = 0.0
    revenue: float = 0.0
    avg_wait_min: float = 0.0
    fleet_utilization_pct: float = 0.0
    pending_trips: float = 0.0
    deadhead_ratio: float = 0.0
    trips_completed: float = 0.0


class ExperimentRun(BaseModel):
    """Saved experiment checkpoint for before/after comparison."""

    id: str
    label: str
    seed: int = 42
    scenario: str = "custom"
    city: str = "austin"
    sim_time_h: float = 0.0
    policy: dict[str, object] = Field(default_factory=dict)
    routing_rules: dict[str, object] = Field(default_factory=dict)
    kpis: dict[str, float] = Field(default_factory=dict)
    created_at_iso: str = ""


class OperatorPreset(BaseModel):
    """Named bundle of policy + routing rules for reproducible experiments."""

    name: str
    description: str = ""
    policy: dict[str, object] = Field(default_factory=dict)
    routing_rules: dict[str, object] = Field(default_factory=dict)
    operator_setup: dict[str, object] = Field(default_factory=dict)
