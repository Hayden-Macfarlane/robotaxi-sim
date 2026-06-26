import { useState } from 'react'
import type {
  DispatchCandidateSnap,
  DispatchAssignmentMode,
  SimCommand,
  TripSnap,
} from '../types/simulation'
import { useUiMode } from '../contexts/UiModeContext'
import { labelForTerm } from '../lib/fleetTerminology'
import { statusLabel } from '../lib/vehicleLabels'
import { PanelSection } from './ui/PanelSection'
import { StatusBadge } from './ui/StatusBadge'

function formatCoord(lat: number, lon: number): string {
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`
}

const MODE_LABELS: Record<DispatchAssignmentMode, string> = {
  manual: 'Manual dispatch',
  closest_idle_or_repositioning: 'Nearest available vehicle',
  closest_idle: 'Nearest idle vehicle',
}

function MatchExplain({ candidate }: { candidate: DispatchCandidateSnap }) {
  const { uiMode } = useUiMode()

  return (
    <div className="mt-1.5 p-2 rounded bg-surface-base/80 border border-border-default/60 text-[10px] space-y-1">
      <div className="font-medium text-text-primary">Why this vehicle?</div>
      <div className="text-text-secondary">
        <span className="text-text-primary">Pickup ETA:</span> {candidate.eta_min.toFixed(1)} min — closer vehicles rank higher.
      </div>
      {candidate.score != null && (
        <div className="text-text-secondary">
          <span className="text-text-primary">{labelForTerm('match_score', uiMode)}:</span>{' '}
          {candidate.score.toFixed(1)} — lower is better.
        </div>
      )}
      {candidate.dropoff_zone && (
        <div className="text-text-secondary">
          <span className="text-text-primary">{labelForTerm('destination_zone', uiMode)}:</span>{' '}
          {candidate.dropoff_zone.replace(/_/g, ' ')}
        </div>
      )}
      {candidate.balance_adjustment != null && candidate.balance_adjustment !== 0 && (
        <div className="text-text-secondary">
          <span className="text-text-primary">{labelForTerm('rebalancing_adjustment', uiMode)}:</span>{' '}
          {candidate.balance_adjustment > 0 ? '+' : ''}
          {candidate.balance_adjustment.toFixed(1)} —{' '}
          {candidate.balance_adjustment < 0
            ? 'helps fill an under-supplied zone after dropoff.'
            : 'would overcrowd the destination zone.'}
        </div>
      )}
    </div>
  )
}

interface Props {
  trips: TripSnap[]
  dispatchCandidates: Record<string, DispatchCandidateSnap[]>
  dispatchMode: DispatchAssignmentMode | null
  onCommand: (cmd: SimCommand) => void
}

/** Open order queue with manual dispatch and ranked vehicle suggestions. */
export function TripQueuePanel({ trips, dispatchCandidates, dispatchMode, onCommand }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [explainVehicleId, setExplainVehicleId] = useState<string | null>(null)
  const { uiMode } = useUiMode()
  const isManual = dispatchMode === 'manual'

  const pending = trips.filter(t => t.status === 'pending')
  const title = uiMode === 'standard' ? 'Open orders' : 'Open orders'

  return (
    <PanelSection title={title} count={pending.length}>
      <div className="p-2 space-y-1">
        {pending.length === 0 && (
          <div className="px-2 py-4 text-sm text-text-secondary text-center italic">
            No open orders
          </div>
        )}
        {pending.map(t => {
          const candidates = dispatchCandidates[t.id] ?? []
          const top = candidates[0]
          const expanded = expandedId === t.id
          return (
            <div
              key={t.id}
              className="px-2 py-2 rounded-md hover:bg-surface-base/60 border-b border-border-default/50 last:border-b-0"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-sm text-text-primary">{t.id}</span>
                <StatusBadge state={t.status} />
              </div>
              <div className="font-mono text-xs text-text-secondary mb-0.5">
                {formatCoord(t.origin.lat, t.origin.lon)}
              </div>
              <div className="font-mono text-xs text-text-secondary mb-1">
                → {formatCoord(t.destination.lat, t.destination.lon)}
              </div>
              <div className="text-xs font-mono text-emerald-400 mb-1">
                ${t.fare_estimate.toFixed(2)}
              </div>

              {top && (
                <div className="text-[10px] text-text-secondary mb-1">
                  {uiMode === 'standard' ? 'Recommended match' : 'Recommended match'}:{' '}
                  <span className="text-emerald-300 font-mono">
                    {top.vehicle_id} · {top.eta_min.toFixed(1)} min
                    {top.score != null && ` · ${labelForTerm('match_score', uiMode)} ${top.score.toFixed(1)}`}
                    {top.dropoff_zone && ` · ${labelForTerm('destination_zone', uiMode)} ${top.dropoff_zone.replace(/_/g, ' ')}`}
                  </span>
                  <button
                    type="button"
                    onClick={() => setExplainVehicleId(explainVehicleId === top.vehicle_id ? null : top.vehicle_id)}
                    className="ml-2 text-accent hover:underline"
                  >
                    Why this vehicle?
                  </button>
                  {explainVehicleId === top.vehicle_id && <MatchExplain candidate={top} />}
                </div>
              )}

              {!isManual && dispatchMode && (
                <div className="text-[10px] text-text-secondary mb-1">
                  Auto: {MODE_LABELS[dispatchMode]}
                </div>
              )}

              {isManual && (
                <>
                  <button
                    type="button"
                    onClick={() => setExpandedId(expanded ? null : t.id)}
                    className="text-[10px] text-accent hover:underline mr-2"
                  >
                    {expanded ? 'Hide vehicles' : `Assign vehicle (${candidates.length})`}
                  </button>
                  <button
                    type="button"
                    onClick={() => onCommand({ type: 'CANCEL_TRIP', trip_id: t.id })}
                    className="text-[10px] text-red-400 hover:underline"
                  >
                    Cancel
                  </button>
                  {expanded && (
                    <div className="mt-2 space-y-1">
                      {candidates.length === 0 && (
                        <div className="text-[10px] text-text-secondary italic">No eligible vehicles</div>
                      )}
                      {candidates.map((c, idx) => (
                        <div
                          key={c.vehicle_id}
                          className="text-xs bg-surface-raised/50 rounded px-2 py-1"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-text-primary">
                              {idx === 0 && '★ '}
                              {c.vehicle_id}
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                onCommand({
                                  type: 'DISPATCH_VEHICLE',
                                  vehicle_id: c.vehicle_id,
                                  trip_id: t.id,
                                })
                              }
                              className="text-[10px] px-2 py-0.5 rounded border border-emerald-800 text-emerald-300 hover:bg-emerald-950"
                            >
                              Assign
                            </button>
                          </div>
                          <span className="text-text-secondary text-[10px] block mt-0.5">
                            {c.eta_min.toFixed(1)}m · {statusLabel(c.state, uiMode)}
                            {c.score != null && ` · ${labelForTerm('match_score', uiMode)} ${c.score.toFixed(1)}`}
                            {c.dropoff_zone && ` · ${labelForTerm('destination_zone', uiMode)} ${c.dropoff_zone.replace(/_/g, ' ')}`}
                            {c.balance_adjustment != null && c.balance_adjustment !== 0 && (
                              ` · ${labelForTerm('rebalancing_adjustment', uiMode)} ${c.balance_adjustment > 0 ? '+' : ''}${c.balance_adjustment.toFixed(1)}`
                            )}
                          </span>
                          <button
                            type="button"
                            onClick={() => setExplainVehicleId(explainVehicleId === c.vehicle_id ? null : c.vehicle_id)}
                            className="text-[10px] text-accent hover:underline mt-0.5"
                          >
                            Why this vehicle?
                          </button>
                          {explainVehicleId === c.vehicle_id && <MatchExplain candidate={c} />}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )
        })}
      </div>
    </PanelSection>
  )
}
