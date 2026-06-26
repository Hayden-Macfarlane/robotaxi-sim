import { useMemo } from 'react'
import type { SimCommand, ZoneBalanceSnap } from '../types/simulation'

interface Props {
  vehicleId: string
  zoneBalance: ZoneBalanceSnap[]
  onCommand: (cmd: SimCommand) => void
  onClose: () => void
}

function formatZone(zone: string): string {
  return zone.replace(/_/g, ' ')
}

/** Modal to pick a destination zone when releasing a vehicle from a facility. */
export function ReleaseZonePicker({ vehicleId, zoneBalance, onCommand, onClose }: Props) {
  const rows = useMemo(
    () => [...zoneBalance].sort((a, b) => b.gap - a.gap),
    [zoneBalance],
  )

  const release = (zone: string) => {
    onCommand({ type: 'RELEASE_FROM_FACILITY', vehicle_id: vehicleId, zone })
    onClose()
  }

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-[2000] bg-black/50"
        aria-label="Close release picker"
        onClick={onClose}
      />
      <aside className="fixed top-0 right-0 bottom-0 z-[2001] w-full max-w-lg bg-surface-base border-l border-border-default flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-default">
          <div>
            <h2 className="text-sm font-semibold text-text-primary">Return to street</h2>
            <p className="text-[10px] text-text-secondary mt-0.5">
              Choose zone for <span className="font-mono text-accent">{vehicleId}</span> — sorted by need (gap)
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-text-secondary hover:text-text-primary text-sm">
            Close
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface-header border-b border-border-default">
              <tr className="text-text-secondary text-left">
                <th className="px-3 py-2 font-medium">Zone</th>
                <th className="px-2 py-2 font-medium text-right">Idle</th>
                <th className="px-2 py-2 font-medium text-right">Orders</th>
                <th className="px-2 py-2 font-medium text-right">Forecast</th>
                <th className="px-2 py-2 font-medium text-right">Gap</th>
                <th className="px-2 py-2 font-medium text-right">Cap</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(row => {
                const atCap = row.supply >= row.max_idle
                const needsCars = row.gap > 0 || row.supply < row.target_supply
                return (
                  <tr
                    key={row.zone}
                    className={`border-b border-border-default/50 ${
                      atCap
                        ? 'opacity-40 cursor-not-allowed'
                        : needsCars
                          ? 'bg-amber-950/20 hover:bg-amber-950/40 cursor-pointer'
                          : 'hover:bg-surface-raised/50 cursor-pointer'
                    }`}
                    onClick={() => !atCap && release(row.zone)}
                    title={atCap ? 'Zone at idle cap' : `Release to ${formatZone(row.zone)}`}
                  >
                    <td className="px-3 py-2 capitalize text-text-primary">{formatZone(row.zone)}</td>
                    <td className="px-2 py-2 text-right font-mono">{row.supply}</td>
                    <td className="px-2 py-2 text-right font-mono">{row.pending_demand}</td>
                    <td className="px-2 py-2 text-right font-mono">{row.expected_demand.toFixed(1)}</td>
                    <td className={`px-2 py-2 text-right font-mono ${row.gap > 0 ? 'text-amber-400' : 'text-text-secondary'}`}>
                      {row.gap.toFixed(1)}
                    </td>
                    <td className="px-2 py-2 text-right font-mono text-text-secondary">{row.max_idle}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {rows.length === 0 && (
            <p className="p-6 text-center text-text-secondary italic text-sm">No zone balance data yet — play the sim.</p>
          )}
        </div>
        <div className="px-3 py-2 border-t border-border-default text-[10px] text-text-secondary">
          Higher gap = more shortage. Amber rows need cars. Disabled rows are at idle cap.
        </div>
      </aside>
    </>
  )
}
