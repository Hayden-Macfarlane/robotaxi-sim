import { useMemo, useState } from 'react'
import type { FacilitySnap, KpiSnap, SimCommand, VehicleSnap } from '../types/simulation'
import { filterVehicles, fleetSummary, facilityOccupancy, minHealthPct, type AssetFilter } from '../lib/fleetStats'
import { facilityKindLabel, healthAlert, statusLabel } from '../lib/vehicleLabels'
import { DataTable, type Column } from './ui/DataTable'
import { MetricPill } from './ui/MetricPill'
import { PanelSection } from './ui/PanelSection'

const OFF_STREET = new Set(['at_depot', 'charging', 'maintenance', 'cleaning'])

interface Props {
  vehicles: VehicleSnap[]
  facilities: FacilitySnap[]
  kpis: KpiSnap
  stagingVehicleId: string | null
  selectedVehicleIds: string[]
  highlightVehicleId: string | null
  onSelectVehicle: (vehicleId: string | null) => void
  onToggleSelect: (vehicleId: string) => void
  onHighlightVehicle: (vehicleId: string | null) => void
  onPanToFacility: (lat: number, lon: number) => void
  onRequestRelease: (vehicleId: string) => void
  onCommand: (cmd: SimCommand) => void
}

const FILTERS: { id: AssetFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'idle', label: 'Idle' },
  { id: 'busy', label: 'Busy' },
  { id: 'needs_service', label: 'Needs service' },
  { id: 'at_facility', label: 'At facility' },
]

function barColor(pct: number): string {
  if (pct <= 25) return 'bg-red-500'
  if (pct <= 50) return 'bg-amber-400'
  return 'bg-emerald-500'
}

function HealthCompact({ v }: { v: VehicleSnap }) {
  const rows = [
    { pct: v.battery_pct },
    { pct: v.condition_pct ?? 100 },
    { pct: v.cleanliness_pct ?? 100 },
  ]
  return (
    <div className="flex gap-0.5 w-16">
      {rows.map((row, i) => (
        <div key={i} className="flex-1 h-2 bg-surface-base rounded-sm overflow-hidden">
          <div className={`h-full ${barColor(row.pct)}`} style={{ width: `${Math.max(0, Math.min(100, row.pct))}%` }} />
        </div>
      ))}
    </div>
  )
}

/** Fleet and facility overview with sortable tables and map selection. */
export function AssetsPanel({
  vehicles,
  facilities,
  kpis,
  stagingVehicleId,
  selectedVehicleIds,
  highlightVehicleId,
  onSelectVehicle,
  onToggleSelect,
  onHighlightVehicle,
  onPanToFacility,
  onRequestRelease,
  onCommand,
}: Props) {
  const [filter, setFilter] = useState<AssetFilter>('all')
  const [sortKey, setSortKey] = useState('id')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const summary = fleetSummary(vehicles, kpis)
  const byKind = (kind: string) => facilities.find(f => f.kind === kind)

  const parkedByFacility = useMemo(() => {
    const out: Record<string, VehicleSnap[]> = {}
    for (const v of vehicles) {
      if (v.facility_id && OFF_STREET.has(v.state)) {
        out[v.facility_id] = out[v.facility_id] ?? []
        out[v.facility_id].push(v)
      }
    }
    return out
  }, [vehicles])

  const filtered = useMemo(() => filterVehicles(vehicles, filter), [vehicles, filter])

  const sorted = useMemo(() => {
    const rows = [...filtered]
    rows.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'status':
          cmp = statusLabel(a.state).localeCompare(statusLabel(b.state))
          break
        case 'zone':
          cmp = (a.zone ?? '').localeCompare(b.zone ?? '')
          break
        case 'health':
          cmp = minHealthPct(a) - minHealthPct(b)
          break
        default:
          cmp = a.id.localeCompare(b.id)
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
    return rows
  }, [filtered, sortKey, sortDir])

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const vehicleColumns: Column<VehicleSnap>[] = [
    {
      key: 'select',
      header: '',
      render: v => {
        const canStage = v.state === 'idle'
        return canStage ? (
          <input
            type="checkbox"
            checked={selectedVehicleIds.includes(v.id)}
            onChange={e => {
              e.stopPropagation()
              onToggleSelect(v.id)
            }}
            className="checkbox-dark"
          />
        ) : null
      },
      className: 'w-6',
    },
    {
      key: 'id',
      header: 'ID',
      sortable: true,
      render: v => <span className="font-mono text-text-primary">{v.id}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: v => <span className="text-text-secondary">{statusLabel(v.state)}</span>,
    },
    {
      key: 'zone',
      header: 'Zone',
      sortable: true,
      render: v => <span className="capitalize text-text-secondary">{v.zone ?? '—'}</span>,
    },
    {
      key: 'health',
      header: 'Health',
      sortable: true,
      render: v => <HealthCompact v={v} />,
    },
    {
      key: 'alert',
      header: 'Alert',
      render: v => {
        const alert = healthAlert(v)
        return alert ? <span className="text-amber-400">{alert}</span> : null
      },
    },
    {
      key: 'actions',
      header: '',
      render: v => {
        const atFacility = OFF_STREET.has(v.state)
        return (
          <div className="flex gap-1 flex-wrap justify-end" onClick={e => e.stopPropagation()}>
            {v.state === 'idle' && (
              <>
                <button
                  type="button"
                  title="Stage on map"
                  onClick={() => onSelectVehicle(stagingVehicleId === v.id ? null : v.id)}
                  className="px-1 py-0.5 text-[10px] text-accent hover:bg-accent/20 rounded"
                >
                  Stage
                </button>
                {byKind('charger') && (
                  <button type="button" title="Send to charger" onClick={() => onCommand({ type: 'SEND_TO_FACILITY', vehicle_id: v.id, facility_id: byKind('charger')!.id })} className="px-1 py-0.5 text-[10px] text-text-secondary hover:text-yellow-400 rounded">Charge</button>
                )}
                {byKind('cleaning') && (
                  <button type="button" title="Send to cleaning" onClick={() => onCommand({ type: 'SEND_TO_FACILITY', vehicle_id: v.id, facility_id: byKind('cleaning')!.id })} className="px-1 py-0.5 text-[10px] text-text-secondary hover:text-blue-400 rounded">Clean</button>
                )}
                {byKind('maintenance') && (
                  <button type="button" title="Send to maintenance" onClick={() => onCommand({ type: 'SEND_TO_FACILITY', vehicle_id: v.id, facility_id: byKind('maintenance')!.id })} className="px-1 py-0.5 text-[10px] text-text-secondary hover:text-orange-400 rounded">Service</button>
                )}
                {byKind('depot') && (
                  <button type="button" title="Send to depot" onClick={() => onCommand({ type: 'SEND_TO_FACILITY', vehicle_id: v.id, facility_id: byKind('depot')!.id })} className="px-1 py-0.5 text-[10px] text-text-secondary hover:text-text-primary rounded">Depot</button>
                )}
              </>
            )}
            {v.state === 'repositioning' && (
              <>
                <button type="button" title="Restage on map" onClick={() => onSelectVehicle(stagingVehicleId === v.id ? null : v.id)} className="px-1 py-0.5 text-[10px] text-accent hover:bg-accent/20 rounded">Stage</button>
                {byKind('depot') && (
                  <button type="button" onClick={() => onCommand({ type: 'SEND_TO_FACILITY', vehicle_id: v.id, facility_id: byKind('depot')!.id })} className="px-1 py-0.5 text-[10px] text-text-secondary rounded">Depot</button>
                )}
              </>
            )}
            {atFacility && (
              <button
                type="button"
                title="Route out to a zone you choose"
                onClick={() => onRequestRelease(v.id)}
                className="px-1 py-0.5 text-[10px] text-emerald-400 hover:text-emerald-300 rounded"
              >
                Return to street
              </button>
            )}
          </div>
        )
      },
      className: 'text-right',
    },
  ]

  const facilityColumns: Column<FacilitySnap>[] = [
    {
      key: 'name',
      header: 'Name',
      render: f => <span className="text-text-primary">{f.name || f.id}</span>,
    },
    {
      key: 'type',
      header: 'Type',
      render: f => <span className="text-text-secondary">{facilityKindLabel(f.kind)}</span>,
    },
    {
      key: 'parked',
      header: 'Parked',
      render: f => {
        const parked = parkedByFacility[f.id] ?? []
        if (parked.length === 0) return <span className="text-text-secondary">—</span>
        return (
          <div className="flex flex-col gap-0.5">
            {parked.map(v => (
              <div key={v.id} className="flex items-center gap-1">
                <span className="font-mono text-[10px]">{v.id}</span>
                <button type="button" onClick={e => { e.stopPropagation(); onRequestRelease(v.id) }} className="text-[10px] text-emerald-400 hover:underline">Return to street</button>
              </div>
            ))}
          </div>
        )
      },
    },
    {
      key: 'occupancy',
      header: 'Occ',
      render: f => {
        const occ = facilityOccupancy(f.id, vehicles)
        return <span className="font-mono text-text-secondary">{occ}/{f.capacity}</span>
      },
    },
    {
      key: 'location',
      header: 'Location',
      render: f => <span className="font-mono text-text-secondary text-[10px]">{f.lat.toFixed(3)}, {f.lon.toFixed(3)}</span>,
    },
  ]

  return (
    <div className="pb-4">
      <div className="p-3 space-y-3">
        <div className="flex gap-2">
          <MetricPill label="On street" value={summary.onStreet} accent="blue" />
          <MetricPill label="Serving" value={summary.serving} accent="emerald" />
          <MetricPill label="Needs attention" value={summary.needsAttention} accent="amber" />
          <MetricPill label="At facilities" value={summary.atFacilities} />
        </div>
        <div className="flex flex-wrap gap-1">
          {FILTERS.map(f => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={`px-2 py-0.5 text-[10px] rounded-full border transition-colors ${
                filter === f.id
                  ? 'bg-accent/20 border-accent text-accent'
                  : 'border-border-default text-text-secondary hover:text-text-primary'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-3 space-y-4">
      <PanelSection title="Vehicles" count={sorted.length}>
        <div className="p-2">
          <DataTable
            columns={vehicleColumns}
            rows={sorted}
            rowKey={v => v.id}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={handleSort}
            selectedKey={highlightVehicleId ?? stagingVehicleId}
            onSelectRow={v => {
              onHighlightVehicle(v.id)
              if (v.state === 'idle' || v.state === 'repositioning') {
                onSelectVehicle(v.id)
              }
            }}
            emptyMessage="No vehicles match this filter"
          />
          {stagingVehicleId && (
            <p className="pt-2 text-xs text-accent">
              {stagingVehicleId} selected — click anywhere on the map to stage
            </p>
          )}
          {selectedVehicleIds.length > 0 && (
            <p className="pt-2 text-xs text-accent">{selectedVehicleIds.length} selected — click map to stage</p>
          )}
        </div>
      </PanelSection>

      <PanelSection title="Facilities" count={facilities.length}>
        <div className="p-2">
          <DataTable
            columns={facilityColumns}
            rows={facilities}
            rowKey={f => f.id}
            onSelectRow={f => onPanToFacility(f.lat, f.lon)}
            emptyMessage="No facilities"
          />
        </div>
      </PanelSection>
      </div>
    </div>
  )
}
