import { useEffect, useState } from 'react'
import type { OperatorSetupSnap, SimCommand } from '../types/simulation'
import type { RoutingRule, RoutingRuleHit, RoutingRuleSet, RulePhase } from '../types/routing'
import { ACTION_LABELS, CONDITION_LABELS } from '../types/routing'
import { RuleEditor } from './RuleEditor'
import { PanelSection } from './ui/PanelSection'

const MODE_SUMMARY: Record<string, string> = {
  manual: 'Manual assignment — no auto-dispatch rules',
  closest_idle_or_repositioning: 'Auto-assign: closest idle or repositioning vehicle',
  closest_idle: 'Auto-assign: closest idle vehicle only',
}

interface Props {
  ruleSet: RoutingRuleSet
  ruleHits: RoutingRuleHit[]
  operatorSetup: OperatorSetupSnap
  onCommand: (cmd: SimCommand) => void
}

function summarizeConditions(rule: RoutingRule): string {
  if (rule.conditions.length === 0) return 'No conditions'
  return rule.conditions
    .map(c => {
      const label = CONDITION_LABELS[c.type] ?? c.type
      if (c.type === 'active_event') return `${label}${c.zone ? ` (${c.zone})` : ''}`
      return `${label} ${c.operator} ${c.value}`
    })
    .join(' · ')
}

function nextRuleId(rules: RoutingRule[]): string {
  const nums = rules
    .map(r => parseInt(r.id.replace(/\D/g, ''), 10))
    .filter(n => !Number.isNaN(n))
  const n = (nums.length ? Math.max(...nums) : 0) + 1
  return `rule-${String(n).padStart(3, '0')}`
}

/** Operator routing rule builder. */
export function RoutingPanel({ ruleSet, ruleHits, operatorSetup, onCommand }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [localRules, setLocalRules] = useState<RoutingRule[]>(ruleSet.rules)
  const advanced = operatorSetup.advanced_automation_enabled
  const mode = operatorSetup.dispatch_assignment_mode

  useEffect(() => {
    setLocalRules(ruleSet.rules)
  }, [ruleSet.rules])

  const sorted = [...localRules].sort((a, b) => a.priority - b.priority)

  const applyRules = (rules: RoutingRule[], routingEnabled = ruleSet.routing_enabled) => {
    setLocalRules(rules)
    onCommand({ type: 'SET_ROUTING_RULES', rules, routing_enabled: routingEnabled })
  }

  const moveRule = (id: string, dir: -1 | 1) => {
    const idx = sorted.findIndex(r => r.id === id)
    const swapIdx = idx + dir
    if (idx < 0 || swapIdx < 0 || swapIdx >= sorted.length) return
    const reordered = [...sorted]
    const a = reordered[idx]
    const b = reordered[swapIdx]
    reordered[idx] = { ...b, priority: a.priority }
    reordered[swapIdx] = { ...a, priority: b.priority }
    applyRules(reordered)
  }

  const addRule = (phase: RulePhase) => {
    const priority = sorted.length ? Math.max(...sorted.map(r => r.priority)) + 10 : 10
    const rule: RoutingRule = {
      id: nextRuleId(localRules),
      name: phase === 'dispatch' ? 'New dispatch rule' : 'New reposition rule',
      enabled: true,
      priority,
      phase,
      conditions: phase === 'dispatch'
        ? [{ type: 'pending_trips', operator: 'gte', value: 1 }]
        : [{ type: 'idle_minutes', operator: 'gte', value: 15 }],
      action: phase === 'dispatch'
        ? { type: 'assign_nearest_eligible' }
        : { type: 'reposition_to_best_deficit' },
    }
    applyRules([...localRules, rule])
    setEditingId(rule.id)
  }

  const updateRule = (updated: RoutingRule) => {
    applyRules(localRules.map(r => (r.id === updated.id ? updated : r)))
  }

  const toggleEnabled = (id: string) => {
    applyRules(localRules.map(r => (r.id === id ? { ...r, enabled: !r.enabled } : r)))
  }

  const deleteRule = (id: string) => {
    applyRules(localRules.filter(r => r.id !== id))
    if (editingId === id) setEditingId(null)
  }

  return (
    <div className="p-3 pb-4 space-y-4 overflow-y-auto h-full">
      {!advanced && mode && (
        <div className="px-3 py-2 text-xs text-text-secondary bg-surface-raised/50 border border-border-default rounded-lg">
          <span className="text-text-primary font-medium">Active policy: </span>
          {MODE_SUMMARY[mode] ?? mode}
          <p className="mt-1 italic">Enable advanced automation in the Auto tab to edit routing rules.</p>
        </div>
      )}

      <div className={advanced ? '' : 'opacity-40 pointer-events-none select-none'}>
      <PanelSection title="Routing strategy">
        <div className="p-3 space-y-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={ruleSet.routing_enabled}
              onChange={e => applyRules(localRules, e.target.checked)}
              className="checkbox-dark"
            />
            <span className="text-sm text-text-primary">Routing rules enabled</span>
          </label>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => addRule('dispatch')}
              className="px-2 py-1 text-xs rounded border border-border-default bg-surface-raised hover:bg-surface-base"
            >
              + Dispatch rule
            </button>
            <button
              type="button"
              onClick={() => addRule('reposition')}
              className="px-2 py-1 text-xs rounded border border-border-default bg-surface-raised hover:bg-surface-base"
            >
              + Reposition rule
            </button>
            <button
              type="button"
              onClick={() => onCommand({ type: 'RESET_ROUTING_RULES' })}
              className="px-2 py-1 text-xs rounded border border-border-default text-text-secondary hover:text-text-primary"
            >
              Reset to defaults
            </button>
          </div>

          <div className="space-y-2">
            {sorted.map((rule, idx) => (
              <div key={rule.id} className="rounded-lg border border-border-default bg-surface-raised/50">
                {editingId === rule.id ? (
                  <div className="p-2">
                    <RuleEditor
                      rule={rule}
                      onChange={updateRule}
                      onClose={() => setEditingId(null)}
                    />
                  </div>
                ) : (
                  <div className="p-2 space-y-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-text-secondary">{idx + 1}</span>
                          <span className="text-xs uppercase text-accent">{rule.phase}</span>
                          {!rule.enabled && (
                            <span className="text-[10px] text-text-secondary">(off)</span>
                          )}
                        </div>
                        <div className="text-sm font-medium text-text-primary">{rule.name}</div>
                        <div className="text-[10px] text-text-secondary">{summarizeConditions(rule)}</div>
                        <div className="text-[10px] text-emerald-400/80">→ {ACTION_LABELS[rule.action.type]}</div>
                      </div>
                      <div className="flex flex-col gap-0.5 flex-shrink-0">
                        <button type="button" onClick={() => moveRule(rule.id, -1)} className="text-[10px] text-text-secondary hover:text-text-primary px-1">↑</button>
                        <button type="button" onClick={() => moveRule(rule.id, 1)} className="text-[10px] text-text-secondary hover:text-text-primary px-1">↓</button>
                        <button type="button" onClick={() => setEditingId(rule.id)} className="text-[10px] text-accent px-1">Edit</button>
                        <button type="button" onClick={() => toggleEnabled(rule.id)} className="text-[10px] text-text-secondary px-1">{rule.enabled ? 'Off' : 'On'}</button>
                        <button type="button" onClick={() => deleteRule(rule.id)} className="text-[10px] text-red-400 px-1">Del</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </PanelSection>
      </div>

      {advanced && ruleHits.length > 0 && (
        <PanelSection title="Recent rule hits" count={ruleHits.length}>
          <div className="p-2 max-h-32 overflow-y-auto space-y-1">
            {[...ruleHits].reverse().slice(0, 8).map((hit, i) => (
              <div key={`${hit.rule_id}-${hit.timestamp_h}-${i}`} className="text-[10px] border-b border-border-default/40 pb-1">
                <span className="text-accent">{hit.rule_name}</span>
                <span className="text-text-secondary"> · {hit.phase} · {hit.subject_id}</span>
                {hit.detail && <span className="text-text-secondary"> — {hit.detail}</span>}
              </div>
            ))}
          </div>
        </PanelSection>
      )}
    </div>
  )
}
