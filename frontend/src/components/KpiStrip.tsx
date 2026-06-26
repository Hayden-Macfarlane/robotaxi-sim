import { useState } from 'react'
import type { KpiSnap } from '../types/simulation'
import { formatIsoDateTime, formatSimDateTime } from '../lib/simTime'
import { labelForTerm, getTerm } from '../lib/fleetTerminology'
import { useUiMode } from '../contexts/UiModeContext'
import { HelpPopover } from './ui/HelpPopover'

interface Props {
  kpis: KpiSnap
  currentTimeIso?: string
  currentTimeH: number
  simStartIso: string
  connected: boolean
}

interface MetricProps {
  termId?: string
  label: string
  value: string
  accent?: 'default' | 'amber' | 'emerald'
  plainHint?: string
}

function MetricCard({ termId, label, value, accent = 'default', plainHint }: MetricProps) {
  const [hover, setHover] = useState(false)
  const valueClass = {
    default: 'text-text-primary',
    amber: 'text-amber-400',
    emerald: 'text-emerald-400',
  }[accent]

  return (
    <div
      className="relative flex flex-col gap-0.5 px-4 py-2 border-r border-border-default last:border-r-0"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <div className="flex items-center gap-1">
        <span className="text-xs text-text-secondary">{label}</span>
        {termId && <HelpPopover termId={termId} />}
      </div>
      <span className={`text-sm font-semibold font-mono ${valueClass}`}>{value}</span>
      {hover && plainHint && (
        <div className="absolute top-full left-2 z-50 mt-1 px-2 py-1 rounded border border-border-default bg-surface-header shadow text-[10px] text-text-secondary max-w-[12rem]">
          {plainHint}
        </div>
      )}
    </div>
  )
}

/** Top KPI strip — industry labels with plain explanations on hover. */
export function KpiStrip({ kpis, currentTimeIso, currentTimeH, simStartIso, connected }: Props) {
  const [showMore, setShowMore] = useState(false)
  const { uiMode } = useUiMode()

  const hint = (termId: string) => getTerm(termId)?.description

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
      <MetricCard
        termId="pickup_wait"
        label={labelForTerm('pickup_wait', uiMode)}
        value={`${kpis.avg_wait_min.toFixed(1)} min`}
        plainHint={hint('pickup_wait')}
      />
      <MetricCard
        termId="fleet_utilization"
        label={labelForTerm('fleet_utilization', uiMode)}
        value={`${kpis.fleet_utilization_pct.toFixed(0)}%`}
        plainHint={hint('fleet_utilization')}
      />
      <MetricCard
        termId="pending_orders"
        label={labelForTerm('pending_orders', uiMode)}
        value={String(kpis.pending_trips)}
        accent="amber"
        plainHint={hint('pending_orders')}
      />
      <MetricCard
        termId="net_margin"
        label={labelForTerm('net_margin', uiMode)}
        value={`$${(kpis.profit ?? kpis.revenue).toFixed(0)}`}
        accent="emerald"
        plainHint={hint('net_margin')}
      />
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
          <MetricCard label="Cancelled" value={String(kpis.trips_cancelled)} />
          <MetricCard label="P95 wait" value={`${kpis.p95_wait_min.toFixed(1)} min`} />
          <MetricCard
            termId="fulfillment_rate"
            label={labelForTerm('fulfillment_rate', uiMode)}
            value={`${((kpis.completion_rate ?? 0) * 100).toFixed(0)}%`}
            plainHint={hint('fulfillment_rate')}
          />
          <MetricCard
            termId="trips_per_vph"
            label={labelForTerm('trips_per_vph', uiMode)}
            value={(kpis.trips_per_vehicle_hour ?? 0).toFixed(2)}
            plainHint={hint('trips_per_vph')}
          />
          <MetricCard label="Revenue" value={`$${kpis.revenue.toFixed(0)}`} />
          <MetricCard
            termId="deadhead_cost"
            label={labelForTerm('deadhead_cost', uiMode)}
            value={`$${(kpis.deadhead_cost ?? 0).toFixed(0)}`}
            accent="amber"
            plainHint={hint('deadhead_cost')}
          />
          <MetricCard
            termId="empty_mile_ratio"
            label={labelForTerm('empty_mile_ratio', uiMode)}
            value={`${(kpis.deadhead_ratio * 100).toFixed(0)}%`}
            plainHint={hint('empty_mile_ratio')}
          />
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
