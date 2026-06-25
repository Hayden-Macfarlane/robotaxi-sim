# AGENTS.md — Robotaxi Sim

**Read this first.** Independent simulation — **never import from apex-logistics**.

## Purpose

Single-city robotaxi fleet manager: spawn trip demand, auto-dispatch idle vehicles, track wait time / utilization / revenue on an OSM (or synthetic) Austin graph.

## Layer boundaries

| Layer | Location | Allowed |
|-------|----------|---------|
| Schemas | `core_data/models.py` | Pydantic only |
| Scheduler | `event_engine/` | Heap queue, no domain |
| Routing | `routing/` | Graph load + Dijkstra + highway-aligned Austin zone polygons |
| Demand | `demand/` | Trip spawn + forecast curves |
| Dispatch | `dispatch/` | Vehicle–trip matching helpers |
| Fleet routing | `fleet_routing/` | Operator rule engine (dispatch + reposition) |
| Fleet health | `fleet/` | Wear, eligibility, service duration |
| Orchestration | `simulation_loop/manager.py` | Events, KPIs, snapshots |
| API | `api/server.py` | WS + command routing |
| UI | `frontend/src/` | React display only |

## Commands (WebSocket JSON)

- `PLAY` / `PAUSE` / `STEP` — time control (`PLAY` accepts optional `speed`; default 1× = 1 sim minute per real second)
- `SET_PLAYBACK_SPEED` — `{ speed }` multiplier (0.25–120×) without toggling play/pause
- `RESET_SIMULATION` — rebuild world (manual dispatch by default; change mode in Auto tab)
- `SET_OPERATOR_SETUP` — `{ dispatch_assignment_mode?, advanced_automation_enabled? }` switch dispatch policy anytime
- `SET_NETWORK_POLICY` — surge, fleet_size, caps, ROI gates, depot release, battery, etc.
- `SET_ROUTING_RULES` — `{ rules[], routing_enabled? }` operator routing playbook
- `RESET_ROUTING_RULES` — restore default routing playbook
- `DISPATCH_VEHICLE` — manual `{ vehicle_id, trip_id }`
- `REPOSITION_VEHICLE` — `{ vehicle_id, node_id }` or `{ vehicle_id, lat, lon }` (sets manual hold)
- `STAGE_VEHICLES` — `{ vehicle_ids[], lat, lon }` bulk staging
- `CREATE_SPECIAL_EVENT` — `{ label, zone, start_h, end_h, demand_multiplier }`
- `SEND_TO_FACILITY` — `{ vehicle_id, facility_id }`
- `RELEASE_FROM_FACILITY` — `{ vehicle_id }`

## Ports

- Backend: **8001**
- Frontend: **5174**

## Independence rule

Do not add dependencies on `logistics-sim`. Copied files (e.g. `event_engine`) diverge freely in this repo.

## Local dev launcher

- Default city: **`austin`** (full OSM graph; ~30s first load). Tests override to `mini_austin` via [`tests/conftest.py`](tests/conftest.py).
- Double-click **`Start Robotaxi Sim.command`** — foreground supervisor; keeps terminal open and **auto-restarts** backend/frontend if they are stopped externally
- **`./scripts/reload-local.sh`** — stop services only (agent use after code changes); the user's launcher terminal will restart them within ~2s
- Do **not** run `start-local.sh --detach` while the user has the `.command` launcher open — use `reload-local.sh` instead

## Testing

- **Fast (default):** `pytest` — uses `mini_austin` graph via `tests/conftest.py`; skips `@pytest.mark.slow` tests
- **Full Austin accuracy:** `pytest -m slow` — zone placement and large-graph router tests (~30s each)
- **Everything:** `pytest -m ""` — runs fast + slow suites

Graph and router instances are cached per process (`load_city_graph`, `get_city_router`); repeated `mgr.reset()` in tests reuses the parsed graph.

`SimulationManager.reset()` respects `ROBOTAXI_CITY` when no explicit `city=` is passed (tests set `mini_austin` in `conftest.py`). Production defaults to `austin`.

Fast tests fail after **30s** (`pytest-timeout`); `@pytest.mark.slow` tests allow **120s** for full-Austin cases.

## When to update this file

New package, command, snapshot field, or panel → update AGENTS.md and README.md in the same change.

## Ops features

- **Manual-first reset**: manual dispatch by default; Auto tab opens dispatch assignment picker
- **Dispatch assignment modes**: `manual`, `closest_idle_or_repositioning` (auto-assign, includes repositioning cars), `closest_idle` (auto-assign idle only)
- **Advanced automation gate**: reposition rules, global constraints, zone minimums, and full rule builder locked until `advanced_automation_enabled`
- **Routing rule engine** (`fleet_routing/`): unified dispatch + reposition via prioritized IF/THEN rules; full playbook available after advanced unlock
- **Forecast**: per-zone hourly curves (`demand/forecast.py`) and special events feed rule conditions
- **Supply caps**: global + per-zone `max_idle_by_zone` used by zone surplus conditions
- **Zone minimums**: `target_supply_by_zone` per-zone idle floor; map shows full-city zone overlays (`zone_overlays`)
- **Deadhead ROI**: global constraints (`min_reposition_benefit`, `max_reposition_min`) applied after rules match
- **Human override**: click/drag staging, `manual_hold_until_h`, ops audit log
- **Depot release**: depot/charger facilities, health gates, `send_to_depot` routing action

Snapshot includes `operator_setup`, `dispatch_candidates`, `routing_rules`, `routing_rule_hits`, vehicle health KPIs, forecast, zone balance, `zone_overlays`, facilities, events, and dispatch log fields.

See [docs/FUTURE_NODE_OPERATIONS.md](docs/FUTURE_NODE_OPERATIONS.md) for maintenance/cleaning queue details.

## UI (control tower)

Tabbed sidebar (`w-96`, default **Assets**):

| Tab | Component | Purpose |
|-----|-----------|---------|
| **Assets** | `AssetsPanel.tsx` | Vehicle/facility tables, summary pills, map selection + staging |
| **Routing** | `RoutingPanel.tsx` + `RuleEditor.tsx` | Operator rule builder (dispatch + reposition playbook) |
| **Auto** | `AutomationPanel.tsx` | Master dispatch switch + global deadhead/zone constraints |
| **Demand** | `DemandPanel.tsx` | Pricing, zone minimums, caps, wear thresholds, forecast/events |
| **Activity** | `TripQueuePanel` + `OpsLogPanel` | Pending trips (manual assign + ranked suggestions) and dispatch audit log |

On load or reset, the **Auto** tab shows dispatch assignment options (manual default). Switch to closest idle/repositioning anytime without a blocking modal.

Routing rules evaluate top-to-bottom; first matching enabled rule wins. Phases: `dispatch` (trip assignment) and `reposition` (idle vehicle moves).

Shared primitives: `SidebarTabs`, `ToggleCard`, `MetricPill`, `DataTable` under `frontend/src/components/ui/`; helpers in `frontend/src/lib/fleetStats.ts` and `vehicleLabels.ts`.

KPI strip shows six primary metrics with a **More** dropdown for secondary stats.
