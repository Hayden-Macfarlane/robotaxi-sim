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
| Dispatch | `dispatch/` | Vehicle–trip matching + batch assignment |
| Experiment | `experiment/` | Run ledger persistence |
| Fleet routing | `fleet_routing/` | v1 rule engine + **v2 playbook** (`fleet_routing/v2/`) |
| Fleet health | `fleet/` | Wear, eligibility, service duration |
| Orchestration | `simulation_loop/manager.py` | Events, KPIs, snapshots |
| API | `api/server.py` | WS + command routing |
| UI | `frontend/src/` | React display only |

## Commands (WebSocket JSON)

- `PLAY` / `PAUSE` / `STEP` — time control (`PLAY` accepts optional `speed`; default 1× = 1 sim minute per real second)
- `SET_PLAYBACK_SPEED` — `{ speed }` multiplier (0.25–120×) without toggling play/pause
- `RESET_SIMULATION` — rebuild world (manual dispatch by default; change mode in Dispatch tab)
- `SET_OPERATOR_SETUP` — `{ dispatch_assignment_mode?, advanced_automation_enabled? }` switch dispatch policy anytime
- `SET_NETWORK_POLICY` — surge, fleet_size, caps, ROI gates, depot release, battery, etc.
- `SET_ROUTING_RULES` — `{ rules[], routing_enabled? }` legacy v1 playbook
- `SET_PLAYBOOK_V2` — `{ rules[], constants?, enabled? }` composable rule studio (primary)
- `SET_ROUTING_ENGINE_VERSION` — `{ version: "v1"|"v2"|"shadow" }` engine selector
- `RESET_PLAYBOOK_V2` — restore default v2 playbook from `fleet_routing/v2/defaults.py`
- `RESET_ROUTING_RULES` — restore default routing playbook (v1 + v2 parity preset)
- `DISPATCH_VEHICLE` — manual `{ vehicle_id, trip_id }`
- `REPOSITION_VEHICLE` — `{ vehicle_id, node_id }` or `{ vehicle_id, lat, lon }` (sets manual hold)
- `STAGE_VEHICLES` — `{ vehicle_ids[], lat, lon }` bulk staging
- `CREATE_SPECIAL_EVENT` — `{ label, zone, start_h, end_h, demand_multiplier }`
- `DELETE_SPECIAL_EVENT` — `{ event_id }`
- `UPDATE_SPECIAL_EVENT` — `{ event_id, label?, zone?, start_h?, end_h?, demand_multiplier? }`
- `CANCEL_TRIP` — `{ trip_id }` force-cancel pending/matched trip
- `APPLY_SCENARIO` — `{ preset }` rush_hour, low_demand, concert_surge, maintenance_heavy, airport_peak
- `CHECKPOINT_RUN` — `{ label }` save KPIs + policy snapshot to experiment ledger (`.local/experiments/`)
- `DELETE_EXPERIMENT_RUN` — `{ run_id }`
- `SAVE_OPERATOR_PRESET` — `{ name, description? }` persist policy + routing rules bundle
- `LOAD_OPERATOR_PRESET` — `{ name }`
- `DELETE_OPERATOR_PRESET` — `{ name }`
- `SEND_TO_FACILITY` — `{ vehicle_id, facility_id }` (manual ops; logged as operator action)
- `RELEASE_FROM_FACILITY` — `{ vehicle_id, zone }` route out to a zone staging point (not instant teleport)

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

- **Manual-first reset**: manual dispatch by default; Dispatch tab opens assignment mode picker
- **Dispatch assignment modes**: `manual`, `closest_idle_or_repositioning` (auto-assign, includes repositioning cars), `closest_idle` (auto-assign idle only)
- **Advanced automation gate**: reposition rules, global constraints, zone minimums, and full rule builder locked until `advanced_automation_enabled`
- **Routing rule engine** (`fleet_routing/`): unified dispatch + reposition via prioritized IF/THEN rules; full playbook available after advanced unlock
- **Forecast**: per-zone hourly curves (`demand/forecast.py`) and special events feed rule conditions
- **Supply caps**: global + per-zone `max_idle_by_zone` used by zone surplus conditions
- **Zone minimums**: `target_supply_by_zone` per-zone idle floor; map shows full-city zone overlays (`zone_overlays`)
- **Rule engine v2** (`fleet_routing/v2/`): MetricRegistry (~80+ variables), composable IF/AND/OR expressions, parameterized actions, selection modes (most_crowded, one_per_cluster), Rule Studio UI. Default engine is **v2**; playbook replaces scattered automation toggles.
- **NetworkPolicy automation fields deprecated** — `auto_dispatch_enabled`, deadzone filler, scoring weights move into playbook constants/rules when using v2.
- **Human override**: click vehicle on map or sidebar **Stage**, then click/drag map to reposition; `manual_hold_until_h`, ops audit log
- **Facility ops**: off-street vehicles visible on map at facility coords; **Send here** / **Return to street** (zone picker sorted by `zone_balance.gap`); release cancels pending service timers and routes via reposition leg
- **Depot release**: depot/charger facilities, health gates, `send_to_depot` routing action

Snapshot includes `operator_setup`, `dispatch_candidates`, `routing_rules`, `routing_rule_hits`, vehicle health KPIs, forecast, zone balance, `zone_overlays`, facilities, events, dispatch log, **`seed`**, **`kpi_series`**, **`experiment_runs`**, **`operator_presets`**, **`playbook_v2`**, **`rule_hits_v2`**, **`metric_catalog`**, **`constant_catalog`**, **`action_catalog`**, **`selection_catalog`**, and **`rule_templates`**.

## Optimization lab

Human-in-the-loop fleet tuning — you set levers, sim reports metrics; no auto-tuning.

| Mode | UI | Purpose |
|------|-----|---------|
| Live | **Analytics** tab sparklines + KPI strip | Intuition while sim is PLAY |
| Proof | **Analytics** → Save checkpoint → tweak → reset same seed → compare | Fixed-run A/B via experiment ledger |

Economics KPIs: `profit`, `deadhead_cost`, `completion_rate`, `trips_per_vehicle_hour`, `composite_score` (operator-set weights on `NetworkPolicy`).

Presets stored under `.local/presets/`; experiment runs under `.local/experiments/runs.json`.

See [docs/FUTURE_NODE_OPERATIONS.md](docs/FUTURE_NODE_OPERATIONS.md) for maintenance/cleaning queue details.

## UI (control tower)

Rules-first sidebar (`w-96`, default **Fleet rules**). Header: **Standard / Expert** mode toggle and **Fleet glossary** drawer.

| Tab | Component | Purpose |
|-----|-----------|---------|
| **Fleet rules** | `RulesHubPanel.tsx` | Sub-tabs: **Build** (playbook editor), **Monitor** (rule-hit feed), **Library** (browse constraints, thresholds, templates, actions) |
| **Live ops** | `LivePanel.tsx` | Sub-tabs: **Fleet** (AssetsPanel) and **Orders** (TripQueuePanel + OpsLogPanel) |

**Sim settings** (gear icon): slide-over drawer with Dispatch, Market, Operations, Performance (`SimSettingsDrawer.tsx`).

### Rules hub

| Sub-tab | Component | Purpose |
|---------|-----------|---------|
| **Build** | `RulesBuildPanel.tsx` | Thresholds, rule list, ConditionBuilder, ActionPicker, SelectionPicker |
| **Monitor** | `RulesMonitorPanel.tsx` | Unified `rule_hits_v2` feed with drill-down to Live |
| **Library** | `RulesLibraryPanel.tsx` | Searchable catalogs: constraints (metrics), thresholds (constants), templates, actions |

Discoverability: backend ships `constant_catalog`, `action_catalog`, `selection_catalog`, `rule_templates` alongside `metric_catalog`. Operators pick from labeled lists — no need to memorize IDs.

### Terminology

- Single registry: `frontend/src/lib/fleetTerminology.ts` — industry label + plain label + description per lever/KPI
- `FieldLabel` + `HelpPopover` on policy controls; KPI strip uses registry labels with hover descriptions
- **Standard** mode: plain-first labels; hides advanced scoring formula and expert-only weights
- **Expert** mode: industry labels (rebalancing, supply floor, match score, fulfillment rate)

### Sim settings sections

| Section | Component | Controls |
|---------|-----------|----------|
| **Dispatch** | `DispatchPanel.tsx` | Assignment mode (manual / nearest available / idle only) |
| **Market** | `MarketDemandPanel.tsx` | Pricing, fleet size, trip spawn rate, wear thresholds, forecast/events |
| **Operations** | `OperationsPanel.tsx` | Scenarios, trip SLA, fleet health, operator alert thresholds |
| **Performance** | `AnalyticsPanel.tsx` | Economics KPIs, composite score weights, sparklines, experiments, presets |

On load or reset, use **Sim settings → Dispatch** for assignment mode (manual default).

Shared primitives: `SearchableSelect`, `CatalogCard`, `FilterChips`, `FieldLabel`, `HelpPopover`, `PolicyLink`, `ToggleCard`, `PanelSection` under `frontend/src/components/ui/`; rules components under `frontend/src/components/rules/`.
