/** Types mirroring fleet routing rule engine payloads. */

export type RulePhase = 'dispatch' | 'reposition'

export type ConditionType =
  | 'zone_deficit'
  | 'zone_surplus'
  | 'idle_minutes'
  | 'forecast_rising'
  | 'pending_trips'
  | 'trip_wait_minutes'
  | 'active_event'
  | 'time_of_day'

export type ActionType =
  | 'assign_nearest_eligible'
  | 'assign_nearest_idle_or_repositioning'
  | 'assign_prefer_zone'
  | 'reposition_to_best_deficit'
  | 'reposition_to_zone'
  | 'send_to_depot'
  | 'hold'

export type CompareOp = 'gte' | 'gt' | 'lte' | 'lt' | 'eq'

export interface RoutingCondition {
  type: ConditionType
  operator: CompareOp
  value: number
  value_max?: number | null
  zone?: string | null
}

export interface RoutingAction {
  type: ActionType
  target_zone?: string | null
}

export interface RoutingRule {
  id: string
  name: string
  enabled: boolean
  priority: number
  phase: RulePhase
  conditions: RoutingCondition[]
  action: RoutingAction
}

export interface RoutingRuleSet {
  rules: RoutingRule[]
  routing_enabled: boolean
}

export interface RoutingRuleHit {
  timestamp_h: number
  rule_id: string
  rule_name: string
  phase: RulePhase
  subject_id: string
  action: ActionType
  detail: string
}

export const CONDITION_LABELS: Record<ConditionType, string> = {
  zone_deficit: 'Zone needs more cars',
  zone_surplus: 'Zone has too many idle cars',
  idle_minutes: 'Vehicle idle time (min)',
  forecast_rising: 'Forecast demand rising',
  pending_trips: 'Pending trips in zone',
  trip_wait_minutes: 'Trip wait time (min)',
  active_event: 'Special event active',
  time_of_day: 'Hour of day',
}

export const ACTION_LABELS: Record<ActionType, string> = {
  assign_nearest_eligible: 'Assign nearest eligible vehicle',
  assign_nearest_idle_or_repositioning: 'Assign nearest idle or repositioning vehicle',
  assign_prefer_zone: 'Prefer vehicle already in zone',
  reposition_to_best_deficit: 'Reposition to highest-need zone',
  reposition_to_zone: 'Reposition to specific zone',
  send_to_depot: 'Send to depot',
  hold: 'Hold position',
}

export const ZONES = [
  'airport',
  'buda',
  'campus',
  'central',
  'domain',
  'downtown',
  'east_side',
  'kyle',
  'northeast',
  'northwest',
  'riverside',
  'south_central',
  'southwest',
  'westlake',
]

export const COMPARE_LABELS: Record<CompareOp, string> = {
  gte: '≥',
  gt: '>',
  lte: '≤',
  lt: '<',
  eq: '=',
}
