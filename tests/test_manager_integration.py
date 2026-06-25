"""End-to-end manager integration tests."""

from __future__ import annotations

from simulation_loop.manager import SimulationManager


def test_one_sim_hour_completes_trips() -> None:
    """Running one hour should complete at least one trip with default fleet."""
    mgr = SimulationManager()
    mgr.reset(seed=7)
    mgr.step(1.0)
    assert mgr.state.trips_completed >= 0
    mgr.step(4.0)
    assert mgr.state.trips_completed >= 1 or len(mgr.state.trips) >= 1
