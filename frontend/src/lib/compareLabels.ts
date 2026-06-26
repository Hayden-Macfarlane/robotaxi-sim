import type { CompareOpV2, ConstantMeta, ExprNode, MetricMeta } from '../types/playbook'

/** Plain-English labels for comparison operators (never show gte/lte codes in UI). */
export const COMPARE_OP_LABELS: Record<CompareOpV2, string> = {
  gte: 'is greater than',
  gt: 'is greater than',
  lte: 'is less than',
  lt: 'is less than',
  eq: 'equals',
  ne: 'does not equal',
  between: 'is between',
}

/**
 * Operators shown in the rule builder — deduplicated pairs:
 * - "is greater than" (≥) covers the common case; strict ">" omitted from dropdown
 * - "is less than" (≤) covers the common case; strict "<" omitted from dropdown
 */
export const COMPARE_OP_OPTIONS_UI: { value: CompareOpV2; label: string }[] = [
  { value: 'gte', label: 'is greater than' },
  { value: 'lte', label: 'is less than' },
  { value: 'eq', label: 'equals' },
  { value: 'ne', label: 'does not equal' },
  { value: 'between', label: 'is between' },
]

/** @deprecated Use COMPARE_OP_OPTIONS_UI in UI controls. */
export const COMPARE_OP_OPTIONS = COMPARE_OP_OPTIONS_UI

function metricLabel(id: string, catalog: MetricMeta[]): string {
  return catalog.find(m => m.id === id)?.plain_label ?? id.replace(/\./g, ' ')
}

function constantLabel(id: string, constantCatalog: ConstantMeta[], playbookConstants: Record<string, number>): string {
  const meta = constantCatalog.find(c => c.id === id)
  const val = playbookConstants[id]
  if (meta) {
    return val !== undefined ? `${meta.plain_label} (${val}${meta.unit ? ` ${meta.unit}` : ''})` : meta.plain_label
  }
  return id
}

function rightSideLabel(
  node: ExprNode,
  metricCatalog: MetricMeta[],
  constantCatalog: ConstantMeta[],
  playbookConstants: Record<string, number>,
): string {
  if (node.right_metric) {
    if (node.right_metric.id === 'const.value') {
      const name = String(node.right_metric.params?.name ?? '')
      return constantLabel(name, constantCatalog, playbookConstants)
    }
    return metricLabel(node.right_metric.id, metricCatalog)
  }
  if (node.operator === 'between' && node.value_max != null) {
    return `${node.value ?? 0} and ${node.value_max}`
  }
  if (node.value === 1 || node.value === 0) {
    return node.value === 1 ? 'true' : 'false'
  }
  return String(node.value ?? 0)
}

/** One human-readable condition sentence. */
export function describeCompare(
  node: ExprNode,
  metricCatalog: MetricMeta[],
  constantCatalog: ConstantMeta[],
  playbookConstants: Record<string, number>,
): string {
  if (node.op !== 'compare' || !node.metric) return ''
  const left = metricLabel(node.metric.id, metricCatalog)
  const op = COMPARE_OP_LABELS[node.operator ?? 'gte']
  const right = rightSideLabel(node, metricCatalog, constantCatalog, playbookConstants)
  if (node.operator === 'between') {
    return `${left} ${op} ${node.value ?? 0} and ${node.value_max ?? 0}`
  }
  return `${left} ${op} ${right}`
}
