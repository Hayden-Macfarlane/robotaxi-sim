import { useState } from 'react'
import { useSimulation } from './hooks/useSimulation'
import { AssetsPanel } from './components/AssetsPanel'
import { AutomationPanel } from './components/AutomationPanel'
import { CityMap } from './components/CityMap'
import { DemandPanel } from './components/DemandPanel'
import { KpiStrip } from './components/KpiStrip'
import { OpsLogPanel } from './components/OpsLogPanel'
import { TripQueuePanel } from './components/TripQueuePanel'
import { RoutingPanel } from './components/RoutingPanel'
import { SidebarTabs, type SidebarTabId } from './components/ui/SidebarTabs'
import { PlaybackSpeedControl, DEFAULT_PLAYBACK_SPEED } from './components/PlaybackSpeedControl'
import { SimButton } from './components/ui/SimButton'

/** Robotaxi manager control tower shell. */
export default function App() {
  const { snapshot, connected, alert, setAlert, sendCommand } = useSimulation()
  const [activeTab, setActiveTab] = useState<SidebarTabId>('assets')
  const [stagingVehicleId, setStagingVehicleId] = useState<string | null>(null)
  const [selectedVehicleIds, setSelectedVehicleIds] = useState<string[]>([])
  const [highlightVehicleId, setHighlightVehicleId] = useState<string | null>(null)
  const [panTo, setPanTo] = useState<{ lat: number; lon: number } | null>(null)

  const toggleSelect = (vehicleId: string) => {
    setSelectedVehicleIds(prev =>
      prev.includes(vehicleId) ? prev.filter(id => id !== vehicleId) : [...prev, vehicleId],
    )
  }

  const clearStaging = () => {
    setStagingVehicleId(null)
    setSelectedVehicleIds([])
  }

  return (
    <div className="h-full flex flex-col bg-surface-base">
      <header className="flex items-center justify-between px-5 py-3 border-b border-border-default bg-surface-header">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-text-primary tracking-tight">Robotaxi Manager</h1>
          <span className="px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-text-secondary bg-surface-raised border border-border-default rounded">
            {snapshot.city}
          </span>
          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-xs rounded-full border ${
            connected ? 'border-emerald-800 bg-emerald-950/50 text-emerald-300' : 'border-red-800 bg-red-950/50 text-red-300'
          }`}>
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
            {connected ? 'Connected' : 'Offline'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <PlaybackSpeedControl
            speed={snapshot.speed_multiplier || DEFAULT_PLAYBACK_SPEED}
            onCommand={sendCommand}
          />
          <SimButton
            variant="primary"
            onClick={() => sendCommand({ type: 'PLAY', speed: snapshot.speed_multiplier || DEFAULT_PLAYBACK_SPEED })}
          >
            Play
          </SimButton>
          <SimButton onClick={() => sendCommand({ type: 'PAUSE' })}>Pause</SimButton>
          <SimButton onClick={() => sendCommand({ type: 'STEP', hours: 1 })}>+1h</SimButton>
          <SimButton variant="danger" onClick={() => sendCommand({ type: 'RESET_SIMULATION' })}>Reset</SimButton>
        </div>
      </header>

      <KpiStrip
        kpis={snapshot.kpis}
        currentTimeIso={snapshot.current_time_iso}
        currentTimeH={snapshot.current_time_h}
        simStartIso={snapshot.sim_start_iso}
        connected={connected}
      />

      {alert && (
        <div className="px-5 py-2 bg-red-950 border-b border-red-800 text-red-200 text-sm flex justify-between items-center">
          <span>{alert}</span>
          <button type="button" onClick={() => setAlert(null)} className="text-red-300 hover:text-red-100 px-2 py-0.5 rounded hover:bg-red-900/50">Dismiss</button>
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        <div className="flex-1 min-w-0 relative">
          <CityMap
            snapshot={snapshot}
            stagingVehicleId={stagingVehicleId}
            selectedVehicleIds={selectedVehicleIds}
            highlightVehicleId={highlightVehicleId}
            panTo={panTo}
            onCommand={sendCommand}
            onClearStaging={clearStaging}
          />
        </div>
        <aside className="w-96 border-l border-border-default bg-surface-base flex flex-col overflow-hidden">
          <SidebarTabs active={activeTab} onChange={setActiveTab} />
          <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain">
            {activeTab === 'assets' && (
              <AssetsPanel
                vehicles={snapshot.vehicles}
                facilities={snapshot.facilities ?? []}
                kpis={snapshot.kpis}
                stagingVehicleId={stagingVehicleId}
                selectedVehicleIds={selectedVehicleIds}
                highlightVehicleId={highlightVehicleId}
                onSelectVehicle={setStagingVehicleId}
                onToggleSelect={toggleSelect}
                onHighlightVehicle={setHighlightVehicleId}
                onPanToFacility={(lat, lon) => setPanTo({ lat, lon })}
                onCommand={sendCommand}
              />
            )}
            {activeTab === 'routing' && (
              <RoutingPanel
                ruleSet={snapshot.routing_rules ?? { routing_enabled: true, rules: [] }}
                ruleHits={snapshot.routing_rule_hits ?? []}
                onCommand={sendCommand}
              />
            )}
            {activeTab === 'automation' && (
              <AutomationPanel policy={snapshot.policy} onCommand={sendCommand} />
            )}
            {activeTab === 'demand' && (
              <DemandPanel
                policy={snapshot.policy}
                forecast={snapshot.forecast_by_zone ?? []}
                events={snapshot.special_events ?? []}
                zoneBalance={snapshot.zone_balance ?? []}
                currentTimeH={snapshot.current_time_h}
                onCommand={sendCommand}
              />
            )}
            {activeTab === 'activity' && (
              <div className="flex flex-col p-3 pb-4 gap-3">
                <TripQueuePanel trips={snapshot.trips} />
                <OpsLogPanel actions={snapshot.recent_dispatch_actions ?? []} simStartIso={snapshot.sim_start_iso} />
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}
