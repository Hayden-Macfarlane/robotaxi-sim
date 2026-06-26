import { useState } from 'react'
import type { ForecastSnap, NetworkPolicySnap, SimCommand, SpecialEventSnap } from '../types/simulation'
import { ZONES } from '../types/routing'
import { FieldLabel } from './ui/FieldLabel'
import { PanelSection } from './ui/PanelSection'
import { PolicyLink } from './ui/PolicyLink'

interface Props {
  policy: NetworkPolicySnap
  forecast: ForecastSnap[]
  events: SpecialEventSnap[]
  currentTimeH: number
  onCommand: (cmd: SimCommand) => void
}

function formatZoneLabel(zone: string): string {
  return zone.replace(/_/g, ' ')
}

/** Market pricing, demand rate, vehicle wear, and special events. */
export function MarketDemandPanel({ policy, forecast, events, currentTimeH, onCommand }: Props) {
  const [surge, setSurge] = useState(String(policy.surge_multiplier))
  const [fleet, setFleet] = useState(String(policy.fleet_size))
  const [baseTrips, setBaseTrips] = useState(String(policy.base_trips_per_hour ?? 24))
  const [spillChance, setSpillChance] = useState(String(policy.cleanliness_spill_chance))
  const [lowBattery, setLowBattery] = useState(String(policy.low_battery_pct))
  const [lowClean, setLowClean] = useState(String(policy.low_cleanliness_pct))
  const [label, setLabel] = useState('Concert')
  const [zone, setZone] = useState('east_side')
  const [duration, setDuration] = useState('3')
  const [eventMult, setEventMult] = useState('2.5')

  const applyMarket = () => {
    onCommand({
      type: 'SET_NETWORK_POLICY',
      surge_multiplier: parseFloat(surge) || 1,
      fleet_size: parseInt(fleet, 10) || policy.fleet_size,
      base_trips_per_hour: parseFloat(baseTrips) || 24,
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
      demand_multiplier: parseFloat(eventMult) || 2.5,
    })
  }

  return (
    <div className="p-3 pb-4 space-y-3 overflow-y-auto">
      <PanelSection
        title="Pricing & fleet"
        subtitle="Market & demand"
        impact="How many trips spawn and what riders pay."
      >
        <div className="p-3 space-y-3 text-xs">
          <FieldLabel termId="base_trips_per_hour">
            <input type="number" min={0} max={500} value={baseTrips} onChange={e => setBaseTrips(e.target.value)} className="input-dark w-full mt-1" />
          </FieldLabel>
          <FieldLabel termId="surge_multiplier">
            <input type="number" step={0.1} min={0.5} max={5} value={surge} onChange={e => setSurge(e.target.value)} className="input-dark w-full mt-1" />
          </FieldLabel>
          <label className="block space-y-1">
            <span className="text-text-secondary">Base fare ($)</span>
            <input type="number" min={0} step={0.5} defaultValue={policy.base_fare} onBlur={e => onCommand({ type: 'SET_NETWORK_POLICY', base_fare: parseFloat(e.target.value) || policy.base_fare })} className="input-dark w-full" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Fleet size</span>
            <input type="number" min={1} max={200} value={fleet} onChange={e => setFleet(e.target.value)} className="input-dark w-full" />
            <span className="text-[10px] text-text-secondary">Number of robotaxis in the simulation</span>
          </label>
          <button type="button" onClick={applyMarket} className="w-full py-2 bg-accent text-white text-sm font-medium rounded-md">
            Save market settings
          </button>
        </div>
      </PanelSection>

      <PanelSection title="Supply by zone" impact="Zone floors and caps are configured separately.">
        <p className="p-3 text-xs text-text-secondary">
          Minimum idle cars and zone caps: <PolicyLink subTab="supply" />
        </p>
      </PanelSection>

      <PanelSection title="Vehicle wear" impact="When vehicles need cleaning, charging, or service.">
        <div className="p-3 grid grid-cols-3 gap-2 text-xs">
          <label className="block space-y-1">
            <span className="text-text-secondary">Spill chance</span>
            <input type="number" step={0.01} min={0} max={1} value={spillChance} onChange={e => setSpillChance(e.target.value)} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Low battery %</span>
            <input type="number" min={5} max={50} value={lowBattery} onChange={e => setLowBattery(e.target.value)} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Low clean %</span>
            <input type="number" min={5} max={50} value={lowClean} onChange={e => setLowClean(e.target.value)} className="input-dark" />
          </label>
        </div>
      </PanelSection>

      <PanelSection title="Events & forecast" impact="Demand spikes and short-term forecast preview.">
        <div className="p-3 space-y-2 text-xs">
          <div className="space-y-1 max-h-28 overflow-y-auto">
            {forecast.slice(0, 5).map(row => (
              <div key={row.zone} className="flex justify-between">
                <span className="text-text-primary capitalize">{formatZoneLabel(row.zone)}</span>
                <span className="font-mono text-text-secondary">
                  {row.now.toFixed(1)} → {row.t_plus_30.toFixed(1)} (+30m)
                </span>
              </div>
            ))}
          </div>
          {events.map(ev => (
            <div key={ev.id} className="flex justify-between items-center gap-2">
              <span className="text-amber-300 truncate">{ev.label} · {ev.zone} ×{ev.demand_multiplier}</span>
              <button type="button" onClick={() => onCommand({ type: 'DELETE_SPECIAL_EVENT', event_id: ev.id })} className="text-red-400 shrink-0">Del</button>
            </div>
          ))}
          <input value={label} onChange={e => setLabel(e.target.value)} className="input-dark w-full" placeholder="Event label" />
          <select value={zone} onChange={e => setZone(e.target.value)} className="input-dark w-full">
            {ZONES.map(z => <option key={z} value={z}>{formatZoneLabel(z)}</option>)}
          </select>
          <input type="number" min={1} value={duration} onChange={e => setDuration(e.target.value)} className="input-dark w-full" placeholder="Duration (hours)" />
          <input type="number" min={1} max={10} step={0.1} value={eventMult} onChange={e => setEventMult(e.target.value)} className="input-dark w-full" placeholder="Demand multiplier" />
          <button type="button" onClick={createEvent} className="w-full py-1.5 text-sm bg-surface-raised hover:bg-surface-base border border-border-default rounded-md">
            Add demand event
          </button>
        </div>
      </PanelSection>
    </div>
  )
}
