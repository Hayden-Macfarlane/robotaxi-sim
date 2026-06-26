import { useMemo } from 'react'
import type { MetricMeta, MetricRef, RulePhaseV2 } from '../types/playbook'
import {
  categoryLabel,
  metricCategoryId,
  metricUseHint,
  sortMetricsForPicker,
} from '../lib/constraintCategories'
import { SearchableSelect, type SearchableOption } from './ui/SearchableSelect'

interface Props {
  catalog: MetricMeta[]
  value: MetricRef
  onChange: (ref: MetricRef) => void
  /** When set, metrics for this phase sort first — all metrics remain visible. */
  phaseHint?: RulePhaseV2 | null
  dropdownZIndex?: number
}

function humanizeMetricId(id: string): string {
  const part = id.split('.').pop() ?? id
  return part.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

/** Searchable metric picker grouped by plain-English category. */
export function MetricPicker({ catalog, value, onChange, phaseHint, dropdownZIndex }: Props) {
  const options: SearchableOption[] = useMemo(() => {
    return sortMetricsForPicker(catalog, phaseHint).map(m => {
      const phaseOk = !phaseHint || !m.phases?.length || m.phases.includes(phaseHint)
      return {
        value: m.id,
        label: m.plain_label || humanizeMetricId(m.id),
        group: categoryLabel(metricCategoryId(m)),
        description: m.description || undefined,
        meta: phaseOk ? m.unit : `${m.unit ? m.unit + ' · ' : ''}other phases`,
      }
    })
  }, [catalog, phaseHint])

  const meta = catalog.find(m => m.id === value.id)
  const paramKeys = meta?.param_schema ? Object.keys(meta.param_schema) : []
  const displayLabel = meta?.plain_label || humanizeMetricId(value.id)

  if (catalog.length === 0) {
    return (
      <div className="space-y-1">
        <div className="input-dark w-full text-xs text-text-secondary px-3 py-2">
          Loading constraints…
        </div>
        <p className="text-[10px] text-text-secondary">
          Waiting for metric catalog from simulation. Try again once connected.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <label className="text-[10px] text-text-secondary">What should we check?</label>
      <SearchableSelect
        options={options}
        value={value.id}
        onChange={id => onChange({ id, params: {} })}
        placeholder="Search by topic…"
        dropdownZIndex={dropdownZIndex}
        emptyMessage={`No matches — ${catalog.length} available, try another search`}
      />
      {!meta && value.id && (
        <p className="text-[10px] text-amber-400">{displayLabel} (loading label…)</p>
      )}
      {meta && (
        <>
          <p className="text-[10px] text-text-secondary italic">{metricUseHint(meta)}</p>
          {meta.description && meta.description !== metricUseHint(meta) && (
            <p className="text-[10px] text-text-secondary">{meta.description}</p>
          )}
        </>
      )}
      {paramKeys.map(key => (
        <label key={key} className="flex items-center gap-2 text-[10px]">
          <span className="text-text-secondary w-20">{key}</span>
          <input
            type="text"
            value={String(value.params?.[key] ?? '')}
            onChange={e => {
              const raw = e.target.value
              const num = parseFloat(raw)
              onChange({
                id: value.id,
                params: { ...value.params, [key]: Number.isFinite(num) && raw !== '' ? num : raw },
              })
            }}
            className="input-dark flex-1"
          />
        </label>
      ))}
    </div>
  )
}
