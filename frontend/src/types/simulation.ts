/** Types mirroring robotaxi backend snapshot payloads. */

export type VehicleState =
  | 'idle'
  | 'to_pickup'
  | 'with_rider'
  | 'repositioning'
  | 'at_depot'
  | 'charging'
  | 'maintenance'
  | 'cleaning'
export type TripStatus = 'pending' | 'matched' | 'in_progress' | 'completed' | 'cancelled'

export interface GeoPoint {
  lat: number
  lon: number
}

export interface RoadNodeSnap {
  id: string
  lat: number
  lon: number
  zone: string
}

export interface VehicleSnap {
  id: string
  state: VehicleState
  lat: number
  lon: number
  current_node_id: string
  assigned_trip_id: string | null
  battery_pct: number
  condition_pct?: number
  cleanliness_pct?: number
  idle_since_h: number
  manual_hold_until_h: number | null
  facility_id: string | null
  route_polyline: [number, number][] | null
  heading_deg?: number
  zone?: string
  zone_saturated?: boolean
}

export interface TripSnap {
  id: string
  origin: GeoPoint
  destination: GeoPoint
  origin_snap_node_id: string
  destination_snap_node_id: string
  status: TripStatus
  requested_at_h: number
  matched_vehicle_id: string | null
  fare_estimate: number
  wait_min: number
}

export interface RiderSnap {
  id: string
  lat: number
  lon: number
  status: TripStatus
  fare_estimate: number
}

export interface NetworkPolicySnap {
  fleet_size: number
  base_fare: number
  surge_multiplier: number
  reposition_idle_min: number
  auto_dispatch_enabled: boolean
  auto_reposition_enabled: boolean
  post_trip_reposition_enabled: boolean
  max_idle_per_zone: number
  max_idle_by_zone: Record<string, number>
  reposition_idle_min_by_zone: Record<string, number>
  target_supply_by_zone: Record<string, number>
  max_wait_min: number
  reposition_lead_min: number
  min_reposition_benefit: number
  max_reposition_min: number
  deadhead_cost_per_min: number
  value_per_trip: number
  manual_hold_min: number
  depot_release_enabled: boolean
  min_depot_buffer: number
  proactive_staging_enabled: boolean
  battery_drain_per_km: number
  low_battery_pct: number
  condition_drain_per_km: number
  condition_drain_per_trip: number
  cleanliness_drain_per_trip: number
  cleanliness_spill_chance: number
  cleanliness_spill_floor_pct: number
  low_condition_pct: number
  low_cleanliness_pct: number
  charge_minutes_to_full: number
  cleaning_service_min: number
  maintenance_service_min: number
  base_trips_per_hour?: number
  zone_demand_weights?: Record<string, number>
  dispatch_candidate_limit?: number
  dispatch_use_fast_eta?: boolean
  dispatch_weight_eta?: number
  dispatch_weight_surge?: number
  dispatch_weight_zone_balance?: number
  cross_zone_dispatch_penalty_min?: number
  max_deadhead_to_pickup_min?: number
  allow_preempt_reposition?: boolean
  failover_pending_queue_max?: number
  failover_avg_wait_max_min?: number
  dispatch_tie_breaker?: 'closest' | 'idle_longest' | 'lowest_battery'
  per_minute_fare?: number
  per_mile_fare?: number
  forecast_rising_threshold?: number
  charge_aware_dispatch?: boolean
  min_battery_pct_for_trip?: number
  km_per_soc_pct?: number
  alert_avg_wait_min?: number
  alert_pending_queue?: number
  alert_utilization_below_pct?: number
  alert_vehicles_needing_service?: number
  alert_zone_deficit?: number
  global_traffic_multiplier?: number
  scenario_preset?: string
  batch_dispatch_enabled?: boolean
  auto_dispatch_by_zone?: Record<string, boolean>
  score_weight_profit?: number
  score_weight_wait?: number
  score_weight_deadhead?: number
  score_weight_completion?: number
  dispatch_consider_dropoff_balance?: boolean
  dispatch_weight_dropoff_balance?: number
  dispatch_penalty_dropoff_surplus_min?: number
  deadzone_filler_enabled?: boolean
  max_distance_from_nearest_asset_km?: number
  deadzone_fill_ratio_threshold?: number
  deadzone_size_adjustment_km?: number
  deadzone_travel_adjustment_km?: number
}

export interface OperatorAlertSnap {
  level: string
  code: string
  message: string
}

export interface ZoneBalanceSnap {
  zone: string
  supply: number
  pending_demand: number
  expected_demand: number
  target_supply: number
  gap: number
  max_idle: number
}

export interface ZoneOverlaySnap {
  zone: string
  kind: 'grid' | 'poi'
  color: string
  polygons: [number, number][][]
}

export interface ForecastSnap {
  zone: string
  now: number
  t_plus_30: number
  t_plus_60: number
}

export interface SpecialEventSnap {
  id: string
  label: string
  zone: string
  start_h: number
  end_h: number
  demand_multiplier: number
}

export interface FacilitySnap {
  id: string
  kind: string
  node_id: string
  lat: number
  lon: number
  name: string
  capacity: number
}

export interface DispatchActionSnap {
  timestamp_h: number
  vehicle_id: string
  action: string
  source: string
  reason: string
}

export interface KpiSnap {
  avg_wait_min: number
  p95_wait_min: number
  fleet_utilization_pct: number
  trips_completed: number
  trips_cancelled: number
  revenue: number
  deadhead_cost?: number
  profit?: number
  completion_rate?: number
  trips_per_vehicle_hour?: number
  sim_hours?: number
  composite_score?: number
  pending_trips: number
  deadhead_ratio: number
  vehicles_at_depot: number
  vehicles_on_street: number
  avg_battery_pct: number
  avg_condition_pct?: number
  avg_cleanliness_pct?: number
  vehicles_needing_service?: number
}

export interface KpiSampleSnap {
  sim_time_h: number
  profit: number
  revenue: number
  avg_wait_min: number
  fleet_utilization_pct: number
  pending_trips: number
  deadhead_ratio: number
  trips_completed: number
}

export interface ExperimentRunSnap {
  id: string
  label: string
  seed: number
  scenario: string
  city: string
  sim_time_h: number
  policy: Record<string, unknown>
  routing_rules: Record<string, unknown>
  kpis: KpiSnap
  created_at_iso: string
}

export type DispatchAssignmentMode =
  | 'manual'
  | 'closest_idle_or_repositioning'
  | 'closest_idle'

export interface DispatchCandidateSnap {
  vehicle_id: string
  eta_min: number
  score?: number
  state: VehicleState
  dropoff_zone?: string
  balance_adjustment?: number
}

export interface OperatorSetupSnap {
  setup_complete: boolean
  dispatch_assignment_mode: DispatchAssignmentMode | null
  advanced_automation_enabled: boolean
}

export interface SimulationSnapshot {
  type: 'STATE_SNAPSHOT'
  status?: 'initializing'
  current_time_h: number
  sim_start_iso: string
  current_time_iso?: string
  is_running: boolean
  speed_multiplier: number
  city: string
  map_center?: GeoPoint
  map_bounds?: { south: number; north: number; west: number; east: number }
  policy: NetworkPolicySnap
  kpis: KpiSnap
  supply_by_zone: Record<string, number>
  demand_by_zone: Record<string, number>
  expected_demand_by_zone?: Record<string, number>
  zone_balance?: ZoneBalanceSnap[]
  zone_overlays?: ZoneOverlaySnap[]
  forecast_by_zone?: ForecastSnap[]
  special_events?: SpecialEventSnap[]
  facilities?: FacilitySnap[]
  recent_dispatch_actions?: DispatchActionSnap[]
  routing_rules?: import('./routing').RoutingRuleSet
  routing_rule_hits?: import('./routing').RoutingRuleHit[]
  operator_setup?: OperatorSetupSnap
  operator_alerts?: OperatorAlertSnap[]
  dispatch_candidates?: Record<string, DispatchCandidateSnap[]>
  vehicles: VehicleSnap[]
  trips: TripSnap[]
  riders: RiderSnap[]
  streets: [number, number][][]
  nodes: RoadNodeSnap[]
  seed?: number
  kpi_series?: KpiSampleSnap[]
  experiment_runs?: ExperimentRunSnap[]
  operator_presets?: string[]
}

export type SimCommand =
  | { type: 'PLAY'; speed?: number }
  | { type: 'SET_PLAYBACK_SPEED'; speed: number }
  | { type: 'PAUSE' }
  | { type: 'STEP'; hours?: number }
  | { type: 'RESET_SIMULATION' }
  | { type: 'SET_NETWORK_POLICY'; [key: string]: unknown }
  | { type: 'SET_ROUTING_RULES'; rules: import('./routing').RoutingRule[]; routing_enabled?: boolean }
  | { type: 'RESET_ROUTING_RULES' }
  | { type: 'SET_OPERATOR_SETUP'; dispatch_assignment_mode?: DispatchAssignmentMode; advanced_automation_enabled?: boolean }
  | { type: 'DISPATCH_VEHICLE'; vehicle_id: string; trip_id: string }
  | { type: 'REPOSITION_VEHICLE'; vehicle_id: string; node_id?: string; lat?: number; lon?: number }
  | { type: 'STAGE_VEHICLES'; vehicle_ids: string[]; lat: number; lon: number }
  | { type: 'CREATE_SPECIAL_EVENT'; label: string; zone: string; start_h: number; end_h: number; demand_multiplier?: number }
  | { type: 'DELETE_SPECIAL_EVENT'; event_id: string }
  | { type: 'UPDATE_SPECIAL_EVENT'; event_id: string; label?: string; zone?: string; start_h?: number; end_h?: number; demand_multiplier?: number }
  | { type: 'CANCEL_TRIP'; trip_id: string }
  | { type: 'APPLY_SCENARIO'; preset: string }
  | { type: 'CHECKPOINT_RUN'; label: string }
  | { type: 'DELETE_EXPERIMENT_RUN'; run_id: string }
  | { type: 'SAVE_OPERATOR_PRESET'; name: string; description?: string }
  | { type: 'LOAD_OPERATOR_PRESET'; name: string }
  | { type: 'DELETE_OPERATOR_PRESET'; name: string }
  | { type: 'SEND_TO_FACILITY'; vehicle_id: string; facility_id: string }
  | { type: 'RELEASE_FROM_FACILITY'; vehicle_id: string; zone: string }
