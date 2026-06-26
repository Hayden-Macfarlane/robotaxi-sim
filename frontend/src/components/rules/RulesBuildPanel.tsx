import { useEffect, useMemo, useRef, useState } from 'react'
import type { SimCommand } from '../../types/simulation'
import type {
  ActionMeta,
  ConstantMeta,
  MetricMeta,
  PlaybookV2,
  RuleTemplate,
  RuleV2,
  SelectionMeta,
} from '../../types/playbook'
import { countConstantUsage, summarizeExpr } from '../../lib/playbookUtils'
import { useUiMode } from '../../contexts/UiModeContext'
import { ConstantBrowser } from './ConstantBrowser'
import { defaultWizardRule, RuleWizard } from './RuleWizard'
import type { RuleCreationMode } from '../../types/playbook'
import { PanelSection } from '../ui/PanelSection'
import { SimButton } from '../ui/SimButton'

interface Props {
  playbook: PlaybookV2
  metricCatalog: MetricMeta[]
  constantCatalog: ConstantMeta[]
  actionCatalog: ActionMeta[]
  selectionCatalog: SelectionMeta[]
  ruleTemplates: RuleTemplate[]
  routingEngineVersion: string
  onCommand: (cmd: SimCommand) => void
}

function nextRuleId(rules: RuleV2[]): string {
  let n = rules.length + 1
  while (rules.some(r => r.id === `rule-${n}`)) n += 1
  return `rule-${n}`
}

/** Playbook editor: thresholds, rule list, wizard-based rule create/edit. */
export function RulesBuildPanel({
  playbook,
  metricCatalog,
  constantCatalog,
  actionCatalog,
  selectionCatalog,
  ruleTemplates,
  routingEngineVersion,
  onCommand,
}: Props) {
  const { navigate, pendingMetricId, setPendingMetricId, highlightRuleId, setHighlightRuleId, pendingWizardDraft, pendingWizardMode, setPendingWizardDraft } = useUiMode()
  const [local, setLocal] = useState<PlaybookV2>(playbook)
  const [selectedId, setSelectedId] = useState<string | null>(playbook.rules[0]?.id ?? null)
  const [showConstantBrowser, setShowConstantBrowser] = useState(false)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardDraft, setWizardDraft] = useState<RuleV2 | null>(null)
  const [wizardMode, setWizardMode] = useState<RuleCreationMode>('wizard')
  const [isEditing, setIsEditing] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const playbookRef = useRef(playbook)

  useEffect(() => {
    if (playbook !== playbookRef.current) {
      playbookRef.current = playbook
      setLocal(playbook)
      if (!playbook.rules.some(r => r.id === selectedId)) {
        setSelectedId(playbook.rules[0]?.id ?? null)
      }
    }
  }, [playbook, selectedId])

  useEffect(() => {
    if (highlightRuleId && local.rules.some(r => r.id === highlightRuleId)) {
      const rule = local.rules.find(r => r.id === highlightRuleId)
      setSelectedId(highlightRuleId)
      if (rule) openEditWizard(rule)
      setHighlightRuleId(null)
    }
  }, [highlightRuleId, local.rules, setHighlightRuleId])

  useEffect(() => {
    if (pendingWizardDraft) {
      openWizard(pendingWizardDraft, pendingWizardMode, false)
      setPendingWizardDraft(null)
    }
  }, [pendingWizardDraft, pendingWizardMode, setPendingWizardDraft])

  const selected = useMemo(
    () => local.rules.find(r => r.id === selectedId) ?? null,
    [local.rules, selectedId],
  )

  const apply = (pb: PlaybookV2) => {
    setLocal(pb)
    onCommand({ type: 'SET_PLAYBOOK_V2', enabled: pb.enabled, constants: pb.constants, rules: pb.rules })
  }

  const openWizard = (draft: RuleV2, mode: RuleCreationMode, editing: boolean) => {
    setWizardDraft(draft)
    setWizardMode(mode)
    setIsEditing(editing)
    setWizardOpen(true)
  }

  const openNewRuleWizard = () => {
    openWizard(defaultWizardRule(local.rules, pendingMetricId), 'wizard', false)
    if (pendingMetricId) setPendingMetricId(null)
  }

  const openEditWizard = (rule: RuleV2) => {
    openWizard({ ...rule }, 'wizard', true)
  }

  const handleWizardSave = (rule: RuleV2) => {
    if (isEditing) {
      apply({ ...local, rules: local.rules.map(r => (r.id === rule.id ? rule : r)) })
      setSelectedId(rule.id)
    } else {
      apply({ ...local, rules: [...local.rules, rule] })
      setSelectedId(rule.id)
    }
    setWizardOpen(false)
    setWizardDraft(null)
  }

  const addFromTemplate = (templateRule: RuleV2) => {
    const rule = { ...templateRule, id: nextRuleId(local.rules), priority: (local.rules.length + 1) * 10 }
    openWizard(rule, 'template', false)
  }

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(local, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'playbook_v2.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const importJson = (text: string) => {
    try {
      const parsed = JSON.parse(text) as PlaybookV2
      apply(parsed)
      setSelectedId(parsed.rules[0]?.id ?? null)
    } catch {
      alert('Invalid playbook JSON')
    }
  }

  const labelForConstant = (id: string) =>
    constantCatalog.find(c => c.id === id)?.plain_label ?? id

  const summarize = (when: RuleV2['when']) =>
    summarizeExpr(when, metricCatalog, constantCatalog, local.constants)

  return (
    <div className="p-3 space-y-4 pb-8">
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-xs text-text-secondary">
          <input
            type="checkbox"
            checked={local.enabled}
            onChange={e => apply({ ...local, enabled: e.target.checked })}
            className="checkbox-dark"
          />
          Playbook enabled
        </label>
        <select
          value={routingEngineVersion}
          onChange={e => onCommand({ type: 'SET_ROUTING_ENGINE_VERSION', version: e.target.value as 'v1' | 'v2' | 'shadow' })}
          className="input-dark text-xs"
        >
          <option value="v2">Engine v2 (playbook)</option>
          <option value="v1">Engine v1 (legacy)</option>
          <option value="shadow">Shadow (v2 log + v1 run)</option>
        </select>
        <SimButton onClick={() => onCommand({ type: 'RESET_PLAYBOOK_V2' })}>Reset default</SimButton>
        <SimButton onClick={exportJson}>Export</SimButton>
        <SimButton onClick={() => fileRef.current?.click()}>Import</SimButton>
        <input ref={fileRef} type="file" accept="application/json" className="hidden" onChange={e => {
          const f = e.target.files?.[0]
          if (f) f.text().then(importJson)
        }} />
      </div>

      <PanelSection title="Thresholds" count={Object.keys(local.constants).length}>
        <div className="p-2 space-y-2">
          {Object.entries(local.constants).map(([key, val]) => {
            const meta = constantCatalog.find(c => c.id === key)
            const usage = countConstantUsage(local.rules, key)
            return (
              <div key={key} className="space-y-0.5">
                <div className="flex gap-2 items-center text-xs">
                  <span className="text-text-primary w-32 truncate" title={key}>
                    {labelForConstant(key)}
                  </span>
                  <input
                    type="number"
                    step="any"
                    value={val}
                    onChange={e =>
                      apply({
                        ...local,
                        constants: { ...local.constants, [key]: parseFloat(e.target.value) || 0 },
                      })
                    }
                    className="input-dark flex-1"
                  />
                  {meta?.unit && <span className="text-[10px] text-text-secondary">{meta.unit}</span>}
                </div>
                {meta?.description && (
                  <p className="text-[10px] text-text-secondary pl-0.5">{meta.description}</p>
                )}
                {usage > 0 && (
                  <p className="text-[10px] text-accent/80">Used in {usage} rule{usage === 1 ? '' : 's'}</p>
                )}
              </div>
            )
          })}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              className="text-[10px] text-accent"
              onClick={() => setShowConstantBrowser(v => !v)}
            >
              {showConstantBrowser ? 'Hide threshold browser' : 'Browse all thresholds'}
            </button>
            <button
              type="button"
              className="text-[10px] text-text-secondary"
              onClick={() => navigate({ tab: 'rules', rulesSubTab: 'library', libraryView: 'thresholds' })}
            >
              Open in Library →
            </button>
          </div>
          {showConstantBrowser && (
            <ConstantBrowser
              catalog={constantCatalog}
              playbook={local}
              onAddConstant={(id, defaultValue) =>
                apply({ ...local, constants: { ...local.constants, [id]: defaultValue } })
              }
            />
          )}
        </div>
      </PanelSection>

      <PanelSection title="Rules" count={local.rules.length}>
        <div className="p-2 space-y-1 max-h-48 overflow-y-auto">
          {[...local.rules].sort((a, b) => a.priority - b.priority).map(rule => (
            <button
              key={rule.id}
              type="button"
              onClick={() => setSelectedId(rule.id)}
              className={`w-full text-left px-2 py-1.5 rounded text-xs ${
                selectedId === rule.id ? 'bg-accent/20 text-accent' : 'hover:bg-surface-base text-text-primary'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-text-secondary">P{rule.priority}</span>
                <span className="font-medium truncate">{rule.name}</span>
                <span className="ml-auto capitalize text-[10px] text-text-secondary">{rule.phase}</span>
                {!rule.enabled && <span className="text-[10px] text-text-secondary">off</span>}
              </div>
              <div className="text-[10px] text-text-secondary truncate mt-0.5">{summarize(rule.when)}</div>
            </button>
          ))}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={openNewRuleWizard} className="text-xs text-accent font-medium">
              + New rule
            </button>
            <button
              type="button"
              onClick={() => navigate({ tab: 'rules', rulesSubTab: 'library', libraryView: 'templates' })}
              className="text-xs text-text-secondary"
            >
              + From template
            </button>
          </div>
        </div>
      </PanelSection>

      {selected && (
        <div className="border border-border-default rounded-lg p-3 space-y-2 bg-surface-raised/30">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="text-sm font-medium text-text-primary">{selected.name}</div>
              <div className="text-[10px] text-text-secondary capitalize mt-0.5">
                {selected.phase} · Priority {selected.priority}
                {!selected.enabled && ' · Disabled'}
              </div>
            </div>
            <SimButton onClick={() => openEditWizard(selected)}>Edit rule</SimButton>
          </div>
          <div className="text-xs space-y-1 pt-1 border-t border-border-default/50">
            <div>
              <span className="text-text-secondary">When: </span>
              <span className="text-text-primary">{summarize(selected.when)}</span>
            </div>
            <div>
              <span className="text-text-secondary">Selection: </span>
              <span className="text-text-primary">
                {selectionCatalog.find(s => s.id === selected.selection)?.plain_label ?? selected.selection}
              </span>
            </div>
            <div>
              <span className="text-text-secondary">Action: </span>
              <span className="text-text-primary">
                {actionCatalog.find(a => a.id === selected.action.type)?.plain_label ?? selected.action.type}
              </span>
            </div>
          </div>
        </div>
      )}

      {ruleTemplates.length > 0 && local.rules.length === 0 && (
        <PanelSection title="Quick start templates" count={ruleTemplates.length}>
          <div className="p-2">
            <p className="text-[10px] text-text-secondary mb-2">Start from a preset, then customize in the wizard.</p>
            <div className="space-y-1">
              {ruleTemplates.slice(0, 3).map(t => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => addFromTemplate(t.rule)}
                  className="w-full text-left text-xs px-2 py-1.5 rounded hover:bg-surface-base border border-border-default"
                >
                  {t.name}
                </button>
              ))}
            </div>
          </div>
        </PanelSection>
      )}

      {wizardOpen && wizardDraft && (
        <RuleWizard
          initialDraft={wizardDraft}
          creationMode={wizardMode}
          metricCatalog={metricCatalog}
          constantCatalog={constantCatalog}
          actionCatalog={actionCatalog}
          selectionCatalog={selectionCatalog}
          playbookConstants={local.constants}
          onSave={handleWizardSave}
          onCancel={() => {
            setWizardOpen(false)
            setWizardDraft(null)
          }}
        />
      )}
    </div>
  )
}
