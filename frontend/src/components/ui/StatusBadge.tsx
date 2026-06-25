/** Semantic status pill with colored dot for fleet and trip states. */

const STATE_STYLES: Record<string, { dot: string; label: string }> = {
  idle: { dot: 'bg-status-idle', label: 'Idle' },
  to_pickup: { dot: 'bg-status-pickup', label: 'En Route' },
  with_rider: { dot: 'bg-status-rider', label: 'With Rider' },
  repositioning: { dot: 'bg-status-reposition', label: 'Repositioning' },
  at_depot: { dot: 'bg-slate-500', label: 'At Depot' },
  charging: { dot: 'bg-yellow-400', label: 'Charging' },
  maintenance: { dot: 'bg-orange-500', label: 'Maintenance' },
  cleaning: { dot: 'bg-blue-400', label: 'Cleaning' },
  pending: { dot: 'bg-status-pickup', label: 'Pending' },
  assigned: { dot: 'bg-status-idle', label: 'Assigned' },
  in_progress: { dot: 'bg-status-rider', label: 'In Progress' },
  completed: { dot: 'bg-status-rider', label: 'Completed' },
  cancelled: { dot: 'bg-red-500', label: 'Cancelled' },
}

interface Props {
  state: string
}

export function StatusBadge({ state }: Props) {
  const style = STATE_STYLES[state] ?? { dot: 'bg-text-secondary', label: state }
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-base border border-border-default text-xs text-text-primary">
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {style.label}
    </span>
  )
}
