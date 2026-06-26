import { useMemo, useState } from 'react'
import type { MetricMeta, RuleHitV2 } from '../../types/playbook'
import { useUiMode } from '../../contexts/UiModeContext'
import { FilterChips } from '../ui/FilterChips'
import { PanelSection } from '../ui/PanelSection'

const PHASE_OPTIONS = [
  { id: 'dispatch', label: 'Dispatch' },
  { id: 'reposition', label: 'Reposition' },
  { id: 'facility', label: 'Facility' },
]

interface Props {
  ruleHits: RuleHitV2[]
  metricCatalog?: MetricMeta[]
  onHighlightVehicle?: (vehicleId: string | null) => void
  onEditRule?: (ruleId: string) => void
}

/** Unified rule-hit feed with filters and expandable detail. */
export function RulesMonitorPanel({
  ruleHits,
  metricCatalog = [],
  onHighlightVehicle,
  onEditRule,
}: Props) {
  const { navigate, setHighlightRuleId } = useUiMode()
  const [phaseFilter, setPhaseFilter] = useState<string | null>(null)
  const [expandedKey, setExpandedKey] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const hits = [...ruleHits].reverse()
    if (!phaseFilter) return hits
    return hits.filter(h => h.phase === phaseFilter)
  }, [ruleHits, phaseFilter])

  return (
    <div className="p-3 space-y-3 pb-8">
      <p className="text-[10px] text-text-secondary">
        Live feed of rule evaluations. Dispatch hits also appear on trip cards in Live → Orders.
      </p>
      <FilterChips options={PHASE_OPTIONS} active={phaseFilter} onChange={setPhaseFilter} />
      <PanelSection title="Rule hits" count={filtered.length}>
        <div className="p-2 max-h-[32rem] overflow-y-auto space-y-1">
          {filtered.length === 0 && (
            <p className="text-xs text-text-secondary py-4 text-center">No rule hits yet. Play the sim to see activity.</p>
          )}
          {filtered.map((h, i) => {
            const key = `${h.rule_id}-${h.timestamp_h}-${h.subject_id}-${i}`
            const expanded = expandedKey === key
            return (
              <div
                key={key}
                className={`rounded border text-[10px] ${
                  h.matched ? 'border-emerald-900/50 bg-emerald-950/20' : 'border-border-default bg-surface-base/50'
                }`}
              >
                <button
                  type="button"
                  onClick={() => setExpandedKey(expanded ? null : key)}
                  className="w-full text-left px-2 py-1.5"
                >
                  <div className="flex items-center gap-2">
                    <span className={`font-medium ${h.matched ? 'text-emerald-300' : 'text-text-secondary'}`}>
                      {h.rule_name}
                    </span>
                    <span className="text-text-secondary capitalize">{h.phase}</span>
                    {h.shadow_only && <span className="text-amber-400">shadow</span>}
                  </div>
                  <div className="text-text-secondary mt-0.5">
                    {h.subject_id} · {h.detail || h.action}
                  </div>
                </button>
                {expanded && (
                  <div className="px-2 pb-2 space-y-1 border-t border-border-default/50 pt-1">
                    {h.selection_reason && (
                      <div className="text-text-secondary">Selection: {h.selection_reason}</div>
                    )}
                    {h.metric_values && Object.keys(h.metric_values).length > 0 && (
                      <div className="text-text-secondary space-y-0.5">
                        {Object.entries(h.metric_values).map(([k, v]) => {
                          const label = metricCatalog.find(m => m.id === k)?.plain_label ?? k
                          return (
                            <div key={k}>{label}: {String(v)}</div>
                          )
                        })}
                      </div>
                    )}
                    {h.destination_search && Object.keys(h.destination_search).length > 0 && (
                      <div className="text-text-secondary">
                        Destination: {JSON.stringify(h.destination_search)}
                      </div>
                    )}
                    <div className="flex gap-2 pt-1">
                      <button
                        type="button"
                        className="text-accent hover:underline"
                        onClick={() => {
                          setHighlightRuleId(h.rule_id)
                          onEditRule?.(h.rule_id)
                          navigate({ tab: 'rules', rulesSubTab: 'build' })
                        }}
                      >
                        Edit rule
                      </button>
                      {(h.phase === 'reposition' || h.phase === 'facility') && h.subject_id.startsWith('v-') && (
                        <button
                          type="button"
                          className="text-accent hover:underline"
                          onClick={() => {
                            onHighlightVehicle?.(h.subject_id)
                            navigate({ tab: 'live', liveSubTab: 'fleet' })
                          }}
                        >
                          View vehicle
                        </button>
                      )}
                      {h.phase === 'dispatch' && (
                        <button
                          type="button"
                          className="text-accent hover:underline"
                          onClick={() => navigate({ tab: 'live', liveSubTab: 'orders' })}
                        >
                          View trips
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </PanelSection>
    </div>
  )
}
