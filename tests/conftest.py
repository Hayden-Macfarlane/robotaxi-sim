"""Shared pytest fixtures and defaults for fast test runs."""

from __future__ import annotations

import os

import pytest

from simulation_loop.manager import SimulationManager


@pytest.fixture(scope="session", autouse=True)
def _default_test_city() -> None:
    """Use the tiny mini_austin graph unless a test opts into full Austin."""
    os.environ["ROBOTAXI_CITY"] = "mini_austin"


@pytest.fixture
def sim_manager() -> SimulationManager:
    """Fresh manager reset against the default test city graph."""
    from routing.city_loader import clear_city_graph_cache

    clear_city_graph_cache()
    mgr = SimulationManager()
    mgr.reset(seed=42)
    mgr.state.operator_setup = mgr.state.operator_setup.model_copy(
        update={"routing_engine_version": "v1"},
    )
    return mgr
