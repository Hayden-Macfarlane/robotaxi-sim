"""Async WebSocket server for the robotaxi manager simulation."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core_data.models import NetworkPolicy
from simulation_loop.manager import SimulationManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

app = FastAPI(title="Robotaxi Manager", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_manager: SimulationManager | None = None
_sim_playing: bool = False
_playback_speed: float = 1.0
_clients: set[WebSocket] = set()
_pending_manager_reload: bool = False
TICK_INTERVAL_S: float = 0.1
# At playback speed 1×, one real second advances one simulation minute.
PLAYBACK_SIM_MINUTES_PER_REAL_SECOND: float = float(
    os.environ.get("ROBOTAXI_PLAYBACK_SIM_MIN_PER_REAL_SEC", "1.0")
)
MIN_PLAYBACK_SPEED: float = 0.25
MAX_PLAYBACK_SPEED: float = 120.0
BROADCAST_INTERVAL_S: float = 0.2
_sim_last_wall: float = 0.0
_last_broadcast_wall: float = 0.0
_manager_ready = asyncio.Event()


def _sim_dt_hours(playback_speed: float) -> float:
    """Convert one wall-clock tick into simulation hours at the given playback speed."""
    sim_minutes = TICK_INTERVAL_S * playback_speed * PLAYBACK_SIM_MINUTES_PER_REAL_SECOND
    return sim_minutes / 60.0


def _clamp_playback_speed(speed: float) -> float:
    """Bound playback speed to supported UI range."""
    return max(MIN_PLAYBACK_SPEED, min(MAX_PLAYBACK_SPEED, speed))


def _reset_wall_clock() -> None:
    """Reset wall-clock anchor so playback does not jump after pause or idle."""
    global _sim_last_wall
    _sim_last_wall = time.monotonic()


def _sim_dt_hours_from_elapsed(elapsed_s: float, playback_speed: float) -> float:
    """Convert elapsed wall seconds into simulation hours at the given playback speed."""
    sim_minutes = elapsed_s * playback_speed * PLAYBACK_SIM_MINUTES_PER_REAL_SECOND
    return sim_minutes / 60.0


def _init_manager() -> SimulationManager:
    """Create and reset the simulation manager."""
    mgr = SimulationManager()
    mgr.reset()
    return mgr


def _initializing_snapshot() -> dict[str, object]:
    """Minimal snapshot while the city graph loads in the background."""
    return {
        "type": "STATE_SNAPSHOT",
        "status": "initializing",
        "current_time_h": 0,
        "sim_start_iso": "",
        "is_running": False,
        "speed_multiplier": round(_playback_speed, 2),
        "city": os.environ.get("ROBOTAXI_CITY", "austin"),
        "policy": NetworkPolicy(
            auto_dispatch_enabled=False,
            auto_reposition_enabled=False,
            post_trip_reposition_enabled=False,
        ).model_dump(),
        "kpis": {
            "avg_wait_min": 0,
            "p95_wait_min": 0,
            "fleet_utilization_pct": 0,
            "trips_completed": 0,
            "trips_cancelled": 0,
            "revenue": 0,
            "pending_trips": 0,
            "deadhead_ratio": 0,
            "vehicles_at_depot": 0,
            "vehicles_on_street": 0,
            "avg_battery_pct": 100,
            "avg_condition_pct": 100,
            "avg_cleanliness_pct": 100,
            "vehicles_needing_service": 0,
        },
        "supply_by_zone": {},
        "demand_by_zone": {},
        "operator_setup": {
            "setup_complete": True,
            "dispatch_assignment_mode": "closest_idle_or_repositioning",
            "advanced_automation_enabled": False,
        },
        "dispatch_candidates": {},
        "vehicles": [],
        "trips": [],
        "riders": [],
        "streets": [],
        "nodes": [],
        "map_center": {"lat": 30.27, "lon": -97.74},
    }


def _snapshot() -> str:
    if _manager is None:
        return json.dumps(_initializing_snapshot())
    return _manager.build_ui_snapshot(
        is_running=_sim_playing,
        speed_multiplier=round(_playback_speed, 2),
    )


async def _snapshot_async() -> str:
    """Build snapshot off the event loop so routing work does not block I/O."""
    if _manager is None:
        return json.dumps(_initializing_snapshot())
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: _manager.build_ui_snapshot(  # type: ignore[union-attr]
            is_running=_sim_playing,
            speed_multiplier=round(_playback_speed, 2),
        ),
    )


async def _broadcast(snapshot: str) -> None:
    dead: set[WebSocket] = set()
    for ws in _clients:
        try:
            await ws.send_text(snapshot)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


def _system_alert(message: str, level: str = "error") -> dict[str, str]:
    return {"type": "SYSTEM_ALERT", "level": level, "message": message}


def _handle_command(raw: str) -> dict[str, str] | None:
    global _sim_playing, _playback_speed, _manager, _pending_manager_reload

    try:
        cmd: dict[str, object] = json.loads(raw)
    except json.JSONDecodeError:
        return None

    cmd_type = str(cmd.get("type", "")).upper()

    if cmd_type == "PLAY":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        _sim_playing = True
        _reset_wall_clock()
        speed_raw = cmd.get("speed")
        if isinstance(speed_raw, (int, float)):
            _playback_speed = _clamp_playback_speed(float(speed_raw))

    elif cmd_type == "PAUSE":
        _sim_playing = False
        _reset_wall_clock()

    elif cmd_type == "SET_PLAYBACK_SPEED":
        speed_raw = cmd.get("speed", 1)
        if isinstance(speed_raw, (int, float)):
            _playback_speed = _clamp_playback_speed(float(speed_raw))

    elif cmd_type == "STEP":
        hours_raw = cmd.get("hours", 1.0)
        hours = float(hours_raw) if isinstance(hours_raw, (int, float)) else 1.0
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        _manager.step(hours)

    elif cmd_type == "SET_OPERATOR_SETUP":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        from core_data.models import DispatchAssignmentMode

        mode_raw = cmd.get("dispatch_assignment_mode")
        mode: DispatchAssignmentMode | None = None
        if isinstance(mode_raw, str) and mode_raw:
            try:
                mode = DispatchAssignmentMode(mode_raw)
            except ValueError:
                return _system_alert(f"Unknown dispatch mode: {mode_raw}")
        advanced_raw = cmd.get("advanced_automation_enabled")
        advanced = advanced_raw if isinstance(advanced_raw, bool) else None
        if mode is None and advanced is None:
            return _system_alert("SET_OPERATOR_SETUP requires dispatch_assignment_mode or advanced_automation_enabled.")
        _manager.set_operator_setup(
            dispatch_assignment_mode=mode,
            advanced_automation_enabled=advanced,
        )

    elif cmd_type == "RESET_SIMULATION":
        _sim_playing = False
        _manager = None
        _manager_ready.clear()
        _pending_manager_reload = True
        return _system_alert("Resetting simulation…", level="info")

    elif cmd_type == "SET_NETWORK_POLICY":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        patch: dict[str, object] = {}
        for key in (
            "fleet_size",
            "base_fare",
            "surge_multiplier",
            "reposition_idle_min",
            "auto_dispatch_enabled",
            "auto_reposition_enabled",
            "post_trip_reposition_enabled",
            "max_idle_per_zone",
            "max_idle_by_zone",
            "reposition_idle_min_by_zone",
            "target_supply_by_zone",
            "max_wait_min",
            "reposition_lead_min",
            "min_reposition_benefit",
            "max_reposition_min",
            "deadhead_cost_per_min",
            "value_per_trip",
            "manual_hold_min",
            "depot_release_enabled",
            "min_depot_buffer",
            "proactive_staging_enabled",
            "battery_drain_per_km",
            "low_battery_pct",
            "condition_drain_per_km",
            "condition_drain_per_trip",
            "cleanliness_drain_per_trip",
            "cleanliness_spill_chance",
            "cleanliness_spill_floor_pct",
            "low_condition_pct",
            "low_cleanliness_pct",
            "charge_minutes_to_full",
            "cleaning_service_min",
            "maintenance_service_min",
            "base_trips_per_hour",
            "zone_demand_weights",
            "dispatch_candidate_limit",
            "dispatch_use_fast_eta",
            "dispatch_weight_eta",
            "dispatch_weight_surge",
            "dispatch_weight_zone_balance",
            "cross_zone_dispatch_penalty_min",
            "max_deadhead_to_pickup_min",
            "allow_preempt_reposition",
            "failover_pending_queue_max",
            "failover_avg_wait_max_min",
            "dispatch_tie_breaker",
            "per_minute_fare",
            "per_mile_fare",
            "forecast_rising_threshold",
            "charge_aware_dispatch",
            "min_battery_pct_for_trip",
            "km_per_soc_pct",
            "alert_avg_wait_min",
            "alert_pending_queue",
            "alert_utilization_below_pct",
            "alert_vehicles_needing_service",
            "alert_zone_deficit",
            "global_traffic_multiplier",
            "scenario_preset",
            "batch_dispatch_enabled",
            "auto_dispatch_by_zone",
            "score_weight_profit",
            "score_weight_wait",
            "score_weight_deadhead",
            "score_weight_completion",
            "dispatch_consider_dropoff_balance",
            "dispatch_weight_dropoff_balance",
            "dispatch_penalty_dropoff_surplus_min",
        ):
            if key in cmd and cmd[key] is not None:
                patch[key] = cmd[key]
        if patch:
            _manager.set_network_policy(**patch)

    elif cmd_type == "SET_ROUTING_RULES":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        current = _manager.state.routing_rules.model_dump()
        rules_raw = cmd.get("rules")
        if isinstance(rules_raw, list):
            current["rules"] = rules_raw
        enabled = cmd.get("routing_enabled")
        if isinstance(enabled, bool):
            current["routing_enabled"] = enabled
        try:
            _manager.set_routing_rules_from_dict(current)
        except Exception as exc:
            return _system_alert(f"Invalid routing rules: {exc}")

    elif cmd_type == "RESET_ROUTING_RULES":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        from fleet_routing.defaults import default_routing_rules, dispatch_only_rules

        setup = _manager.state.operator_setup
        if setup.advanced_automation_enabled:
            _manager.set_routing_rules(default_routing_rules())
        elif setup.dispatch_assignment_mode is not None and setup.dispatch_assignment_mode.value != "manual":
            _manager.set_routing_rules(dispatch_only_rules(setup.dispatch_assignment_mode))
        else:
            from fleet_routing.defaults import manual_first_routing_rules

            _manager.set_routing_rules(manual_first_routing_rules())

    elif cmd_type == "DISPATCH_VEHICLE":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        vid = str(cmd.get("vehicle_id", ""))
        tid = str(cmd.get("trip_id", ""))
        err = _manager.dispatch_vehicle(vid, tid)
        if err:
            return _system_alert(err)

    elif cmd_type == "REPOSITION_VEHICLE":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        vid = str(cmd.get("vehicle_id", ""))
        lat = cmd.get("lat")
        lon = cmd.get("lon")
        if lat is not None and lon is not None:
            err = _manager.reposition_vehicle_to_point(vid, float(lat), float(lon), manual=True)
        else:
            nid = str(cmd.get("node_id", ""))
            err = _manager.reposition_vehicle(vid, nid, manual=True)
        if err:
            return _system_alert(err)

    elif cmd_type == "STAGE_VEHICLES":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        ids_raw = cmd.get("vehicle_ids", [])
        lat = cmd.get("lat")
        lon = cmd.get("lon")
        if not isinstance(ids_raw, list) or lat is None or lon is None:
            return _system_alert("STAGE_VEHICLES requires vehicle_ids, lat, lon.")
        ids = [str(v) for v in ids_raw]
        err = _manager.stage_vehicles(ids, float(lat), float(lon))
        if err:
            return _system_alert(err)

    elif cmd_type == "CREATE_SPECIAL_EVENT":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        label = str(cmd.get("label", "Event"))
        zone = str(cmd.get("zone", "downtown"))
        start_h = float(cmd.get("start_h", _manager.current_time))
        end_h = float(cmd.get("end_h", start_h + 2.0))
        mult = float(cmd.get("demand_multiplier", 2.0))
        _manager.create_special_event(
            label=label,
            zone=zone,
            start_h=start_h,
            end_h=end_h,
            demand_multiplier=mult,
        )

    elif cmd_type == "CANCEL_TRIP":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        tid = str(cmd.get("trip_id", ""))
        err = _manager.cancel_trip(tid)
        if err:
            return _system_alert(err)

    elif cmd_type == "DELETE_SPECIAL_EVENT":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        eid = str(cmd.get("event_id", ""))
        err = _manager.delete_special_event(eid)
        if err:
            return _system_alert(err)

    elif cmd_type == "UPDATE_SPECIAL_EVENT":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        eid = str(cmd.get("event_id", ""))
        err = _manager.update_special_event(
            eid,
            label=str(cmd["label"]) if "label" in cmd else None,
            zone=str(cmd["zone"]) if "zone" in cmd else None,
            start_h=float(cmd["start_h"]) if "start_h" in cmd else None,
            end_h=float(cmd["end_h"]) if "end_h" in cmd else None,
            demand_multiplier=float(cmd["demand_multiplier"]) if "demand_multiplier" in cmd else None,
        )
        if err:
            return _system_alert(err)

    elif cmd_type == "APPLY_SCENARIO":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        from core_data.models import ScenarioPreset

        preset_raw = str(cmd.get("preset", "custom"))
        try:
            preset = ScenarioPreset(preset_raw)
        except ValueError:
            return _system_alert(f"Unknown scenario preset: {preset_raw}")
        _manager.apply_scenario(preset)

    elif cmd_type == "CHECKPOINT_RUN":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        label = str(cmd.get("label", "Checkpoint"))
        _manager.checkpoint_run(label)

    elif cmd_type == "DELETE_EXPERIMENT_RUN":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        run_id = str(cmd.get("run_id", ""))
        err = _manager.delete_experiment_run(run_id)
        if err:
            return _system_alert(err)

    elif cmd_type == "SAVE_OPERATOR_PRESET":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        name = str(cmd.get("name", "")).strip()
        if not name:
            return _system_alert("SAVE_OPERATOR_PRESET requires name.")
        desc = str(cmd.get("description", ""))
        _manager.save_operator_preset(name, desc)

    elif cmd_type == "LOAD_OPERATOR_PRESET":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        name = str(cmd.get("name", "")).strip()
        if not name:
            return _system_alert("LOAD_OPERATOR_PRESET requires name.")
        err = _manager.load_operator_preset(name)
        if err:
            return _system_alert(err)

    elif cmd_type == "DELETE_OPERATOR_PRESET":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        name = str(cmd.get("name", "")).strip()
        err = _manager.delete_operator_preset(name)
        if err:
            return _system_alert(err)

    elif cmd_type == "SEND_TO_FACILITY":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        vid = str(cmd.get("vehicle_id", ""))
        fid = str(cmd.get("facility_id", ""))
        err = _manager.send_to_facility(vid, fid, manual=True)
        if err:
            return _system_alert(err)

    elif cmd_type == "RELEASE_FROM_FACILITY":
        if _manager is None:
            return _system_alert("Simulation not initialized.")
        vid = str(cmd.get("vehicle_id", ""))
        zone = str(cmd.get("zone", "")).strip()
        if not zone:
            return _system_alert("RELEASE_FROM_FACILITY requires zone.")
        err = _manager.release_from_facility(vid, zone)
        if err:
            return _system_alert(err)

    else:
        logger.warning("Unknown command type: %s", cmd_type)

    return None


async def simulation_loop_task() -> None:
    """Background tick when PLAY is active — wall-clock driven with throttled snapshots."""
    global _sim_playing, _last_broadcast_wall, _sim_last_wall
    _reset_wall_clock()
    _last_broadcast_wall = time.monotonic()
    while True:
        await asyncio.sleep(TICK_INTERVAL_S)
        if not _sim_playing or _manager is None:
            _reset_wall_clock()
            continue
        try:
            now = time.monotonic()
            elapsed = now - _sim_last_wall
            _sim_last_wall = now
            dt_h = _sim_dt_hours_from_elapsed(elapsed, _playback_speed)
            if dt_h > 0.0:
                _manager.step(dt_h)
            if now - _last_broadcast_wall >= BROADCAST_INTERVAL_S:
                await _broadcast(await _snapshot_async())
                _last_broadcast_wall = now
        except Exception:
            logger.exception("Simulation tick failed")
            _sim_playing = False
            _reset_wall_clock()


@app.get("/health")
async def health() -> dict[str, bool | str]:
    """Liveness probe; ``ready`` when the simulation world has finished loading."""
    return {"ok": True, "ready": _manager is not None}


async def _init_manager_background() -> None:
    """Load the city graph without blocking the event loop (~30s for Austin)."""
    global _manager
    loop = asyncio.get_running_loop()
    logger.info("Loading simulation world…")
    mgr = await loop.run_in_executor(None, _init_manager)
    _manager = mgr
    _manager_ready.set()
    logger.info("Simulation world ready")
    if _clients:
        await _broadcast(await _snapshot_async())


@app.on_event("startup")
async def on_startup() -> None:
    asyncio.create_task(_init_manager_background())
    asyncio.create_task(simulation_loop_task())


async def _ws_send_text(ws: WebSocket, text: str) -> bool:
    """Send on a WebSocket; return False if the client already disconnected."""
    try:
        await ws.send_text(text)
        return True
    except Exception:
        return False


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    global _pending_manager_reload

    await ws.accept()
    _clients.add(ws)
    try:
        if _manager is None:
            if not await _ws_send_text(ws, json.dumps(_initializing_snapshot())):
                return
            await _manager_ready.wait()
        if not await _ws_send_text(ws, await _snapshot_async()):
            return
        while True:
            raw = await ws.receive_text()
            alert = _handle_command(raw)
            if _pending_manager_reload:
                _pending_manager_reload = False
                asyncio.create_task(_init_manager_background())
            if alert is not None:
                if not await _ws_send_text(ws, json.dumps(alert)):
                    break
            await _broadcast(await _snapshot_async())
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)


def main() -> None:
    """Run uvicorn on port 8001."""
    uvicorn.run("api.server:app", host="0.0.0.0", port=8001, reload=False)


if __name__ == "__main__":
    main()
