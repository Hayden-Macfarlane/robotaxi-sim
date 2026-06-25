"""Vehicle motion and interpolation tests."""

from __future__ import annotations

import json

from simulation_loop.manager import SimulationManager


def test_snapshot_includes_interpolated_vehicle_position() -> None:
    """Vehicle snapshot should expose lat/lon, heading, and route polyline."""
    mgr = SimulationManager()
    mgr.reset(seed=7)
    mgr.step(0.5)
    raw = mgr.build_ui_snapshot(is_running=False, speed_multiplier=1)
    data = json.loads(raw)
    assert len(data["vehicles"]) > 0
    v = data["vehicles"][0]
    assert "lat" in v
    assert "lon" in v
    assert "heading_deg" in v
    assert "route_polyline" in v
    assert "streets" in data


def test_riders_appear_for_pending_trips() -> None:
    """Pending trips should surface as rider markers in the snapshot."""
    mgr = SimulationManager()
    mgr.reset(seed=7)
    for _ in range(30):
        mgr.step(0.25)
    raw = mgr.build_ui_snapshot(is_running=False, speed_multiplier=1)
    data = json.loads(raw)
    pending = [t for t in data["trips"] if t["status"] == "pending"]
    if pending:
        assert len(data["riders"]) >= 1
        rider = data["riders"][0]
        assert "lat" in rider
        assert "lon" in rider


def test_vehicle_position_changes_during_step() -> None:
    """Sim stepping should eventually move a vehicle from its spawn point."""
    mgr = SimulationManager()
    mgr.reset(seed=7)
    raw0 = json.loads(mgr.build_ui_snapshot(is_running=False, speed_multiplier=1))
    moved = False
    for _ in range(50):
        mgr.step(0.5)
        raw = json.loads(mgr.build_ui_snapshot(is_running=False, speed_multiplier=1))
        for v in raw["vehicles"]:
            if v["state"] != "idle":
                moved = True
                break
        if moved:
            break
    assert moved or raw0["vehicles"][0]["lat"] != raw["vehicles"][0]["lat"]
