import { useMemo, useRef, useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, Marker, Polygon, useMapEvents, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { FacilitySnap, SimCommand, SimulationSnapshot, VehicleSnap, ZoneBalanceSnap, ZoneOverlaySnap } from '../types/simulation'

const STATE_COLOR: Record<string, string> = {
  idle: '#22d3ee',
  to_pickup: '#fbbf24',
  with_rider: '#34d399',
  repositioning: '#a78bfa',
  at_depot: '#64748b',
  charging: '#eab308',
  maintenance: '#f97316',
  cleaning: '#60a5fa',
}

const LEGEND_ITEMS = [
  { color: '#64748b', label: 'Road Network' },
  { color: '#f97316', label: 'Zone deficit / below min' },
  { color: '#ef4444', label: 'Zone at cap' },
  { color: '#38bdf8', label: 'Zone surplus' },
  { color: STATE_COLOR.idle, label: 'Idle' },
  { color: '#a855f7', label: 'Depot / Charger' },
  { color: '#ec4899', label: 'Waiting Rider' },
]

function formatCoord(lat: number, lon: number): string {
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`
}

function vehicleIcon(v: VehicleSnap, draggable: boolean, highlighted: boolean) {
  const color = STATE_COLOR[v.state] ?? '#fff'
  const heading = v.heading_deg ?? 0
  const ring = highlighted
    ? 'box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.9), 0 0 8px rgba(56, 189, 248, 0.6); border-radius: 50%;'
    : ''
  return L.divIcon({
    className: '',
    html: `<div style="${ring} display:inline-block;">
      <div style="
        width:0;height:0;
        border-left:7px solid transparent;
        border-right:7px solid transparent;
        border-bottom:14px solid ${color};
        transform: rotate(${heading}deg);
        transform-origin: center 70%;
        filter: drop-shadow(0 1px 2px rgba(0,0,0,0.45));
        ${draggable ? 'cursor: grab;' : ''}
      "></div>
    </div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

function facilityIcon(kind: string) {
  const colors: Record<string, string> = {
    charger: '#eab308',
    depot: '#a855f7',
    cleaning: '#60a5fa',
    maintenance: '#f97316',
  }
  const color = colors[kind] ?? '#a855f7'
  return L.divIcon({
    className: '',
    html: `<div style="width:12px;height:12px;border-radius:2px;background:${color};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.4);"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  })
}

function zoneStatusColor(row: ZoneBalanceSnap): string {
  if (row.supply >= row.max_idle) return '#ef4444'
  if (row.gap > 0.5 || row.supply < row.target_supply) return '#f97316'
  if (row.gap < -0.5) return '#38bdf8'
  return '#64748b'
}

interface MapClickProps {
  stagingVehicleId: string | null
  selectedVehicleIds: string[]
  onStage: (lat: number, lon: number) => void
}

function MapClickHandler({ stagingVehicleId, selectedVehicleIds, onStage }: MapClickProps) {
  useMapEvents({
    click(e) {
      if (!stagingVehicleId && selectedVehicleIds.length === 0) return
      onStage(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

interface MapPanProps {
  panTo: { lat: number; lon: number } | null
}

function MapPanHandler({ panTo }: MapPanProps) {
  const map = useMap()
  useEffect(() => {
    if (panTo) map.flyTo([panTo.lat, panTo.lon], map.getZoom(), { duration: 0.6 })
  }, [map, panTo])
  return null
}

interface DraggableVehicleProps {
  vehicle: VehicleSnap
  draggable: boolean
  highlighted: boolean
  onDragEnd: (vehicleId: string, lat: number, lon: number) => void
}

function DraggableVehicleMarker({ vehicle, draggable, highlighted, onDragEnd }: DraggableVehicleProps) {
  const markerRef = useRef<L.Marker>(null)
  return (
    <Marker
      ref={markerRef}
      position={[vehicle.lat, vehicle.lon]}
      icon={vehicleIcon(vehicle, draggable, highlighted)}
      draggable={draggable}
      zIndexOffset={highlighted ? 1000 : 0}
      eventHandlers={{
        dragend: () => {
          const m = markerRef.current
          if (!m) return
          const pos = m.getLatLng()
          onDragEnd(vehicle.id, pos.lat, pos.lng)
        },
      }}
    >
      <Popup>
        <span className="font-mono">{vehicle.id}</span>
        <br />
        <span className="text-text-secondary">{vehicle.state.replace(/_/g, ' ')}</span>
        {vehicle.battery_pct != null && (
          <>
            <br />
            <span className="text-xs">Battery {vehicle.battery_pct.toFixed(0)}%</span>
            <br />
            <span className="text-xs">Condition {(vehicle.condition_pct ?? 100).toFixed(0)}%</span>
            <br />
            <span className="text-xs">Clean {(vehicle.cleanliness_pct ?? 100).toFixed(0)}%</span>
          </>
        )}
        <br />
        <span className="font-mono text-xs">{formatCoord(vehicle.lat, vehicle.lon)}</span>
      </Popup>
    </Marker>
  )
}

interface Props {
  snapshot: SimulationSnapshot
  stagingVehicleId: string | null
  selectedVehicleIds: string[]
  highlightVehicleId?: string | null
  panTo?: { lat: number; lon: number } | null
  onCommand: (cmd: SimCommand) => void
  onClearStaging: () => void
}

/** Leaflet map with zone overlays, facilities, drag-to-stage, and click-to-stage. */
export function CityMap({
  snapshot,
  stagingVehicleId,
  selectedVehicleIds,
  highlightVehicleId = null,
  panTo = null,
  onCommand,
  onClearStaging,
}: Props) {
  const nodes = snapshot.nodes
  const zoneRows: ZoneBalanceSnap[] = snapshot.zone_balance ?? []
  const zoneOverlays: ZoneOverlaySnap[] = snapshot.zone_overlays ?? []
  const balanceByZone = useMemo(() => {
    const out: Record<string, ZoneBalanceSnap> = {}
    for (const row of zoneRows) out[row.zone] = row
    return out
  }, [zoneRows])
  const facilities: FacilitySnap[] = snapshot.facilities ?? []

  if (nodes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-surface-base text-text-secondary text-sm">
        Loading map…
      </div>
    )
  }

  const lats = nodes.map(n => n.lat)
  const lons = nodes.map(n => n.lon)
  const center: [number, number] = [
    (Math.min(...lats) + Math.max(...lats)) / 2,
    (Math.min(...lons) + Math.max(...lons)) / 2,
  ]

  const handleStage = (lat: number, lon: number) => {
    if (selectedVehicleIds.length > 0) {
      onCommand({ type: 'STAGE_VEHICLES', vehicle_ids: selectedVehicleIds, lat, lon })
      onClearStaging()
      return
    }
    if (!stagingVehicleId) return
    onCommand({ type: 'REPOSITION_VEHICLE', vehicle_id: stagingVehicleId, lat, lon })
    onClearStaging()
  }

  const handleDragEnd = (vehicleId: string, lat: number, lon: number) => {
    onCommand({ type: 'REPOSITION_VEHICLE', vehicle_id: vehicleId, lat, lon })
  }

  const streetLines = (snapshot.streets ?? []).map((line, i) => (
    <Polyline
      key={`street-${i}`}
      positions={line as [number, number][]}
      pathOptions={{ color: '#64748b', weight: 1.5, opacity: 0.35 }}
    />
  ))

  const zonePolygons = zoneOverlays.flatMap(overlay => {
    const row = balanceByZone[overlay.zone]
    const borderColor = row ? zoneStatusColor(row) : '#64748b'
    const fillOpacity = overlay.kind === 'poi' ? 0.22 : 0.14
    return overlay.polygons.map((ring, ringIdx) => (
      <Polygon
        key={`zone-${overlay.zone}-${ringIdx}`}
        positions={ring as [number, number][]}
        pathOptions={{
          color: borderColor,
          fillColor: overlay.color,
          fillOpacity,
          weight: row && (row.gap > 0.5 || row.supply >= row.max_idle || row.supply < row.target_supply) ? 2.5 : 1.5,
          opacity: 0.75,
        }}
      >
        {ringIdx === 0 && (
          <Popup>
            <span className="font-medium capitalize">{overlay.zone.replace(/_/g, ' ')}</span>
            {row ? (
              <>
                <br />
                Idle: {row.supply}/{row.max_idle} · Min target: {row.target_supply}
                <br />
                Pending: {row.pending_demand} · Expected: {row.expected_demand.toFixed(1)}
                <br />
                Gap: {row.gap.toFixed(1)}
              </>
            ) : (
              <>
                <br />
                <span className="text-xs text-text-secondary capitalize">{overlay.kind} zone</span>
              </>
            )}
          </Popup>
        )}
      </Polygon>
    ))
  })

  const facilityMarkers = facilities.map(f => (
    <Marker key={f.id} position={[f.lat, f.lon]} icon={facilityIcon(f.kind)}>
      <Popup>
        <span className="font-medium">{f.name || f.id}</span>
        <br />
        <span className="capitalize">{f.kind}</span> · cap {f.capacity}
      </Popup>
    </Marker>
  ))

  const vehicleMarkers = snapshot.vehicles
    .filter(v => !['at_depot', 'charging', 'maintenance', 'cleaning'].includes(v.state))
    .map(v => {
      const draggable = v.state === 'idle' && (stagingVehicleId === v.id || selectedVehicleIds.includes(v.id))
      const highlighted = highlightVehicleId === v.id || stagingVehicleId === v.id || selectedVehicleIds.includes(v.id)
      return (
        <DraggableVehicleMarker
          key={v.id}
          vehicle={v}
          draggable={draggable}
          highlighted={highlighted}
          onDragEnd={handleDragEnd}
        />
      )
    })

  const routePolylines = snapshot.vehicles
    .filter(v => v.route_polyline && v.route_polyline.length >= 2)
    .map(v => (
      <Polyline
        key={`route-${v.id}`}
        positions={v.route_polyline as [number, number][]}
        pathOptions={{
          color: STATE_COLOR[v.state] ?? '#94a3b8',
          weight: 4,
          opacity: 0.85,
        }}
      />
    ))

  const riderMarkers = (snapshot.riders ?? []).map(r => (
    <CircleMarker
      key={`rider-${r.id}`}
      center={[r.lat, r.lon]}
      radius={7}
      pathOptions={{ color: '#ec4899', fillColor: '#f472b6', fillOpacity: 0.9, weight: 2 }}
    >
      <Popup>
        <span className="font-mono">{r.id}</span>
        <br />
        <span className="text-emerald-400">${r.fare_estimate.toFixed(2)}</span>
      </Popup>
    </CircleMarker>
  ))

  const stagingActive = stagingVehicleId || selectedVehicleIds.length > 0

  return (
    <div className="relative h-full w-full">
      {stagingActive && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] px-4 py-2 bg-accent/90 text-white text-sm rounded-lg shadow-lg">
          {selectedVehicleIds.length > 0
            ? `Staging ${selectedVehicleIds.length} vehicles — click map`
            : `Override: drag or click to stage ${stagingVehicleId}`}
        </div>
      )}
      <MapContainer center={center} zoom={12} className="h-full w-full" zoomControl={false}>
        <TileLayer
          attribution='&copy; CARTO &copy; OpenStreetMap'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        {zonePolygons}
        {streetLines}
        {routePolylines}
        {riderMarkers}
        {facilityMarkers}
        {vehicleMarkers}
        <MapClickHandler
          stagingVehicleId={stagingVehicleId}
          selectedVehicleIds={selectedVehicleIds}
          onStage={handleStage}
        />
        <MapPanHandler panTo={panTo} />
      </MapContainer>

      <div className="absolute bottom-4 left-4 z-[1000] bg-surface-raised/95 border border-border-default rounded-lg px-3 py-2 shadow-lg backdrop-blur-sm">
        <div className="text-xs font-medium uppercase tracking-wider text-text-secondary mb-2">Legend</div>
        <div className="space-y-1.5">
          {LEGEND_ITEMS.map(item => (
            <div key={item.label} className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
              <span className="text-xs text-text-primary">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
