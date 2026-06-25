# Future: Operational Node Logic

Graph nodes (`RoadNode`) remain the **routing backbone** for Dijkstra pathfinding. Rider trips use arbitrary lat/lon snapped to the network; nodes are reserved for **fleet operations** a robotaxi manager would run in production.

## Implemented (v2)

- `NodeKind` enum and `RoadNode.kind` / `capacity` / `name`
- Vehicle states: `AT_DEPOT`, `CHARGING`, `MAINTENANCE`, `CLEANING`
- Vehicle health: `battery_pct`, `condition_pct`, `cleanliness_pct`
- Wear on movement (battery + condition) and trip completion (cleanliness + spill events)
- Timed facility service dwell (charge scales with deficit; fixed clean/maint minutes)
- Auto-routing to charger / cleaning / maintenance when below thresholds
- Dispatch gates block unfit vehicles from new trips
- `data/cities/{city}/facilities.json` — depot, charger, cleaning, maintenance
- Commands: `SEND_TO_FACILITY`, `RELEASE_FROM_FACILITY`

## Still planned

- Scheduled breakdown / maintenance downtime events mid-shift
- Idle parasitic battery drain
- Rider-facing cleanliness ratings affecting demand

## Related files

- Schemas: `core_data/models.py`
- Health logic: `fleet/health.py`
- Routing: `routing/city_router.py`
- Orchestration: `simulation_loop/manager.py`
- Command: `REPOSITION_VEHICLE` in `api/server.py`
