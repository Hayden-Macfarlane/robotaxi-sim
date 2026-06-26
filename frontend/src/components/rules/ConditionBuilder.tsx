import type { CompareOpV2, ConstantMeta, ExprNode, MetricMeta, MetricRef, RulePhaseV2 } from '../../types/playbook'
import { COMPARE_OP_OPTIONS_UI, describeCompare } from '../../lib/compareLabels'
import {
  categoryLabel,
  metricCategoryId,
  sortMetricsForPicker,
} from '../../lib/constraintCategories'
import { MetricPicker } from '../MetricPicker'
import { SearchableSelect, type SearchableOption } from '../ui/SearchableSelect'

interface Props {
  node: ExprNode
  catalog: MetricMeta[]
  constantCatalog: ConstantMeta[]
  playbookConstants: Record<string, number>
  onChange: (node: ExprNode) => void
  depth?: number
  phaseHint?: RulePhaseV2 | null
  dropdownZIndex?: number
}

type RightSide = 'literal' | 'constant' | 'metric'

function rightSideOf(node: ExprNode): RightSide {
  if (node.right_metric?.id === 'const.value') return 'constant'
  if (node.right_metric) return 'metric'
  return 'literal'
}

function defaultCompareNode(phaseHint?: RulePhaseV2 | null): ExprNode {
  if (phaseHint === 'dispatch') {
    return { op: 'compare', metric: { id: 'zone.pending_demand' }, operator: 'gte', value: 1 }
  }
  if (phaseHint === 'facility') {
    return { op: 'compare', metric: { id: 'vehicle.is_off_street' }, operator: 'eq', value: 1 }
  }
  return { op: 'compare', metric: { id: 'vehicle.idle_minutes' }, operator: 'gte', value: 0 }
}

function metricOptions(catalog: MetricMeta[], phaseHint?: RulePhaseV2 | null): SearchableOption[] {
  return sortMetricsForPicker(catalog, phaseHint).map(m => ({
    value: m.id,
    label: m.plain_label,
    group: categoryLabel(metricCategoryId(m)),
    description: m.description,
  }))
}

/** Sentence-style condition builder with plain-English operators and category grouping. */
export function ConditionBuilder({
  node,
  catalog,
  constantCatalog,
  playbookConstants,
  onChange,
  depth = 0,
  phaseHint,
  dropdownZIndex,
}: Props) {
  const defaultCompare = defaultCompareNode(phaseHint)

  if (node.op === 'and' || node.op === 'or') {
    return (
      <div className={`space-y-2 ${depth > 0 ? 'pl-3 border-l border-border-default' : ''}`}>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={node.op}
            onChange={e => onChange({ ...node, op: e.target.value as 'and' | 'or' })}
            className="input-dark text-xs"
          >
            <option value="and">Match all of these</option>
            <option value="or">Match any of these</option>
          </select>
          <button
            type="button"
            className="text-[10px] text-accent"
            onClick={() =>
              onChange({
                ...node,
                children: [...(node.children ?? []), defaultCompare],
              })
            }
          >
            + Add condition
          </button>
          <button
            type="button"
            className="text-[10px] text-text-secondary"
            onClick={() =>
              onChange({
                ...node,
                children: [...(node.children ?? []), { op: 'not', children: [defaultCompare] }],
              })
            }
          >
            + Add exception
          </button>
        </div>
        {(node.children ?? []).map((child, i) => (
          <div key={i} className="relative pr-12">
            <ConditionBuilder
              node={child}
              catalog={catalog}
              constantCatalog={constantCatalog}
              playbookConstants={playbookConstants}
              depth={depth + 1}
              phaseHint={phaseHint}
              dropdownZIndex={dropdownZIndex}
              onChange={updated => {
                const children = [...(node.children ?? [])]
                children[i] = updated
                onChange({ ...node, children })
              }}
            />
            <button
              type="button"
              className="absolute top-0 right-0 text-[10px] text-red-400"
              onClick={() => onChange({ ...node, children: (node.children ?? []).filter((_, j) => j !== i) })}
            >
              remove
            </button>
          </div>
        ))}
      </div>
    )
  }

  if (node.op === 'not') {
    const inner = node.children?.[0] ?? defaultCompare
    return (
      <div className="space-y-1 pl-2 border-l border-amber-800/50">
        <span className="text-[10px] text-amber-400 font-medium">Unless</span>
        <ConditionBuilder
          node={inner}
          catalog={catalog}
          constantCatalog={constantCatalog}
          playbookConstants={playbookConstants}
          phaseHint={phaseHint}
          dropdownZIndex={dropdownZIndex}
          onChange={child => onChange({ ...node, children: [child] })}
        />
      </div>
    )
  }

  if (node.op === 'compare' && node.metric) {
    const rightSide = rightSideOf(node)
    const metricMeta = catalog.find(m => m.id === node.metric!.id)
    const isBool = metricMeta?.value_type === 'bool'
    const preview = describeCompare(node, catalog, constantCatalog, playbookConstants)

    const constantOptions: SearchableOption[] = [
      ...constantCatalog.map(c => ({
        value: c.id,
        label: c.plain_label,
        group: 'Thresholds',
        description: c.description,
      })),
      ...Object.keys(playbookConstants)
        .filter(k => !constantCatalog.some(c => c.id === k))
        .map(k => ({ value: k, label: k, group: 'Your thresholds' })),
    ]

    const numericOps = COMPARE_OP_OPTIONS_UI.filter(op => (isBool ? op.value === 'eq' || op.value === 'ne' : true))
    const operatorValue = numericOps.some(o => o.value === node.operator) ? (node.operator ?? 'gte') : 'gte'

    return (
      <div className="space-y-2 p-2 rounded border border-border-default bg-surface-base/50">
        <p className="text-[10px] uppercase tracking-wide text-text-secondary font-medium">When</p>
        <MetricPicker
          catalog={catalog}
          value={node.metric}
          phaseHint={phaseHint}
          dropdownZIndex={dropdownZIndex}
          onChange={(metric: MetricRef) => onChange({ ...node, metric })}
        />
        <div className="space-y-2">
          <label className="text-[10px] text-text-secondary">Comparison</label>
          <div className="flex flex-wrap gap-2 items-center">
            <select
              value={operatorValue}
              onChange={e => onChange({ ...node, operator: e.target.value as CompareOpV2 })}
              className="input-dark text-xs min-w-[8rem]"
            >
              {numericOps.map(op => (
                <option key={op.value} value={op.value}>{op.label}</option>
              ))}
            </select>
            {isBool ? (
              <select
                value={String(node.value ?? 1)}
                onChange={e => onChange({ ...node, value: parseFloat(e.target.value) })}
                className="input-dark text-xs"
              >
                <option value="1">true</option>
                <option value="0">false</option>
              </select>
            ) : (
              <>
                <select
                  value={rightSide}
                  onChange={e => {
                    const mode = e.target.value as RightSide
                    if (mode === 'literal') {
                      onChange({ ...node, right_metric: null, value: node.value ?? 0 })
                    } else if (mode === 'constant') {
                      const first = constantOptions[0]?.value ?? 'idle_patience_min'
                      onChange({
                        ...node,
                        value: null,
                        right_metric: { id: 'const.value', params: { name: first } },
                      })
                    } else {
                      onChange({
                        ...node,
                        value: null,
                        right_metric: { id: 'zone.pending_demand', params: {} },
                      })
                    }
                  }}
                  className="input-dark text-xs"
                >
                  <option value="literal">a number</option>
                  <option value="constant">a threshold</option>
                  <option value="metric">another check</option>
                </select>
                {rightSide === 'literal' && node.operator !== 'between' && (
                  <input
                    type="number"
                    step="any"
                    value={node.value ?? 0}
                    onChange={e => onChange({ ...node, value: parseFloat(e.target.value) || 0 })}
                    className="input-dark text-xs w-24"
                  />
                )}
                {rightSide === 'literal' && node.operator === 'between' && (
                  <div className="flex gap-2 items-center flex-wrap">
                    <input
                      type="number"
                      step="any"
                      value={node.value ?? 0}
                      onChange={e => onChange({ ...node, value: parseFloat(e.target.value) || 0 })}
                      className="input-dark text-xs w-20"
                      placeholder="Min"
                    />
                    <span className="text-[10px] text-text-secondary">and</span>
                    <input
                      type="number"
                      step="any"
                      value={node.value_max ?? 0}
                      onChange={e => onChange({ ...node, value_max: parseFloat(e.target.value) || 0 })}
                      className="input-dark text-xs w-20"
                      placeholder="Max"
                    />
                  </div>
                )}
              </>
            )}
          </div>
          {!isBool && rightSide === 'constant' && (
            <SearchableSelect
              options={constantOptions}
              value={String(node.right_metric?.params?.name ?? constantOptions[0]?.value ?? '')}
              onChange={name =>
                onChange({
                  ...node,
                  right_metric: { id: 'const.value', params: { name } },
                })
              }
              placeholder="Pick a threshold…"
            />
          )}
          {!isBool && rightSide === 'metric' && node.right_metric && (
            <SearchableSelect
              options={metricOptions(catalog, phaseHint)}
              value={node.right_metric.id}
              onChange={id => onChange({ ...node, right_metric: { id, params: {} } })}
              placeholder="What should we compare to?"
              dropdownZIndex={dropdownZIndex}
              emptyMessage={
                catalog.length === 0
                  ? 'Loading constraints…'
                  : `No matches — ${catalog.length} checks available`
              }
            />
          )}
        </div>
        {preview && (
          <p className="text-[10px] text-accent/90 italic border-t border-border-default/50 pt-1.5">
            {preview}
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="flex gap-2">
      <button type="button" className="text-xs text-accent" onClick={() => onChange(defaultCompare)}>
        Add condition
      </button>
      <button
        type="button"
        className="text-xs text-text-secondary"
        onClick={() => onChange({ op: 'not', children: [defaultCompare] })}
      >
        Add exception (unless)
      </button>
    </div>
  )
}

/** Wrap a single compare node in an AND group for editing. */
export function normalizeWhen(when: ExprNode): ExprNode {
  if (when.op === 'and' || when.op === 'or') return when
  return { op: 'and', children: [when] }
}
