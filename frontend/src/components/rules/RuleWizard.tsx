import { useState } from 'react'
import { createPortal } from 'react-dom'
import type {
  ActionMeta,
  ConstantMeta,
  MetricMeta,
  RuleCreationMode,
  RuleV2,
  SelectionMeta,
} from '../../types/playbook'
import { summarizeExpr } from '../../lib/playbookUtils'
import { ActionPicker } from './ActionPicker'
import { ConditionBuilder, normalizeWhen } from './ConditionBuilder'
import { SelectionPicker } from './SelectionPicker'
import { SimButton } from '../ui/SimButton'

const STEPS = ['Phase', 'When', 'Who', 'Then', 'Review'] as const
type StepId = (typeof STEPS)[number]

const PHASE_HELP: Record<RuleV2['phase'], string> = {
  dispatch: 'Runs when trips need vehicles — assigns riders to cars.',
  reposition: 'Runs for idle or rebalancing vehicles — moves fleet around.',
  facility: 'Runs for vehicles at depots — release or send to facility.',
}

interface Props {
  /** Pre-filled rule when editing or cloning from template/intent (future). */
  initialDraft: RuleV2
  creationMode?: RuleCreationMode
  metricCatalog: MetricMeta[]
  constantCatalog: ConstantMeta[]
  actionCatalog: ActionMeta[]
  selectionCatalog: SelectionMeta[]
  playbookConstants: Record<string, number>
  onSave: (rule: RuleV2) => void
  onCancel: () => void
}

/** Four-step rule builder wizard with plain-English review. */
export function RuleWizard({
  initialDraft,
  creationMode = 'wizard',
  metricCatalog,
  constantCatalog,
  actionCatalog,
  selectionCatalog,
  playbookConstants,
  onSave,
  onCancel,
}: Props) {
  const [step, setStep] = useState<number>(0)
  const [draft, setDraft] = useState<RuleV2>(initialDraft)

  const phaseMetrics = metricCatalog.filter(
    m => !m.phases?.length || m.phases.includes(draft.phase),
  )
  const stepId = STEPS[step] as StepId

  const selectionMeta = selectionCatalog.find(s => s.id === draft.selection)
  const actionMeta = actionCatalog.find(a => a.id === draft.action.type)

  const canNext = () => {
    if (stepId === 'Phase') return draft.name.trim().length > 0
    if (stepId === 'When') return true
    if (stepId === 'Who') return true
    if (stepId === 'Then') return true
    return true
  }

  const handleSave = () => {
    onSave(draft)
  }

  return createPortal(
    <>
      <button
        type="button"
        className="fixed inset-0 z-[2000] bg-black/50"
        aria-label="Close rule wizard"
        onClick={onCancel}
      />
      <div className="fixed inset-y-0 right-0 z-[2001] w-full max-w-md bg-surface-base border-l border-border-default flex flex-col shadow-xl">
        <div className="px-4 py-3 border-b border-border-default">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary">
              {creationMode === 'template' ? 'Edit template rule' : 'New rule'}
            </h2>
            <button type="button" onClick={onCancel} className="text-xs text-text-secondary hover:text-text-primary">
              Cancel
            </button>
          </div>
          <div className="flex gap-1 mt-2">
            {STEPS.map((s, i) => (
              <div
                key={s}
                className={`flex-1 h-1 rounded ${i <= step ? 'bg-accent' : 'bg-border-default'}`}
                title={s}
              />
            ))}
          </div>
          <p className="text-[10px] text-text-secondary mt-1.5">
            Step {step + 1} of {STEPS.length}: {stepId}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {stepId === 'Phase' && (
            <>
              <label className="block text-xs">
                <span className="text-text-secondary">Rule name</span>
                <input
                  value={draft.name}
                  onChange={e => setDraft({ ...draft, name: e.target.value })}
                  className="input-dark w-full mt-1 text-sm"
                  placeholder="e.g. Relocate if idle too long"
                />
              </label>
              <label className="block text-xs">
                <span className="text-text-secondary">Phase</span>
                <select
                  value={draft.phase}
                  onChange={e => {
                    const phase = e.target.value as RuleV2['phase']
                    const patch: Partial<RuleV2> = { phase }
                    if (phase === 'dispatch') {
                      patch.when = {
                        op: 'compare',
                        metric: { id: 'zone.pending_demand' },
                        operator: 'gte',
                        value: 1,
                      }
                      patch.action = { type: 'assign_nearest_available' }
                    } else if (phase === 'reposition') {
                      patch.when = {
                        op: 'compare',
                        metric: { id: 'vehicle.idle_minutes' },
                        operator: 'gte',
                        value: 15,
                      }
                      patch.action = { type: 'reposition_to_best_deficit' }
                    }
                    setDraft({ ...draft, ...patch })
                  }}
                  className="input-dark w-full mt-1"
                >
                  <option value="dispatch">Dispatch</option>
                  <option value="reposition">Reposition</option>
                  <option value="facility">Facility</option>
                </select>
                <p className="text-[10px] text-text-secondary mt-1">{PHASE_HELP[draft.phase]}</p>
              </label>
              <label className="block text-xs">
                <span className="text-text-secondary">Priority (lower runs first)</span>
                <input
                  type="number"
                  value={draft.priority}
                  onChange={e => setDraft({ ...draft, priority: parseInt(e.target.value, 10) || 0 })}
                  className="input-dark w-full mt-1"
                />
              </label>
              <label className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={draft.enabled}
                  onChange={e => setDraft({ ...draft, enabled: e.target.checked })}
                  className="checkbox-dark"
                />
                Rule enabled
              </label>
            </>
          )}

          {stepId === 'When' && (
            <>
              <p className="text-xs text-text-secondary">
                Define when this rule should fire. Pick what to check — grouped by topic, not technical names.
                {phaseMetrics.length < metricCatalog.length && (
                  <> {phaseMetrics.length} checks are especially relevant for {draft.phase}.</>
                )}
              </p>
              <ConditionBuilder
                node={normalizeWhen(draft.when)}
                catalog={metricCatalog}
                constantCatalog={constantCatalog}
                playbookConstants={playbookConstants}
                phaseHint={draft.phase}
                dropdownZIndex={2100}
                onChange={when => setDraft({ ...draft, when })}
              />
            </>
          )}

          {stepId === 'Who' && (
            <>
              <p className="text-xs text-text-secondary">
                If multiple vehicles or trips match, how should the engine pick which ones to act on?
              </p>
              <SelectionPicker
                catalog={selectionCatalog}
                metricCatalog={metricCatalog}
                phase={draft.phase}
                selection={draft.selection}
                selectionMetric={draft.selection_metric}
                selectionParams={draft.selection_params}
                onChange={patch => setDraft({ ...draft, ...patch })}
              />
            </>
          )}

          {stepId === 'Then' && (
            <>
              <p className="text-xs text-text-secondary">What should happen when the conditions match?</p>
              {draft.phase === 'dispatch' && (
                <p className="text-[11px] text-text-secondary leading-snug">
                  Suggested pairing: when waiting riders in zone ≥ 1 → assign nearest available car.
                </p>
              )}
              <ActionPicker
                catalog={actionCatalog}
                phase={draft.phase}
                value={draft.action}
                onChange={action => setDraft({ ...draft, action })}
              />
            </>
          )}

          {stepId === 'Review' && (
            <div className="space-y-3 text-xs border border-border-default rounded-lg p-3 bg-surface-raised/30">
              <div>
                <span className="text-text-secondary">Name</span>
                <div className="font-medium text-text-primary">{draft.name}</div>
              </div>
              <div>
                <span className="text-text-secondary">Phase</span>
                <div className="capitalize">{draft.phase} · Priority {draft.priority}</div>
              </div>
              <div>
                <span className="text-text-secondary">When</span>
                <div className="text-text-primary mt-0.5">
                  {summarizeExpr(draft.when, metricCatalog, constantCatalog, playbookConstants)}
                </div>
              </div>
              <div>
                <span className="text-text-secondary">Who</span>
                <div>{selectionMeta?.plain_label ?? draft.selection}</div>
                {selectionMeta?.description && (
                  <div className="text-[10px] text-text-secondary">{selectionMeta.description}</div>
                )}
              </div>
              <div>
                <span className="text-text-secondary">Then</span>
                <div>{actionMeta?.plain_label ?? draft.action.type}</div>
                {actionMeta?.description && (
                  <div className="text-[10px] text-text-secondary">{actionMeta.description}</div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="px-4 py-3 border-t border-border-default flex gap-2 justify-between">
          <SimButton
            onClick={() => (step > 0 ? setStep(step - 1) : onCancel())}
          >
            {step > 0 ? 'Back' : 'Cancel'}
          </SimButton>
          {step < STEPS.length - 1 ? (
            <SimButton variant="primary" onClick={() => canNext() && setStep(step + 1)} disabled={!canNext()}>
              Next
            </SimButton>
          ) : (
            <SimButton variant="primary" onClick={handleSave}>
              Save rule
            </SimButton>
          )}
        </div>
      </div>
    </>,
    document.body,
  )
}

/** Default blank rule for wizard creation. */
export function defaultWizardRule(
  existingRules: RuleV2[],
  pendingMetricId: string | null,
  phase: RuleV2['phase'] = 'reposition',
): RuleV2 {
  let n = existingRules.length + 1
  while (existingRules.some(r => r.id === `rule-${n}`)) n += 1
  if (phase === 'dispatch') {
    return {
      id: `rule-${n}`,
      name: 'Pick up waiting riders',
      enabled: true,
      priority: (existingRules.length + 1) * 10,
      phase: 'dispatch',
      when: {
        op: 'compare',
        metric: { id: pendingMetricId ?? 'zone.pending_demand' },
        operator: 'gte',
        value: 1,
      },
      selection: 'all_matching',
      action: { type: 'assign_nearest_available' },
    }
  }
  return {
    id: `rule-${n}`,
    name: 'New rule',
    enabled: true,
    priority: (existingRules.length + 1) * 10,
    phase: 'reposition',
    when: {
      op: 'compare',
      metric: { id: pendingMetricId ?? 'vehicle.idle_minutes' },
      operator: 'gte',
      value: 15,
    },
    selection: 'all_matching',
    action: { type: 'reposition_to_best_deficit' },
  }
}
