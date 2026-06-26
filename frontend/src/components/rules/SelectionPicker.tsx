import type { MetricMeta, RulePhaseV2, SelectionMeta, SelectionMode } from '../../types/playbook'
import { useUiMode } from '../../contexts/UiModeContext'
import { MetricPicker } from '../MetricPicker'
import { SearchableSelect, type SearchableOption } from '../ui/SearchableSelect'

interface Props {
  catalog: SelectionMeta[]
  metricCatalog: MetricMeta[]
  phase: RulePhaseV2
  selection: SelectionMode
  selectionMetric?: { id: string; params?: Record<string, string | number | boolean> } | null
  selectionParams?: Record<string, string | number | boolean>
  onChange: (patch: {
    selection: SelectionMode
    selection_metric?: { id: string; params?: Record<string, string | number | boolean> } | null
    selection_params?: Record<string, string | number | boolean>
  }) => void
}

/** Selection mode picker with params and optional metric. */
export function SelectionPicker({
  catalog,
  metricCatalog,
  phase,
  selection,
  selectionMetric,
  selectionParams = {},
  onChange,
}: Props) {
  const { uiMode } = useUiMode()
  const meta = catalog.find(s => s.id === selection)

  const options: SearchableOption[] = catalog
    .filter(s => !s.phases?.length || s.phases.includes(phase))
    .map(s => ({
      value: s.id,
      label: uiMode === 'standard' ? s.plain_label : s.industry_label,
      description: s.description,
    }))

  return (
    <div className="space-y-2">
      <SearchableSelect
        options={options}
        value={selection}
        onChange={id => onChange({ selection: id as SelectionMode, selection_params: {} })}
        placeholder="Search selection modes…"
      />
      {meta?.description && <p className="text-[10px] text-text-secondary">{meta.description}</p>}
      {meta?.requires_metric && (
        <div>
          <span className="text-[10px] text-text-secondary">Rank by metric</span>
          <MetricPicker
            catalog={metricCatalog}
            value={selectionMetric ?? { id: 'vehicle.idle_minutes' }}
            onChange={ref => onChange({ selection, selection_metric: ref, selection_params: selectionParams })}
          />
        </div>
      )}
      {meta?.param_schema &&
        Object.entries(meta.param_schema).map(([key, field]) => (
          <label key={key} className="block text-[10px]">
            <span className="text-text-secondary">{field.plain_label}</span>
            <input
              type="number"
              step="any"
              value={String(selectionParams[key] ?? field.default ?? '')}
              onChange={e =>
                onChange({
                  selection,
                  selection_metric: selectionMetric,
                  selection_params: {
                    ...selectionParams,
                    [key]: parseFloat(e.target.value) || 0,
                  },
                })
              }
              className="input-dark w-full mt-0.5 text-xs"
            />
          </label>
        ))}
    </div>
  )
}
