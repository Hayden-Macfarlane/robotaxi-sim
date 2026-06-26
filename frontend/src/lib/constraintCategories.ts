import type { MetricMeta, RulePhaseV2 } from '../types/playbook'

/** Plain-English labels for metric UI categories. */
export const CATEGORY_LABELS: Record<string, string> = {
  demand: 'Waiting riders',
  distance: 'Distance & proximity',
  timing: 'Time & idle',
  zone: 'Zone balance',
  vehicle: 'Vehicle status',
  dispatch: 'Dispatch scoring',
  fleet: 'Fleet-wide',
  other: 'Other',
}

export const CATEGORY_ORDER = [
  'demand',
  'distance',
  'timing',
  'zone',
  'vehicle',
  'dispatch',
  'fleet',
  'other',
] as const

const SCOPE_FALLBACK_CATEGORY: Record<string, string> = {
  vehicle: 'vehicle',
  trip: 'demand',
  zone: 'zone',
  pairwise: 'dispatch',
  global: 'fleet',
  facility: 'fleet',
  constant: 'other',
}

/** Resolve category id for a metric (backend field or scope fallback). */
export function metricCategoryId(metric: MetricMeta): string {
  if (metric.category && metric.category in CATEGORY_LABELS) {
    return metric.category
  }
  return SCOPE_FALLBACK_CATEGORY[metric.scope] ?? 'other'
}

export function categoryLabel(categoryId: string): string {
  return CATEGORY_LABELS[categoryId] ?? categoryId
}

function phaseRecommended(metric: MetricMeta, phaseHint?: RulePhaseV2 | null): boolean {
  if (!phaseHint) return true
  return !metric.phases?.length || metric.phases.includes(phaseHint)
}

/** Sort metrics for pickers: recommended for phase first, then category order, then label. */
export function sortMetricsForPicker(catalog: MetricMeta[], phaseHint?: RulePhaseV2 | null): MetricMeta[] {
  return catalog.slice().sort((a, b) => {
    const aRec = phaseRecommended(a, phaseHint)
    const bRec = phaseRecommended(b, phaseHint)
    if (aRec !== bRec) return aRec ? -1 : 1
    const aCat = CATEGORY_ORDER.indexOf(metricCategoryId(a) as (typeof CATEGORY_ORDER)[number])
    const bCat = CATEGORY_ORDER.indexOf(metricCategoryId(b) as (typeof CATEGORY_ORDER)[number])
    const aIdx = aCat >= 0 ? aCat : CATEGORY_ORDER.length
    const bIdx = bCat >= 0 ? bCat : CATEGORY_ORDER.length
    if (aIdx !== bIdx) return aIdx - bIdx
    return a.plain_label.localeCompare(b.plain_label)
  })
}

export function metricUseHint(metric: MetricMeta): string {
  const cat = metricCategoryId(metric)
  if (metric.id === 'vehicle.nearest_unmatched_rider_km') {
    return 'Use when deciding if a car is too far from any waiting rider'
  }
  if (metric.id === 'zone.pending_demand') {
    return 'Use when riders are waiting for a match in this area'
  }
  if (cat === 'distance') {
    return 'Use for proximity and spacing rules between vehicles'
  }
  if (cat === 'timing') {
    return 'Use for idle time, wait time, or leg duration rules'
  }
  if (cat === 'zone') {
    return 'Use for supply/demand balance across areas'
  }
  if (cat === 'dispatch') {
    return 'Use when scoring a specific car–trip match'
  }
  return metric.description || 'Use in rule conditions'
}
