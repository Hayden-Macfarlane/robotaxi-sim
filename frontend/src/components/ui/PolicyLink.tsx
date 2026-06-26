import type { PolicySubTab } from '../../lib/fleetTerminology'
import { POLICY_SUBTAB_LABELS } from '../../lib/fleetTerminology'
import { useUiMode } from '../../contexts/UiModeContext'

interface Props {
  subTab: PolicySubTab
  className?: string
}

/** Deep link to Rules hub or Sim settings section. */
export function PolicyLink({ subTab, className = '' }: Props) {
  const { uiMode, navigate } = useUiMode()
  const labels = POLICY_SUBTAB_LABELS[subTab]
  const label = uiMode === 'standard' ? labels.plain : labels.industry

  const handleClick = () => {
    if (subTab === 'rules') {
      navigate({ tab: 'rules', rulesSubTab: 'build' })
    } else if (subTab === 'market') {
      navigate({ settingsOpen: true, settingsSection: 'market' })
    } else {
      navigate({ settingsOpen: true, settingsSection: 'operations' })
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`text-accent hover:underline text-xs ${className}`}
    >
      {subTab === 'rules' ? `Rules → ${label}` : `Settings → ${label}`}
    </button>
  )
}
