import { useState } from 'react'
import type { NetworkPolicySnap, SimCommand } from '../types/simulation'
import { useUiMode } from '../contexts/UiModeContext'
import { FieldLabel } from './ui/FieldLabel'
import { PanelSection } from './ui/PanelSection'

interface Props {
  policy: NetworkPolicySnap
  onCommand: (cmd: SimCommand) => void
}

/** Dispatch candidate scoring weights and dropoff balance controls. */
export function RoutingScoringPanel({ policy, onCommand }: Props) {
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

  return (
    <div className="p-3 pb-4 space-y-3 overflow-y-auto">
      <PanelSection
        title="Matching weights"
        subtitle="Scoring"
        impact="How the system ranks vehicles for each open order."
      >
        {uiMode === 'expert' && (
          <p className="px-3 pt-3 text-[10px] text-text-secondary leading-relaxed font-mono">
            score = ETA×w_eta − surge − origin_bonus + cross_zone_pen ± dropoff_balance
            <br />
            Lower score = better match
          </p>
        )}
        {uiMode === 'standard' && (
          <p className="px-3 pt-3 text-[10px] text-text-secondary leading-relaxed">
            Lower match score means a better candidate. Closer pickup ETA and helpful dropoff zones rank higher.
          </p>
        )}
        <div className="p-3 grid grid-cols-2 gap-2 text-xs">
          <FieldLabel termId="dispatch_weight_eta">
            <input type="number" min={0} step={0.1} value={val('dispatch_weight_eta', 1)} onChange={e => set('dispatch_weight_eta', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
          </FieldLabel>
          {uiMode === 'expert' && (
            <FieldLabel termId="dispatch_weight_surge">
              <input type="number" min={0} step={0.1} value={val('dispatch_weight_surge', 0)} onChange={e => set('dispatch_weight_surge', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
            </FieldLabel>
          )}
          <FieldLabel termId="dispatch_weight_zone_balance">
            <input type="number" min={0} step={0.1} value={val('dispatch_weight_zone_balance', 0)} onChange={e => set('dispatch_weight_zone_balance', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
          </FieldLabel>
          <FieldLabel termId="cross_zone_dispatch_penalty_min">
            <input type="number" min={0} step={0.5} value={val('cross_zone_dispatch_penalty_min', 0)} onChange={e => set('cross_zone_dispatch_penalty_min', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
          </FieldLabel>
          <FieldLabel termId="max_deadhead_to_pickup_min">
            <input type="number" min={0} value={val('max_deadhead_to_pickup_min', 0)} onChange={e => set('max_deadhead_to_pickup_min', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
          </FieldLabel>
          {uiMode === 'expert' && (
            <>
              <label className="block space-y-1">
                <span className="text-text-secondary">Candidate limit</span>
                <input type="number" min={1} max={25} value={val('dispatch_candidate_limit', 5)} onChange={e => set('dispatch_candidate_limit', parseInt(e.target.value, 10) || 5)} className="input-dark" />
              </label>
              <label className="block space-y-1 col-span-2">
                <span className="text-text-secondary">Tie-breaker</span>
                <select value={val('dispatch_tie_breaker', 'closest')} onChange={e => set('dispatch_tie_breaker', e.target.value as NetworkPolicySnap['dispatch_tie_breaker'])} className="input-dark w-full">
                  <option value="closest">Closest ETA</option>
                  <option value="idle_longest">Idle longest</option>
                  <option value="lowest_battery">Lowest battery</option>
                </select>
              </label>
              <label className="flex items-center gap-2 col-span-2">
                <input type="checkbox" checked={val('dispatch_use_fast_eta', false)} onChange={e => apply({ dispatch_use_fast_eta: e.target.checked })} />
                Fast ETA (haversine) for ranking
              </label>
              <label className="flex items-center gap-2 col-span-2">
                <input type="checkbox" checked={val('allow_preempt_reposition', true)} onChange={e => apply({ allow_preempt_reposition: e.target.checked })} />
                Allow preempting repositioning vehicles
              </label>
            </>
          )}
        </div>
      </PanelSection>

      <PanelSection
        title="Dropoff rebalancing"
        impact="Prefer vehicles that land in under-supplied zones after the trip."
      >
        <div className="p-3 space-y-2 text-xs">
          <FieldLabel termId="dispatch_consider_dropoff_balance" showHelp={false}>
            <label className="flex items-center gap-2 mt-1">
              <input type="checkbox" checked={val('dispatch_consider_dropoff_balance', false)} onChange={e => apply({ dispatch_consider_dropoff_balance: e.target.checked })} />
              Enable dropoff zone scoring
            </label>
          </FieldLabel>
          <div className="grid grid-cols-2 gap-2">
            <FieldLabel termId="dispatch_weight_dropoff_balance">
              <input type="number" min={0} step={0.1} value={val('dispatch_weight_dropoff_balance', 0)} onChange={e => set('dispatch_weight_dropoff_balance', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
            </FieldLabel>
            <FieldLabel termId="dispatch_penalty_dropoff_surplus_min">
              <input type="number" min={0} step={0.1} value={val('dispatch_penalty_dropoff_surplus_min', 0)} onChange={e => set('dispatch_penalty_dropoff_surplus_min', parseFloat(e.target.value) || 0)} className="input-dark w-full mt-1" />
            </FieldLabel>
          </div>
        </div>
      </PanelSection>

      {Object.keys(draft).length > 0 && (
        <button type="button" onClick={applyAll} className="w-full py-2 bg-accent text-white text-sm font-medium rounded-md">
          Apply matching ({Object.keys(draft).length} changed)
        </button>
      )}
    </div>
  )
}
