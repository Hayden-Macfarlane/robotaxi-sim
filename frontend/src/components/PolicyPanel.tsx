import type { NetworkPolicySnap, OperatorSetupSnap, SimCommand } from '../types/simulation'
import type { ForecastSnap, SpecialEventSnap, ZoneBalanceSnap } from '../types/simulation'
import type { RoutingRuleHit, RoutingRuleSet } from '../types/routing'
import { useUiMode } from '../contexts/UiModeContext'
import { MarketDemandPanel } from './MarketDemandPanel'
import { OperationsPanel } from './OperationsPanel'
import { PolicySubTabs } from './PolicySubTabs'
import { RoutingConstraintsPanel } from './RoutingConstraintsPanel'
import { RoutingRulesPanel } from './RoutingRulesPanel'
import { RoutingScoringPanel } from './RoutingScoringPanel'
import { RoutingZonePolicyPanel } from './RoutingZonePolicyPanel'

interface Props {
  policy: NetworkPolicySnap
  ruleSet: RoutingRuleSet
  ruleHits: RoutingRuleHit[]
  operatorSetup: OperatorSetupSnap
  forecast: ForecastSnap[]
  events: SpecialEventSnap[]
  zoneBalance: ZoneBalanceSnap[]
  currentTimeH: number
  onCommand: (cmd: SimCommand) => void
}

/** Fleet policy hub: matching, supply, automation, network, market, operations. */
export function PolicyPanel({
  policy,
  ruleSet,
  ruleHits,
  operatorSetup,
  forecast,
  events,
  currentTimeH,
  onCommand,
}: Props) {
  const { policySubTab, setPolicySubTab, uiMode } = useUiMode()

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      <div className="px-3 py-2 border-b border-border-default bg-surface-raised/30">
        <h2 className="text-sm font-medium text-text-primary">
          {uiMode === 'standard' ? 'Fleet policy' : 'Fleet policy'}
        </h2>
        <p className="text-[10px] text-text-secondary mt-0.5">
          {uiMode === 'standard'
            ? 'Supply, pricing, matching, and automation settings'
            : 'Supply floors, matching weights, automation playbook, network constraints'}
        </p>
      </div>
      <PolicySubTabs active={policySubTab} onChange={setPolicySubTab} />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {policySubTab === 'matching' && <RoutingScoringPanel policy={policy} onCommand={onCommand} />}
        {policySubTab === 'supply' && <RoutingZonePolicyPanel policy={policy} onCommand={onCommand} />}
        {policySubTab === 'automation' && (
          <RoutingRulesPanel
            ruleSet={ruleSet}
            ruleHits={ruleHits}
            operatorSetup={operatorSetup}
            onCommand={onCommand}
          />
        )}
        {policySubTab === 'network' && (
          <RoutingConstraintsPanel policy={policy} ruleSet={ruleSet} onCommand={onCommand} />
        )}
        {policySubTab === 'market' && (
          <MarketDemandPanel
            policy={policy}
            forecast={forecast}
            events={events}
            currentTimeH={currentTimeH}
            onCommand={onCommand}
          />
        )}
        {policySubTab === 'operations' && <OperationsPanel policy={policy} onCommand={onCommand} />}
      </div>
    </div>
  )
}
