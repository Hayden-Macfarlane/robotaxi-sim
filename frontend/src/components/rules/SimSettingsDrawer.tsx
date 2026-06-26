import type { NetworkPolicySnap, OperatorSetupSnap, SimCommand } from '../../types/simulation'
import type { ForecastSnap, SpecialEventSnap } from '../../types/simulation'
import { useUiMode, type SettingsSectionId } from '../../contexts/UiModeContext'
import { AnalyticsPanel } from '../AnalyticsPanel'
import { DispatchPanel } from '../DispatchPanel'
import { MarketDemandPanel } from '../MarketDemandPanel'
import { OperationsPanel } from '../OperationsPanel'

const SECTIONS: { id: SettingsSectionId; label: string }[] = [
  { id: 'dispatch', label: 'Dispatch' },
  { id: 'market', label: 'Market' },
  { id: 'operations', label: 'Operations' },
  { id: 'analyze', label: 'Performance' },
]

interface Props {
  policy: NetworkPolicySnap
  operatorSetup: OperatorSetupSnap
  forecast: ForecastSnap[]
  events: SpecialEventSnap[]
  currentTimeH: number
  kpis: import('../../types/simulation').KpiSnap
  kpiSeries: import('../../types/simulation').KpiSampleSnap[]
  experimentRuns: import('../../types/simulation').ExperimentRunSnap[]
  operatorPresets: string[]
  seed: number
  onCommand: (cmd: SimCommand) => void
}

/** Slide-over drawer for sim settings: dispatch, market, ops, analytics. */
export function SimSettingsDrawer({
  policy,
  operatorSetup,
  forecast,
  events,
  currentTimeH,
  kpis,
  kpiSeries,
  experimentRuns,
  operatorPresets,
  seed,
  onCommand,
}: Props) {
  const { settingsOpen, setSettingsOpen, settingsSection, setSettingsSection } = useUiMode()

  if (!settingsOpen) return null

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 bg-black/40"
        aria-label="Close settings"
        onClick={() => setSettingsOpen(false)}
      />
      <div className="fixed inset-y-0 right-0 z-50 w-[28rem] max-w-full bg-surface-base border-l border-border-default flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-default">
          <h2 className="text-sm font-medium text-text-primary">Sim settings</h2>
          <button
            type="button"
            onClick={() => setSettingsOpen(false)}
            className="text-text-secondary hover:text-text-primary text-xs px-2 py-1"
          >
            Close
          </button>
        </div>
        <div className="flex border-b border-border-default flex-shrink-0 overflow-x-auto">
          {SECTIONS.map(s => (
            <button
              key={s.id}
              type="button"
              onClick={() => setSettingsSection(s.id)}
              className={`px-3 py-2 text-xs whitespace-nowrap ${
                settingsSection === s.id
                  ? 'text-accent border-b-2 border-accent'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto">
          {settingsSection === 'dispatch' && (
            <DispatchPanel operatorSetup={operatorSetup} onCommand={onCommand} />
          )}
          {settingsSection === 'market' && (
            <MarketDemandPanel
              policy={policy}
              forecast={forecast}
              events={events}
              currentTimeH={currentTimeH}
              onCommand={onCommand}
            />
          )}
          {settingsSection === 'operations' && (
            <OperationsPanel policy={policy} onCommand={onCommand} />
          )}
          {settingsSection === 'analyze' && (
            <AnalyticsPanel
              kpis={kpis}
              kpiSeries={kpiSeries}
              experimentRuns={experimentRuns}
              operatorPresets={operatorPresets}
              policy={policy}
              seed={seed}
              onCommand={onCommand}
            />
          )}
        </div>
      </div>
    </>
  )
}
