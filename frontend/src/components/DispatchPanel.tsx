import type { DispatchAssignmentMode, OperatorSetupSnap, SimCommand } from '../types/simulation'
import { PolicyLink } from './ui/PolicyLink'
import { PanelSection } from './ui/PanelSection'

const DISPATCH_OPTIONS: {
  mode: DispatchAssignmentMode
  industryTitle: string
  plainTitle: string
  description: string
}[] = [
  {
    mode: 'manual',
    industryTitle: 'Manual dispatch',
    plainTitle: 'Manual assignment',
    description: 'You assign each open order from the Live → Orders panel.',
  },
  {
    mode: 'closest_idle_or_repositioning',
    industryTitle: 'Nearest available vehicle',
    plainTitle: 'Auto — idle or rebalancing',
    description: 'System assigns the best-ranked idle or rebalancing vehicle.',
  },
  {
    mode: 'closest_idle',
    industryTitle: 'Nearest idle vehicle',
    plainTitle: 'Auto — idle only',
    description: 'System assigns only vehicles waiting for trips (not rebalancing).',
  },
]

interface Props {
  operatorSetup: OperatorSetupSnap
  onCommand: (cmd: SimCommand) => void
}

/** Dispatch assignment mode and links to matching policy. */
export function DispatchPanel({ operatorSetup, onCommand }: Props) {
  const mode = operatorSetup.dispatch_assignment_mode ?? 'manual'

  return (
    <div className="p-3 pb-4 space-y-4 overflow-y-auto">
      <PanelSection
        title="Assignment mode"
        subtitle="Dispatch"
        impact="How open orders get matched to vehicles."
      >
        <div className="p-3 space-y-2">
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
                <div className="text-sm font-medium text-text-primary">{opt.industryTitle}</div>
                <p className="text-[10px] text-accent">{opt.plainTitle}</p>
                <p className="text-[11px] text-text-secondary mt-0.5 leading-relaxed">{opt.description}</p>
              </div>
            </label>
          ))}
        </div>
      </PanelSection>

      <PanelSection title="Related policy" impact="Configure how auto-dispatch ranks and assigns vehicles.">
        <div className="p-3 space-y-2 text-xs">
          <p className="text-text-secondary">
            Matching weights, supply floors, and automation rules live under Fleet policy.
          </p>
          <div className="flex flex-wrap gap-3">
            <PolicyLink subTab="matching" />
            <PolicyLink subTab="supply" />
            <PolicyLink subTab="automation" />
            <PolicyLink subTab="network" />
          </div>
        </div>
      </PanelSection>
    </div>
  )
}
