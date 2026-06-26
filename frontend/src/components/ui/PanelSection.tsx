import type { ReactNode } from 'react'

interface Props {
  title: string
  subtitle?: string
  impact?: string
  count?: number
  children: ReactNode
  className?: string
}

/** Sidebar section with title row, optional impact line, and elevated card body. */
export function PanelSection({ title, subtitle, impact, count, children, className = '' }: Props) {
  return (
    <section className={`flex flex-col min-h-0 ${className}`}>
      <div className="mb-2 px-1">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-xs font-medium uppercase tracking-wider text-text-secondary">
            {title}
          </h2>
          {count !== undefined && (
            <span className="text-xs font-mono text-text-secondary bg-surface-base border border-border-default rounded px-1.5 py-0.5">
              {count}
            </span>
          )}
        </div>
        {subtitle && <p className="text-[10px] text-accent mt-0.5">{subtitle}</p>}
        {impact && <p className="text-[10px] text-text-secondary mt-1 leading-relaxed italic">{impact}</p>}
      </div>
      <div className="bg-surface-raised border border-border-default rounded-lg">
        {children}
      </div>
    </section>
  )
}
