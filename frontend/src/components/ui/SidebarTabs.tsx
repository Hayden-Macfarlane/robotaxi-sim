import type { SidebarTabId } from '../../contexts/UiModeContext'
import { useUiMode } from '../../contexts/UiModeContext'

interface Tab {
  id: SidebarTabId
  industry: string
  plain: string
}

const TABS: Tab[] = [
  { id: 'rules', industry: 'Rules', plain: 'Fleet rules' },
  { id: 'live', industry: 'Live', plain: 'Live ops' },
]

interface Props {
  active: SidebarTabId
  onChange: (tab: SidebarTabId) => void
}

/** Primary sidebar tabs: Rules engine + Live ops, with Sim settings gear. */
export function SidebarTabs({ active, onChange }: Props) {
  const { uiMode, setSettingsOpen } = useUiMode()

  return (
    <div className="flex border-b border-border-default bg-surface-header flex-shrink-0 items-stretch">
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
      <button
        type="button"
        onClick={() => setSettingsOpen(true)}
        className="px-3 py-2.5 text-xs text-text-secondary hover:text-text-primary border-l border-border-default hover:bg-surface-raised/30"
        title="Sim settings"
        aria-label="Sim settings"
      >
        ⚙
      </button>
    </div>
  )
}
