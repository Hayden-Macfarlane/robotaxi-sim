import type { VehicleState } from '../types/simulation'

interface StatusCopy {
  industry: string
  plain: string
}

/** Industry and plain labels for vehicle operational states. */
export const STATUS_COPY: Record<VehicleState, StatusCopy> = {
  idle: { industry: 'Available', plain: 'Waiting for a trip' },
  to_pickup: { industry: 'En route to pickup', plain: 'Heading to rider' },
  with_rider: { industry: 'On trip', plain: 'Carrying a rider' },
  repositioning: { industry: 'Rebalancing', plain: 'Empty, moving to better location' },
  to_facility: { industry: 'En route to facility', plain: 'Heading to facility' },
  at_depot: { industry: 'At depot', plain: 'Parked off-street' },
  charging: { industry: 'Charging', plain: 'Charging battery' },
  maintenance: { industry: 'In service', plain: 'In maintenance' },
  cleaning: { industry: 'Cleaning', plain: 'Being cleaned' },
}

/** @deprecated Use statusLabel(state, mode) instead. */
export const STATUS_LABELS: Record<VehicleState, string> = Object.fromEntries(
  Object.entries(STATUS_COPY).map(([k, v]) => [k, v.industry]),
) as Record<VehicleState, string>

export function statusLabel(state: VehicleState | string, mode: 'standard' | 'expert' = 'expert'): string {
  const copy = STATUS_COPY[state as VehicleState]
  if (!copy) return state.replace(/_/g, ' ')
  return mode === 'standard' ? copy.plain : copy.industry
}

const FACILITY_KIND_LABELS: Record<string, string> = {
  charger: 'Charge',
  cleaning: 'Clean',
  maintenance: 'Service',
  depot: 'Depot',
}

export function facilityKindLabel(kind: string): string {
  return FACILITY_KIND_LABELS[kind] ?? kind
}

export function healthAlert(v: {
  battery_pct: number
  condition_pct?: number
  cleanliness_pct?: number
}): string | null {
  if ((v.cleanliness_pct ?? 100) <= 20) return 'Needs cleaning'
  if (v.battery_pct <= 20) return 'Low battery'
  if ((v.condition_pct ?? 100) <= 25) return 'Needs maintenance'
  return null
}
