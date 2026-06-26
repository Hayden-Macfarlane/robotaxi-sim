import type { SimCommand } from '../../types/simulation'
import type {
  ActionMeta,
  ConstantMeta,
  MetricMeta,
  PlaybookV2,
  RuleHitV2,
  RuleTemplate,
  RuleV2,
  SelectionMeta,
} from '../../types/playbook'
import { useUiMode } from '../../contexts/UiModeContext'
import { RulesBuildPanel } from './RulesBuildPanel'
import { RulesLibraryPanel } from './RulesLibraryPanel'
import { RulesMonitorPanel } from './RulesMonitorPanel'
import { RulesSubTabs } from './RulesSubTabs'

interface Props {
  playbook: PlaybookV2
  ruleHits: RuleHitV2[]
  metricCatalog: MetricMeta[]
  constantCatalog: ConstantMeta[]
  actionCatalog: ActionMeta[]
  selectionCatalog: SelectionMeta[]
  ruleTemplates: RuleTemplate[]
  routingEngineVersion: string
  onCommand: (cmd: SimCommand) => void
  onHighlightVehicle?: (vehicleId: string | null) => void
}

/** Rules hub: Build, Monitor, Library sub-tabs. */
export function RulesHubPanel({
  playbook,
  ruleHits,
  metricCatalog,
  constantCatalog,
  actionCatalog,
  selectionCatalog,
  ruleTemplates,
  routingEngineVersion,
  onCommand,
  onHighlightVehicle,
}: Props) {
  const { rulesSubTab, setRulesSubTab, uiMode, setPendingWizardDraft, navigate, setHighlightRuleId } = useUiMode()

  const applyPlaybook = (patch: Partial<PlaybookV2>) => {
    onCommand({
      type: 'SET_PLAYBOOK_V2',
      enabled: patch.enabled ?? playbook.enabled,
      constants: patch.constants ?? playbook.constants,
      rules: patch.rules ?? playbook.rules,
    })
  }

  const addConstant = (id: string, defaultValue: number) => {
    applyPlaybook({ constants: { ...playbook.constants, [id]: defaultValue } })
  }

  const addRuleFromTemplate = (rule: RuleV2) => {
    setPendingWizardDraft(rule, 'template')
    navigate({ tab: 'rules', rulesSubTab: 'build' })
  }

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      <div className="px-3 py-2 border-b border-border-default bg-surface-raised/30">
        <h2 className="text-sm font-medium text-text-primary">
          {uiMode === 'standard' ? 'Fleet rules' : 'Rules engine'}
        </h2>
        <p className="text-[10px] text-text-secondary mt-0.5">
          Build playbook rules, browse constraints, monitor live hits
        </p>
      </div>
      <RulesSubTabs active={rulesSubTab} onChange={setRulesSubTab} />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {rulesSubTab === 'build' && (
          <RulesBuildPanel
            playbook={playbook}
            metricCatalog={metricCatalog}
            constantCatalog={constantCatalog}
            actionCatalog={actionCatalog}
            selectionCatalog={selectionCatalog}
            ruleTemplates={ruleTemplates}
            routingEngineVersion={routingEngineVersion}
            onCommand={onCommand}
          />
        )}
        {rulesSubTab === 'monitor' && (
          <RulesMonitorPanel
            ruleHits={ruleHits}
            metricCatalog={metricCatalog}
            onHighlightVehicle={onHighlightVehicle}
            onEditRule={ruleId => setHighlightRuleId(ruleId)}
          />
        )}
        {rulesSubTab === 'library' && (
          <RulesLibraryPanel
            metricCatalog={metricCatalog}
            constantCatalog={constantCatalog}
            actionCatalog={actionCatalog}
            ruleTemplates={ruleTemplates}
            playbook={playbook}
            onAddConstant={addConstant}
            onAddRule={addRuleFromTemplate}
          />
        )}
      </div>
    </div>
  )
}
