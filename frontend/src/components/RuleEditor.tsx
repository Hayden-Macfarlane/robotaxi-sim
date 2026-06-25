import type {
  ActionType,
  CompareOp,
  ConditionType,
  RoutingAction,
  RoutingCondition,
  RoutingRule,
} from '../types/routing'
import {
  ACTION_LABELS,
  COMPARE_LABELS,
  CONDITION_LABELS,
  ZONES,
} from '../types/routing'

interface Props {
  rule: RoutingRule
  onChange: (rule: RoutingRule) => void
  onClose: () => void
}

const CONDITION_TYPES: ConditionType[] = [
  'pending_trips',
  'trip_wait_minutes',
  'zone_deficit',
  'zone_surplus',
  'idle_minutes',
  'forecast_rising',
  'active_event',
  'time_of_day',
]

const DISPATCH_ACTIONS: ActionType[] = ['assign_nearest_eligible', 'assign_prefer_zone', 'hold']
const REPOSITION_ACTIONS: ActionType[] = [
  'reposition_to_best_deficit',
  'reposition_to_zone',
  'send_to_depot',
  'hold',
]

/** Inline editor for one routing rule's conditions and action. */
export function RuleEditor({ rule, onChange, onClose }: Props) {
  const actions = rule.phase === 'dispatch' ? DISPATCH_ACTIONS : REPOSITION_ACTIONS

  const updateCondition = (index: number, patch: Partial<RoutingCondition>) => {
    const conditions = rule.conditions.map((c, i) => (i === index ? { ...c, ...patch } : c))
    onChange({ ...rule, conditions })
  }

  const addCondition = () => {
    const base: RoutingCondition =
      rule.phase === 'dispatch'
        ? { type: 'pending_trips', operator: 'gte', value: 1 }
        : { type: 'idle_minutes', operator: 'gte', value: 15 }
    onChange({ ...rule, conditions: [...rule.conditions, base] })
  }

  const removeCondition = (index: number) => {
    onChange({ ...rule, conditions: rule.conditions.filter((_, i) => i !== index) })
  }

  const updateAction = (patch: Partial<RoutingAction>) => {
    onChange({ ...rule, action: { ...rule.action, ...patch } })
  }

  return (
    <div className="border border-accent/40 rounded-lg p-3 space-y-3 bg-surface-base/40">
      <div className="flex items-center justify-between gap-2">
        <input
          value={rule.name}
          onChange={e => onChange({ ...rule, name: e.target.value })}
          className="input-dark flex-1 text-sm font-medium"
        />
        <button type="button" onClick={onClose} className="text-xs text-text-secondary hover:text-text-primary">
          Done
        </button>
      </div>

      <div className="space-y-2">
        <span className="text-xs text-text-secondary uppercase tracking-wide">When (all must match)</span>
        {rule.conditions.map((cond, i) => (
          <div key={i} className="flex flex-wrap gap-1 items-center">
            <select
              value={cond.type}
              onChange={e => updateCondition(i, { type: e.target.value as ConditionType })}
              className="input-dark text-xs flex-1 min-w-[8rem]"
            >
              {CONDITION_TYPES.filter(t =>
                rule.phase === 'dispatch'
                  ? ['pending_trips', 'trip_wait_minutes', 'zone_deficit', 'active_event', 'time_of_day'].includes(t)
                  : true,
              ).map(t => (
                <option key={t} value={t}>{CONDITION_LABELS[t]}</option>
              ))}
            </select>
            {cond.type !== 'active_event' && (
              <>
                <select
                  value={cond.operator}
                  onChange={e => updateCondition(i, { operator: e.target.value as CompareOp })}
                  className="input-dark text-xs w-14"
                >
                  {Object.entries(COMPARE_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
                <input
                  type="number"
                  step="0.1"
                  value={cond.value}
                  onChange={e => updateCondition(i, { value: parseFloat(e.target.value) || 0 })}
                  className="input-dark text-xs w-16"
                />
              </>
            )}
            {['zone_deficit', 'zone_surplus', 'pending_trips', 'forecast_rising', 'active_event'].includes(cond.type) && (
              <select
                value={cond.zone ?? ''}
                onChange={e => updateCondition(i, { zone: e.target.value || null })}
                className="input-dark text-xs min-w-[6rem]"
              >
                <option value="">Vehicle/trip zone</option>
                {ZONES.map(z => <option key={z} value={z}>{z}</option>)}
              </select>
            )}
            <button type="button" onClick={() => removeCondition(i)} className="text-xs text-red-400 px-1">×</button>
          </div>
        ))}
        <button type="button" onClick={addCondition} className="text-xs text-accent hover:underline">
          + Add condition
        </button>
      </div>

      <div className="space-y-1">
        <span className="text-xs text-text-secondary uppercase tracking-wide">Then</span>
        <select
          value={rule.action.type}
          onChange={e => updateAction({ type: e.target.value as ActionType })}
          className="input-dark w-full text-xs"
        >
          {actions.map(a => (
            <option key={a} value={a}>{ACTION_LABELS[a]}</option>
          ))}
        </select>
        {rule.action.type === 'reposition_to_zone' && (
          <select
            value={rule.action.target_zone ?? ''}
            onChange={e => updateAction({ target_zone: e.target.value })}
            className="input-dark w-full text-xs"
          >
            <option value="">Select zone</option>
            {ZONES.map(z => <option key={z} value={z}>{z}</option>)}
          </select>
        )}
      </div>
    </div>
  )
}
