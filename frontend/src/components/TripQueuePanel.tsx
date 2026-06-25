import { useState } from 'react'
import type {
  DispatchCandidateSnap,
  DispatchAssignmentMode,
  SimCommand,
  TripSnap,
} from '../types/simulation'
import { PanelSection } from './ui/PanelSection'
import { StatusBadge } from './ui/StatusBadge'

function formatCoord(lat: number, lon: number): string {
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`
}

const MODE_LABELS: Record<DispatchAssignmentMode, string> = {
  manual: 'Manual assignment',
  closest_idle_or_repositioning: 'Closest idle or repositioning',
  closest_idle: 'Closest idle only',
}

interface Props {
  trips: TripSnap[]
  dispatchCandidates: Record<string, DispatchCandidateSnap[]>
  dispatchMode: DispatchAssignmentMode | null
  onCommand: (cmd: SimCommand) => void
}

/** Open trip queue with manual dispatch and ranked vehicle suggestions. */
export function TripQueuePanel({ trips, dispatchCandidates, dispatchMode, onCommand }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const isManual = dispatchMode === 'manual'

  const pending = trips.filter(t => t.status === 'pending')

  return (
    <PanelSection title="Trip Queue" count={pending.length}>
      <div className="p-2 space-y-1">
        {pending.length === 0 && (
          <div className="px-2 py-4 text-sm text-text-secondary text-center italic">
            No open trips
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

              {top && isManual && (
                <div className="text-[10px] text-text-secondary mb-1">
                  Suggested:{' '}
                  <span className="text-emerald-300 font-mono">
                    {top.vehicle_id} · {top.eta_min.toFixed(1)} min · {top.state}
                  </span>
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
                    className="text-[10px] text-accent hover:underline"
                  >
                    {expanded ? 'Hide vehicles' : `Assign vehicle (${candidates.length})`}
                  </button>
                  {expanded && (
                    <div className="mt-2 space-y-1">
                      {candidates.length === 0 && (
                        <div className="text-[10px] text-text-secondary italic">No eligible vehicles</div>
                      )}
                      {candidates.map((c, idx) => (
                        <div
                          key={c.vehicle_id}
                          className="flex items-center justify-between gap-2 text-xs bg-surface-raised/50 rounded px-2 py-1"
                        >
                          <span className="font-mono text-text-primary">
                            {idx === 0 && '★ '}
                            {c.vehicle_id}
                            <span className="text-text-secondary ml-1">
                              {c.eta_min.toFixed(1)}m · {c.state}
                            </span>
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
