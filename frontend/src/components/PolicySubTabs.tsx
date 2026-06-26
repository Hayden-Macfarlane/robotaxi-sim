import type { PolicySubTab } from '../lib/fleetTerminology'
import { POLICY_SUBTAB_LABELS } from '../lib/fleetTerminology'
import { useUiMode } from '../contexts/UiModeContext'

const TAB_ORDER: PolicySubTab[] = ['matching', 'supply', 'automation', 'network', 'market', 'operations']

interface Props {
  active: PolicySubTab
  onChange: (tab: PolicySubTab) => void
}

/** Sub-tab navigation within Fleet policy. */
export function PolicySubTabs({ active, onChange }: Props) {
  const { uiMode } = useUiMode()

  return (
    <div className="flex flex-wrap border-b border-border-default bg-surface-header shrink-0">
      {TAB_ORDER.map(tab => {
        const labels = POLICY_SUBTAB_LABELS[tab]
        const label = uiMode === 'standard' ? labels.plain : labels.industry
        return (
          <button
            key={tab}
            type="button"
            onClick={() => onChange(tab)}
            className={`px-2 py-2 text-[10px] font-medium transition-colors ${
              active === tab
                ? 'text-accent border-b-2 border-accent -mb-px'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
