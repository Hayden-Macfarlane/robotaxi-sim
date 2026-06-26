import type { PolicySubTab } from '../../lib/fleetTerminology'
import { POLICY_SUBTAB_LABELS } from '../../lib/fleetTerminology'
import { useUiMode } from '../../contexts/UiModeContext'

interface Props {
  subTab: PolicySubTab
  className?: string
}

/** Deep link to a Fleet policy sub-tab. */
export function PolicyLink({ subTab, className = '' }: Props) {
  const { uiMode, navigate } = useUiMode()
  const labels = POLICY_SUBTAB_LABELS[subTab]
  const label = uiMode === 'standard' ? labels.plain : labels.industry

  return (
    <button
      type="button"
      onClick={() => navigate({ tab: 'policy', policySubTab: subTab })}
      className={`text-accent hover:underline text-xs ${className}`}
    >
      Policy → {label}
    </button>
  )
}
