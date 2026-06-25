"""Robotaxi network simulation orchestrator."""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from core_data.models import (
    DispatchAction,
    DispatchAssignmentMode,
    GeoPoint,
    NetworkPolicy,
    OperatorSetup,
    RouteLeg,
    SpecialEvent,
    TripRequest,
    TripStatus,
    Vehicle,
    VehicleState,
)
from demand import DemandGenerator
from dispatch.matcher import rank_dispatch_candidates
from dispatch.reposition import (
    expected_demand_by_zone,
    forecast_snapshot,
    vehicle_zone,
    zone_balances,
    zone_cap,
)
from fleet_routing.context import build_routing_context
from fleet_routing.defaults import (
    default_routing_rules,
    dispatch_only_rules,
    manual_first_routing_rules,
)
from fleet_routing.engine import RuleEvaluator
from fleet_routing.models import ActionType, RoutingRuleSet
from fleet.health import (
    SERVICE_STATES,
    apply_movement_wear,
    apply_trip_complete_wear,
    facility_kind_for_alert,
    health_alert,
    is_dispatch_eligible,
    restore_after_service,
    service_duration_min,
)
from event_engine.engine import Event, EventType, SimulationEngine
from routing.city_router import CityRouter
from routing.zones import zone_for_point, zone_overlay_snapshot, all_zone_names
from simulation_loop.state import SimulationState
from simulation_loop.world_builder import build_world

DEMAND_TICK_HOURS = 0.25
INITIAL_PENDING_TRIPS = 2
MINUTES_PER_HOUR = 60.0
MAX_STREET_LINES_IN_SNAPSHOT = 4000
MAX_DISPATCH_LOG = 50
MAX_ROUTING_RULE_HITS = 30
OFF_STREET_STATES = SERVICE_STATES
AUSTIN_TZ = ZoneInfo("America/Chicago")
DEFAULT_SIM_START = datetime(2025, 6, 20, 17, 0, 0, tzinfo=AUSTIN_TZ)


@dataclass
class SimulationManager:
    """Discrete-event robotaxi fleet manager for a single city."""

    _engine: SimulationEngine = field(default_factory=SimulationEngine)
    _router: CityRouter | None = None
    _state: SimulationState = field(default_factory=SimulationState)
    _demand: DemandGenerator = field(default_factory=DemandGenerator)
    _rng: random.Random = field(default_factory=random.Random)
    _trip_counter: int = 0
    _event_counter: int = 0
    _city: str = "austin"
    _street_lines: list[list[list[float]]] | None = field(default=None)
    _staging_claims: set[tuple[float, float]] = field(default_factory=set)
    _sim_start: datetime = field(default_factory=lambda: DEFAULT_SIM_START)

    def __post_init__(self) -> None:
        if not isinstance(self._rng, random.Random):
            self._rng = random.Random()

    @property
    def current_time(self) -> float:
        """Current simulation clock in hours."""
        return self._engine.current_time

    @property
    def router(self) -> CityRouter:
        """Active city router."""
        if self._router is None:
            raise RuntimeError("Simulation not initialized")
        return self._router

    @property
    def state(self) -> SimulationState:
        """Live simulation state."""
        return self._state

    def reset(self, *, city: str | None = None, seed: int = 42) -> None:
        """Rebuild world and reschedule periodic demand ticks."""
        if city is not None:
            self._city = city
        else:
            self._city = os.environ.get("ROBOTAXI_CITY", "austin")
        self._engine = SimulationEngine(initial_time=0.0)
        self._rng = random.Random(seed)
        self._demand.set_seed(seed)
        self._trip_counter = 0
        self._event_counter = 0
        self._router, self._state = build_world(city=self._city, seed=seed)
        self._apply_startup_defaults()
        self._demand.set_events(self._state.special_events)
        self._street_lines: list[list[list[float]]] | None = None
        self._staging_claims = set()
        self._sim_start = DEFAULT_SIM_START
        self._seed_initial_trips(INITIAL_PENDING_TRIPS)
        self._schedule_demand_tick(self._engine.current_time + DEMAND_TICK_HOURS)
        self._apply_routing_rules()

    def _apply_startup_defaults(self) -> None:
        """Reset policy to auto-dispatch closest idle/repositioning vehicles on startup."""
        self._state.policy = self._state.policy.model_copy(
            update={
                "auto_reposition_enabled": False,
                "post_trip_reposition_enabled": False,
            },
        )
        self.set_operator_setup(
            dispatch_assignment_mode=DispatchAssignmentMode.CLOSEST_IDLE_OR_REPOSITIONING,
            advanced_automation_enabled=False,
        )

    def set_operator_setup(
        self,
        *,
        dispatch_assignment_mode: DispatchAssignmentMode | None = None,
        advanced_automation_enabled: bool | None = None,
    ) -> None:
        """Apply operator setup choices and configure dispatch automation."""
        setup = self._state.operator_setup.model_copy()
        if dispatch_assignment_mode is not None:
            setup.dispatch_assignment_mode = dispatch_assignment_mode
            setup.setup_complete = True
            if dispatch_assignment_mode == DispatchAssignmentMode.MANUAL:
                self._state.policy = self._state.policy.model_copy(
                    update={"auto_dispatch_enabled": False},
                )
                self._state.routing_rules = manual_first_routing_rules()
            elif dispatch_assignment_mode == DispatchAssignmentMode.CLOSEST_IDLE_OR_REPOSITIONING:
                self._state.policy = self._state.policy.model_copy(
                    update={"auto_dispatch_enabled": True},
                )
                self._state.routing_rules = dispatch_only_rules(dispatch_assignment_mode)
            elif dispatch_assignment_mode == DispatchAssignmentMode.CLOSEST_IDLE:
                self._state.policy = self._state.policy.model_copy(
                    update={"auto_dispatch_enabled": True},
                )
                self._state.routing_rules = dispatch_only_rules(dispatch_assignment_mode)
        if advanced_automation_enabled is not None:
            setup.advanced_automation_enabled = advanced_automation_enabled
            if advanced_automation_enabled and setup.dispatch_assignment_mode is not None:
                if setup.dispatch_assignment_mode == DispatchAssignmentMode.MANUAL:
                    self._state.routing_rules = manual_first_routing_rules()
                else:
                    self._state.routing_rules = default_routing_rules()
                    mode = setup.dispatch_assignment_mode
                    if mode in (
                        DispatchAssignmentMode.CLOSEST_IDLE_OR_REPOSITIONING,
                        DispatchAssignmentMode.CLOSEST_IDLE,
                    ):
                        dispatch_rule = dispatch_only_rules(mode).rules[0]
                        rules = self._state.routing_rules.rules
                        for i, rule in enumerate(rules):
                            if rule.phase.value == "dispatch" and rule.id == "rule-serve-pending":
                                rules[i] = dispatch_rule
                                break
        self._state.operator_setup = setup

    @property
    def setup_complete(self) -> bool:
        """Return True when operator has completed required setup."""
        return self._state.operator_setup.setup_complete

    def _sim_datetime(self, hours: float) -> datetime:
        """Wall-clock time for a simulation hour offset from reset."""
        return self._sim_start + timedelta(hours=hours)

    def _build_street_lines(self) -> list[list[list[float]]]:
        """Cache street centerlines for map rendering (capped for payload size)."""
        lines: list[list[list[float]]] = []
        for geom in self._router.street_geometries():
            if len(geom) < 2:
                continue
            lines.append([[p.lat, p.lon] for p in geom])
            if len(lines) >= MAX_STREET_LINES_IN_SNAPSHOT:
                break
        return lines

    def _street_lines_snapshot(self) -> list[list[list[float]]]:
        """Return cached street polylines, building on first snapshot request."""
        if self._street_lines is None:
            self._street_lines = self._build_street_lines()
        return self._street_lines

    def step(self, hours: float) -> None:
        """Advance simulation by ``hours`` and process all due events."""
        if hours <= 0.0:
            return
        target = self._engine.current_time + hours
        for event in self._engine.run_until(target):
            self._handle_event(event)
        self._engine.current_time = target
        self._apply_routing_rules()
        self._check_vehicle_health()
        self._cancel_stale_trips()

    def set_routing_rules(self, rule_set: RoutingRuleSet) -> None:
        """Replace the operator routing playbook."""
        self._state.routing_rules = rule_set

    def set_routing_rules_from_dict(self, payload: dict[str, object]) -> None:
        """Validate and apply routing rules from a JSON payload."""
        self._state.routing_rules = RoutingRuleSet.model_validate(payload)

    def set_network_policy(self, **kwargs: object) -> None:
        """Update manager policy fields from keyword args."""
        pol = self._state.policy.model_copy(
            update={k: v for k, v in kwargs.items() if v is not None},
        )
        self._state.policy = pol

    def create_special_event(
        self,
        *,
        label: str,
        zone: str,
        start_h: float,
        end_h: float,
        demand_multiplier: float = 2.0,
    ) -> str:
        """Register a temporary demand boost event."""
        self._event_counter += 1
        ev = SpecialEvent(
            id=f"ev-{self._event_counter:04d}",
            label=label,
            zone=zone,
            start_h=start_h,
            end_h=end_h,
            demand_multiplier=demand_multiplier,
        )
        self._state.special_events.append(ev)
        self._demand.set_events(self._state.special_events)
        return ev.id

    def stage_vehicles(self, vehicle_ids: list[str], lat: float, lon: float) -> str | None:
        """Send multiple idle vehicles to a map coordinate."""
        errors: list[str] = []
        for vid in vehicle_ids:
            err = self.reposition_vehicle_to_point(vid, lat, lon, manual=True)
            if err:
                errors.append(f"{vid}: {err}")
        if errors:
            return "; ".join(errors)
        return None

    def send_to_facility(self, vehicle_id: str, facility_id: str) -> str | None:
        """Route an on-street vehicle to a depot or charger."""
        vehicle = self._state.vehicles.get(vehicle_id)
        fac = self._state.facilities.get(facility_id)
        if vehicle is None:
            return f"Unknown vehicle '{vehicle_id}'."
        if fac is None:
            return f"Unknown facility '{facility_id}'."
        if vehicle.state not in (VehicleState.IDLE, VehicleState.REPOSITIONING):
            return f"Vehicle '{vehicle_id}' is not available."
        parked = sum(
            1 for v in self._state.vehicles.values()
            if v.facility_id == facility_id and v.state in OFF_STREET_STATES
        )
        if parked >= fac.capacity:
            return f"Facility '{facility_id}' is at capacity."
        return self._route_to_facility(vehicle, fac)

    def release_from_facility(self, vehicle_id: str) -> str | None:
        """Return a depot/charging vehicle to on-street idle service."""
        vehicle = self._state.vehicles.get(vehicle_id)
        if vehicle is None:
            return f"Unknown vehicle '{vehicle_id}'."
        if vehicle.state not in OFF_STREET_STATES:
            return f"Vehicle '{vehicle_id}' is not at a facility."
        vehicle.state = VehicleState.IDLE
        vehicle.facility_id = None
        vehicle.idle_since_h = self._engine.current_time
        self._log_dispatch(vehicle.id, "release", "manual", "Released from facility")
        return None

    def dispatch_vehicle(self, vehicle_id: str, trip_id: str) -> str | None:
        """Manually assign ``vehicle_id`` to serve ``trip_id``."""
        vehicle = self._state.vehicles.get(vehicle_id)
        trip = self._state.trips.get(trip_id)
        if vehicle is None:
            return f"Unknown vehicle '{vehicle_id}'."
        if trip is None:
            return f"Unknown trip '{trip_id}'."
        if trip.status != TripStatus.PENDING:
            return f"Trip '{trip_id}' is not pending."
        if vehicle.state not in (VehicleState.IDLE, VehicleState.REPOSITIONING):
            return f"Vehicle '{vehicle_id}' is not available."
        if not is_dispatch_eligible(vehicle, self._state.policy):
            return f"Vehicle '{vehicle_id}' is not fit for dispatch (health)."
        if vehicle.state == VehicleState.REPOSITIONING:
            self._clear_leg(vehicle)
            self._engine.cancel_events_for_entity(
                vehicle.id,
                event_type=EventType.VEHICLE_ARRIVE,
            )
        self._assign_trip(vehicle, trip)
        return None

    def reposition_vehicle(self, vehicle_id: str, node_id: str, *, manual: bool = True) -> str | None:
        """Send an idle vehicle to ``node_id``."""
        node = self._router.nodes.get(node_id) if self._router else None
        if node is None:
            return f"Unknown node '{node_id}'."
        return self.reposition_vehicle_to_point(
            vehicle_id, node.lat, node.lon, node_id=node_id, manual=manual,
        )

    def reposition_vehicle_to_point(
        self,
        vehicle_id: str,
        lat: float,
        lon: float,
        *,
        node_id: str | None = None,
        manual: bool = True,
        reason: str = "",
    ) -> str | None:
        """Send an idle vehicle to a map coordinate (snapped to the street network)."""
        vehicle = self._state.vehicles.get(vehicle_id)
        if vehicle is None:
            return f"Unknown vehicle '{vehicle_id}'."
        if vehicle.state != VehicleState.IDLE:
            return f"Vehicle '{vehicle_id}' is not idle."
        snap_node_id, snap_point = self._router.snap_point(lat, lon)
        dest_node_id = node_id or snap_node_id
        route = self._router.route_between(vehicle.lat, vehicle.lon, snap_point.lat, snap_point.lon)
        if route is None:
            return "No route to staging point."
        if manual:
            hold = self._state.policy.manual_hold_min / MINUTES_PER_HOUR
            vehicle.manual_hold_until_h = self._engine.current_time + hold
        if route.travel_time_min <= 0.01:
            vehicle.current_node_id = dest_node_id
            vehicle.lat = snap_point.lat
            vehicle.lon = snap_point.lon
            vehicle.idle_since_h = self._engine.current_time
            src = "manual" if manual else "auto"
            self._log_dispatch(
                vehicle.id, "stage", src, reason or "Arrived at staging point",
                to_lat=snap_point.lat, to_lon=snap_point.lon,
            )
            return None
        vehicle.state = VehicleState.REPOSITIONING
        vehicle.assigned_trip_id = None
        self._start_leg(
            vehicle,
            route,
            leg="reposition",
            payload={
                "node_id": dest_node_id,
                "lat": snap_point.lat,
                "lon": snap_point.lon,
                "manual": manual,
                "reason": reason,
            },
            track_deadhead=True,
        )
        return None

    def build_ui_snapshot(self, *, is_running: bool, speed_multiplier: float) -> str:
        """Serialise state for WebSocket clients."""
        t = self._engine.current_time
        kpis = self._compute_kpis()
        supply, demand = self._zone_heatmaps()
        events = self._state.special_events
        expected = expected_demand_by_zone(
            self._demand,
            self._router,
            sim_time_h=t,
            pending_by_zone=demand,
            events=events,
        )
        balances = zone_balances(
            self._router,
            self._state.policy,
            self._demand,
            sim_time_h=t,
            supply_by_zone=supply,
            pending_by_zone=demand,
            events=events,
        )
        dispatch_candidates = self._dispatch_candidates_snapshot()
        payload = {
            "type": "STATE_SNAPSHOT",
            "current_time_h": round(t, 5),
            "sim_start_iso": self._sim_start.isoformat(),
            "current_time_iso": self._sim_datetime(t).isoformat(),
            "is_running": is_running,
            "speed_multiplier": speed_multiplier,
            "city": self._city,
            "policy": self._state.policy.model_dump(),
            "kpis": kpis,
            "supply_by_zone": supply,
            "demand_by_zone": demand,
            "expected_demand_by_zone": {k: round(v, 2) for k, v in expected.items()},
            "zone_balance": [
                {
                    "zone": row.zone,
                    "supply": row.supply,
                    "pending_demand": row.pending_demand,
                    "expected_demand": row.expected_demand,
                    "target_supply": row.target_supply,
                    "gap": row.gap,
                    "max_idle": row.max_idle,
                }
                for row in balances
            ],
            "zone_overlays": zone_overlay_snapshot(),
            "forecast_by_zone": forecast_snapshot(
                self._demand,
                self._router,
                sim_time_h=t,
                pending_by_zone=demand,
                events=events,
            ),
            "special_events": [e.model_dump() for e in events],
            "facilities": [f.model_dump() for f in self._state.facilities.values()],
            "recent_dispatch_actions": [
                a.model_dump() for a in self._state.dispatch_log[-MAX_DISPATCH_LOG:]
            ],
            "routing_rules": self._state.routing_rules.model_dump(),
            "routing_rule_hits": [
                h.model_dump() for h in self._state.routing_rule_hits[-MAX_ROUTING_RULE_HITS:]
            ],
            "operator_setup": self._state.operator_setup.model_dump(),
            "dispatch_candidates": dispatch_candidates,
            "vehicles": [self._vehicle_snapshot(v) for v in self._state.vehicles.values()],
            "trips": [
                tr.model_dump()
                for tr in self._state.trips.values()
                if tr.status in (TripStatus.PENDING, TripStatus.MATCHED, TripStatus.IN_PROGRESS)
            ],
            "riders": self._rider_snapshots(),
            "streets": self._street_lines_snapshot(),
            "nodes": [],
            "map_bounds": self._map_bounds_snapshot(),
            "map_center": self._map_center_snapshot(),
        }
        return json.dumps(payload)

    def _map_bounds_snapshot(self) -> dict[str, float]:
        """Geographic bounds for map fit (avoids sending every node to the UI)."""
        min_lat, max_lat, min_lon, max_lon = self._router.geographic_bounds()
        return {
            "south": min_lat,
            "north": max_lat,
            "west": min_lon,
            "east": max_lon,
        }

    def _map_center_snapshot(self) -> dict[str, float]:
        """Map center derived from graph bounds."""
        min_lat, max_lat, min_lon, max_lon = self._router.geographic_bounds()
        return {
            "lat": (min_lat + max_lat) / 2.0,
            "lon": (min_lon + max_lon) / 2.0,
        }

    def _dispatch_candidates_snapshot(self) -> dict[str, list[dict[str, object]]]:
        """Ranked vehicle options for each pending trip (manual mode UI only)."""
        setup = self._state.operator_setup
        if not setup.setup_complete or setup.dispatch_assignment_mode != DispatchAssignmentMode.MANUAL:
            return {}
        include_repositioning = True
        result: dict[str, list[dict[str, object]]] = {}
        pol = self._state.policy
        for trip in self._state.trips.values():
            if trip.status != TripStatus.PENDING:
                continue
            ranked = rank_dispatch_candidates(
                trip,
                self._state.vehicles,
                self._router,
                surge_multiplier=pol.surge_multiplier,
                policy=pol,
                include_repositioning=include_repositioning,
                use_fast_eta=True,
            )
            result[trip.id] = [
                {
                    "vehicle_id": c.vehicle_id,
                    "eta_min": round(c.eta_min, 2),
                    "state": c.state.value,
                }
                for c in ranked
            ]
        return result

    def _vehicle_geo_at_time(self, vehicle: Vehicle) -> tuple[GeoPoint, float]:
        """Interpolate vehicle position and heading along its active route leg."""
        if (
            not vehicle.active_route_geometry
            or vehicle.leg_started_at_h is None
            or vehicle.leg_ends_at_h is None
        ):
            return GeoPoint(lat=vehicle.lat, lon=vehicle.lon), vehicle.heading_deg
        duration = vehicle.leg_ends_at_h - vehicle.leg_started_at_h
        if duration <= 0.0:
            progress = 1.0
        else:
            progress = (self._engine.current_time - vehicle.leg_started_at_h) / duration
            progress = max(0.0, min(1.0, progress))
        return self._router.position_on_leg(
            RouteLeg(
                edge_ids=vehicle.active_route_edges,
                node_path=[],
                geometry=vehicle.active_route_geometry,
                distance_km=0.0,
                travel_time_min=0.0,
            ),
            progress,
        )

    def _vehicle_snapshot(self, vehicle: Vehicle) -> dict[str, object]:
        """Build vehicle dict with interpolated lat/lon and optional route polyline."""
        if vehicle.state in OFF_STREET_STATES:
            data: dict[str, object] = vehicle.model_dump()
            data["route_polyline"] = None
            return data
        geo, heading = self._vehicle_geo_at_time(vehicle)
        data = vehicle.model_dump()
        data["lat"] = round(geo.lat, 6)
        data["lon"] = round(geo.lon, 6)
        data["heading_deg"] = round(heading, 1)
        data["zone"] = zone_for_point(geo.lat, geo.lon)
        data["zone_saturated"] = self._is_zone_saturated(vehicle)
        if vehicle.active_route_geometry:
            data["route_polyline"] = [[p.lat, p.lon] for p in vehicle.active_route_geometry]
        else:
            data["route_polyline"] = None
        return data

    def _is_zone_saturated(self, vehicle: Vehicle) -> bool:
        if vehicle.state != VehicleState.IDLE:
            return False
        zone = vehicle_zone(vehicle, self._router)
        supply, _ = self._zone_heatmaps()
        return supply.get(zone, 0) >= zone_cap(self._state.policy, zone)

    def _rider_snapshots(self) -> list[dict[str, object]]:
        """Active waiting riders for map display (pending/matched at pickup only)."""
        riders: list[dict[str, object]] = []
        for trip in self._state.trips.values():
            if trip.status not in (TripStatus.PENDING, TripStatus.MATCHED):
                continue
            riders.append({
                "id": trip.id,
                "lat": trip.origin.lat,
                "lon": trip.origin.lon,
                "status": trip.status.value,
                "fare_estimate": trip.fare_estimate,
            })
        return riders

    def _clear_leg(self, vehicle: Vehicle) -> None:
        vehicle.active_route_edges = []
        vehicle.active_route_geometry = []
        vehicle.leg_started_at_h = None
        vehicle.leg_ends_at_h = None

    def _start_leg(
        self,
        vehicle: Vehicle,
        route: RouteLeg,
        *,
        leg: str,
        payload: dict[str, object],
        track_deadhead: bool = False,
        track_revenue: bool = False,
    ) -> None:
        """Schedule a routed leg and store street geometry on the vehicle."""
        now = self._engine.current_time
        self._engine.cancel_events_for_entity(
            vehicle.id,
            event_type=EventType.VEHICLE_ARRIVE,
        )
        vehicle.active_route_edges = list(route.edge_ids)
        vehicle.active_route_geometry = list(route.geometry)
        vehicle.leg_started_at_h = now
        vehicle.leg_ends_at_h = now + route.travel_time_min / MINUTES_PER_HOUR
        _, heading = self._router.position_on_leg(route, 0.0)
        vehicle.heading_deg = heading
        if track_deadhead:
            self._state.reposition_km += route.distance_km
            self._state.reposition_min += route.travel_time_min
        if track_revenue:
            self._state.revenue_km += route.distance_km
        apply_movement_wear(vehicle, route.distance_km, self._state.policy)
        event_payload = {"leg": leg, **payload}
        self._engine.schedule_event(
            Event(
                timestamp=vehicle.leg_ends_at_h,
                event_type=EventType.VEHICLE_ARRIVE,
                entity_id=vehicle.id,
                payload=event_payload,
            ),
        )

    def _seed_initial_trips(self, count: int) -> None:
        """Create pending trip requests at sim start (riders waiting on the map)."""
        zones = all_zone_names()
        if not zones or count <= 0:
            return
        pol = self._state.policy
        created = 0
        for i in range(count):
            for _ in range(40):
                origin_zone = zones[i % len(zones)]
                dest_zone = self._rng.choice(zones)
                origin = self._demand._random_point_in_zone(self._router, origin_zone)
                dest = self._demand._random_point_in_zone(self._router, dest_zone)
                if origin is None or dest is None:
                    continue
                if origin.lat == dest.lat and origin.lon == dest.lon:
                    continue
                route = self._router.route_between(origin.lat, origin.lon, dest.lat, dest.lon)
                if route is None:
                    continue
                origin_snap_id, _ = self._router.snap_point(origin.lat, origin.lon)
                dest_snap_id, _ = self._router.snap_point(dest.lat, dest.lon)
                self._trip_counter += 1
                tid = f"trip-{self._trip_counter:05d}"
                fare = pol.base_fare * pol.surge_multiplier + route.travel_time_min * 0.15
                self._state.trips[tid] = TripRequest(
                    id=tid,
                    origin=origin,
                    destination=dest,
                    origin_snap_node_id=origin_snap_id,
                    destination_snap_node_id=dest_snap_id,
                    requested_at_h=0.0,
                    fare_estimate=round(fare, 2),
                )
                created += 1
                break

    def _schedule_demand_tick(self, at_h: float) -> None:
        self._engine.schedule_event(
            Event(
                timestamp=at_h,
                event_type=EventType.DEMAND_TICK,
                entity_id="demand",
                payload={},
            ),
        )

    def _handle_event(self, event: Event) -> None:
        if event.event_type == EventType.DEMAND_TICK:
            self._on_demand_tick(event.timestamp)
            self._schedule_demand_tick(event.timestamp + DEMAND_TICK_HOURS)
        elif event.event_type == EventType.VEHICLE_ARRIVE:
            self._on_vehicle_arrive(event)

    def _on_demand_tick(self, sim_time_h: float) -> None:
        pair = self._demand.maybe_spawn_trip(
            self._router,
            sim_time_h=sim_time_h,
            dt_hours=DEMAND_TICK_HOURS,
        )
        if pair is None:
            return
        origin, dest = pair
        origin_snap_id, _ = self._router.snap_point(origin.lat, origin.lon)
        dest_snap_id, _ = self._router.snap_point(dest.lat, dest.lon)
        route = self._router.route_between(origin.lat, origin.lon, dest.lat, dest.lon)
        travel = route.travel_time_min if route else 0.0
        self._trip_counter += 1
        tid = f"trip-{self._trip_counter:05d}"
        pol = self._state.policy
        fare = pol.base_fare * pol.surge_multiplier + travel * 0.15
        self._state.trips[tid] = TripRequest(
            id=tid,
            origin=origin,
            destination=dest,
            origin_snap_node_id=origin_snap_id,
            destination_snap_node_id=dest_snap_id,
            requested_at_h=sim_time_h,
            fare_estimate=round(fare, 2),
        )

    def _apply_routing_rules(self) -> None:
        """Run dispatch and reposition rules against current world state."""
        rules = self._state.routing_rules
        if not rules.routing_enabled:
            return
        pol = self._state.policy
        supply, pending = self._zone_heatmaps()
        horizon_h = pol.reposition_lead_min / MINUTES_PER_HOUR
        ctx = build_routing_context(
            self._router,
            pol,
            self._demand,
            sim_time_h=self._engine.current_time,
            supply_by_zone=supply,
            pending_by_zone=pending,
            events=self._state.special_events,
            horizon_h=horizon_h,
            rng=self._rng,
        )
        evaluator = RuleEvaluator(rules)
        assigned: set[str] = set()
        now = self._engine.current_time

        if pol.auto_dispatch_enabled:
            pending_trips = sorted(
                (t for t in self._state.trips.values() if t.status == TripStatus.PENDING),
                key=lambda t: t.requested_at_h,
            )
            for trip in pending_trips:
                decision = evaluator.evaluate_dispatch(
                    ctx,
                    trip,
                    self._state.vehicles,
                    assigned_vehicle_ids=assigned,
                )
                if decision is None:
                    continue
                vehicle = self._state.vehicles.get(decision.vehicle_id)
                if vehicle is None:
                    continue
                self._assign_trip(vehicle, trip)
                assigned.add(decision.vehicle_id)
                self._record_rule_hit(RuleEvaluator.hit_from_dispatch(decision, now))

        self._staging_claims = set()
        idle_vehicles = sorted(
            (v for v in self._state.vehicles.values() if v.state == VehicleState.IDLE),
            key=lambda v: v.idle_since_h,
        )
        for vehicle in idle_vehicles:
            if vehicle.id in assigned:
                continue
            decision = evaluator.evaluate_reposition(
                ctx,
                vehicle,
                claimed=self._staging_claims,
            )
            if decision is None:
                continue
            self._record_rule_hit(RuleEvaluator.hit_from_reposition(decision, now))
            if decision.action == ActionType.HOLD:
                continue
            if decision.send_to_depot:
                if pol.depot_release_enabled:
                    self._try_depot_pull(vehicle, reason=f"rule: {decision.rule_name}")
                continue
            self._staging_claims.add(
                (round(decision.staging.lat, 4), round(decision.staging.lon, 4)),
            )
            self.reposition_vehicle_to_point(
                vehicle.id,
                decision.staging.lat,
                decision.staging.lon,
                manual=False,
                reason=f"rule: {decision.rule_name} → {decision.zone}",
            )

    def _record_rule_hit(self, hit) -> None:
        """Append a routing rule audit entry."""
        self._state.routing_rule_hits.append(hit)
        if len(self._state.routing_rule_hits) > MAX_ROUTING_RULE_HITS * 2:
            self._state.routing_rule_hits = self._state.routing_rule_hits[-MAX_ROUTING_RULE_HITS:]

    def _assign_trip(self, vehicle: Vehicle, trip: TripRequest) -> None:
        if vehicle.state == VehicleState.REPOSITIONING:
            self._clear_leg(vehicle)
            self._engine.cancel_events_for_entity(
                vehicle.id,
                event_type=EventType.VEHICLE_ARRIVE,
            )
        route = self._router.route_between(
            vehicle.lat,
            vehicle.lon,
            trip.origin.lat,
            trip.origin.lon,
        )
        if route is None:
            return
        trip.status = TripStatus.MATCHED
        trip.matched_vehicle_id = vehicle.id
        trip.wait_min = max(
            0.0,
            (self._engine.current_time - trip.requested_at_h) * MINUTES_PER_HOUR + route.travel_time_min,
        )
        vehicle.state = VehicleState.TO_PICKUP
        vehicle.assigned_trip_id = trip.id
        self._start_leg(vehicle, route, leg="pickup", payload={"trip_id": trip.id})

    def _on_vehicle_arrive(self, event: Event) -> None:
        vehicle = self._state.vehicles.get(event.entity_id)
        if vehicle is None:
            return
        self._clear_leg(vehicle)
        leg = str(event.payload.get("leg", ""))
        if leg == "reposition":
            node_id = str(event.payload.get("node_id", vehicle.current_node_id))
            lat_raw = event.payload.get("lat")
            lon_raw = event.payload.get("lon")
            if lat_raw is not None and lon_raw is not None:
                vehicle.lat = float(lat_raw)
                vehicle.lon = float(lon_raw)
            else:
                node = self._router.get_node(node_id)
                if node is not None:
                    vehicle.lat = node.lat
                    vehicle.lon = node.lon
            vehicle.current_node_id = node_id
            vehicle.state = VehicleState.IDLE
            vehicle.idle_since_h = event.timestamp
            manual = bool(event.payload.get("manual", False))
            reason = str(event.payload.get("reason", ""))
            src = "manual" if manual else "auto"
            self._log_dispatch(
                vehicle.id, "reposition", src, reason or f"Staged in {vehicle_zone(vehicle, self._router)}",
                to_lat=vehicle.lat, to_lon=vehicle.lon,
            )
            return
        if leg == "to_facility":
            fac_id = str(event.payload.get("facility_id", ""))
            fac = self._state.facilities.get(fac_id)
            if fac is not None:
                vehicle.lat = fac.lat
                vehicle.lon = fac.lon
                vehicle.current_node_id = fac.node_id
                vehicle.facility_id = fac_id
                kind = fac.kind.value
                if kind == "charger":
                    vehicle.state = VehicleState.CHARGING
                elif kind == "maintenance":
                    vehicle.state = VehicleState.MAINTENANCE
                elif kind == "cleaning":
                    vehicle.state = VehicleState.CLEANING
                else:
                    vehicle.state = VehicleState.AT_DEPOT
                    return
                dwell_min = service_duration_min(vehicle, kind, self._state.policy)
                if dwell_min <= 0.01:
                    self._complete_facility_service(vehicle, fac_id, kind, event.timestamp)
                else:
                    self._engine.schedule_event(
                        Event(
                            timestamp=event.timestamp + dwell_min / MINUTES_PER_HOUR,
                            event_type=EventType.VEHICLE_ARRIVE,
                            entity_id=vehicle.id,
                            payload={"leg": "service_complete", "facility_id": fac_id, "facility_kind": kind},
                        ),
                    )
            return
        if leg == "service_complete":
            fac_id = str(event.payload.get("facility_id", ""))
            kind = str(event.payload.get("facility_kind", ""))
            self._complete_facility_service(vehicle, fac_id, kind, event.timestamp)
            return
        trip_id = str(event.payload.get("trip_id", ""))
        trip = self._state.trips.get(trip_id)
        if trip is None:
            vehicle.state = VehicleState.IDLE
            vehicle.assigned_trip_id = None
            return
        if leg == "pickup":
            vehicle.lat = trip.origin.lat
            vehicle.lon = trip.origin.lon
            vehicle.current_node_id = trip.origin_snap_node_id
            vehicle.state = VehicleState.WITH_RIDER
            trip.status = TripStatus.IN_PROGRESS
            trip.pickup_at_h = event.timestamp
            ride_route = self._router.route_between(
                trip.origin.lat,
                trip.origin.lon,
                trip.destination.lat,
                trip.destination.lon,
            )
            if ride_route is None:
                trip.status = TripStatus.CANCELLED
                self._state.trips_cancelled += 1
                vehicle.state = VehicleState.IDLE
                vehicle.assigned_trip_id = None
                return
            self._start_leg(
                vehicle, ride_route, leg="dropoff", payload={"trip_id": trip.id}, track_revenue=True,
            )
        elif leg == "dropoff":
            vehicle.lat = trip.destination.lat
            vehicle.lon = trip.destination.lon
            vehicle.current_node_id = trip.destination_snap_node_id
            vehicle.state = VehicleState.IDLE
            vehicle.assigned_trip_id = None
            vehicle.idle_since_h = event.timestamp
            trip.status = TripStatus.COMPLETED
            trip.completed_at_h = event.timestamp
            self._state.revenue += trip.fare_estimate
            self._state.trips_completed += 1
            self._state.wait_times_min.append(trip.wait_min)
            apply_trip_complete_wear(vehicle, self._state.policy, self._rng)
            if not is_dispatch_eligible(vehicle, self._state.policy):
                self._route_to_nearest_facility_for_health(vehicle)

    def _try_depot_pull(self, vehicle: Vehicle, *, reason: str) -> bool:
        """Send surplus vehicle to nearest depot with capacity."""
        pol = self._state.policy
        on_street = sum(
            1 for v in self._state.vehicles.values()
            if v.state not in OFF_STREET_STATES
        )
        if on_street <= pol.fleet_size - pol.min_depot_buffer:
            return False
        best_fac = None
        best_eta = float("inf")
        for fac in self._state.facilities.values():
            if fac.kind.value not in ("depot", "charger"):
                continue
            parked = sum(
                1 for v in self._state.vehicles.values()
                if v.facility_id == fac.id and v.state in OFF_STREET_STATES
            )
            if parked >= fac.capacity:
                continue
            route = self._router.route_between(vehicle.lat, vehicle.lon, fac.lat, fac.lon)
            if route is None or route.travel_time_min >= best_eta:
                continue
            best_eta = route.travel_time_min
            best_fac = fac
        if best_fac is None:
            return False
        return self._route_to_facility(vehicle, best_fac, reason=reason) is None

    def _route_to_facility(self, vehicle: Vehicle, fac: object, *, reason: str = "") -> str | None:
        from core_data.models import Facility

        if not isinstance(fac, Facility):
            return "Invalid facility."
        route = self._router.route_between(vehicle.lat, vehicle.lon, fac.lat, fac.lon)
        if route is None:
            return "No route to facility."
        vehicle.state = VehicleState.REPOSITIONING
        vehicle.assigned_trip_id = None
        self._start_leg(
            vehicle,
            route,
            leg="to_facility",
            payload={"facility_id": fac.id},
            track_deadhead=True,
        )
        self._log_dispatch(
            vehicle.id, "to_facility", "auto", reason or f"Sent to {fac.name}",
            to_lat=fac.lat, to_lon=fac.lon,
        )
        return None

    def _complete_facility_service(
        self,
        vehicle: Vehicle,
        facility_id: str,
        facility_kind: str,
        timestamp: float,
    ) -> None:
        """Restore health metrics and return vehicle to on-street idle."""
        restore_after_service(vehicle, facility_kind)
        vehicle.state = VehicleState.IDLE
        vehicle.facility_id = None
        vehicle.idle_since_h = timestamp
        self._log_dispatch(
            vehicle.id,
            "service_complete",
            "auto",
            f"Service done at {facility_id}",
        )

    def _route_to_nearest_facility_for_health(self, vehicle: Vehicle) -> bool:
        """Send vehicle to the nearest facility matching its health alert."""
        alert = health_alert(vehicle, self._state.policy)
        if alert is None:
            return False
        kind = facility_kind_for_alert(alert)
        best_fac = None
        best_eta = float("inf")
        for fac in self._state.facilities.values():
            if fac.kind.value != kind:
                continue
            parked = sum(
                1 for v in self._state.vehicles.values()
                if v.facility_id == fac.id and v.state in OFF_STREET_STATES
            )
            if parked >= fac.capacity:
                continue
            route = self._router.route_between(vehicle.lat, vehicle.lon, fac.lat, fac.lon)
            if route is None or route.travel_time_min >= best_eta:
                continue
            best_eta = route.travel_time_min
            best_fac = fac
        if best_fac is None:
            return False
        return self._route_to_facility(vehicle, best_fac, reason=alert) is None

    def _check_vehicle_health(self) -> None:
        """Auto-route unfit idle vehicles to charger, cleaning, or maintenance."""
        for vehicle in self._state.vehicles.values():
            if vehicle.state != VehicleState.IDLE:
                continue
            if self._is_manual_hold(vehicle):
                continue
            if health_alert(vehicle, self._state.policy) is None:
                continue
            self._route_to_nearest_facility_for_health(vehicle)

    def _is_manual_hold(self, vehicle: Vehicle) -> bool:
        hold = vehicle.manual_hold_until_h
        return hold is not None and self._engine.current_time < hold

    def _log_dispatch(
        self,
        vehicle_id: str,
        action: str,
        source: str,
        reason: str,
        *,
        from_lat: float | None = None,
        from_lon: float | None = None,
        to_lat: float | None = None,
        to_lon: float | None = None,
    ) -> None:
        entry = DispatchAction(
            timestamp_h=round(self._engine.current_time, 2),
            vehicle_id=vehicle_id,
            action=action,
            source=source,
            reason=reason,
            from_lat=from_lat,
            from_lon=from_lon,
            to_lat=to_lat,
            to_lon=to_lon,
        )
        self._state.dispatch_log.append(entry)
        if len(self._state.dispatch_log) > MAX_DISPATCH_LOG * 2:
            self._state.dispatch_log = self._state.dispatch_log[-MAX_DISPATCH_LOG:]

    def _cancel_stale_trips(self) -> None:
        pol = self._state.policy
        max_wait_h = pol.max_wait_min / MINUTES_PER_HOUR
        for trip in self._state.trips.values():
            if trip.status != TripStatus.PENDING:
                continue
            if self._engine.current_time - trip.requested_at_h > max_wait_h:
                trip.status = TripStatus.CANCELLED
                self._state.trips_cancelled += 1

    def _compute_kpis(self) -> dict[str, float]:
        waits = self._state.wait_times_min
        avg_wait = sum(waits) / len(waits) if waits else 0.0
        p95 = sorted(waits)[int(len(waits) * 0.95)] if len(waits) >= 2 else avg_wait
        active = sum(
            1
            for v in self._state.vehicles.values()
            if v.state in (VehicleState.TO_PICKUP, VehicleState.WITH_RIDER, VehicleState.REPOSITIONING)
        )
        fleet = len(self._state.vehicles) or 1
        pending = sum(1 for t in self._state.trips.values() if t.status == TripStatus.PENDING)
        total_km = self._state.reposition_km + self._state.revenue_km
        deadhead = self._state.reposition_km / total_km if total_km > 0 else 0.0
        at_depot = sum(1 for v in self._state.vehicles.values() if v.state in OFF_STREET_STATES)
        on_street = fleet - at_depot
        avg_battery = sum(v.battery_pct for v in self._state.vehicles.values()) / fleet
        avg_condition = sum(v.condition_pct for v in self._state.vehicles.values()) / fleet
        avg_cleanliness = sum(v.cleanliness_pct for v in self._state.vehicles.values()) / fleet
        needing_service = sum(
            1 for v in self._state.vehicles.values()
            if v.state == VehicleState.IDLE and not is_dispatch_eligible(v, self._state.policy)
        )
        return {
            "avg_wait_min": round(avg_wait, 2),
            "p95_wait_min": round(p95, 2),
            "fleet_utilization_pct": round(active / fleet * 100.0, 1),
            "trips_completed": float(self._state.trips_completed),
            "trips_cancelled": float(self._state.trips_cancelled),
            "revenue": round(self._state.revenue, 2),
            "pending_trips": float(pending),
            "deadhead_ratio": round(deadhead, 3),
            "vehicles_at_depot": float(at_depot),
            "vehicles_on_street": float(on_street),
            "avg_battery_pct": round(avg_battery, 1),
            "avg_condition_pct": round(avg_condition, 1),
            "avg_cleanliness_pct": round(avg_cleanliness, 1),
            "vehicles_needing_service": float(needing_service),
        }

    def _demand_by_zone(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for trip in self._state.trips.values():
            if trip.status not in (TripStatus.PENDING, TripStatus.MATCHED):
                continue
            zone = zone_for_point(trip.origin.lat, trip.origin.lon)
            counts[zone] = counts.get(zone, 0) + 1
        return counts

    def _zone_heatmaps(self) -> tuple[dict[str, int], dict[str, int]]:
        supply: dict[str, int] = {}
        for vehicle in self._state.vehicles.values():
            if vehicle.state != VehicleState.IDLE:
                continue
            zone = vehicle_zone(vehicle, self._router)
            supply[zone] = supply.get(zone, 0) + 1
        return supply, self._demand_by_zone()
