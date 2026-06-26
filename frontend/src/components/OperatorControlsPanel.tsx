import type { NetworkPolicySnap, SimCommand } from '../types/simulation'
import { PolicyLink } from './ui/PolicyLink'
import { PanelSection } from './ui/PanelSection'

interface Props {
  policy: NetworkPolicySnap
  onCommand: (cmd: SimCommand) => void
}

/**
 * Legacy redirect — scenarios/alerts/health moved to Policy → Operations;
 * score weights moved to Analyze; pricing/demand moved to Market & demand.
 */
export function OperatorControlsPanel(_props: Props) {
  return (
    <div className="p-3 pb-4 space-y-3">
      <PanelSection title="Controls consolidated">
        <div className="p-3 space-y-3 text-xs text-text-secondary">
          <p>Each lever now has one primary panel. Use the links below.</p>
          <ul className="space-y-2 list-disc list-inside">
            <li>Scenarios, trip SLA, fleet health, operator alerts → <PolicyLink subTab="operations" className="inline" /></li>
            <li>Pricing and demand rate → <PolicyLink subTab="market" className="inline" /></li>
            <li>Matching weights and dropoff scoring → <PolicyLink subTab="matching" className="inline" /></li>
            <li>Composite score weights → Analyze tab</li>
          </ul>
        </div>
      </PanelSection>
    </div>
  )
}
