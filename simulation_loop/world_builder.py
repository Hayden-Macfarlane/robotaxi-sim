"""Bootstrap city graph and initial fleet for a robotaxi simulation."""

from __future__ import annotations

import os
import random

from core_data.models import NetworkPolicy, Vehicle, VehicleState
from routing.austin_zones_geo import AUSTIN_BASE_ZONE_POLYGONS, AUSTIN_POI_ZONE_RINGS
from routing.city_loader import get_city_router, load_facilities
from routing.city_router import CityRouter
from routing.geo import haversine_km
from routing.zones import all_zone_names, sample_interior_point, zone_bounding_boxes, zone_for_point
from simulation_loop.state import SimulationState

# One idle vehicle per zone at reset; matches default ``NetworkPolicy.fleet_size``.
VEHICLES_PER_ZONE = 1


def _zone_rings_by_name() -> dict[str, tuple[tuple[float, float], ...]]:
    """Return a sample polygon ring per zone label."""
    rings = {name: ring for name, ring in AUSTIN_BASE_ZONE_POLYGONS}
    rings.update(AUSTIN_POI_ZONE_RINGS)
    return rings


def _nodes_by_zone(router: CityRouter) -> dict[str, list[str]]:
    """Group graph node ids by demand zone."""
    return router.nodes_by_demand_zone()


_ZONE_NEIGHBORS: dict[str, tuple[str, ...]] = {
    "kyle": ("buda",),
}


def _nearest_street_in_zone(
    router: CityRouter,
    zone: str,
    nodes_by_zone: dict[str, list[str]],
) -> tuple[str, float, float] | None:
    """Place on the nearest street when a zone has no native graph nodes."""
    ring = _zone_rings_by_name().get(zone)
    if ring is None:
        return None
    target_lat, target_lon = sample_interior_point(ring)
    if zone == "kyle":
        pool = [
            node_id
            for node_id in nodes_by_zone.get("buda", [])
            if (node := router.get_node(node_id)) is not None
            and zone_for_point(node.lat, node.lon) == "buda"
        ]
    else:
        pool = list(nodes_by_zone.get(zone, []))
        if not pool:
            for neighbor in _ZONE_NEIGHBORS.get(zone, ("buda", "southwest")):
                pool.extend(nodes_by_zone.get(neighbor, []))
    if not pool:
        return None
    best_id = min(
        pool,
        key=lambda node_id: (
            (router.get_node(node_id).lat - target_lat) ** 2  # type: ignore[union-attr]
            + (router.get_node(node_id).lon - target_lon) ** 2  # type: ignore[union-attr]
        ),
    )
    node = router.get_node(best_id)
    assert node is not None
    return best_id, node.lat, node.lon


_MIN_VEHICLE_SEPARATION_KM = 0.3


def _too_close(lat: float, lon: float, used: list[tuple[float, float]]) -> bool:
    """Return True when ``(lat, lon)`` is within the minimum fleet spacing."""
    return any(haversine_km(lat, lon, ulat, ulon) < _MIN_VEHICLE_SEPARATION_KM for ulat, ulon in used)


def _placement_in_zone(
    router: CityRouter,
    zone: str,
    rng: random.Random,
    nodes_by_zone: dict[str, list[str]],
    used_positions: list[tuple[float, float]],
) -> tuple[str, float, float] | None:
    """Place one vehicle inside ``zone``, spread from existing fleet positions."""
    zone_node_id = f"n-{zone}"
    node = router.get_node(zone_node_id)
    if node is not None and not _too_close(node.lat, node.lon, used_positions):
        return zone_node_id, node.lat, node.lon

    ring = _zone_rings_by_name().get(zone)
    if ring is not None:
        for _ in range(16):
            lat, lon = sample_interior_point(ring)
            node_id, snap = router.snap_point(lat, lon)
            if snap is None:
                continue
            if _too_close(snap.lat, snap.lon, used_positions):
                continue
            return node_id, snap.lat, snap.lon

    candidate = _snap_point_in_zone(router, zone, rng, nodes_by_zone)
    if candidate is not None:
        node_id, lat, lon = candidate
        if not _too_close(lat, lon, used_positions):
            return node_id, lat, lon

    if not nodes_by_zone.get(zone):
        candidate = _nearest_street_in_zone(router, zone, nodes_by_zone)
        if candidate is not None:
            node_id, lat, lon = candidate
            if not _too_close(lat, lon, used_positions):
                return node_id, lat, lon
    return None


def _snap_point_in_zone(
    router: CityRouter,
    zone: str,
    rng: random.Random,
    nodes_by_zone: dict[str, list[str]],
) -> tuple[str, float, float] | None:
    """Return ``(node_id, lat, lon)`` for a street point inside ``zone``."""
    candidates = [nid for nid in nodes_by_zone.get(zone, [])]
    rng.shuffle(candidates)
    for node_id in candidates:
        node = router.get_node(node_id)
        if node is not None and zone_for_point(node.lat, node.lon) == zone:
            return node_id, node.lat, node.lon

    bbox = zone_bounding_boxes().get(zone)
    if bbox is not None:
        min_lat, max_lat, min_lon, max_lon = bbox
        for _ in range(8):
            lat = rng.uniform(min_lat, max_lat)
            lon = rng.uniform(min_lon, max_lon)
            if zone_for_point(lat, lon) != zone:
                continue
            node_id, snap = router.snap_point(lat, lon)
            if node_id is not None and snap is not None and zone_for_point(snap.lat, snap.lon) == zone:
                return node_id, snap.lat, snap.lon

    ring = _zone_rings_by_name().get(zone)
    if ring is not None:
        for _ in range(8):
            lat, lon = sample_interior_point(ring)
            node_id, snap = router.snap_point(lat, lon)
            if node_id is not None and snap is not None and zone_for_point(snap.lat, snap.lon) == zone:
                return node_id, snap.lat, snap.lon
    return None


def _zone_fleet_assignments(fleet_size: int) -> list[str]:
    """Return zone labels receiving one vehicle each, then round-robin extras."""
    zones = all_zone_names()
    if not zones:
        return []
    assignments: list[str] = []
    while len(assignments) < fleet_size:
        for zone in zones:
            assignments.append(zone)
            if len(assignments) >= fleet_size:
                break
    return assignments


def build_world(
    *,
    city: str | None = None,
    policy: NetworkPolicy | None = None,
    seed: int = 42,
) -> tuple[CityRouter, SimulationState]:
    """Load city graph and seed exactly one idle vehicle per demand zone."""
    city_name = city or os.environ.get("ROBOTAXI_CITY", "austin")
    router = get_city_router(city_name)
    facilities = load_facilities(city_name, router)
    zones = all_zone_names()
    if not zones:
        raise RuntimeError("City has no demand zones")
    pol = (policy or NetworkPolicy()).model_copy(update={"fleet_size": len(zones)})
    rng = random.Random(seed)
    if not router.node_ids:
        raise RuntimeError("City graph has no nodes")

    nodes_by_zone = _nodes_by_zone(router)
    vehicles: dict[str, Vehicle] = {}
    used_positions: list[tuple[float, float]] = []

    for i, zone in enumerate(zones):
        vid = f"rx-{i + 1:03d}"
        placement = _placement_in_zone(router, zone, rng, nodes_by_zone, used_positions)
        if placement is None:
            zone_node = f"n-{zone}"
            node = router.get_node(zone_node)
            if node is not None:
                node_id, lat, lon = zone_node, node.lat, node.lon
            else:
                node_id = rng.choice(router.node_ids)
                node = router.get_node(node_id)
                assert node is not None
                lat, lon = node.lat, node.lon
        else:
            node_id, lat, lon = placement

        used_positions.append((lat, lon))
        vehicles[vid] = Vehicle(
            id=vid,
            state=VehicleState.IDLE,
            lat=lat,
            lon=lon,
            current_node_id=node_id,
            idle_since_h=0.0,
            facility_id=None,
        )

    state = SimulationState(vehicles=vehicles, policy=pol, facilities=facilities)
    return router, state
