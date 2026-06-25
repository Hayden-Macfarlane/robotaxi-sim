import { useState } from 'react'
import type { DispatchAssignmentMode, NetworkPolicySnap, OperatorSetupSnap, SimCommand } from '../types/simulation'
import { ToggleCard } from './ui/ToggleCard'
import { PanelSection } from './ui/PanelSection'

const DISPATCH_OPTIONS: {
  mode: DispatchAssignmentMode
  title: string
  description: string
}[] = [
  {
    mode: 'manual',
    title: 'Manual assignment',
    description: 'Assign each trip yourself from the Activity tab',
  },
  {
    mode: 'closest_idle_or_repositioning',
    title: 'Closest idle or repositioning',
    description: 'Auto-assign to the nearest idle or repositioning vehicle',
  },
  {
    mode: 'closest_idle',
    title: 'Closest idle only',
    description: 'Auto-assign to idle vehicles only',
  },
]

interface Props {
  policy: NetworkPolicySnap
  operatorSetup: OperatorSetupSnap
  onCommand: (cmd: SimCommand) => void
}

/** Dispatch policy picker and advanced automation controls. */
export function AutomationPanel({ policy, operatorSetup, onCommand }: Props) {
  const [repositionLeadMin, setRepositionLeadMin] = useState(String(policy.reposition_lead_min))
  const [minBenefit, setMinBenefit] = useState(String(policy.min_reposition_benefit))
  const [maxRepositionMin, setMaxRepositionMin] = useState(String(policy.max_reposition_min))
  const [maxIdle, setMaxIdle] = useState(String(policy.max_idle_per_zone))
  const [downtownCap, setDowntownCap] = useState(String(policy.max_idle_by_zone?.downtown ?? ''))

  const advanced = operatorSetup.advanced_automation_enabled
  const mode = operatorSetup.dispatch_assignment_mode ?? 'manual'

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
    <div className="p-3 pb-4 space-y-4">
      <PanelSection title="Dispatch assignment">
        <div className="p-3 space-y-2">
          <p className="text-xs text-text-secondary leading-relaxed">
            Choose how pending trips are matched to vehicles. Switch anytime during the simulation.
          </p>
          {DISPATCH_OPTIONS.map(opt => (
            <label
              key={opt.mode}
              className={`flex gap-3 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                mode === opt.mode
                  ? 'border-accent bg-accent/10'
                  : 'border-border-default bg-surface-raised/40 hover:bg-surface-raised/70'
              }`}
            >
              <input
                type="radio"
                name="dispatch-mode"
                value={opt.mode}
                checked={mode === opt.mode}
                onChange={() =>
                  onCommand({ type: 'SET_OPERATOR_SETUP', dispatch_assignment_mode: opt.mode })
                }
                className="mt-0.5"
              />
              <div className="min-w-0">
                <div className="text-sm font-medium text-text-primary">{opt.title}</div>
                <p className="text-[11px] text-text-secondary mt-0.5 leading-relaxed">{opt.description}</p>
              </div>
            </label>
          ))}
        </div>
      </PanelSection>

      <PanelSection title="Advanced automation">
        <div className="p-3 space-y-4">
          <ToggleCard
            title="Enable advanced automation"
            description="Unlock reposition rules, global constraints, zone minimums, and full rule builder"
            checked={advanced}
            onChange={v => onCommand({ type: 'SET_OPERATOR_SETUP', advanced_automation_enabled: v })}
          />

          {!advanced && (
            <p className="text-xs text-text-secondary italic px-1">
              Advanced settings are locked. Enable advanced automation to configure repositioning and constraints.
            </p>
          )}

          <div className={advanced ? '' : 'opacity-40 pointer-events-none select-none'}>
            <p className="text-xs text-text-secondary leading-relaxed mb-3">
              Trip matching and repositioning logic lives in the <strong className="text-text-primary">Routing</strong> tab.
              Use this panel for the master dispatch switch and global deadhead constraints.
            </p>

            <ToggleCard
              title="Auto-assign trips"
              description="When on, dispatch rules in the Routing tab can match cars to riders"
              checked={policy.auto_dispatch_enabled}
              onChange={v => onCommand({ type: 'SET_NETWORK_POLICY', auto_dispatch_enabled: v })}
            />

            <ToggleCard
              title="Allow depot overflow"
              description="When reposition rules send cars to depot, park off-street if capacity allows"
              checked={policy.depot_release_enabled}
              onChange={v => onCommand({ type: 'SET_NETWORK_POLICY', depot_release_enabled: v })}
            />

            <details className="border border-border-default rounded-lg mt-4">
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
        </div>
      </PanelSection>
    </div>
  )
}
