/** Single source of truth for industry + plain fleet terminology. */

export type TermCategory = 'dispatch' | 'supply' | 'economics' | 'automation' | 'network' | 'fleet'

export type PolicySubTab = 'rules' | 'market' | 'operations'

export interface FleetTerm {
  id: string
  category: TermCategory
  industryLabel: string
  plainLabel: string
  description: string
  affects?: string[]
  policySubTab?: PolicySubTab
}

export const FLEET_TERMS: FleetTerm[] = [
  {
    id: 'pickup_wait',
    category: 'economics',
    industryLabel: 'Pickup wait',
    plainLabel: 'Avg wait',
    description: 'Time from trip request until the vehicle arrives at pickup.',
  },
  {
    id: 'fleet_utilization',
    category: 'economics',
    industryLabel: 'Fleet utilization',
    plainLabel: 'Utilization',
    description: 'Share of vehicles actively serving or rebalancing (not idle at depot).',
  },
  {
    id: 'pending_orders',
    category: 'dispatch',
    industryLabel: 'Open orders',
    plainLabel: 'Pending',
    description: 'Trips waiting for a vehicle assignment.',
  },
  {
    id: 'net_margin',
    category: 'economics',
    industryLabel: 'Net margin',
    plainLabel: 'Profit',
    description: 'Fare revenue minus empty-mile (deadhead) repositioning cost.',
  },
  {
    id: 'fulfillment_rate',
    category: 'economics',
    industryLabel: 'Fulfillment rate',
    plainLabel: 'Completion rate',
    description: 'Completed trips divided by completed plus cancelled.',
  },
  {
    id: 'empty_mile_ratio',
    category: 'economics',
    industryLabel: 'Empty-mile ratio',
    plainLabel: 'Deadhead %',
    description: 'Share of fleet miles driven without a rider onboard.',
  },
  {
    id: 'deadhead_cost',
    category: 'economics',
    industryLabel: 'Deadhead cost',
    plainLabel: 'Empty-mile cost',
    description: 'Total cost of repositioning empty vehicles.',
  },
  {
    id: 'trips_per_vph',
    category: 'economics',
    industryLabel: 'Trips per VPH',
    plainLabel: 'Trips per vehicle·hr',
    description: 'Throughput: completed trips per vehicle hour of fleet time.',
  },
  {
    id: 'match_score',
    category: 'dispatch',
    industryLabel: 'Match score',
    plainLabel: 'Match score',
    description: 'Lower is better. Combines pickup ETA, zone balance, and penalties.',
    policySubTab: 'rules',
  },
  {
    id: 'dispatch_weight_eta',
    category: 'dispatch',
    industryLabel: 'Pickup ETA weight',
    plainLabel: 'Closeness to pickup',
    description: 'How strongly closer-to-pickup beats other factors when auto-assigning.',
    affects: ['Match score', 'Open orders wait'],
    policySubTab: 'rules',
  },
  {
    id: 'dispatch_weight_surge',
    category: 'dispatch',
    industryLabel: 'Surge bias',
    plainLabel: 'Surge pricing bias',
    description: 'Bonus for assigning during high surge periods when weight is set.',
    policySubTab: 'rules',
  },
  {
    id: 'dispatch_weight_zone_balance',
    category: 'dispatch',
    industryLabel: 'Same-zone pickup bonus',
    plainLabel: 'Local pickup preference',
    description: 'Prefer vehicles already in the trip pickup zone.',
    policySubTab: 'rules',
  },
  {
    id: 'cross_zone_dispatch_penalty_min',
    category: 'dispatch',
    industryLabel: 'Cross-zone penalty',
    plainLabel: 'Cross-zone pickup penalty',
    description: 'Extra minutes added to match score when vehicle and pickup are in different zones.',
    policySubTab: 'rules',
  },
  {
    id: 'max_deadhead_to_pickup_min',
    category: 'dispatch',
    industryLabel: 'Max deadhead to pickup',
    plainLabel: 'Max empty drive to pickup',
    description: 'Hard cap on empty travel time to reach pickup (0 = disabled).',
    policySubTab: 'rules',
  },
  {
    id: 'dispatch_consider_dropoff_balance',
    category: 'dispatch',
    industryLabel: 'Dropoff rebalancing',
    plainLabel: 'Consider destination zone',
    description: 'Rank vehicles by where the trip ends — prefer landing in under-supplied zones.',
    policySubTab: 'rules',
  },
  {
    id: 'dispatch_weight_dropoff_balance',
    category: 'dispatch',
    industryLabel: 'Dropoff deficit bonus',
    plainLabel: 'Under-supplied zone bonus',
    description: 'Score bonus when the trip dropoff helps fill a supply shortage.',
    policySubTab: 'rules',
  },
  {
    id: 'dispatch_penalty_dropoff_surplus_min',
    category: 'dispatch',
    industryLabel: 'Dropoff surplus penalty',
    plainLabel: 'Over-cap zone penalty',
    description: 'Score penalty when the trip would overcrowd the destination zone.',
    policySubTab: 'rules',
  },
  {
    id: 'target_supply_by_zone',
    category: 'supply',
    industryLabel: 'Supply floor',
    plainLabel: 'Minimum idle cars',
    description: 'Target idle vehicles per zone before rebalancing pulls cars away.',
    policySubTab: 'rules',
  },
  {
    id: 'max_idle_by_zone',
    category: 'supply',
    industryLabel: 'Idle vehicle cap',
    plainLabel: 'Max empty cars',
    description: 'Maximum idle vehicles allowed in a zone before surplus rules fire.',
    policySubTab: 'rules',
  },
  {
    id: 'reposition_idle_min_by_zone',
    category: 'supply',
    industryLabel: 'Rebalancing patience',
    plainLabel: 'Idle wait before move',
    description: 'Minutes a car waits idle before rebalancing rules can move it.',
    policySubTab: 'rules',
  },
  {
    id: 'auto_dispatch_by_zone',
    category: 'supply',
    industryLabel: 'Zone auto-dispatch',
    plainLabel: 'Auto-assign by area',
    description: 'Whether trips originating in this zone are auto-matched to vehicles.',
    policySubTab: 'rules',
  },
  {
    id: 'zone_demand_weights',
    category: 'supply',
    industryLabel: 'Demand weight',
    plainLabel: 'Trip spawn weight',
    description: 'Relative trip generation rate for forecast and demand curves.',
    policySubTab: 'rules',
  },
  {
    id: 'deadhead_cost_per_min',
    category: 'network',
    industryLabel: 'Deadhead cost',
    plainLabel: 'Empty-mile cost per minute',
    description: 'Used in rebalancing ROI and profit KPI calculations.',
    policySubTab: 'rules',
  },
  {
    id: 'min_reposition_benefit',
    category: 'network',
    industryLabel: 'Min rebalancing ROI',
    plainLabel: 'Min benefit to move empty car',
    description: 'Minimum expected value before an idle car repositions.',
    policySubTab: 'rules',
  },
  {
    id: 'auto_dispatch_enabled',
    category: 'network',
    industryLabel: 'Auto-dispatch',
    plainLabel: 'Auto-assign trips',
    description: 'Master switch for automatic trip-to-vehicle matching.',
    policySubTab: 'rules',
  },
  {
    id: 'global_traffic_multiplier',
    category: 'network',
    industryLabel: 'Traffic multiplier',
    plainLabel: 'Road congestion factor',
    description: 'Scales all travel times (1.0 = normal, higher = slower traffic).',
    policySubTab: 'rules',
  },
  {
    id: 'max_distance_from_nearest_asset_km',
    category: 'network',
    industryLabel: 'Max asset coverage radius',
    plainLabel: 'Max distance from nearest idle car',
    description: 'Zones whose centroid is farther than this from any idle vehicle are treated as deadzones.',
    policySubTab: 'rules',
  },
  {
    id: 'deadzone_fill_ratio_threshold',
    category: 'network',
    industryLabel: 'Deadzone fill ratio threshold',
    plainLabel: 'Min size-to-travel ratio',
    description: 'Fill a deadzone only when (deadzone size + adjustment) / (travel distance + adjustment) meets this minimum.',
    policySubTab: 'rules',
  },
  {
    id: 'deadzone_size_adjustment_km',
    category: 'network',
    industryLabel: 'Deadzone size adjustment',
    plainLabel: 'Coverage gap bonus (km)',
    description: 'Added to deadzone size in the fill ratio numerator — favors filling larger gaps.',
    policySubTab: 'rules',
  },
  {
    id: 'deadzone_travel_adjustment_km',
    category: 'network',
    industryLabel: 'Travel distance adjustment',
    plainLabel: 'Deadhead penalty (km)',
    description: 'Added to travel distance in the fill ratio denominator — penalizes longer reposition drives.',
    policySubTab: 'rules',
  },
  {
    id: 'deadzone_filler_enabled',
    category: 'network',
    industryLabel: 'Deadzone filler',
    plainLabel: 'Auto-fill coverage gaps',
    description: 'When routing rules do not reposition, send idle cars to zones lacking nearby assets if the fill ratio passes.',
    policySubTab: 'rules',
  },
  {
    id: 'base_trips_per_hour',
    category: 'supply',
    industryLabel: 'Trip demand rate',
    plainLabel: 'Base trips per hour',
    description: 'How many rider requests spawn per simulated hour citywide.',
    policySubTab: 'market',
  },
  {
    id: 'surge_multiplier',
    category: 'economics',
    industryLabel: 'Surge multiplier',
    plainLabel: 'Dynamic pricing surge',
    description: 'Multiplier on base fare during high demand.',
    policySubTab: 'market',
  },
  {
    id: 'score_weight_profit',
    category: 'economics',
    industryLabel: 'Profit weight',
    plainLabel: 'Profit in composite score',
    description: 'Your weight for profit in the Analytics composite KPI score.',
  },
  {
    id: 'rebalancing_adjustment',
    category: 'dispatch',
    industryLabel: 'Rebalancing adjustment',
    plainLabel: 'Zone balance adjustment',
    description: 'Score change from dropoff zone supply impact (negative = better match).',
  },
  {
    id: 'destination_zone',
    category: 'dispatch',
    industryLabel: 'Destination zone',
    plainLabel: 'Dropoff zone',
    description: 'Supply zone where the trip ends after dropoff.',
  },
]

const TERM_MAP = new Map(FLEET_TERMS.map(t => [t.id, t]))

export function getTerm(id: string): FleetTerm | undefined {
  return TERM_MAP.get(id)
}

export function labelForTerm(id: string, mode: 'standard' | 'expert'): string {
  const term = getTerm(id)
  if (!term) return id
  return mode === 'standard' ? term.plainLabel : term.industryLabel
}

export function searchTerms(query: string): FleetTerm[] {
  const q = query.trim().toLowerCase()
  if (!q) return FLEET_TERMS
  return FLEET_TERMS.filter(
    t =>
      t.id.includes(q)
      || t.industryLabel.toLowerCase().includes(q)
      || t.plainLabel.toLowerCase().includes(q)
      || t.description.toLowerCase().includes(q),
  )
}

export const CATEGORY_LABELS: Record<TermCategory, string> = {
  dispatch: 'Dispatch',
  supply: 'Supply & zones',
  economics: 'Economics',
  automation: 'Automation',
  network: 'Network',
  fleet: 'Fleet',
}

export const POLICY_SUBTAB_LABELS: Record<PolicySubTab, { industry: string; plain: string }> = {
  rules: { industry: 'Rule studio', plain: 'Fleet rules' },
  market: { industry: 'Market & demand', plain: 'Pricing, events, wear' },
  operations: { industry: 'Operations', plain: 'Scenarios, alerts, health' },
}
