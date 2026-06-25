interface Props {
  label: string
  value: number | string
  accent?: 'default' | 'amber' | 'emerald' | 'blue'
}

/** Compact summary metric for the Assets tab. */
export function MetricPill({ label, value, accent = 'default' }: Props) {
  const valueClass = {
    default: 'text-text-primary',
    amber: 'text-amber-400',
    emerald: 'text-emerald-400',
    blue: 'text-sky-400',
  }[accent]

  return (
    <div className="flex-1 min-w-0 px-2 py-2 rounded-md bg-surface-base/60 border border-border-default/60">
      <div className="text-[10px] uppercase tracking-wide text-text-secondary truncate">{label}</div>
      <div className={`text-lg font-semibold font-mono ${valueClass}`}>{value}</div>
    </div>
  )
}
