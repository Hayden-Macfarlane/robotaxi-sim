import type { TripSnap } from '../types/simulation'
import { PanelSection } from './ui/PanelSection'
import { StatusBadge } from './ui/StatusBadge'

function formatCoord(lat: number, lon: number): string {
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`
}

interface Props {
  trips: TripSnap[]
}

/** Open trip queue with manual dispatch hook (future: vehicle picker). */
export function TripQueuePanel({ trips }: Props) {
  return (
    <PanelSection title="Trip Queue" count={trips.length}>
      <div className="p-2 space-y-1">
        {trips.length === 0 && (
          <div className="px-2 py-4 text-sm text-text-secondary text-center italic">
            No open trips
          </div>
        )}
        {trips.map(t => (
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
            <div className="text-xs font-mono text-emerald-400">
              ${t.fare_estimate.toFixed(2)}
            </div>
          </div>
        ))}
      </div>
    </PanelSection>
  )
}
