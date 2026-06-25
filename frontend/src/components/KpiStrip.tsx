import { useState } from 'react'
import type { KpiSnap } from '../types/simulation'
import { formatIsoDateTime, formatSimDateTime } from '../lib/simTime'

interface Props {
  kpis: KpiSnap
  currentTimeIso?: string
  currentTimeH: number
  simStartIso: string
  connected: boolean
}

interface MetricProps {
  label: string
  value: string
  accent?: 'default' | 'amber' | 'emerald'
}

function MetricCard({ label, value, accent = 'default' }: MetricProps) {
  const valueClass = {
    default: 'text-text-primary',
    amber: 'text-amber-400',
    emerald: 'text-emerald-400',
  }[accent]

  return (
    <div className="flex flex-col gap-0.5 px-4 py-2 border-r border-border-default last:border-r-0">
      <span className="text-xs text-text-secondary">{label}</span>
      <span className={`text-sm font-semibold font-mono ${valueClass}`}>{value}</span>
    </div>
  )
}

/** Top KPI strip — six primary metrics with optional detail popover. */
export function KpiStrip({ kpis, currentTimeIso, currentTimeH, simStartIso, connected }: Props) {
  const [showMore, setShowMore] = useState(false)

  return (
    <div className="relative flex bg-surface-header border-b border-border-default">
      <div className="flex items-center gap-2 px-4 py-2 border-r border-border-default">
        <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-text-secondary">Status</span>
          <span className={`text-sm font-semibold ${connected ? 'text-emerald-400' : 'text-red-400'}`}>
            {connected ? 'Live' : 'Offline'}
          </span>
        </div>
      </div>
      <MetricCard
        label="Time"
        value={currentTimeIso ? formatIsoDateTime(currentTimeIso) : formatSimDateTime(currentTimeH, simStartIso)}
      />
      <MetricCard label="Avg Wait" value={`${kpis.avg_wait_min.toFixed(1)} min`} />
      <MetricCard label="Utilization" value={`${kpis.fleet_utilization_pct.toFixed(0)}%`} />
      <MetricCard label="Pending" value={String(kpis.pending_trips)} accent="amber" />
      <MetricCard label="Revenue" value={`$${kpis.revenue.toFixed(0)}`} accent="emerald" />
      <MetricCard label="Need Service" value={String(kpis.vehicles_needing_service ?? 0)} accent="amber" />
      <div className="flex items-center px-3">
        <button
          type="button"
          onClick={() => setShowMore(v => !v)}
          className="text-xs text-text-secondary hover:text-text-primary px-2 py-1 rounded border border-border-default hover:bg-surface-raised transition-colors"
        >
          {showMore ? 'Less' : 'More'}
        </button>
      </div>
      {showMore && (
        <div className="absolute top-full left-0 right-0 z-50 flex flex-wrap bg-surface-header border-b border-border-default shadow-lg">
          <MetricCard label="Completed" value={String(kpis.trips_completed)} />
          <MetricCard label="Deadhead" value={`${(kpis.deadhead_ratio * 100).toFixed(0)}%`} />
          <MetricCard label="On Street" value={String(kpis.vehicles_on_street ?? 0)} />
          <MetricCard label="At Depot" value={String(kpis.vehicles_at_depot ?? 0)} />
          <MetricCard label="Battery" value={`${(kpis.avg_battery_pct ?? 100).toFixed(0)}%`} />
          <MetricCard label="Condition" value={`${(kpis.avg_condition_pct ?? 100).toFixed(0)}%`} />
          <MetricCard label="Cleanliness" value={`${(kpis.avg_cleanliness_pct ?? 100).toFixed(0)}%`} />
        </div>
      )}
    </div>
  )
}
