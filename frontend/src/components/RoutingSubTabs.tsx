export type RoutingSubTabId = 'scoring' | 'zones' | 'rules' | 'constraints'

const TABS: { id: RoutingSubTabId; label: string }[] = [
  { id: 'scoring', label: 'Scoring' },
  { id: 'zones', label: 'Zone policy' },
  { id: 'rules', label: 'Rules' },
  { id: 'constraints', label: 'Constraints' },
]

interface Props {
  active: RoutingSubTabId
  onChange: (tab: RoutingSubTabId) => void
}

/** Sub-tab navigation within the Routing sidebar panel. */
export function RoutingSubTabs({ active, onChange }: Props) {
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
          {tab.label}
        </button>
      ))}
    </div>
  )
}
