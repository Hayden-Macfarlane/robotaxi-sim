import { useState } from 'react'
import { useSimulation } from './hooks/useSimulation'
import { UiModeProvider, useUiMode } from './contexts/UiModeContext'
import { CityMap } from './components/CityMap'
import { KpiStrip } from './components/KpiStrip'
import { LivePanel } from './components/LivePanel'
import { RulesHubPanel } from './components/rules/RulesHubPanel'
import { SimSettingsDrawer } from './components/rules/SimSettingsDrawer'
import { GlossaryDrawer } from './components/GlossaryDrawer'
import { ReleaseZonePicker } from './components/ReleaseZonePicker'
import { SidebarTabs } from './components/ui/SidebarTabs'
import { PlaybackSpeedControl, DEFAULT_PLAYBACK_SPEED } from './components/PlaybackSpeedControl'
import { SimButton } from './components/ui/SimButton'

/** Inner shell — requires UiModeProvider. */
function AppShell() {
  const { snapshot, connected, connecting, alert, setAlert, sendCommand } = useSimulation()
  const { activeTab, setActiveTab, uiMode, setUiMode, setGlossaryOpen } = useUiMode()
  const [stagingVehicleId, setStagingVehicleId] = useState<string | null>(null)
  const [selectedVehicleIds, setSelectedVehicleIds] = useState<string[]>([])
  const [highlightVehicleId, setHighlightVehicleId] = useState<string | null>(null)
  const [releaseVehicleId, setReleaseVehicleId] = useState<string | null>(null)
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

  const selectVehicleForStaging = (vehicleId: string | null) => {
    setStagingVehicleId(vehicleId)
    if (vehicleId) {
      const v = snapshot.vehicles.find(x => x.id === vehicleId)
      if (v) setPanTo({ lat: v.lat, lon: v.lon })
    }
  }

  const operatorSetup = snapshot.operator_setup ?? {
    setup_complete: true,
    dispatch_assignment_mode: 'closest_idle_or_repositioning',
    advanced_automation_enabled: false,
    routing_engine_version: 'v2',
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
            connected ? 'border-emerald-800 bg-emerald-950/50 text-emerald-300' : connecting ? 'border-amber-800 bg-amber-950/50 text-amber-300' : 'border-red-800 bg-red-950/50 text-red-300'
          }`}>
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : connecting ? 'bg-amber-400 animate-pulse' : 'bg-red-400'}`} />
            {connected ? 'Connected' : connecting ? 'Connecting…' : 'Offline'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border border-border-default overflow-hidden text-xs">
            <button
              type="button"
              onClick={() => setUiMode('standard')}
              className={`px-2.5 py-1.5 transition-colors ${uiMode === 'standard' ? 'bg-accent text-white' : 'bg-surface-raised text-text-secondary hover:text-text-primary'}`}
            >
              Standard
            </button>
            <button
              type="button"
              onClick={() => setUiMode('expert')}
              className={`px-2.5 py-1.5 transition-colors ${uiMode === 'expert' ? 'bg-accent text-white' : 'bg-surface-raised text-text-secondary hover:text-text-primary'}`}
            >
              Expert
            </button>
          </div>
          <button
            type="button"
            onClick={() => setGlossaryOpen(true)}
            className="px-2.5 py-1.5 text-xs rounded border border-border-default bg-surface-raised hover:bg-surface-base text-text-secondary hover:text-text-primary"
          >
            Fleet glossary
          </button>
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

      {(alert || (snapshot.operator_alerts?.length ?? 0) > 0) && (
        <div className="px-5 py-2 bg-red-950 border-b border-red-800 text-red-200 text-sm flex flex-col gap-1">
          {alert && (
            <div className="flex justify-between items-center">
              <span>{alert}</span>
              <button type="button" onClick={() => setAlert(null)} className="text-red-300 hover:text-red-100 px-2 py-0.5 rounded hover:bg-red-900/50">Dismiss</button>
            </div>
          )}
          {snapshot.operator_alerts?.map(a => (
            <div key={a.code} className={a.level === 'info' ? 'text-amber-200' : 'text-red-200'}>{a.message}</div>
          ))}
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        <div className="flex-1 min-w-0 relative">
          <CityMap
            snapshot={snapshot}
            connected={connected}
            connecting={connecting}
            stagingVehicleId={stagingVehicleId}
            selectedVehicleIds={selectedVehicleIds}
            highlightVehicleId={highlightVehicleId}
            panTo={panTo}
            onCommand={sendCommand}
            onClearStaging={clearStaging}
            onSelectVehicle={selectVehicleForStaging}
            onRequestRelease={setReleaseVehicleId}
          />
        </div>
        <aside className="w-96 border-l border-border-default bg-surface-base flex flex-col overflow-hidden">
          <SidebarTabs active={activeTab} onChange={setActiveTab} />
          <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain">
            {activeTab === 'rules' && (
              <RulesHubPanel
                playbook={snapshot.playbook_v2 ?? { enabled: true, constants: {}, rules: [] }}
                ruleHits={snapshot.rule_hits_v2 ?? []}
                metricCatalog={snapshot.metric_catalog ?? []}
                constantCatalog={snapshot.constant_catalog ?? []}
                actionCatalog={snapshot.action_catalog ?? []}
                selectionCatalog={snapshot.selection_catalog ?? []}
                ruleTemplates={snapshot.rule_templates ?? []}
                routingEngineVersion={operatorSetup.routing_engine_version ?? 'v2'}
                onCommand={sendCommand}
                onHighlightVehicle={setHighlightVehicleId}
              />
            )}
            {activeTab === 'live' && (
              <LivePanel
                vehicles={snapshot.vehicles}
                facilities={snapshot.facilities ?? []}
                kpis={snapshot.kpis}
                trips={snapshot.trips}
                dispatchCandidates={snapshot.dispatch_candidates ?? {}}
                dispatchMode={operatorSetup.dispatch_assignment_mode}
                dispatchActions={snapshot.recent_dispatch_actions ?? []}
                ruleHitsV2={snapshot.rule_hits_v2 ?? []}
                simStartIso={snapshot.sim_start_iso}
                stagingVehicleId={stagingVehicleId}
                selectedVehicleIds={selectedVehicleIds}
                highlightVehicleId={highlightVehicleId}
                onSelectVehicle={selectVehicleForStaging}
                onToggleSelect={toggleSelect}
                onHighlightVehicle={setHighlightVehicleId}
                onPanToFacility={(lat, lon) => setPanTo({ lat, lon })}
                onRequestRelease={setReleaseVehicleId}
                onCommand={sendCommand}
              />
            )}
          </div>
        </aside>
      </div>
      <SimSettingsDrawer
        policy={snapshot.policy}
        operatorSetup={operatorSetup}
        forecast={snapshot.forecast_by_zone ?? []}
        events={snapshot.special_events ?? []}
        currentTimeH={snapshot.current_time_h}
        kpis={snapshot.kpis}
        kpiSeries={snapshot.kpi_series ?? []}
        experimentRuns={snapshot.experiment_runs ?? []}
        operatorPresets={snapshot.operator_presets ?? []}
        seed={snapshot.seed ?? 42}
        onCommand={sendCommand}
      />
      <GlossaryDrawer />
      {releaseVehicleId && (
        <ReleaseZonePicker
          vehicleId={releaseVehicleId}
          zoneBalance={snapshot.zone_balance ?? []}
          onCommand={sendCommand}
          onClose={() => setReleaseVehicleId(null)}
        />
      )}
    </div>
  )
}

/** Robotaxi manager control tower shell. */
export default function App() {
  return (
    <UiModeProvider>
      <AppShell />
    </UiModeProvider>
  )
}
