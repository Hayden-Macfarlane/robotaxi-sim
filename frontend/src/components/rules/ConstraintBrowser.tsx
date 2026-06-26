import { useMemo, useState } from 'react'
import type { MetricMeta, RulePhaseV2 } from '../../types/playbook'
import { useUiMode } from '../../contexts/UiModeContext'
import {
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  categoryLabel,
  metricCategoryId,
} from '../../lib/constraintCategories'
import { CatalogCard } from '../ui/CatalogCard'
import { FilterChips } from '../ui/FilterChips'
import { SimButton } from '../ui/SimButton'

const CATEGORY_OPTIONS = CATEGORY_ORDER.map(id => ({
  id,
  label: CATEGORY_LABELS[id] ?? id,
}))

const PHASE_OPTIONS = [
  { id: 'dispatch', label: 'Dispatch' },
  { id: 'reposition', label: 'Reposition' },
  { id: 'facility', label: 'Facility' },
]

interface Props {
  catalog: MetricMeta[]
  phaseFilter?: RulePhaseV2 | null
  onUseInCondition?: (metricId: string) => void
}

/** Searchable browse view for rule constraints (metrics). */
export function ConstraintBrowser({ catalog, phaseFilter: initialPhase, onUseInCondition }: Props) {
  const { uiMode, navigate } = useUiMode()
  const [query, setQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [phaseFilter, setPhaseFilter] = useState<string | null>(initialPhase ?? null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return catalog.filter(m => {
      if (categoryFilter && metricCategoryId(m) !== categoryFilter) return false
      if (phaseFilter && !(m.phases ?? []).includes(phaseFilter as RulePhaseV2)) return false
      if (!q) return true
      return (
        m.plain_label.toLowerCase().includes(q) ||
        m.industry_label.toLowerCase().includes(q) ||
        m.id.toLowerCase().includes(q) ||
        m.description.toLowerCase().includes(q) ||
        categoryLabel(metricCategoryId(m)).toLowerCase().includes(q)
      )
    })
  }, [catalog, query, categoryFilter, phaseFilter])

  return (
    <div className="space-y-3">
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Search by topic or name…"
        className="input-dark w-full text-xs"
      />
      <div className="space-y-2">
        <FilterChips options={CATEGORY_OPTIONS} active={categoryFilter} onChange={setCategoryFilter} />
        <FilterChips options={PHASE_OPTIONS} active={phaseFilter} onChange={setPhaseFilter} />
      </div>
      <p className="text-[10px] text-text-secondary">{filtered.length} checks</p>
      <div className="space-y-2 max-h-[28rem] overflow-y-auto">
        {filtered.map(m => {
          const label = uiMode === 'standard' ? m.plain_label : m.industry_label
          const badges = [
            categoryLabel(metricCategoryId(m)),
            ...(m.phases ?? []),
            ...(m.unit ? [m.unit] : []),
            ...(m.value_type !== 'float' ? [m.value_type] : []),
          ]
          const description =
            uiMode === 'standard' || !m.description
              ? m.description || undefined
              : `${m.description} (${m.id})`
          return (
            <CatalogCard
              key={m.id}
              title={label}
              description={description}
              badges={badges}
              action={
                onUseInCondition ? (
                  <SimButton
                    onClick={e => {
                      e.stopPropagation()
                      onUseInCondition(m.id)
                      navigate({ tab: 'rules', rulesSubTab: 'build' })
                    }}
                  >
                    Use
                  </SimButton>
                ) : undefined
              }
            />
          )
        })}
      </div>
    </div>
  )
}
