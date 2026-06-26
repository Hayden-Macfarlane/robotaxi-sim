import type { NetworkPolicySnap, OperatorSetupSnap, SimCommand } from '../types/simulation'
import { PolicyLink } from './ui/PolicyLink'
import { PanelSection } from './ui/PanelSection'
import { ToggleCard } from './ui/ToggleCard'

interface Props {
  policy: NetworkPolicySnap
  operatorSetup: OperatorSetupSnap
  onCommand: (cmd: SimCommand) => void
}

/**
 * Legacy redirect panel — dispatch mode moved to Dispatch tab;
 * constraints and zone caps moved to Fleet policy.
 */
export function AutomationPanel({ operatorSetup, onCommand }: Props) {
  const advanced = operatorSetup.advanced_automation_enabled

  return (
    <div className="p-3 pb-4 space-y-4">
      <PanelSection title="Moved to Dispatch & Policy">
        <div className="p-3 space-y-3 text-xs text-text-secondary">
          <p>Assignment mode is now under the <strong className="text-text-primary">Dispatch</strong> tab.</p>
          <p>Auto-dispatch, rebalancing ROI, zone caps, and rules are under <strong className="text-text-primary">Fleet policy</strong>.</p>
          <div className="flex flex-wrap gap-2">
            <PolicyLink subTab="network" />
            <PolicyLink subTab="supply" />
            <PolicyLink subTab="matching" />
          </div>
        </div>
      </PanelSection>

      <PanelSection title="Advanced automation gate">
        <div className="p-3">
          <ToggleCard
            title="Enable advanced automation"
            description="Unlock zone supply floors, automation playbook, and full rule builder"
            checked={advanced}
            onChange={v => onCommand({ type: 'SET_OPERATOR_SETUP', advanced_automation_enabled: v })}
          />
          {advanced && (
            <p className="text-xs text-text-secondary mt-3">
              Auto-dispatch master switch: <PolicyLink subTab="network" className="inline" />
            </p>
          )}
        </div>
      </PanelSection>
    </div>
  )
}
