import type { KpiSnap, VehicleSnap } from '../types/simulation'
import { healthAlert } from './vehicleLabels'

const OFF_STREET = new Set(['at_depot', 'charging', 'maintenance', 'cleaning'])
const SERVING_RIDER = new Set(['to_pickup', 'with_rider'])
const BUSY = new Set(['to_pickup', 'with_rider', 'repositioning', 'to_facility'])

export type AssetFilter = 'all' | 'idle' | 'busy' | 'needs_service' | 'at_facility'

export interface FleetSummary {
  onStreet: number
  serving: number
  needsAttention: number
  atFacilities: number
}

export function fleetSummary(vehicles: VehicleSnap[], kpis: KpiSnap): FleetSummary {
  return {
    onStreet: vehicles.filter(v => !OFF_STREET.has(v.state)).length,
    serving: vehicles.filter(v => SERVING_RIDER.has(v.state)).length,
    needsAttention: Math.round(kpis.vehicles_needing_service ?? vehicles.filter(v => healthAlert(v) !== null && v.state === 'idle').length),
    atFacilities: vehicles.filter(v => OFF_STREET.has(v.state)).length,
  }
}

export function facilityOccupancy(facilityId: string, vehicles: VehicleSnap[]): number {
  return vehicles.filter(v => v.facility_id === facilityId).length
}

export function filterVehicles(vehicles: VehicleSnap[], filter: AssetFilter): VehicleSnap[] {
  switch (filter) {
    case 'idle':
      return vehicles.filter(v => v.state === 'idle')
    case 'busy':
      return vehicles.filter(v => BUSY.has(v.state))
    case 'needs_service':
      return vehicles.filter(v => v.state === 'idle' && healthAlert(v) !== null)
    case 'at_facility':
      return vehicles.filter(v => OFF_STREET.has(v.state))
    default:
      return vehicles
  }
}

export function minHealthPct(v: VehicleSnap): number {
  return Math.min(v.battery_pct, v.condition_pct ?? 100, v.cleanliness_pct ?? 100)
}
