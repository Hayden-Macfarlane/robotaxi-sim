import { useCallback, useEffect, useRef, useState } from 'react'
import type { SimCommand, SimulationSnapshot } from '../types/simulation'

const WS_RETRY_MS = 2000

function defaultWsUrl(): string {
  if (typeof window !== 'undefined' && import.meta.env.DEV) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}/ws`
  }
  return 'ws://localhost:8001/ws'
}

const EMPTY_SNAPSHOT: SimulationSnapshot = {
  type: 'STATE_SNAPSHOT',
  current_time_h: 0,
  sim_start_iso: '2025-06-20T17:00:00-05:00',
  is_running: false,
  speed_multiplier: 1,
  city: 'austin',
  map_center: { lat: 30.27, lon: -97.74 },
  policy: {
    fleet_size: 14,
    base_fare: 8,
    surge_multiplier: 1,
    reposition_idle_min: 15,
    auto_dispatch_enabled: false,
    auto_reposition_enabled: false,
    post_trip_reposition_enabled: false,
    max_idle_per_zone: 3,
    max_idle_by_zone: {},
    reposition_idle_min_by_zone: {},
    target_supply_by_zone: {},
    max_wait_min: 12,
    reposition_lead_min: 30,
    min_reposition_benefit: 0.5,
    max_reposition_min: 45,
    deadhead_cost_per_min: 0.15,
    value_per_trip: 2,
    manual_hold_min: 60,
    depot_release_enabled: true,
    min_depot_buffer: 0,
    proactive_staging_enabled: true,
    battery_drain_per_km: 0.4,
    low_battery_pct: 20,
    condition_drain_per_km: 0.08,
    condition_drain_per_trip: 0.5,
    cleanliness_drain_per_trip: 1.5,
    cleanliness_spill_chance: 0.04,
    cleanliness_spill_floor_pct: 8,
    low_condition_pct: 25,
    low_cleanliness_pct: 20,
    charge_minutes_to_full: 45,
    cleaning_service_min: 20,
    maintenance_service_min: 30,
  },
  kpis: {
    avg_wait_min: 0,
    p95_wait_min: 0,
    fleet_utilization_pct: 0,
    trips_completed: 0,
    trips_cancelled: 0,
    revenue: 0,
    pending_trips: 0,
    deadhead_ratio: 0,
    vehicles_at_depot: 0,
    vehicles_on_street: 0,
    avg_battery_pct: 100,
    avg_condition_pct: 100,
    avg_cleanliness_pct: 100,
    vehicles_needing_service: 0,
    deadhead_cost: 0,
    profit: 0,
    completion_rate: 0,
    trips_per_vehicle_hour: 0,
    composite_score: 0,
  },
  supply_by_zone: {},
  demand_by_zone: {},
  seed: 42,
  kpi_series: [],
  experiment_runs: [],
  operator_presets: [],
  operator_setup: {
    setup_complete: true,
    dispatch_assignment_mode: 'closest_idle_or_repositioning',
    advanced_automation_enabled: false,
  },
  dispatch_candidates: {},
  vehicles: [],
  trips: [],
  riders: [],
  streets: [],
  nodes: [],
}

/** WebSocket hook for robotaxi simulation snapshots and commands. */
export function useSimulation() {
  const [snapshot, setSnapshot] = useState<SimulationSnapshot>(EMPTY_SNAPSHOT)
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(true)
  const [alert, setAlert] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const sendCommand = useCallback((cmd: SimCommand) => {
    wsRef.current?.send(JSON.stringify(cmd))
  }, [])

  useEffect(() => {
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      setConnecting(true)
      const ws = new WebSocket(defaultWsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        if (cancelled) return
        setConnected(true)
        setConnecting(false)
      }

      ws.onclose = () => {
        if (cancelled) return
        setConnected(false)
        setConnecting(true)
        wsRef.current = null
        retryRef.current = setTimeout(connect, WS_RETRY_MS)
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data as string) as Record<string, unknown>
          if (data.type === 'STATE_SNAPSHOT') {
            const incoming = data as unknown as SimulationSnapshot
            setSnapshot(prev => ({
              ...prev,
              ...incoming,
              policy: incoming.policy ?? prev.policy,
              kpis: incoming.kpis ?? prev.kpis,
              operator_setup: incoming.operator_setup ?? prev.operator_setup,
              map_center: incoming.map_center ?? prev.map_center,
            }))
            setConnecting(false)
          } else if (data.type === 'SYSTEM_ALERT') {
            setAlert(String(data.message ?? 'Error'))
          }
        } catch {
          /* ignore malformed */
        }
      }
    }

    connect()

    return () => {
      cancelled = true
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [])

  return { snapshot, connected, connecting, alert, setAlert, sendCommand }
}
