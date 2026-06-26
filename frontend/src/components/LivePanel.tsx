import type { DispatchAssignmentMode, FacilitySnap, KpiSnap, SimCommand, TripSnap, VehicleSnap } from '../types/simulation'
import type { DispatchActionSnap } from '../types/simulation'
import { useUiMode } from '../contexts/UiModeContext'
import { AssetsPanel } from './AssetsPanel'
import { LiveSubTabs } from './LiveSubTabs'
import { OpsLogPanel } from './OpsLogPanel'
import { TripQueuePanel } from './TripQueuePanel'

interface Props {
  vehicles: VehicleSnap[]
  facilities: FacilitySnap[]
  kpis: KpiSnap
  trips: TripSnap[]
  dispatchCandidates: Record<string, import('../types/simulation').DispatchCandidateSnap[]>
  dispatchMode: DispatchAssignmentMode | null
  dispatchActions: DispatchActionSnap[]
  simStartIso: string
  stagingVehicleId: string | null
  selectedVehicleIds: string[]
  highlightVehicleId: string | null
  onSelectVehicle: (id: string | null) => void
  onToggleSelect: (id: string) => void
  onHighlightVehicle: (id: string | null) => void
  onPanToFacility: (lat: number, lon: number) => void
  onRequestRelease: (vehicleId: string) => void
  onCommand: (cmd: SimCommand) => void
}

/** Live operations: fleet table and open order queue. */
export function LivePanel(props: Props) {
  const { liveSubTab, setLiveSubTab, uiMode } = useUiMode()

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      <div className="px-3 py-2 border-b border-border-default bg-surface-raised/30">
        <h2 className="text-sm font-medium text-text-primary">Live operations</h2>
        <p className="text-[10px] text-text-secondary mt-0.5">
          {uiMode === 'standard' ? 'Watch the fleet and handle trips' : 'Fleet status and order queue'}
        </p>
      </div>
      <LiveSubTabs active={liveSubTab} onChange={setLiveSubTab} />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {liveSubTab === 'fleet' && (
          <AssetsPanel
            vehicles={props.vehicles}
            facilities={props.facilities}
            kpis={props.kpis}
            stagingVehicleId={props.stagingVehicleId}
            selectedVehicleIds={props.selectedVehicleIds}
            highlightVehicleId={props.highlightVehicleId}
            onSelectVehicle={props.onSelectVehicle}
            onToggleSelect={props.onToggleSelect}
            onHighlightVehicle={props.onHighlightVehicle}
            onPanToFacility={props.onPanToFacility}
            onRequestRelease={props.onRequestRelease}
            onCommand={props.onCommand}
          />
        )}
        {liveSubTab === 'orders' && (
          <div className="flex flex-col p-3 pb-4 gap-3">
            <TripQueuePanel
              trips={props.trips}
              dispatchCandidates={props.dispatchCandidates}
              dispatchMode={props.dispatchMode}
              onCommand={props.onCommand}
            />
            <OpsLogPanel actions={props.dispatchActions} simStartIso={props.simStartIso} />
          </div>
        )}
      </div>
    </div>
  )
}
