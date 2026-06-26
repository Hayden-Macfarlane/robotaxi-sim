import type { LiveSubTabId } from '../contexts/UiModeContext'
import { useUiMode } from '../contexts/UiModeContext'

const TABS: { id: LiveSubTabId; industry: string; plain: string }[] = [
  { id: 'fleet', industry: 'Fleet', plain: 'Vehicles' },
  { id: 'orders', industry: 'Orders', plain: 'Open trips' },
]

interface Props {
  active: LiveSubTabId
  onChange: (tab: LiveSubTabId) => void
}

/** Sub-tabs within Live operations. */
export function LiveSubTabs({ active, onChange }: Props) {
  const { uiMode } = useUiMode()

  return (
    <div className="flex border-b border-border-default bg-surface-header shrink-0">
      {TABS.map(tab => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`flex-1 px-2 py-2 text-[11px] font-medium transition-colors ${
            active === tab.id
              ? 'text-accent border-b-2 border-accent -mb-px'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          {uiMode === 'standard' ? tab.plain : tab.industry}
        </button>
      ))}
    </div>
  )
}
