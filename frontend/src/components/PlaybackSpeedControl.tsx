import type { SimCommand } from '../types/simulation'

/** Preset playback speeds (× multiplier on the 1 sim min / 1 real sec baseline). */
export const PLAYBACK_SPEED_OPTIONS = [
  { value: 0.25, label: '0.25×' },
  { value: 0.5, label: '0.5×' },
  { value: 1, label: '1×' },
  { value: 2, label: '2×' },
  { value: 5, label: '5×' },
  { value: 10, label: '10×' },
  { value: 30, label: '30×' },
  { value: 60, label: '60×' },
  { value: 120, label: '120×' },
] as const

export const DEFAULT_PLAYBACK_SPEED = 1

/** Human-readable rate at the given speed multiplier. */
export function playbackRateLabel(speed: number): string {
  if (speed === 1) return '1 sim min ≈ 1 sec'
  const simMinPerSec = speed
  if (simMinPerSec >= 60) {
    const hours = simMinPerSec / 60
    const hoursLabel = Number.isInteger(hours) ? String(hours) : hours.toFixed(1)
    return `${hoursLabel} sim hr ≈ 1 sec`
  }
  const minLabel = Number.isInteger(simMinPerSec) ? String(simMinPerSec) : simMinPerSec.toFixed(1)
  return `${minLabel} sim min ≈ 1 sec`
}

interface Props {
  speed: number
  onCommand: (cmd: SimCommand) => void
}

/** Header control for simulation playback speed. */
export function PlaybackSpeedControl({ speed, onCommand }: Props) {
  const setSpeed = (next: number) => {
    onCommand({ type: 'SET_PLAYBACK_SPEED', speed: next })
  }

  return (
    <div className="flex items-center gap-2 px-2 py-1 rounded-md border border-border-default bg-surface-raised/60">
      <label htmlFor="playback-speed" className="text-xs text-text-secondary whitespace-nowrap">
        Speed
      </label>
      <select
        id="playback-speed"
        value={speed}
        onChange={e => setSpeed(parseFloat(e.target.value))}
        className="input-dark text-xs py-1 px-2 min-w-[4.5rem]"
      >
        {PLAYBACK_SPEED_OPTIONS.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <span className="text-[10px] text-text-secondary whitespace-nowrap hidden lg:inline">
        {playbackRateLabel(speed)}
      </span>
    </div>
  )
}
