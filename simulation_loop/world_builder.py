"""Bootstrap city graph and initial fleet for a robotaxi simulation."""

from __future__ import annotations

import os
import random

from core_data.models import NetworkPolicy, Vehicle, VehicleState
from routing.city_loader import load_city_graph, load_facilities
from routing.city_router import CityRouter
from simulation_loop.state import SimulationState


def build_world(
    *,
    city: str | None = None,
    policy: NetworkPolicy | None = None,
    seed: int = 42,
) -> tuple[CityRouter, SimulationState]:
    """Load city graph and seed vehicles according to ``policy.fleet_size``."""
    city_name = city or os.environ.get("ROBOTAXI_CITY", "austin")
    nodes, edges = load_city_graph(city_name)
    router = CityRouter(nodes, edges)
    facilities = load_facilities(city_name, router)
    pol = policy or NetworkPolicy()
    rng = random.Random(seed)
    node_ids = router.node_ids
    if not node_ids:
        raise RuntimeError("City graph has no nodes")

    depot = next((f for f in facilities.values() if f.kind.value == "depot"), None)
    vehicles: dict[str, Vehicle] = {}
    for i in range(pol.fleet_size):
        vid = f"rx-{i + 1:03d}"
        if depot is not None and i < pol.min_depot_buffer:
            node_id = depot.node_id or rng.choice(node_ids)
            lat, lon = depot.lat, depot.lon
            state = VehicleState.AT_DEPOT
            facility_id = depot.id
        else:
            node_id = rng.choice(node_ids)
            node = router.get_node(node_id)
            assert node is not None
            lat, lon = node.lat, node.lon
            state = VehicleState.IDLE
            facility_id = None
        vehicles[vid] = Vehicle(
            id=vid,
            state=state,
            lat=lat,
            lon=lon,
            current_node_id=node_id,
            idle_since_h=0.0,
            facility_id=facility_id,
        )

    state = SimulationState(vehicles=vehicles, policy=pol, facilities=facilities)
    return router, state
