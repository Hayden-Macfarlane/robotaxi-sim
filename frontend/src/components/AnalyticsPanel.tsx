import { useMemo, useState } from 'react'
import type {
  ExperimentRunSnap,
  KpiSampleSnap,
  KpiSnap,
  NetworkPolicySnap,
  SimCommand,
} from '../types/simulation'
import { FieldLabel } from './ui/FieldLabel'
import { PanelSection } from './ui/PanelSection'
import { Sparkline } from './Sparkline'

interface Props {
  kpis: KpiSnap
  kpiSeries: KpiSampleSnap[]
  experimentRuns: ExperimentRunSnap[]
  operatorPresets: string[]
  policy: NetworkPolicySnap
  seed: number
  onCommand: (cmd: SimCommand) => void
}

const COMPARE_KEYS: { key: keyof KpiSnap; label: string; fmt: (v: number) => string }[] = [
  { key: 'profit', label: 'Profit', fmt: v => `$${v.toFixed(0)}` },
  { key: 'revenue', label: 'Revenue', fmt: v => `$${v.toFixed(0)}` },
  { key: 'avg_wait_min', label: 'Avg wait', fmt: v => `${v.toFixed(1)} min` },
  { key: 'fleet_utilization_pct', label: 'Utilization', fmt: v => `${v.toFixed(0)}%` },
  { key: 'trips_completed', label: 'Completed', fmt: v => String(Math.round(v)) },
  { key: 'completion_rate', label: 'Completion rate', fmt: v => `${(v * 100).toFixed(0)}%` },
  { key: 'trips_per_vehicle_hour', label: 'Trips/veh·hr', fmt: v => v.toFixed(2) },
  { key: 'deadhead_ratio', label: 'Deadhead', fmt: v => `${(v * 100).toFixed(0)}%` },
]

function delta(a: number, b: number): string {
  const d = b - a
  const sign = d > 0 ? '+' : ''
  return `${sign}${d.toFixed(2)}`
}

/** KPI trends, experiment checkpoints, run comparison, and preset management. */
export function AnalyticsPanel({
  kpis,
  kpiSeries,
  experimentRuns,
  operatorPresets,
  policy,
  seed,
  onCommand,
}: Props) {
  const [checkpointLabel, setCheckpointLabel] = useState('Baseline')
  const [runA, setRunA] = useState('')
  const [runB, setRunB] = useState('')
  const [presetName, setPresetName] = useState('')
  const [presetDesc, setPresetDesc] = useState('')
  const [scoreDraft, setScoreDraft] = useState<Partial<NetworkPolicySnap>>({})

  const scoreVal = <K extends keyof NetworkPolicySnap>(key: K, fallback: NetworkPolicySnap[K]): NetworkPolicySnap[K] =>
    (scoreDraft[key] ?? policy[key] ?? fallback) as NetworkPolicySnap[K]

  const applyScoreWeights = () => {
    onCommand({ type: 'SET_NETWORK_POLICY', ...scoreDraft })
    setScoreDraft({})
  }

  const series = useMemo(
    () => ({
      profit: kpiSeries.map(s => s.profit),
      wait: kpiSeries.map(s => s.avg_wait_min),
      util: kpiSeries.map(s => s.fleet_utilization_pct),
      pending: kpiSeries.map(s => s.pending_trips),
    }),
    [kpiSeries],
  )

  const runAData = experimentRuns.find(r => r.id === runA)
  const runBData = experimentRuns.find(r => r.id === runB)

  return (
    <div className="p-3 pb-4 space-y-3">
      <PanelSection title="Economics">
        <div className="p-3 grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-text-secondary">Profit</span>
            <div className="text-lg font-mono text-emerald-400">${kpis.profit?.toFixed(0) ?? 0}</div>
          </div>
          <div>
            <span className="text-text-secondary">Deadhead cost</span>
            <div className="text-lg font-mono text-amber-400">${kpis.deadhead_cost?.toFixed(0) ?? 0}</div>
          </div>
          <div>
            <span className="text-text-secondary">Completion rate</span>
            <div className="font-mono">{((kpis.completion_rate ?? 0) * 100).toFixed(0)}%</div>
          </div>
          <div>
            <span className="text-text-secondary">Trips / vehicle·hr</span>
            <div className="font-mono">{kpis.trips_per_vehicle_hour?.toFixed(2) ?? '—'}</div>
          </div>
          <div className="col-span-2">
            <span className="text-text-secondary">Composite score (your weights)</span>
            <div className="font-mono text-accent">{kpis.composite_score?.toFixed(1) ?? '—'}</div>
          </div>
        </div>
      </PanelSection>

      <PanelSection
        title="Composite score weights"
        subtitle="Performance"
        impact="How profit, wait, deadhead, and completion combine into your composite KPI."
      >
        <div className="p-3 grid grid-cols-2 gap-2 text-xs">
          <FieldLabel termId="score_weight_profit">
            <input type="number" min={0} step={0.1} value={scoreVal('score_weight_profit', 1)} onChange={e => setScoreDraft(d => ({ ...d, score_weight_profit: parseFloat(e.target.value) || 0 }))} className="input-dark w-full mt-1" />
          </FieldLabel>
          <label className="block space-y-1">
            <span className="text-text-secondary">Wait penalty</span>
            <input type="number" min={0} step={0.1} value={scoreVal('score_weight_wait', 0)} onChange={e => setScoreDraft(d => ({ ...d, score_weight_wait: parseFloat(e.target.value) || 0 }))} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Deadhead penalty</span>
            <input type="number" min={0} step={0.1} value={scoreVal('score_weight_deadhead', 0)} onChange={e => setScoreDraft(d => ({ ...d, score_weight_deadhead: parseFloat(e.target.value) || 0 }))} className="input-dark" />
          </label>
          <label className="block space-y-1">
            <span className="text-text-secondary">Completion bonus</span>
            <input type="number" min={0} step={0.1} value={scoreVal('score_weight_completion', 0)} onChange={e => setScoreDraft(d => ({ ...d, score_weight_completion: parseFloat(e.target.value) || 0 }))} className="input-dark" />
          </label>
        </div>
        {Object.keys(scoreDraft).length > 0 && (
          <div className="px-3 pb-3">
            <button type="button" onClick={applyScoreWeights} className="w-full py-2 bg-accent text-white text-sm font-medium rounded-md">
              Apply score weights
            </button>
          </div>
        )}
      </PanelSection>

      <PanelSection title="KPI trends (15 min samples)">
        <div className="p-3 space-y-3 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="text-text-secondary">Profit</span>
            <Sparkline values={series.profit} stroke="#34d399" />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-text-secondary">Avg wait</span>
            <Sparkline values={series.wait} stroke="#fbbf24" />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-text-secondary">Utilization</span>
            <Sparkline values={series.util} stroke="#60a5fa" />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-text-secondary">Pending</span>
            <Sparkline values={series.pending} stroke="#f87171" />
          </div>
          {kpiSeries.length === 0 && (
            <p className="text-text-secondary italic">Play the sim to collect samples every 15 sim minutes.</p>
          )}
        </div>
      </PanelSection>

      <PanelSection title="Experiments">
        <div className="p-3 space-y-2 text-xs">
          <p className="text-text-secondary">Seed: <span className="font-mono text-text-primary">{seed}</span></p>
          <div className="flex gap-2">
            <input
              value={checkpointLabel}
              onChange={e => setCheckpointLabel(e.target.value)}
              className="input-dark flex-1"
              placeholder="Run label"
            />
            <button
              type="button"
              onClick={() => onCommand({ type: 'CHECKPOINT_RUN', label: checkpointLabel || 'Checkpoint' })}
              className="px-3 py-1 rounded bg-accent text-white text-xs"
            >
              Save checkpoint
            </button>
          </div>
          {experimentRuns.length > 0 && (
            <ul className="space-y-1 max-h-24 overflow-y-auto">
              {experimentRuns.map(r => (
                <li key={r.id} className="flex justify-between items-center gap-2">
                  <span className="truncate">{r.label} · {r.sim_time_h.toFixed(1)}h · profit ${r.kpis.profit?.toFixed(0)}</span>
                  <button
                    type="button"
                    onClick={() => onCommand({ type: 'DELETE_EXPERIMENT_RUN', run_id: r.id })}
                    className="text-red-400 shrink-0"
                  >
                    Del
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </PanelSection>

      <PanelSection title="Compare runs">
        <div className="p-3 space-y-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <select value={runA} onChange={e => setRunA(e.target.value)} className="input-dark">
              <option value="">Run A</option>
              {experimentRuns.map(r => (
                <option key={r.id} value={r.id}>{r.label}</option>
              ))}
            </select>
            <select value={runB} onChange={e => setRunB(e.target.value)} className="input-dark">
              <option value="">Run B</option>
              {experimentRuns.map(r => (
                <option key={r.id} value={r.id}>{r.label}</option>
              ))}
            </select>
          </div>
          {runAData && runBData && (
            <table className="w-full text-left">
              <thead>
                <tr className="text-text-secondary">
                  <th className="py-1">Metric</th>
                  <th className="py-1">A</th>
                  <th className="py-1">B</th>
                  <th className="py-1">Δ</th>
                </tr>
              </thead>
              <tbody>
                {COMPARE_KEYS.map(({ key, label, fmt }) => {
                  const a = runAData.kpis[key] ?? 0
                  const b = runBData.kpis[key] ?? 0
                  const better = key === 'avg_wait_min' || key === 'deadhead_ratio' ? b < a : b > a
                  return (
                    <tr key={key}>
                      <td className="py-0.5 text-text-secondary">{label}</td>
                      <td className="py-0.5 font-mono">{fmt(a)}</td>
                      <td className="py-0.5 font-mono">{fmt(b)}</td>
                      <td className={`py-0.5 font-mono ${better ? 'text-emerald-400' : 'text-red-400'}`}>
                        {delta(a, b)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </PanelSection>

      <PanelSection title="Presets">
        <div className="p-3 space-y-2 text-xs">
          <input value={presetName} onChange={e => setPresetName(e.target.value)} className="input-dark w-full" placeholder="Preset name" />
          <input value={presetDesc} onChange={e => setPresetDesc(e.target.value)} className="input-dark w-full" placeholder="Description (optional)" />
          <button
            type="button"
            disabled={!presetName.trim()}
            onClick={() => onCommand({ type: 'SAVE_OPERATOR_PRESET', name: presetName, description: presetDesc })}
            className="w-full py-1.5 rounded bg-surface-raised border border-border-default hover:bg-surface-base disabled:opacity-40"
          >
            Save current config
          </button>
          {operatorPresets.length > 0 && (
            <ul className="space-y-1">
              {operatorPresets.map(name => (
                <li key={name} className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => onCommand({ type: 'LOAD_OPERATOR_PRESET', name })}
                    className="flex-1 text-left px-2 py-1 rounded border border-border-default hover:bg-surface-raised"
                  >
                    {name}
                  </button>
                  <button
                    type="button"
                    onClick={() => onCommand({ type: 'DELETE_OPERATOR_PRESET', name })}
                    className="text-red-400 px-2"
                  >
                    Del
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </PanelSection>
    </div>
  )
}
