"""Tests for world bootstrap and initial fleet layout."""

from __future__ import annotations

from collections import Counter

import pytest

from core_data.models import NetworkPolicy, TripStatus
from routing.zones import all_zone_names, zone_for_point
from simulation_loop.manager import SimulationManager
from simulation_loop.world_builder import _zone_fleet_assignments, build_world


@pytest.mark.slow
@pytest.mark.timeout(120)
def test_build_world_places_one_vehicle_per_zone() -> None:
    zones = all_zone_names()
    policy = NetworkPolicy(fleet_size=len(zones), min_depot_buffer=0)
    _, state = build_world(city="austin", seed=7, policy=policy)
    assert len(state.vehicles) == len(zones)
    positions = {(round(v.lat, 5), round(v.lon, 5)) for v in state.vehicles.values()}
    assert len(positions) == len(zones)
    zone_counts: Counter[str] = Counter(
        zone_for_point(vehicle.lat, vehicle.lon) for vehicle in state.vehicles.values()
    )
    assert len(zone_counts) >= len(zones) - 1


def test_reset_seeds_pending_trips(sim_manager: SimulationManager) -> None:
    """Reset seeds two trips; auto-dispatch assigns them immediately."""
    trips = list(sim_manager.state.trips.values())
    assert len(trips) == 2
    assert any(t.status == TripStatus.MATCHED for t in trips)
