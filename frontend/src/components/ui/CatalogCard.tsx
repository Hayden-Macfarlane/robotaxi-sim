import type { ReactNode } from 'react'

interface Props {
  title: string
  description?: string
  badges?: string[]
  action?: ReactNode
  onClick?: () => void
  selected?: boolean
}

/** Consistent browse row for library catalogs. */
export function CatalogCard({ title, description, badges = [], action, onClick, selected }: Props) {
  const Wrapper = onClick ? 'button' : 'div'
  return (
    <Wrapper
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      className={`w-full text-left rounded-lg border p-2.5 transition-colors ${
        selected ? 'border-accent bg-accent/10' : 'border-border-default bg-surface-raised/30 hover:bg-surface-raised/60'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-xs font-medium text-text-primary">{title}</div>
          {description && <p className="text-[10px] text-text-secondary mt-0.5 line-clamp-2">{description}</p>}
          {badges.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {badges.map(b => (
                <span key={b} className="px-1.5 py-0.5 rounded text-[9px] bg-surface-base text-text-secondary border border-border-default">
                  {b}
                </span>
              ))}
            </div>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </Wrapper>
  )
}
