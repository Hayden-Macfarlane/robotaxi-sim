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

export interface RuleLabelMeta {
  industry: string
  plain: string
  description: string
}

export const CONDITION_META: Record<ConditionType, RuleLabelMeta> = {
  zone_deficit: {
    industry: 'Zone supply shortage',
    plain: 'Zone needs more cars',
    description: 'Fewer idle cars here than demand needs.',
  },
  zone_surplus: {
    industry: 'Zone idle surplus',
    plain: 'Zone has too many idle cars',
    description: 'More empty vehicles waiting than the cap allows.',
  },
  idle_minutes: {
    industry: 'Idle duration',
    plain: 'Vehicle idle time (min)',
    description: 'How long the vehicle has waited without a trip.',
  },
  forecast_rising: {
    industry: 'Demand forecast rising',
    plain: 'Forecast demand rising',
    description: 'Expected trips in the zone are increasing.',
  },
  pending_trips: {
    industry: 'Open orders in zone',
    plain: 'Pending trips in zone',
    description: 'Unassigned rider requests originating in this zone.',
  },
  trip_wait_minutes: {
    industry: 'Pickup wait time',
    plain: 'Trip wait time (min)',
    description: 'Minutes since the rider requested the trip.',
  },
  active_event: {
    industry: 'Special event active',
    plain: 'Demand event active',
    description: 'A scheduled demand spike is running in a zone.',
  },
  time_of_day: {
    industry: 'Time of day',
    plain: 'Hour of day',
    description: 'Simulated clock hour for time-window rules.',
  },
}

export const ACTION_META: Record<ActionType, RuleLabelMeta> = {
  assign_nearest_eligible: {
    industry: 'Assign nearest eligible',
    plain: 'Assign nearest eligible vehicle',
    description: 'Match the closest vehicle that passes health and range checks.',
  },
  assign_nearest_idle_or_repositioning: {
    industry: 'Assign nearest available',
    plain: 'Assign nearest idle or rebalancing vehicle',
    description: 'Match the closest idle or rebalancing vehicle.',
  },
  assign_prefer_zone: {
    industry: 'Prefer in-zone vehicle',
    plain: 'Prefer vehicle already in zone',
    description: 'Assign a vehicle already waiting in the trip zone when possible.',
  },
  reposition_to_best_deficit: {
    industry: 'Rebalance to highest shortage',
    plain: 'Reposition to highest-need zone',
    description: 'Send empty car to the zone that needs supply most.',
  },
  reposition_to_zone: {
    industry: 'Rebalance to zone',
    plain: 'Reposition to specific zone',
    description: 'Send empty car to a chosen supply zone.',
  },
  send_to_depot: {
    industry: 'Send to depot',
    plain: 'Send to depot',
    description: 'Park the vehicle off-street at a depot facility.',
  },
  hold: {
    industry: 'Hold position',
    plain: 'Hold position',
    description: 'Keep the vehicle where it is; do not reassign or move.',
  },
}

/** @deprecated Use conditionLabel() with ui mode instead. */
export const CONDITION_LABELS: Record<ConditionType, string> = Object.fromEntries(
  Object.entries(CONDITION_META).map(([k, v]) => [k, v.plain]),
) as Record<ConditionType, string>

/** @deprecated Use actionLabel() with ui mode instead. */
export const ACTION_LABELS: Record<ActionType, string> = Object.fromEntries(
  Object.entries(ACTION_META).map(([k, v]) => [k, v.plain]),
) as Record<ActionType, string>

export function conditionLabel(type: ConditionType, mode: 'standard' | 'expert'): string {
  const meta = CONDITION_META[type]
  return mode === 'standard' ? meta.plain : meta.industry
}

export function actionLabel(type: ActionType, mode: 'standard' | 'expert'): string {
  const meta = ACTION_META[type]
  return mode === 'standard' ? meta.plain : meta.industry
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
