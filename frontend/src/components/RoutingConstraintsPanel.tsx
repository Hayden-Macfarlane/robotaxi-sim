import { useState } from 'react'
import type { NetworkPolicySnap, SimCommand } from '../types/simulation'
import type { RoutingRuleSet } from '../types/routing'
import { useUiMode } from '../contexts/UiModeContext'
import { FieldLabel } from './ui/FieldLabel'
import { PanelSection } from './ui/PanelSection'

interface Props {
  policy: NetworkPolicySnap
  ruleSet: RoutingRuleSet
  onCommand: (cmd: SimCommand) => void
}

/** Master routing switches, ROI gates, depot, charge-aware, failover, and traffic. */
export function RoutingConstraintsPanel({ policy, ruleSet, onCommand }: Props) {
  const [draft, setDraft] = useState<Partial<NetworkPolicySnap>>({})
  const { uiMode } = useUiMode()
  const p = policy

  const val = <K extends keyof NetworkPolicySnap>(key: K, fallback: NetworkPolicySnap[K]): NetworkPolicySnap[K] =>
    (draft[key] ?? p[key] ?? fallback) as NetworkPolicySnap[K]

  const set = <K extends keyof NetworkPolicySnap>(key: K, value: NetworkPolicySnap[K]) => {
    setDraft(prev => ({ ...prev, [key]: value }))
  }

  const apply = (patch: Partial<NetworkPolicySnap>) => {
    onCommand({ type: 'SET_NETWORK_POLICY', ...patch })
    setDraft({})
  }

  const applyAll = () => {
    onCommand({ type: 'SET_NETWORK_POLICY', ...draft })
    setDraft({})
  }

  const setRoutingEnabled = (enabled: boolean) => {
    onCommand({ type: 'SET_ROUTING_RULES', rules: ruleSet.rules, routing_enabled: enabled })
  }

  return (
    <div className="p-3 pb-4 space-y-3 overflow-y-auto">
      <PanelSection title="Master switches" impact="Global automation toggles for dispatch and rebalancing.">
        <div className="p-3 space-y-2 text-xs">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={ruleSet.routing_enabled} onChange={e => setRoutingEnabled(e.target.checked)} />
            Routing rules enabled
          </label>
          <FieldLabel termId="auto_dispatch_enabled" showHelp={false}>
            <label className="flex items-center gap-2 mt-1">
              <input type="checkbox" checked={val('auto_dispatch_enabled', true)} onChange={e => apply({ auto_dispatch_enabled: e.target.checked })} />
              Enable auto-dispatch
            </label>
          </FieldLabel>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={val('batch_dispatch_enabled', false)} onChange={e => apply({ batch_dispatch_enabled: e.target.checked })} />
            Batch dispatch (global assignment)
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={val('auto_reposition_enabled', true)} onChange={e => apply({ auto_reposition_enabled: e.target.checked })} />
            Auto-reposition idle vehicles
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={val('post_trip_reposition_enabled', true)} onChange={e => apply({ post_trip_reposition_enabled: e.target.checked })} />
            Post-trip reposition
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={val('proactive_staging_enabled', true)} onChange={e => apply({ proactive_staging_enabled: e.target.checked })} />
            Proactive forecast staging
          </label>
        </div>
      </PanelSection>

      <PanelSection title="Rebalancing ROI" subtitle="Deadhead economics" impact="When empty repositioning moves are worth the drive.">
        <div className="p-3 grid grid-cols-2 gap-2 text-xs">
          <label className="block space-y-1">
            <span className="text-text-secondary">Forecast lookahead (min)</span>
            <input type="number" min={5} value={val('reposition_lead_min', 30)} onChange={e => set('reposition_lead_min', parseFloat(e.target.value) || 30)} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Max reposition (min)</span>
            <input type="number" min={1} value={val('max_reposition_min', 45)} onChange={e => set('max_reposition_min', parseFloat(e.target.value) || 45)} className="input-dark" />
          </label>
          <FieldLabel termId="min_reposition_benefit">
            <input type="number" min={0} step={0.1} value={val('min_reposition_benefit', 0.5)} onChange={e => set('min_reposition_benefit', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
          </FieldLabel>
          <FieldLabel termId="deadhead_cost_per_min">
            <input type="number" min={0} step={0.01} value={val('deadhead_cost_per_min', 0.15)} onChange={e => set('deadhead_cost_per_min', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
          </FieldLabel>
          <label className="block space-y-1 col-span-2">
            <span className="text-text-secondary">Value per expected trip ($)</span>
            <input type="number" min={0} step={0.1} value={val('value_per_trip', 2)} onChange={e => set('value_per_trip', parseFloat(e.target.value) || 0)} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Forecast rise threshold</span>
            <input type="number" min={0} step={0.1} value={val('forecast_rising_threshold', 1.5)} onChange={e => set('forecast_rising_threshold', parseFloat(e.target.value) || 1.5)} className="input-dark" />
          </label>
        </div>
      </PanelSection>

      <PanelSection title="Depot & hold">
        <div className="p-3 grid grid-cols-2 gap-2 text-xs">
          <label className="flex items-center gap-2 col-span-2">
            <input type="checkbox" checked={val('depot_release_enabled', true)} onChange={e => apply({ depot_release_enabled: e.target.checked })} />
            Allow depot overflow release
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Min depot buffer</span>
            <input type="number" min={0} value={val('min_depot_buffer', 0)} onChange={e => set('min_depot_buffer', parseInt(e.target.value, 10) || 0)} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Manual hold (min)</span>
            <input type="number" min={5} value={val('manual_hold_min', 60)} onChange={e => set('manual_hold_min', parseFloat(e.target.value) || 60)} className="input-dark" />
          </label>
        </div>
      </PanelSection>

      <PanelSection title="Charge-aware dispatch">
        <div className="p-3 space-y-2 text-xs">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={val('charge_aware_dispatch', false)} onChange={e => apply({ charge_aware_dispatch: e.target.checked })} />
            Filter by pickup + ride battery need
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block space-y-1">
              <span className="text-text-secondary">Min battery for trip %</span>
              <input type="number" min={5} max={90} value={val('min_battery_pct_for_trip', 25)} onChange={e => set('min_battery_pct_for_trip', parseFloat(e.target.value) || 25)} className="input-dark" />
            </label>
            <label className="block space-y-1">
              <span className="text-text-secondary">km per SOC %</span>
              <input type="number" min={0.1} step={0.1} value={val('km_per_soc_pct', 0.6)} onChange={e => set('km_per_soc_pct', parseFloat(e.target.value) || 0.6)} className="input-dark" />
            </label>
          </div>
        </div>
      </PanelSection>

      <PanelSection
        title="Deadzone filler"
        subtitle="Coverage gaps"
        impact="Reposition idle cars into areas with no nearby asset when size ÷ travel distance clears your ratio."
      >
        <div className="p-3 space-y-2 text-xs">
          <FieldLabel termId="deadzone_filler_enabled" showHelp={false}>
            <label className="flex items-center gap-2 mt-1">
              <input type="checkbox" checked={val('deadzone_filler_enabled', false)} onChange={e => apply({ deadzone_filler_enabled: e.target.checked })} />
              Enable deadzone filler (after routing rules)
            </label>
          </FieldLabel>
          <div className="grid grid-cols-2 gap-2">
            <FieldLabel termId="max_distance_from_nearest_asset_km">
              <input type="number" min={0.1} step={0.1} value={val('max_distance_from_nearest_asset_km', 2)} onChange={e => set('max_distance_from_nearest_asset_km', parseFloat(e.target.value) || 2)} className="input-dark w-full mt-1" />
            </FieldLabel>
            <FieldLabel termId="deadzone_fill_ratio_threshold">
              <input type="number" min={0} step={0.1} value={val('deadzone_fill_ratio_threshold', 1)} onChange={e => set('deadzone_fill_ratio_threshold', parseFloat(e.target.value) || 1)} className="input-dark w-full mt-1" />
            </FieldLabel>
            <FieldLabel termId="deadzone_size_adjustment_km">
              <input type="number" min={0} step={0.1} value={val('deadzone_size_adjustment_km', 0)} onChange={e => set('deadzone_size_adjustment_km', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
            </FieldLabel>
            <FieldLabel termId="deadzone_travel_adjustment_km">
              <input type="number" min={0} step={0.1} value={val('deadzone_travel_adjustment_km', 0)} onChange={e => set('deadzone_travel_adjustment_km', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
            </FieldLabel>
          </div>
          {uiMode === 'expert' && (
            <p className="text-[10px] text-text-secondary font-mono leading-relaxed">
              fill ratio = (deadzone size + size adj) ÷ (travel km + travel adj)
              <br />
              deadzone size = nearest idle car km − max coverage radius
            </p>
          )}
          {uiMode === 'standard' && (
            <p className="text-[10px] text-text-secondary leading-relaxed">
              Larger coverage gaps and shorter drives score higher. Raise the ratio threshold to reposition less often.
            </p>
          )}
        </div>
      </PanelSection>

      <PanelSection title={uiMode === 'standard' ? 'Auto-dispatch tripwires' : 'Failover & traffic'} impact="Automatic responses when queue or wait exceeds limits.">
        <div className="p-3 grid grid-cols-2 gap-2 text-xs">
          <FieldLabel termId="pending_orders" showHelp={false}>
            <input type="number" min={0} value={val('failover_pending_queue_max', 0)} onChange={e => set('failover_pending_queue_max', parseInt(e.target.value, 10) || 0)} className="input-dark w-full mt-1" placeholder="Queue max (0=off)" />
          </FieldLabel>
          <FieldLabel termId="pickup_wait" showHelp={false}>
            <input type="number" min={0} value={val('failover_avg_wait_max_min', 0)} onChange={e => set('failover_avg_wait_max_min', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" placeholder="Wait max (0=off)" />
          </FieldLabel>
          <FieldLabel termId="global_traffic_multiplier" className="col-span-2">
            <input type="number" min={0.25} max={3} step={0.05} value={val('global_traffic_multiplier', 1)} onChange={e => set('global_traffic_multiplier', parseFloat(e.target.value) || 1)} className="input-dark w-full mt-1" />
          </FieldLabel>
        </div>
      </PanelSection>

      {Object.keys(draft).length > 0 && (
        <button type="button" onClick={applyAll} className="w-full py-2 bg-accent text-white text-sm font-medium rounded-md">
          Apply constraints ({Object.keys(draft).length} changed)
        </button>
      )}
    </div>
  )
}
