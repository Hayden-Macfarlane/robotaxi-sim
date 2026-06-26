import type { NetworkPolicySnap, SimCommand } from '../types/simulation'
import { ZONES } from '../types/routing'
import { PanelSection } from './ui/PanelSection'

interface Props {
  policy: NetworkPolicySnap
  onCommand: (cmd: SimCommand) => void
}

/** Per-zone supply targets, caps, reposition patience, auto-dispatch, and demand weights. */
export function RoutingZonePolicyPanel({ policy, onCommand }: Props) {
  const targets = policy.target_supply_by_zone ?? {}
  const caps = policy.max_idle_by_zone ?? {}
  const patience = policy.reposition_idle_min_by_zone ?? {}
  const autoDispatch = policy.auto_dispatch_by_zone ?? {}
  const demandWeights = policy.zone_demand_weights ?? {}

  const patchZone = (
    field: 'target_supply_by_zone' | 'max_idle_by_zone' | 'reposition_idle_min_by_zone' | 'zone_demand_weights',
    zone: string,
    raw: string,
    asFloat = false,
  ) => {
    const maps = {
      target_supply_by_zone: { ...targets },
      max_idle_by_zone: { ...caps },
      reposition_idle_min_by_zone: { ...patience },
      zone_demand_weights: { ...demandWeights },
    }
    const map = maps[field]
    if (raw === '') {
      delete map[zone]
    } else {
      map[zone] = asFloat ? parseFloat(raw) || 0 : parseInt(raw, 10) || 0
    }
    onCommand({ type: 'SET_NETWORK_POLICY', [field]: map })
  }

  const toggleAutoDispatch = (zone: string, enabled: boolean) => {
    onCommand({
      type: 'SET_NETWORK_POLICY',
      auto_dispatch_by_zone: { ...autoDispatch, [zone]: enabled },
    })
  }

  return (
    <div className="p-3 pb-4 space-y-3 overflow-y-auto">
      <PanelSection title="Global defaults">
        <div className="p-3 grid grid-cols-2 gap-2 text-xs">
          <label className="block space-y-1">
            <span className="text-text-secondary">Default max idle / zone</span>
            <input
              type="number"
              min={0}
              value={policy.max_idle_per_zone}
              onChange={e => onCommand({ type: 'SET_NETWORK_POLICY', max_idle_per_zone: parseInt(e.target.value, 10) || 0 })}
              className="input-dark"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Default reposition patience</span>
            <input
              type="number"
              min={1}
              value={policy.reposition_idle_min}
              onChange={e => onCommand({ type: 'SET_NETWORK_POLICY', reposition_idle_min: parseFloat(e.target.value) || 15 })}
              className="input-dark"
            />
          </label>
        </div>
      </PanelSection>

      <PanelSection title="Per-zone policy" count={ZONES.length}>
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-text-secondary text-left border-b border-border-default">
                <th className="py-1 pr-2">Zone</th>
                <th className="py-1 px-1">Target</th>
                <th className="py-1 px-1">Max idle</th>
                <th className="py-1 px-1">Patience</th>
                <th className="py-1 px-1">Demand wt</th>
                <th className="py-1 pl-1">Auto</th>
              </tr>
            </thead>
            <tbody>
              {ZONES.map(zone => (
                <tr key={zone} className="border-b border-border-default/40">
                  <td className="py-1 pr-2 font-medium capitalize text-text-primary">{zone.replace(/_/g, ' ')}</td>
                  <td className="py-1 px-1">
                    <input
                      type="number"
                      min={0}
                      placeholder="—"
                      value={targets[zone] ?? ''}
                      onChange={e => patchZone('target_supply_by_zone', zone, e.target.value)}
                      className="input-dark w-12"
                    />
                  </td>
                  <td className="py-1 px-1">
                    <input
                      type="number"
                      min={0}
                      placeholder="—"
                      value={caps[zone] ?? ''}
                      onChange={e => patchZone('max_idle_by_zone', zone, e.target.value)}
                      className="input-dark w-12"
                    />
                  </td>
                  <td className="py-1 px-1">
                    <input
                      type="number"
                      min={1}
                      placeholder="—"
                      value={patience[zone] ?? ''}
                      onChange={e => patchZone('reposition_idle_min_by_zone', zone, e.target.value, true)}
                      className="input-dark w-12"
                    />
                  </td>
                  <td className="py-1 px-1">
                    <input
                      type="number"
                      min={0}
                      step={0.1}
                      placeholder="—"
                      value={demandWeights[zone] ?? ''}
                      onChange={e => patchZone('zone_demand_weights', zone, e.target.value, true)}
                      className="input-dark w-12"
                    />
                  </td>
                  <td className="py-1 pl-1 text-center">
                    <input
                      type="checkbox"
                      checked={autoDispatch[zone] !== false}
                      onChange={e => toggleAutoDispatch(zone, e.target.checked)}
                      title="Auto-dispatch trips originating in this zone"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PanelSection>
    </div>
  )
}
