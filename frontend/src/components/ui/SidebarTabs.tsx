export type SidebarTabId = 'assets' | 'routing' | 'automation' | 'demand' | 'activity'

interface Tab {
  id: SidebarTabId
  label: string
}

const TABS: Tab[] = [
  { id: 'assets', label: 'Assets' },
  { id: 'routing', label: 'Routing' },
  { id: 'automation', label: 'Auto' },
  { id: 'demand', label: 'Demand' },
  { id: 'activity', label: 'Activity' },
]

interface Props {
  active: SidebarTabId
  onChange: (tab: SidebarTabId) => void
}

/** Tab bar for the command sidebar. */
export function SidebarTabs({ active, onChange }: Props) {
  return (
    <div className="flex border-b border-border-default bg-surface-header flex-shrink-0">
      {TABS.map(tab => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`flex-1 px-2 py-2.5 text-xs font-medium transition-colors ${
            active === tab.id
              ? 'text-accent border-b-2 border-accent bg-surface-raised/50'
              : 'text-text-secondary hover:text-text-primary hover:bg-surface-raised/30'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
