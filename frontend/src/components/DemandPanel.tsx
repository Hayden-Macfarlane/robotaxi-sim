import { useEffect, useState } from 'react'
import type { ForecastSnap, NetworkPolicySnap, SimCommand, SpecialEventSnap, ZoneBalanceSnap } from '../types/simulation'
import { ZONES } from '../types/routing'
import { PanelSection } from './ui/PanelSection'

interface Props {
  policy: NetworkPolicySnap
  forecast: ForecastSnap[]
  events: SpecialEventSnap[]
  zoneBalance: ZoneBalanceSnap[]
  currentTimeH: number
  onCommand: (cmd: SimCommand) => void
}

function formatZoneLabel(zone: string): string {
  return zone.replace(/_/g, ' ')
}

/** Pricing, zone caps, minimum fleet per zone, vehicle wear, and demand forecast controls. */
export function DemandPanel({ policy, forecast, events, zoneBalance, currentTimeH, onCommand }: Props) {
  const [surge, setSurge] = useState(String(policy.surge_multiplier))
  const [fleet, setFleet] = useState(String(policy.fleet_size))
  const [maxIdle, setMaxIdle] = useState(String(policy.max_idle_per_zone))
  const [downtownCap, setDowntownCap] = useState(String(policy.max_idle_by_zone?.downtown ?? ''))
  const [zoneTargets, setZoneTargets] = useState<Record<string, string>>({})
  const [spillChance, setSpillChance] = useState(String(policy.cleanliness_spill_chance))
  const [lowBattery, setLowBattery] = useState(String(policy.low_battery_pct))
  const [lowClean, setLowClean] = useState(String(policy.low_cleanliness_pct))
  const [label, setLabel] = useState('Concert')
  const [zone, setZone] = useState('east_side')
  const [duration, setDuration] = useState('3')

  useEffect(() => {
    const next: Record<string, string> = {}
    for (const z of ZONES) {
      const val = policy.target_supply_by_zone?.[z]
      next[z] = val != null && val > 0 ? String(val) : ''
    }
    setZoneTargets(next)
  }, [policy.target_supply_by_zone])

  const balanceByZone = Object.fromEntries(zoneBalance.map(row => [row.zone, row]))

  const applyDemand = () => {
    const maxIdleByZone = { ...policy.max_idle_by_zone }
    if (downtownCap) maxIdleByZone.downtown = parseInt(downtownCap, 10)
    const targetSupplyByZone: Record<string, number> = {}
    for (const z of ZONES) {
      const raw = zoneTargets[z]?.trim()
      if (raw) targetSupplyByZone[z] = Math.max(0, parseInt(raw, 10) || 0)
    }
    onCommand({
      type: 'SET_NETWORK_POLICY',
      surge_multiplier: parseFloat(surge) || 1,
      fleet_size: parseInt(fleet, 10) || policy.fleet_size,
      max_idle_per_zone: parseInt(maxIdle, 10) || policy.max_idle_per_zone,
      max_idle_by_zone: maxIdleByZone,
      target_supply_by_zone: targetSupplyByZone,
      cleanliness_spill_chance: parseFloat(spillChance) || policy.cleanliness_spill_chance,
      low_battery_pct: parseFloat(lowBattery) || policy.low_battery_pct,
      low_cleanliness_pct: parseFloat(lowClean) || policy.low_cleanliness_pct,
    })
  }

  const createEvent = () => {
    onCommand({
      type: 'CREATE_SPECIAL_EVENT',
      label,
      zone,
      start_h: currentTimeH,
      end_h: currentTimeH + parseFloat(duration),
      demand_multiplier: 2.5,
    })
  }

  const targetTotal = ZONES.reduce((sum, z) => sum + (parseInt(zoneTargets[z] || '0', 10) || 0), 0)

  return (
    <div className="p-3 pb-4">
      <PanelSection title="Demand">
        <div className="p-3 space-y-4">
          <section className="space-y-2">
            <h3 className="text-xs font-medium uppercase tracking-wide text-text-secondary">Pricing</h3>
            <label className="block space-y-1">
              <span className="text-xs text-text-secondary">Surge multiplier</span>
              <input type="number" step="0.1" min="0.5" max="5" value={surge} onChange={e => setSurge(e.target.value)} className="input-dark" />
            </label>
            <label className="block space-y-1">
              <span className="text-xs text-text-secondary">Fleet size</span>
              <input type="number" min="1" max="200" value={fleet} onChange={e => setFleet(e.target.value)} className="input-dark" />
              <span className="text-[10px] text-text-secondary">Number of robotaxis in simulation</span>
            </label>
          </section>

          <section className="space-y-2">
            <h3 className="text-xs font-medium uppercase tracking-wide text-text-secondary">Minimum vehicles per zone</h3>
            <span className="text-[10px] text-text-secondary block">
              Set how many idle cars each zone should keep. Routing rules use this to reposition into deficits.
            </span>
            <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
              {ZONES.map(z => {
                const row = balanceByZone[z]
                const minVal = parseInt(zoneTargets[z] || '0', 10) || 0
                const belowMin = row != null && minVal > 0 && row.supply < minVal
                return (
                  <div key={z} className="grid grid-cols-[5rem_1fr_3rem] gap-2 items-center">
                    <span className={`text-xs capitalize truncate ${belowMin ? 'text-amber-400' : 'text-text-primary'}`}>{formatZoneLabel(z)}</span>
                    <input
                      type="number"
                      min="0"
                      placeholder="0"
                      value={zoneTargets[z] ?? ''}
                      onChange={e => setZoneTargets(prev => ({ ...prev, [z]: e.target.value }))}
                      className="input-dark py-1 text-xs"
                    />
                    <span className="text-[10px] font-mono text-text-secondary text-right">
                      {row ? `${row.supply} idle` : '—'}
                    </span>
                  </div>
                )
              })}
            </div>
            {targetTotal > parseInt(fleet, 10) && (
              <p className="text-[10px] text-amber-400">
                Zone minimums total {targetTotal} — exceeds fleet size {fleet}.
              </p>
            )}
          </section>

          <section className="space-y-2">
            <h3 className="text-xs font-medium uppercase tracking-wide text-text-secondary">Zone limits</h3>
            <div className="grid grid-cols-2 gap-2">
              <label className="block space-y-1">
                <span className="text-xs text-text-secondary">Max idle per zone</span>
                <input type="number" min="1" value={maxIdle} onChange={e => setMaxIdle(e.target.value)} className="input-dark" />
              </label>
              <label className="block space-y-1">
                <span className="text-xs text-text-secondary">Downtown cap</span>
                <input type="number" min="1" placeholder="global" value={downtownCap} onChange={e => setDowntownCap(e.target.value)} className="input-dark" />
              </label>
            </div>
            <span className="text-[10px] text-text-secondary">Max cars waiting empty in one area</span>
          </section>

          <section className="space-y-2">
            <h3 className="text-xs font-medium uppercase tracking-wide text-text-secondary">Vehicle wear</h3>
            <div className="grid grid-cols-3 gap-2">
              <label className="block space-y-1">
                <span className="text-xs text-text-secondary">Spill chance</span>
                <input type="number" step="0.01" min="0" max="1" value={spillChance} onChange={e => setSpillChance(e.target.value)} className="input-dark" />
              </label>
              <label className="block space-y-1">
                <span className="text-xs text-text-secondary">Low battery %</span>
                <input type="number" min="5" max="50" value={lowBattery} onChange={e => setLowBattery(e.target.value)} className="input-dark" />
              </label>
              <label className="block space-y-1">
                <span className="text-xs text-text-secondary">Low clean %</span>
                <input type="number" min="5" max="50" value={lowClean} onChange={e => setLowClean(e.target.value)} className="input-dark" />
              </label>
            </div>
          </section>

          <button type="button" onClick={applyDemand} className="w-full py-2 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-md transition-colors">
            Save demand settings
          </button>

          <section className="space-y-2 border-t border-border-default pt-3">
            <h3 className="text-xs font-medium uppercase tracking-wide text-text-secondary">Events & forecast</h3>
            <div className="space-y-1 max-h-28 overflow-y-auto">
              {forecast.slice(0, 5).map(row => (
                <div key={row.zone} className="flex justify-between text-xs">
                  <span className="text-text-primary capitalize">{row.zone}</span>
                  <span className="font-mono text-text-secondary">
                    {row.now.toFixed(1)} → {row.t_plus_30.toFixed(1)} (+30m)
                  </span>
                </div>
              ))}
            </div>
            {events.length > 0 && (
              <div className="space-y-1">
                <span className="text-xs text-text-secondary">Active events</span>
                {events.filter(e => e.start_h <= currentTimeH && currentTimeH < e.end_h).map(ev => (
                  <div key={ev.id} className="text-xs text-amber-300">
                    {ev.label} · {ev.zone} ×{ev.demand_multiplier}
                  </div>
                ))}
              </div>
            )}
            <div className="space-y-2 pt-2">
              <span className="text-xs text-text-secondary">Schedule a demand spike</span>
              <input value={label} onChange={e => setLabel(e.target.value)} className="input-dark w-full" placeholder="Event label" />
              <select value={zone} onChange={e => setZone(e.target.value)} className="input-dark w-full">
                {ZONES.map(z => <option key={z} value={z}>{formatZoneLabel(z)}</option>)}
              </select>
              <input type="number" min="1" value={duration} onChange={e => setDuration(e.target.value)} className="input-dark w-full" placeholder="Duration (hours)" />
              <button type="button" onClick={createEvent} className="w-full py-1.5 text-sm bg-surface-raised hover:bg-surface-base border border-border-default rounded-md">
                Add event
              </button>
            </div>
          </section>
        </div>
      </PanelSection>
    </div>
  )
}
