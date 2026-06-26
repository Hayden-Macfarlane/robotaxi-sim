import { useState } from 'react'
import type { NetworkPolicySnap, OperatorSetupSnap, SimCommand } from '../types/simulation'
import type { RoutingRuleHit, RoutingRuleSet } from '../types/routing'
import { RoutingConstraintsPanel } from './RoutingConstraintsPanel'
import { RoutingRulesPanel } from './RoutingRulesPanel'
import { RoutingScoringPanel } from './RoutingScoringPanel'
import { RoutingSubTabs, type RoutingSubTabId } from './RoutingSubTabs'
import { RoutingZonePolicyPanel } from './RoutingZonePolicyPanel'

interface Props {
  policy: NetworkPolicySnap
  ruleSet: RoutingRuleSet
  ruleHits: RoutingRuleHit[]
  operatorSetup: OperatorSetupSnap
  onCommand: (cmd: SimCommand) => void
}

/** Unified routing control hub with scoring, zone policy, rules, and constraints sub-tabs. */
export function RoutingPanel({ policy, ruleSet, ruleHits, operatorSetup, onCommand }: Props) {
  const [subTab, setSubTab] = useState<RoutingSubTabId>('scoring')

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      <RoutingSubTabs active={subTab} onChange={setSubTab} />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {subTab === 'scoring' && <RoutingScoringPanel policy={policy} onCommand={onCommand} />}
        {subTab === 'zones' && <RoutingZonePolicyPanel policy={policy} onCommand={onCommand} />}
        {subTab === 'rules' && (
          <RoutingRulesPanel
            ruleSet={ruleSet}
            ruleHits={ruleHits}
            operatorSetup={operatorSetup}
            onCommand={onCommand}
          />
        )}
        {subTab === 'constraints' && (
          <RoutingConstraintsPanel policy={policy} ruleSet={ruleSet} onCommand={onCommand} />
        )}
      </div>
    </div>
  )
}
