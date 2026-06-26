import type { ActionMeta, ActionSpec, RulePhaseV2 } from '../../types/playbook'
import { useUiMode } from '../../contexts/UiModeContext'
import { SearchableSelect, type SearchableOption } from '../ui/SearchableSelect'

interface Props {
  catalog: ActionMeta[]
  phase: RulePhaseV2
  value: ActionSpec
  onChange: (action: ActionSpec) => void
}

/** Map stored action to catalog row (legacy assign_vehicle → plain-English aliases). */
function catalogActionId(action: ActionSpec): string {
  if (action.type === 'assign_vehicle') {
    const preempt = action.params?.preempt_reposition ?? true
    return preempt ? 'assign_nearest_available' : 'assign_nearest_idle'
  }
  return action.type
}

/** Build stored action from catalog selection. */
function actionFromCatalogId(id: string): ActionSpec {
  if (id === 'assign_nearest_idle') {
    return { type: 'assign_nearest_idle' }
  }
  if (id === 'assign_nearest_available') {
    return { type: 'assign_nearest_available' }
  }
  return { type: id as ActionSpec['type'], params: {} }
}

/** Action type picker with param forms from action catalog. */
export function ActionPicker({ catalog, phase, value, onChange }: Props) {
  const { uiMode } = useUiMode()

  const phaseActions = catalog.filter(a => !a.phases?.length || a.phases.includes(phase))
  const selectedId = catalogActionId(value)
  const meta = phaseActions.find(a => a.id === selectedId)

  const options: SearchableOption[] = phaseActions.map(a => ({
    value: a.id,
    label: uiMode === 'standard' ? a.plain_label : a.industry_label,
    description: a.description,
  }))

  return (
    <div className="space-y-2">
      {phase === 'dispatch' && (
        <p className="text-[11px] text-text-secondary leading-snug">
          This rule matches waiting riders to cars.{' '}
          <span className="text-text-primary">Nearest available</span> includes cars that are repositioning but can be
          redirected to the rider.
        </p>
      )}
      <SearchableSelect
        options={options}
        value={selectedId}
        onChange={id => onChange(actionFromCatalogId(id))}
        placeholder="Search actions…"
      />
      {meta?.description && <p className="text-[10px] text-text-secondary">{meta.description}</p>}
      {meta?.param_schema &&
        Object.entries(meta.param_schema).map(([key, field]) => (
          <label key={key} className="block text-[10px]">
            <span className="text-text-secondary">{field.plain_label}</span>
            {field.description && <span className="text-text-secondary/70"> — {field.description}</span>}
            {field.type === 'bool' ? (
              <input
                type="checkbox"
                checked={Boolean(value.params?.[key] ?? field.default ?? false)}
                onChange={e =>
                  onChange({
                    ...value,
                    params: { ...value.params, [key]: e.target.checked },
                  })
                }
                className="checkbox-dark ml-2"
              />
            ) : (
              <input
                type={field.type === 'string' ? 'text' : 'number'}
                step="any"
                value={String(value.params?.[key] ?? field.default ?? '')}
                onChange={e => {
                  const raw = e.target.value
                  const parsed = field.type === 'string' ? raw : parseFloat(raw)
                  onChange({
                    ...value,
                    params: {
                      ...value.params,
                      [key]: field.type === 'string' ? raw : (Number.isFinite(parsed as number) ? parsed : 0),
                    },
                  })
                }}
                className="input-dark w-full mt-0.5 text-xs"
              />
            )}
          </label>
        ))}
    </div>
  )
}
