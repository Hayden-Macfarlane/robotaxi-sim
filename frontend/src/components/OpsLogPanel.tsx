import type { DispatchActionSnap } from '../types/simulation'
import { formatSimTimeShort } from '../lib/simTime'
import { PanelSection } from './ui/PanelSection'

interface Props {
  actions: DispatchActionSnap[]
  simStartIso: string
}

/** Recent manual and automatic fleet dispatch moves. */
export function OpsLogPanel({ actions, simStartIso }: Props) {
  const recent = [...actions].reverse().slice(0, 12)
  return (
    <PanelSection title="Ops Log" count={recent.length}>
      <div className="p-2 max-h-36 overflow-y-auto space-y-1">
        {recent.length === 0 && (
          <p className="text-xs text-text-secondary px-2 py-2 text-center">No dispatch actions yet</p>
        )}
        {recent.map((a, i) => (
          <div key={`${a.vehicle_id}-${a.timestamp_h}-${i}`} className="px-2 py-1.5 text-xs border-b border-border-default/40 last:border-0">
            <div className="flex justify-between gap-2">
              <span className="font-mono text-text-primary">{a.vehicle_id}</span>
              <span className="text-text-secondary">{formatSimTimeShort(a.timestamp_h, simStartIso)}</span>
            </div>
            <div className="text-text-secondary">
              {a.source} · {a.action}
              {a.reason ? ` — ${a.reason}` : ''}
            </div>
          </div>
        ))}
      </div>
    </PanelSection>
  )
}
