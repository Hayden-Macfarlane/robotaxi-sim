import type { ConstantMeta, ExprNode, MetricMeta } from '../types/playbook'
import { COMPARE_OP_LABELS, describeCompare } from './compareLabels'

/** Count how many rules reference a constant via const.value. */
export function countConstantUsage(rules: { when: ExprNode }[], constantId: string): number {
  return rules.filter(r => exprReferencesConstant(r.when, constantId)).length
}

function exprReferencesConstant(node: ExprNode, constantId: string): boolean {
  if (node.op === 'compare') {
    if (node.right_metric?.id === 'const.value' && node.right_metric.params?.name === constantId) return true
    if (node.metric?.id === 'const.value' && node.metric.params?.name === constantId) return true
  }
  if (node.children) {
    return node.children.some((c: ExprNode) => exprReferencesConstant(c, constantId))
  }
  return false
}

/** Summarize an expression tree as plain English. */
export function summarizeExpr(
  node: ExprNode,
  metricCatalog: MetricMeta[] = [],
  constantCatalog: ConstantMeta[] = [],
  playbookConstants: Record<string, number> = {},
): string {
  if (node.op === 'and' && node.children?.length) {
    return node.children.map(c => summarizeExpr(c, metricCatalog, constantCatalog, playbookConstants)).join(' and ')
  }
  if (node.op === 'or' && node.children?.length) {
    return node.children.map(c => summarizeExpr(c, metricCatalog, constantCatalog, playbookConstants)).join(' or ')
  }
  if (node.op === 'not' && node.children?.[0]) {
    return `unless ${summarizeExpr(node.children[0], metricCatalog, constantCatalog, playbookConstants)}`
  }
  if (node.op === 'compare' && node.metric) {
    if (metricCatalog.length > 0) {
      return describeCompare(node, metricCatalog, constantCatalog, playbookConstants)
    }
    const left = node.metric.id
    const op = COMPARE_OP_LABELS[node.operator ?? 'gte']
    if (node.right_metric) {
      const right =
        node.right_metric.id === 'const.value'
          ? String(node.right_metric.params?.name ?? 'threshold')
          : node.right_metric.id
      return `${left} ${op} ${right}`
    }
    return `${left} ${op} ${node.value ?? 0}`
  }
  return node.op
}
