import { useState } from 'react'
import type { NetworkPolicySnap, SimCommand } from '../types/simulation'
import { FieldLabel } from './ui/FieldLabel'
import { PanelSection } from './ui/PanelSection'

interface Props {
  policy: NetworkPolicySnap
  onCommand: (cmd: SimCommand) => void
}

const SCENARIOS = [
  { id: 'rush_hour', label: 'Rush hour' },
  { id: 'low_demand', label: 'Low demand' },
  { id: 'concert_surge', label: 'Concert surge' },
  { id: 'maintenance_heavy', label: 'Maintenance heavy' },
  { id: 'airport_peak', label: 'Airport peak' },
] as const

/** Scenarios, trip SLA, fleet health thresholds, and operator alerts. */
export function OperationsPanel({ policy, onCommand }: Props) {
  const p = policy
  const [draft, setDraft] = useState<Partial<NetworkPolicySnap>>({})

  const val = <K extends keyof NetworkPolicySnap>(key: K, fallback: NetworkPolicySnap[K]): NetworkPolicySnap[K] =>
    (draft[key] ?? p[key] ?? fallback) as NetworkPolicySnap[K]

  const set = <K extends keyof NetworkPolicySnap>(key: K, value: NetworkPolicySnap[K]) => {
    setDraft(prev => ({ ...prev, [key]: value }))
  }

  const applyAll = () => {
    onCommand({ type: 'SET_NETWORK_POLICY', ...draft })
    setDraft({})
  }

  return (
    <div className="p-3 pb-4 space-y-3 overflow-y-auto">
      <PanelSection title="Scenarios" impact="One-click presets for demand and fleet conditions.">
        <div className="p-3 flex flex-wrap gap-2">
          {SCENARIOS.map(s => (
            <button
              key={s.id}
              type="button"
              onClick={() => onCommand({ type: 'APPLY_SCENARIO', preset: s.id })}
              className="px-2 py-1 text-xs rounded border border-border-default bg-surface-raised hover:bg-surface-base"
            >
              {s.label}
            </button>
          ))}
        </div>
      </PanelSection>

      <PanelSection title="Trip SLA" subtitle="Service level" impact="When unmatched orders are cancelled.">
        <div className="p-3 text-xs">
          <label className="block space-y-1">
            <span className="text-text-secondary">Max wait before cancel (min)</span>
            <input type="number" min={1} value={val('max_wait_min', 12)} onChange={e => set('max_wait_min', parseFloat(e.target.value) || 12)} className="input-dark" />
          </label>
        </div>
      </PanelSection>

      <PanelSection title="Fleet health" impact="Wear thresholds that pull vehicles from dispatch.">
        <div className="p-3 grid grid-cols-2 gap-2 text-xs">
          <label className="block space-y-1">
            <span className="text-text-secondary">Battery drain / km</span>
            <input type="number" min={0} step={0.01} value={val('battery_drain_per_km', 0.4)} onChange={e => set('battery_drain_per_km', parseFloat(e.target.value) || 0)} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Low condition %</span>
            <input type="number" min={5} max={50} value={val('low_condition_pct', 25)} onChange={e => set('low_condition_pct', parseFloat(e.target.value) || 25)} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Charge time (min)</span>
            <input type="number" min={1} value={val('charge_minutes_to_full', 45)} onChange={e => set('charge_minutes_to_full', parseFloat(e.target.value) || 45)} className="input-dark" />
          </label>
        </div>
      </PanelSection>

      <PanelSection title="Operator alerts" impact="Banner warnings when KPIs cross these thresholds.">
        <div className="p-3 grid grid-cols-2 gap-2 text-xs">
          <FieldLabel termId="pickup_wait" showHelp={false}>
            <input type="number" min={0} value={val('alert_avg_wait_min', 8)} onChange={e => set('alert_avg_wait_min', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
          </FieldLabel>
          <FieldLabel termId="pending_orders" showHelp={false}>
            <input type="number" min={0} value={val('alert_pending_queue', 10)} onChange={e => set('alert_pending_queue', parseInt(e.target.value, 10) || 0)} className="input-dark w-full mt-1" />
          </FieldLabel>
          <label className="block space-y-1">
            <span className="text-text-secondary">Low utilization % (0=off)</span>
            <input type="number" min={0} max={100} value={val('alert_utilization_below_pct', 0)} onChange={e => set('alert_utilization_below_pct', parseFloat(e.target.value) || 0)} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Zone supply shortage alert</span>
            <input type="number" min={0} value={val('alert_zone_deficit', 3)} onChange={e => set('alert_zone_deficit', parseInt(e.target.value, 10) || 0)} className="input-dark" />
          </label>
        </div>
      </PanelSection>

      {Object.keys(draft).length > 0 && (
        <button type="button" onClick={applyAll} className="w-full py-2 bg-accent text-white text-sm font-medium rounded-md">
          Apply operations ({Object.keys(draft).length} changed)
        </button>
      )}
    </div>
  )
}
