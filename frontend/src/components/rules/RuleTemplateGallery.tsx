import type { RuleTemplate, RuleV2 } from '../../types/playbook'
import { CatalogCard } from '../ui/CatalogCard'
import { SimButton } from '../ui/SimButton'

interface Props {
  templates: RuleTemplate[]
  onAdd: (rule: RuleV2) => void
}

function nextRuleId(rules: RuleV2[], baseId: string): string {
  let id = baseId.replace(/^tpl-/, 'rule-')
  let n = 1
  while (rules.some(r => r.id === id)) {
    id = `${baseId.replace(/^tpl-/, 'rule-')}-${n}`
    n += 1
  }
  return id
}

/** Card grid of insertable rule templates. */
export function RuleTemplateGallery({ templates, onAdd }: Props) {
  return (
    <div className="space-y-2 max-h-[28rem] overflow-y-auto">
      {templates.map(t => (
        <CatalogCard
          key={t.id}
          title={t.name}
          description={t.summary}
          badges={[t.category, t.phase]}
          action={
            <SimButton
              onClick={e => {
                e.stopPropagation()
                const rule = {
                  ...t.rule,
                  id: nextRuleId([], t.id),
                  priority: (templates.indexOf(t) + 1) * 10,
                }
                onAdd(rule)
              }}
            >
              Add
            </SimButton>
          }
        />
      ))}
    </div>
  )
}
