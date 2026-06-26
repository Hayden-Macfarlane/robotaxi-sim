import { useMemo, useState } from 'react'
import type { ConstantMeta, PlaybookV2 } from '../../types/playbook'
import { countConstantUsage } from '../../lib/playbookUtils'
import { useUiMode } from '../../contexts/UiModeContext'
import { CatalogCard } from '../ui/CatalogCard'
import { SimButton } from '../ui/SimButton'

interface Props {
  catalog: ConstantMeta[]
  playbook: PlaybookV2
  onAddConstant?: (id: string, defaultValue: number) => void
}

/** Searchable browse view for playbook thresholds (constants). */
export function ConstantBrowser({ catalog, playbook, onAddConstant }: Props) {
  const { uiMode } = useUiMode()
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return catalog
    return catalog.filter(
      c =>
        c.plain_label.toLowerCase().includes(q) ||
        c.industry_label.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q),
    )
  }, [catalog, query])

  return (
    <div className="space-y-3">
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Search thresholds…"
        className="input-dark w-full text-xs"
      />
      <p className="text-[10px] text-text-secondary">{filtered.length} thresholds</p>
      <div className="space-y-2 max-h-[28rem] overflow-y-auto">
        {filtered.map(c => {
          const label = uiMode === 'standard' ? c.plain_label : c.industry_label
          const inPlaybook = c.id in playbook.constants
          const usage = countConstantUsage(playbook.rules, c.id)
          const badges = [
            ...(c.unit ? [c.unit] : []),
            `default ${c.default}`,
            ...(inPlaybook ? ['in playbook'] : []),
            ...(usage > 0 ? [`${usage} rule${usage === 1 ? '' : 's'}`] : []),
          ]
          return (
            <CatalogCard
              key={c.id}
              title={label}
              description={c.description}
              badges={badges}
              action={
                onAddConstant && !inPlaybook ? (
                  <SimButton
                    onClick={e => {
                      e.stopPropagation()
                      onAddConstant(c.id, c.default)
                    }}
                  >
                    Add
                  </SimButton>
                ) : inPlaybook ? (
                  <span className="text-[10px] text-emerald-400">Added</span>
                ) : undefined
              }
            />
          )
        })}
      </div>
    </div>
  )
}
