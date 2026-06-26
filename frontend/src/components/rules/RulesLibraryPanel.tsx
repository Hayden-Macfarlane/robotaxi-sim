import type { LibraryViewId } from '../../contexts/UiModeContext'
import { useUiMode } from '../../contexts/UiModeContext'
import type {
  ActionMeta,
  ConstantMeta,
  MetricMeta,
  PlaybookV2,
  RuleTemplate,
  RuleV2,
} from '../../types/playbook'
import { ConstraintBrowser } from './ConstraintBrowser'
import { ConstantBrowser } from './ConstantBrowser'
import { RuleTemplateGallery } from './RuleTemplateGallery'
import { CatalogCard } from '../ui/CatalogCard'

const VIEWS: { id: LibraryViewId; label: string }[] = [
  { id: 'constraints', label: 'Constraints' },
  { id: 'thresholds', label: 'Thresholds' },
  { id: 'templates', label: 'Templates' },
  { id: 'actions', label: 'Actions' },
]

interface Props {
  metricCatalog: MetricMeta[]
  constantCatalog: ConstantMeta[]
  actionCatalog: ActionMeta[]
  ruleTemplates: RuleTemplate[]
  playbook: PlaybookV2
  onAddConstant: (id: string, defaultValue: number) => void
  onAddRule: (rule: RuleV2) => void
}

/** Library browse: constraints, thresholds, templates, actions. */
export function RulesLibraryPanel({
  metricCatalog,
  constantCatalog,
  actionCatalog,
  ruleTemplates,
  playbook,
  onAddConstant,
  onAddRule,
}: Props) {
  const { libraryView, setLibraryView, setPendingMetricId, navigate, uiMode } = useUiMode()

  return (
    <div className="p-3 space-y-3 pb-8">
      <div className="flex flex-wrap gap-1">
        {VIEWS.map(v => (
          <button
            key={v.id}
            type="button"
            onClick={() => setLibraryView(v.id)}
            className={`px-2 py-1 rounded text-[10px] border ${
              libraryView === v.id
                ? 'border-accent text-accent bg-accent/10'
                : 'border-border-default text-text-secondary'
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      {libraryView === 'constraints' && (
        <ConstraintBrowser
          catalog={metricCatalog}
          onUseInCondition={id => {
            setPendingMetricId(id)
            navigate({ tab: 'rules', rulesSubTab: 'build' })
          }}
        />
      )}

      {libraryView === 'thresholds' && (
        <ConstantBrowser catalog={constantCatalog} playbook={playbook} onAddConstant={onAddConstant} />
      )}

      {libraryView === 'templates' && (
        <RuleTemplateGallery
          templates={ruleTemplates}
          onAdd={rule => {
            onAddRule(rule)
            navigate({ tab: 'rules', rulesSubTab: 'build' })
          }}
        />
      )}

      {libraryView === 'actions' && (
        <div className="space-y-2 max-h-[28rem] overflow-y-auto">
          {actionCatalog.map(a => (
            <CatalogCard
              key={a.id}
              title={uiMode === 'standard' ? a.plain_label : a.industry_label}
              description={a.description}
              badges={a.phases ?? []}
            />
          ))}
        </div>
      )}
    </div>
  )
}
