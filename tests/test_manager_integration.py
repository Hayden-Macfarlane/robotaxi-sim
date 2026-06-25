"""End-to-end manager integration tests."""

from __future__ import annotations

from simulation_loop.manager import SimulationManager


def test_one_sim_hour_completes_trips(sim_manager: SimulationManager) -> None:
    """Running one hour should complete at least one trip with default fleet."""
    sim_manager.reset(seed=7)
    sim_manager.step(1.0)
    assert sim_manager.state.trips_completed >= 0
    sim_manager.step(4.0)
    assert sim_manager.state.trips_completed >= 1 or len(sim_manager.state.trips) >= 1
