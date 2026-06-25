import { useState } from 'react'
import type { NetworkPolicySnap, SimCommand } from '../types/simulation'
import { ToggleCard } from './ui/ToggleCard'
import { PanelSection } from './ui/PanelSection'

interface Props {
  policy: NetworkPolicySnap
  onCommand: (cmd: SimCommand) => void
}

/** Fleet automation master switch and global routing constraints. */
export function AutomationPanel({ policy, onCommand }: Props) {
  const [repositionLeadMin, setRepositionLeadMin] = useState(String(policy.reposition_lead_min))
  const [minBenefit, setMinBenefit] = useState(String(policy.min_reposition_benefit))
  const [maxRepositionMin, setMaxRepositionMin] = useState(String(policy.max_reposition_min))
  const [maxIdle, setMaxIdle] = useState(String(policy.max_idle_per_zone))
  const [downtownCap, setDowntownCap] = useState(String(policy.max_idle_by_zone?.downtown ?? ''))

  const applyToggle = (field: string, value: boolean) => {
    onCommand({ type: 'SET_NETWORK_POLICY', [field]: value })
  }

  const applyConstraints = () => {
    const maxIdleByZone = { ...policy.max_idle_by_zone }
    if (downtownCap) maxIdleByZone.downtown = parseInt(downtownCap, 10)
    onCommand({
      type: 'SET_NETWORK_POLICY',
      reposition_lead_min: parseFloat(repositionLeadMin) || policy.reposition_lead_min,
      min_reposition_benefit: parseFloat(minBenefit) || policy.min_reposition_benefit,
      max_reposition_min: parseFloat(maxRepositionMin) || policy.max_reposition_min,
      max_idle_per_zone: parseInt(maxIdle, 10) || policy.max_idle_per_zone,
      max_idle_by_zone: maxIdleByZone,
    })
  }

  return (
    <div className="p-3 pb-4">
      <PanelSection title="Automation">
        <div className="p-3 space-y-4">
          <p className="text-xs text-text-secondary leading-relaxed">
            Trip matching and repositioning logic lives in the <strong className="text-text-primary">Routing</strong> tab.
            Use this panel for the master dispatch switch and global deadhead constraints.
          </p>

          <ToggleCard
            title="Auto-assign trips"
            description="When on, dispatch rules in the Routing tab can match idle cars to riders"
            checked={policy.auto_dispatch_enabled}
            onChange={v => applyToggle('auto_dispatch_enabled', v)}
          />

          <ToggleCard
            title="Allow depot overflow"
            description="When reposition rules send cars to depot, park off-street if capacity allows"
            checked={policy.depot_release_enabled}
            onChange={v => applyToggle('depot_release_enabled', v)}
          />

          <details className="border border-border-default rounded-lg" open>
            <summary className="px-3 py-2 text-sm font-medium text-text-primary cursor-pointer hover:bg-surface-base/50 rounded-lg">
              Global routing constraints
            </summary>
            <div className="p-3 pt-0 space-y-2 border-t border-border-default/50">
              <div className="grid grid-cols-2 gap-2 pt-2">
                <label className="block space-y-1">
                  <span className="text-xs text-text-secondary">Forecast lookahead (min)</span>
                  <input type="number" min="5" value={repositionLeadMin} onChange={e => setRepositionLeadMin(e.target.value)} className="input-dark" />
                </label>
                <label className="block space-y-1">
                  <span className="text-xs text-text-secondary">Max deadhead time (min)</span>
                  <input type="number" min="1" value={maxRepositionMin} onChange={e => setMaxRepositionMin(e.target.value)} className="input-dark" />
                </label>
              </div>
              <label className="block space-y-1">
                <span className="text-xs text-text-secondary">Min ROI to reposition</span>
                <input type="number" step="0.1" min="0" value={minBenefit} onChange={e => setMinBenefit(e.target.value)} className="input-dark" />
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="block space-y-1">
                  <span className="text-xs text-text-secondary">Max idle per zone</span>
                  <input type="number" min="1" value={maxIdle} onChange={e => setMaxIdle(e.target.value)} className="input-dark" />
                </label>
                <label className="block space-y-1">
                  <span className="text-xs text-text-secondary">Downtown idle cap</span>
                  <input type="number" min="1" placeholder="Use global" value={downtownCap} onChange={e => setDowntownCap(e.target.value)} className="input-dark" />
                </label>
              </div>
              <button type="button" onClick={applyConstraints} className="w-full py-2 bg-surface-raised hover:bg-surface-base border border-border-default text-sm font-medium rounded-md transition-colors">
                Apply constraints
              </button>
            </div>
          </details>
        </div>
      </PanelSection>
    </div>
  )
}
