"""Tests for battery drain and timed charging service."""

from __future__ import annotations

from core_data.models import VehicleState
from fleet.health import service_duration_min
from simulation_loop.manager import SimulationManager


def test_battery_drain_on_leg() -> None:
    mgr = SimulationManager()
    mgr.reset(seed=3)
    mgr.set_network_policy(battery_drain_per_km=1.0, charge_minutes_to_full=30.0)
    vehicle = next(v for v in mgr.state.vehicles.values() if v.state == VehicleState.IDLE)
    start_battery = vehicle.battery_pct
    charger = next((f for f in mgr.state.facilities.values() if f.kind.value == "charger"), None)
    assert charger is not None
    route = mgr.router.route_between(vehicle.lat, vehicle.lon, charger.lat, charger.lon)
    assert route is not None
    mgr._start_leg(vehicle, route, leg="pickup", payload={"trip_id": "x"}, track_deadhead=True)
    assert vehicle.battery_pct < start_battery


def test_service_duration_scales_with_deficit() -> None:
    mgr = SimulationManager()
    mgr.reset(seed=4)
    vehicle = next(v for v in mgr.state.vehicles.values() if v.state == VehicleState.IDLE)
    vehicle.battery_pct = 25.0
    duration = service_duration_min(vehicle, "charger", mgr.state.policy)
    assert duration == mgr.state.policy.charge_minutes_to_full * 0.75


def test_complete_facility_service_restores_battery() -> None:
    mgr = SimulationManager()
    mgr.reset(seed=5)
    vehicle = next(v for v in mgr.state.vehicles.values() if v.state == VehicleState.IDLE)
    vehicle.battery_pct = 15.0
    vehicle.state = VehicleState.CHARGING
    mgr._complete_facility_service(vehicle, "charger-downtown", "charger", mgr.current_time)
    assert vehicle.battery_pct == 100.0
    assert vehicle.state == VehicleState.IDLE
