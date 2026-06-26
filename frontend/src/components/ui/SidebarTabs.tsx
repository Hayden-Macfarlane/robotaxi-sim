import type { SidebarTabId } from '../../contexts/UiModeContext'
import { useUiMode } from '../../contexts/UiModeContext'

interface Tab {
  id: SidebarTabId
  industry: string
  plain: string
}

const TABS: Tab[] = [
  { id: 'live', industry: 'Live', plain: 'Live ops' },
  { id: 'dispatch', industry: 'Dispatch', plain: 'Dispatch' },
  { id: 'policy', industry: 'Policy', plain: 'Fleet policy' },
  { id: 'analyze', industry: 'Analyze', plain: 'Performance' },
]

interface Props {
  active: SidebarTabId
  onChange: (tab: SidebarTabId) => void
}

/** Tab bar for the four operator jobs in the command sidebar. */
export function SidebarTabs({ active, onChange }: Props) {
  const { uiMode } = useUiMode()

  return (
    <div className="flex border-b border-border-default bg-surface-header flex-shrink-0">
      {TABS.map(tab => {
        const label = uiMode === 'standard' ? tab.plain : tab.industry
        return (
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
            {label}
          </button>
        )
      })}
    </div>
  )
}
