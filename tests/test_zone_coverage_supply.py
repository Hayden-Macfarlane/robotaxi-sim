"""Tests for map zone coverage supply (idle + inbound repositioning)."""

from __future__ import annotations

from core_data.models import GeoPoint, Vehicle, VehicleState
from routing.city_loader import clear_city_graph_cache
from routing.zones import zone_for_point
from simulation_loop.manager import SimulationManager


def test_coverage_supply_counts_idle_and_inbound_reposition() -> None:
    """Idle vehicles count in current zone; repositioning counts at route destination."""
    clear_city_graph_cache()
    mgr = SimulationManager()
    mgr.reset(seed=1)

    idle_lat, idle_lon = 30.250, -97.880
    dest_lat, dest_lon = 30.270, -97.742
    idle_zone = zone_for_point(idle_lat, idle_lon)
    dest_zone = zone_for_point(dest_lat, dest_lon)

    mgr.state.vehicles = {
        "v-idle": Vehicle(
            id="v-idle",
            state=VehicleState.IDLE,
            lat=idle_lat,
            lon=idle_lon,
            current_node_id="n-a",
        ),
        "v-repo": Vehicle(
            id="v-repo",
            state=VehicleState.REPOSITIONING,
            lat=30.20,
            lon=-97.80,
            current_node_id="n-b",
            active_route_geometry=[
                GeoPoint(lat=30.20, lon=-97.80),
                GeoPoint(lat=dest_lat, lon=dest_lon),
            ],
        ),
    }

    coverage = mgr._coverage_supply_by_zone()
    assert coverage.get(idle_zone, 0) == 1
    assert coverage.get(dest_zone, 0) == 1
    assert idle_zone != dest_zone
