import { useUiMode } from '../../contexts/UiModeContext'
import { statusLabel } from '../../lib/vehicleLabels'

/** Semantic status pill with colored dot for fleet and trip states. */

const STATE_DOTS: Record<string, string> = {
  idle: 'bg-status-idle',
  to_pickup: 'bg-status-pickup',
  with_rider: 'bg-status-rider',
  repositioning: 'bg-status-reposition',
  at_depot: 'bg-slate-500',
  charging: 'bg-yellow-400',
  maintenance: 'bg-orange-500',
  cleaning: 'bg-blue-400',
  pending: 'bg-status-pickup',
  assigned: 'bg-status-idle',
  in_progress: 'bg-status-rider',
  completed: 'bg-status-rider',
  cancelled: 'bg-red-500',
}

const TRIP_LABELS: Record<string, string> = {
  pending: 'Pending',
  assigned: 'Assigned',
  in_progress: 'In progress',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

interface Props {
  state: string
}

export function StatusBadge({ state }: Props) {
  const { uiMode } = useUiMode()
  const dot = STATE_DOTS[state] ?? 'bg-text-secondary'
  const label = TRIP_LABELS[state] ?? statusLabel(state, uiMode)

  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-base border border-border-default text-xs text-text-primary">
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  )
}
