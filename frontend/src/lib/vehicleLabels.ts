import type { VehicleState } from '../types/simulation'

/** Operator-friendly labels for vehicle operational states. */
export const STATUS_LABELS: Record<VehicleState, string> = {
  idle: 'Available',
  to_pickup: 'Picking up',
  with_rider: 'With rider',
  repositioning: 'Moving',
  at_depot: 'At depot',
  charging: 'Charging',
  maintenance: 'In maintenance',
  cleaning: 'Being cleaned',
}

export function statusLabel(state: VehicleState | string): string {
  return STATUS_LABELS[state as VehicleState] ?? state.replace(/_/g, ' ')
}

const FACILITY_KIND_LABELS: Record<string, string> = {
  charger: 'Charger',
  cleaning: 'Cleaning bay',
  maintenance: 'Maintenance',
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
