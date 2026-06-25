const SIM_TIMEZONE = 'America/Chicago'

function simInstant(timeH: number, simStartIso: string): Date {
  const startMs = new Date(simStartIso).getTime()
  return new Date(startMs + timeH * 3_600_000)
}

/** Format an ISO simulation timestamp for KPI strip and headers. */
export function formatIsoDateTime(iso: string): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: SIM_TIMEZONE,
  }).format(new Date(iso))
}

/** Format simulation clock for KPI strip and headers. */
export function formatSimDateTime(timeH: number, simStartIso: string): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: SIM_TIMEZONE,
  }).format(simInstant(timeH, simStartIso))
}

/** Compact time for log rows and inline labels. */
export function formatSimTimeShort(timeH: number, simStartIso: string): string {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: SIM_TIMEZONE,
  }).format(simInstant(timeH, simStartIso))
}
