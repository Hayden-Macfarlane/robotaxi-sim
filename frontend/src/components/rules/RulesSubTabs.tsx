import type { RulesSubTabId } from '../../contexts/UiModeContext'
import { useUiMode } from '../../contexts/UiModeContext'

const TABS: { id: RulesSubTabId; industry: string; plain: string }[] = [
  { id: 'build', industry: 'Build', plain: 'Build' },
  { id: 'monitor', industry: 'Monitor', plain: 'Monitor' },
  { id: 'library', industry: 'Library', plain: 'Library' },
]

interface Props {
  active: RulesSubTabId
  onChange: (tab: RulesSubTabId) => void
}

/** Sub-tabs for the Rules hub: Build, Monitor, Library. */
export function RulesSubTabs({ active, onChange }: Props) {
  const { uiMode } = useUiMode()
  return (
    <div className="flex border-b border-border-default bg-surface-raised/20 flex-shrink-0">
      {TABS.map(tab => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`flex-1 px-2 py-2 text-xs font-medium transition-colors ${
            active === tab.id
              ? 'text-accent border-b-2 border-accent'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          {uiMode === 'standard' ? tab.plain : tab.industry}
        </button>
      ))}
    </div>
  )
}
