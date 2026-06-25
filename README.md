# Robotaxi Sim

Single-city robotaxi network manager simulation — balance fleet supply against rider demand on an Austin road graph. Rider trips are **anywhere-to-anywhere** (lat/lon); graph nodes remain for routing and future fleet ops (charging, maintenance).

**Fully independent** of [Apex Logistics](../logistics-sim/logistics-sim). No cross-repo imports.

- Python 3.14+ · FastAPI · WebSocket · Pydantic v2
- React 19 · TypeScript · Vite · Leaflet
- Backend **:8001** · Frontend **:5174** (logistics uses 8000/5173)

## Quick start

**macOS:** double-click `Start Robotaxi Sim.command` in the project folder (opens Terminal, starts backend + UI, opens the browser). Close the Terminal window or press Ctrl+C to stop.

```bash
cd ~/Desktop/robotaxi-sim
chmod +x scripts/start-local.sh "Start Robotaxi Sim.command"
./scripts/start-local.sh
```

Or manually:

```bash
python3.14 -m venv venv && source venv/bin/activate
pip install -e .
python scripts/build_city_graph.py   # if data/cities/austin/ missing
uvicorn api.server:app --reload --port 8001
cd frontend && npm install && npm run dev -- --port 5174
```

Open `http://127.0.0.1:5174`.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `ROBOTAXI_CITY` | `austin` | City graph slug under `data/cities/` |
| `ROBOTAXI_BACKEND_PORT` | `8001` | API port |
| `ROBOTAXI_PLAYBACK_SIM_MIN_PER_REAL_SEC` | `~0.89` | Sim minutes per real second at 1× play (~90s per typical ride) |

## Architecture

```
frontend/  →  WebSocket  →  api/server.py  →  simulation_loop/manager.py
                                    ↓
              routing/city_router · demand/ · dispatch/
              event_engine/ · core_data/
```

## WebSocket commands

`PLAY` · `PAUSE` · `STEP` · `RESET_SIMULATION` · `SET_NETWORK_POLICY` · `DISPATCH_VEHICLE` · `REPOSITION_VEHICLE` · `STAGE_VEHICLES` · `CREATE_SPECIAL_EVENT` · `SEND_TO_FACILITY` · `RELEASE_FROM_FACILITY`

Fleet ops include forecast-based peak staging, per-zone supply caps, deadhead ROI gates, dispatcher override, special events, depot release valves, and **vehicle health** (battery/condition/cleanliness wear with timed recovery at facilities).

## Tests

```bash
./venv/bin/pytest tests/ -q
cd frontend && npm run build
```

## OSM graph

```bash
pip install -e ".[dev]"   # osmnx for real street geometry
python scripts/build_city_graph.py
```

Builds the **full Austin drive network** from OpenStreetMap with street centerline geometry on every edge (~10k–40k edges). Without osmnx, a curved dev street mesh is used instead of the old grid.

Graph JSON lives in `data/cities/austin/` (`nodes.json`, `edges.json`, `meta.json` schema v2). Rebuild after routing schema changes.

## Multi-project workspace

Open `~/Desktop/simulations.code-workspace` in Cursor to work on logistics and robotaxi side-by-side with separate agents.
