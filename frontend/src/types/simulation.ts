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
  pending_trips: number
  deadhead_ratio: number
  vehicles_at_depot: number
  vehicles_on_street: number
  avg_battery_pct: number
  avg_condition_pct?: number
  avg_cleanliness_pct?: number
  vehicles_needing_service?: number
}

export interface SimulationSnapshot {
  type: 'STATE_SNAPSHOT'
  current_time_h: number
  sim_start_iso: string
  current_time_iso?: string
  is_running: boolean
  speed_multiplier: number
  city: string
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
  vehicles: VehicleSnap[]
  trips: TripSnap[]
  riders: RiderSnap[]
  streets: [number, number][][]
  nodes: RoadNodeSnap[]
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
  | { type: 'DISPATCH_VEHICLE'; vehicle_id: string; trip_id: string }
  | { type: 'REPOSITION_VEHICLE'; vehicle_id: string; node_id?: string; lat?: number; lon?: number }
  | { type: 'STAGE_VEHICLES'; vehicle_ids: string[]; lat: number; lon: number }
  | { type: 'CREATE_SPECIAL_EVENT'; label: string; zone: string; start_h: number; end_h: number; demand_multiplier?: number }
  | { type: 'SEND_TO_FACILITY'; vehicle_id: string; facility_id: string }
  | { type: 'RELEASE_FROM_FACILITY'; vehicle_id: string }
