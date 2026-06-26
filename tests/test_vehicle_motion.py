"""Vehicle motion and interpolation tests."""

from __future__ import annotations

import json

from core_data.models import DispatchAssignmentMode
from simulation_loop.manager import SimulationManager


def test_snapshot_includes_interpolated_vehicle_position(sim_manager: SimulationManager) -> None:
    """Vehicle snapshot should expose lat/lon, heading, and route polyline."""
    sim_manager.reset(seed=7)
    sim_manager.step(0.5)
    raw = sim_manager.build_ui_snapshot(is_running=False, speed_multiplier=1)
    data = json.loads(raw)
    assert len(data["vehicles"]) > 0
    v = data["vehicles"][0]
    assert "lat" in v
    assert "lon" in v
    assert "heading_deg" in v
    assert "route_polyline" in v
    assert "streets" in data


def test_riders_appear_for_pending_trips(sim_manager: SimulationManager) -> None:
    """Trips surface as rider markers in the snapshot."""
    sim_manager.step(1.0)
    raw = sim_manager.build_ui_snapshot(is_running=False, speed_multiplier=1)
    data = json.loads(raw)
    assert len(data["trips"]) == len(data["riders"])
    if data["trips"]:
        rider = data["riders"][0]
        assert "lat" in rider
        assert "lon" in rider


def test_vehicle_position_changes_during_step(sim_manager: SimulationManager) -> None:
    """Sim stepping should eventually move a vehicle from its spawn point."""
    sim_manager.reset(seed=7)
    sim_manager.set_operator_setup(
        dispatch_assignment_mode=DispatchAssignmentMode.CLOSEST_IDLE_OR_REPOSITIONING,
    )
    raw0 = json.loads(sim_manager.build_ui_snapshot(is_running=False, speed_multiplier=1))
    moved = False
    raw = raw0
    for _ in range(50):
        sim_manager.step(0.5)
        raw = json.loads(sim_manager.build_ui_snapshot(is_running=False, speed_multiplier=1))
        for v in raw["vehicles"]:
            if v["state"] != "idle":
                moved = True
                break
        if moved:
            break
    assert moved or raw0["vehicles"][0]["lat"] != raw["vehicles"][0]["lat"]
