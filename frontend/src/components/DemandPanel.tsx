import type { ForecastSnap, NetworkPolicySnap, OperatorSetupSnap, SimCommand, SpecialEventSnap, ZoneBalanceSnap } from '../types/simulation'
import { PolicyLink } from './ui/PolicyLink'
import { PanelSection } from './ui/PanelSection'

interface Props {
  policy: NetworkPolicySnap
  forecast: ForecastSnap[]
  events: SpecialEventSnap[]
  zoneBalance: ZoneBalanceSnap[]
  currentTimeH: number
  operatorSetup: OperatorSetupSnap
  onCommand: (cmd: SimCommand) => void
}

/**
 * Legacy redirect — market pricing and events moved to Policy → Market & demand;
 * zone floors/caps moved to Policy → Supply by zone.
 */
export function DemandPanel(_props: Props) {
  return (
    <div className="p-3 pb-4">
      <PanelSection title="Moved to Fleet policy">
        <div className="p-3 space-y-3 text-xs text-text-secondary">
          <p>Pricing, trip spawn rate, events, and vehicle wear are under Market & demand.</p>
          <p>Zone minimums and idle caps are under Supply by zone (single home per lever).</p>
          <div className="flex flex-wrap gap-2">
            <PolicyLink subTab="market" />
            <PolicyLink subTab="supply" />
          </div>
        </div>
      </PanelSection>
    </div>
  )
}
