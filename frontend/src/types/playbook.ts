/** Types mirroring fleet_routing v2 playbook payloads. */

export type RulePhaseV2 = 'dispatch' | 'reposition' | 'facility'

export type CompareOpV2 = 'eq' | 'ne' | 'lt' | 'lte' | 'gt' | 'gte' | 'between'

export type ExprOp = 'and' | 'or' | 'not' | 'compare' | 'metric' | 'const'

export type SelectionMode =
  | 'all_matching'
  | 'most_crowded'
  | 'least_crowded'
  | 'one_per_cluster'
  | 'highest_metric'
  | 'lowest_metric'
  | 'best_dispatch_score'
  | 'round_robin_zone'

export type ActionTypeV2 =
  | 'assign_vehicle'
  | 'assign_nearest_idle'
  | 'assign_nearest_available'
  | 'hold'
  | 'reposition_to_point'
  | 'reposition_to_zone'
  | 'reposition_to_best_deficit'
  | 'reposition_to_nearest_density_floor'
  | 'send_to_facility'
  | 'release_from_facility'
  | 'cancel_trip'

export interface MetricRef {
  id: string
  params?: Record<string, string | number | boolean>
}

export interface ExprNode {
  op: ExprOp
  metric?: MetricRef | null
  operator?: CompareOpV2 | null
  value?: number | null
  value_max?: number | null
  right_metric?: MetricRef | null
  children?: ExprNode[]
}

export interface ActionSpec {
  type: ActionTypeV2
  params?: Record<string, unknown>
  constraints?: ExprNode | null
  rank_by?: MetricRef | null
  filter?: ExprNode | null
}

export interface RuleV2 {
  id: string
  name: string
  enabled: boolean
  priority: number
  phase: RulePhaseV2
  when: ExprNode
  selection: SelectionMode
  selection_metric?: MetricRef | null
  selection_params?: Record<string, string | number | boolean>
  action: ActionSpec
  rank_by?: MetricRef | null
}

export interface PlaybookV2 {
  enabled: boolean
  constants: Record<string, number>
  rules: RuleV2[]
}

export interface MetricMeta {
  id: string
  scope: string
  value_type: string
  industry_label: string
  plain_label: string
  description: string
  unit?: string
  category?: string
  phases?: RulePhaseV2[]
  param_schema?: Record<string, string>
}

export interface RuleHitV2 {
  timestamp_h: number
  rule_id: string
  rule_name: string
  phase: RulePhaseV2
  subject_id: string
  action: ActionTypeV2
  matched: boolean
  detail: string
  metric_values?: Record<string, number | boolean | string>
  selection_reason?: string
  destination_search?: Record<string, unknown>
  shadow_only?: boolean
}

export interface ParamFieldMeta {
  type: string
  plain_label: string
  industry_label?: string
  description?: string
  default?: number | boolean | string | null
  unit?: string
}

export interface ConstantMeta {
  id: string
  plain_label: string
  industry_label: string
  description: string
  unit?: string
  default: number
  min?: number | null
  max?: number | null
  related_metrics?: string[]
  related_rules?: string[]
}

export interface ActionMeta {
  id: string
  plain_label: string
  industry_label: string
  description: string
  phases?: RulePhaseV2[]
  param_schema?: Record<string, ParamFieldMeta>
  requires_selection?: boolean
}

export interface SelectionMeta {
  id: string
  plain_label: string
  industry_label: string
  description: string
  requires_metric?: boolean
  phases?: RulePhaseV2[]
  param_schema?: Record<string, ParamFieldMeta>
}

export interface RuleTemplate {
  id: string
  name: string
  summary: string
  category: string
  phase: RulePhaseV2
  rule: RuleV2
}

/**
 * How a rule editor was opened. Future creation paths:
 * - wizard: default step-by-step flow
 * - template: pre-filled from Library → Templates
 * - blank: inline editor without wizard (future)
 * - intent: pre-filled from "I want to…" picker (future)
 */
export type RuleCreationMode = 'wizard' | 'template' | 'blank' | 'intent'
