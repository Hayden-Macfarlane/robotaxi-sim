import type { ReactNode } from 'react'

interface Props {
  title: string
  count?: number
  children: ReactNode
  className?: string
}

/** Sidebar section with title row and elevated card body. */
export function PanelSection({ title, count, children, className = '' }: Props) {
  return (
    <section className={`flex flex-col min-h-0 ${className}`}>
      <div className="flex items-center justify-between mb-2 px-1">
        <h2 className="text-xs font-medium uppercase tracking-wider text-text-secondary">
          {title}
        </h2>
        {count !== undefined && (
          <span className="text-xs font-mono text-text-secondary bg-surface-base border border-border-default rounded px-1.5 py-0.5">
            {count}
          </span>
        )}
      </div>
      <div className="bg-surface-raised border border-border-default rounded-lg">
        {children}
      </div>
    </section>
  )
}
