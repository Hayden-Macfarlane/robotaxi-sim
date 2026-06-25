"""Edge-aware routing with street geometry."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from core_data.models import GeoPoint, RoadEdge, RouteLeg
from routing.geo import (
    merge_polylines,
    polyline_length_km,
    position_along_polyline,
    trim_polyline_from_fraction,
    trim_polyline_to_fraction,
)
from routing.spatial_index import SnapResult, StreetSpatialIndex


@dataclass(frozen=True)
class _RouteEndpoint:
    """Routing attachment point on the graph."""

    node_id: str
    edge_id: str | None
    fraction_on_edge: float
    point: GeoPoint


def build_route_leg(
    edges: dict[str, RoadEdge],
    adjacency: dict[str, list[RoadEdge]],
    spatial_index: StreetSpatialIndex,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    *,
    nearest_node_fn,
) -> RouteLeg | None:
    """Compute a street-following route between two arbitrary coordinates."""
    start = _endpoint_from_coord(lat1, lon1, spatial_index, nearest_node_fn)
    end = _endpoint_from_coord(lat2, lon2, spatial_index, nearest_node_fn)
    if start is None or end is None:
        return None

    edge_path, node_path, base_minutes = _dijkstra_edges(
        start.node_id,
        end.node_id,
        adjacency,
    )
    if edge_path is None or node_path is None:
        return None

    geometry_parts: list[list[GeoPoint]] = []
    for eid in edge_path:
        edge = edges.get(eid)
        if edge and edge.geometry:
            geometry_parts.append(list(edge.geometry))

    geometry = merge_polylines(geometry_parts)
    if not geometry:
        geometry = [start.point, end.point]

    if edge_path and edge_path[0] == start.edge_id and start.fraction_on_edge > 0:
        first = edges.get(start.edge_id)
        if first and first.geometry:
            trimmed = trim_polyline_from_fraction(list(first.geometry), start.fraction_on_edge)
            rest = merge_polylines([trimmed] + geometry_parts[1:])
            geometry = rest if rest else geometry

    if edge_path and edge_path[-1] == end.edge_id and end.fraction_on_edge < 1.0:
        last = edges.get(end.edge_id)
        if last and last.geometry:
            if edge_path[-1] == edge_path[0] and start.edge_id == end.edge_id:
                geometry = trim_polyline_to_fraction(
                    trim_polyline_from_fraction(list(last.geometry), start.fraction_on_edge),
                    max(0.0, (end.fraction_on_edge - start.fraction_on_edge) / max(1e-9, 1 - start.fraction_on_edge)),
                )
            else:
                geometry = merge_polylines(
                    geometry_parts[:-1] + [trim_polyline_to_fraction(list(last.geometry), end.fraction_on_edge)],
                )

    if not geometry:
        geometry = [start.point, end.point]
    if geometry[0].lat != start.point.lat or geometry[0].lon != start.point.lon:
        geometry = [start.point, *geometry]
    if geometry[-1].lat != end.point.lat or geometry[-1].lon != end.point.lon:
        geometry = [*geometry, end.point]

    travel_min = _adjust_travel_time(
        edges,
        edge_path,
        base_minutes,
        start,
        end,
    )
    distance_km = polyline_length_km(geometry)

    return RouteLeg(
        edge_ids=edge_path,
        node_path=node_path,
        geometry=geometry,
        distance_km=round(distance_km, 4),
        travel_time_min=round(max(0.0, travel_min), 2),
    )


def position_on_route(leg: RouteLeg, progress: float) -> tuple[GeoPoint, float]:
    """Return position and heading on a route leg at progress 0–1."""
    return position_along_polyline(leg.geometry, progress)


def _endpoint_from_coord(
    lat: float,
    lon: float,
    spatial_index: StreetSpatialIndex,
    nearest_node_fn,
) -> _RouteEndpoint | None:
    snap = spatial_index.snap_to_network(lat, lon)
    if snap is not None:
        return _RouteEndpoint(
            node_id=snap.origin_node_id if snap.fraction_along_edge < 0.5 else snap.destination_node_id,
            edge_id=snap.edge_id,
            fraction_on_edge=snap.fraction_along_edge,
            point=snap.point,
        )
    node_id = nearest_node_fn(lat, lon)
    if node_id is None:
        return None
    return _RouteEndpoint(
        node_id=node_id,
        edge_id=None,
        fraction_on_edge=0.0,
        point=GeoPoint(lat=lat, lon=lon),
    )


def _dijkstra_edges(
    origin_id: str,
    dest_id: str,
    adjacency: dict[str, list[RoadEdge]],
) -> tuple[list[str] | None, list[str] | None, float]:
    """Shortest path by travel time; return edge ids, node path, minutes."""
    if origin_id == dest_id:
        return [], [origin_id], 0.0

    dist: dict[str, float] = {origin_id: 0.0}
    prev_node: dict[str, str] = {}
    prev_edge: dict[str, str] = {}
    visited: set[str] = set()
    heap: list[tuple[float, str]] = [(0.0, origin_id)]

    while heap:
        cost, node_id = heapq.heappop(heap)
        if node_id in visited:
            continue
        visited.add(node_id)
        if node_id == dest_id:
            break
        for edge in adjacency.get(node_id, []):
            neighbour = edge.destination_id
            if neighbour in visited:
                continue
            edge_cost = edge.travel_time_min * edge.weight_multiplier
            new_cost = cost + edge_cost
            if new_cost < dist.get(neighbour, math.inf):
                dist[neighbour] = new_cost
                prev_node[neighbour] = node_id
                prev_edge[neighbour] = edge.id
                heapq.heappush(heap, (new_cost, neighbour))

    if dest_id not in dist:
        return None, None, 0.0

    node_path: list[str] = [dest_id]
    cursor = dest_id
    edge_path_rev: list[str] = []
    while cursor in prev_node:
        edge_path_rev.append(prev_edge[cursor])
        cursor = prev_node[cursor]
        node_path.append(cursor)
    node_path.reverse()
    edge_path_rev.reverse()
    return edge_path_rev, node_path, dist[dest_id]


def _adjust_travel_time(
    edges: dict[str, RoadEdge],
    edge_path: list[str],
    base_minutes: float,
    start: _RouteEndpoint,
    end: _RouteEndpoint,
) -> float:
    """Scale base edge-sum time for partial start/end edge fractions."""
    if not edge_path:
        return base_minutes
    total = 0.0
    for i, eid in enumerate(edge_path):
        edge = edges.get(eid)
        if edge is None:
            continue
        frac = 1.0
        if i == 0 and start.edge_id == eid:
            frac = max(0.0, 1.0 - start.fraction_on_edge)
        if i == len(edge_path) - 1 and end.edge_id == eid:
            end_frac = end.fraction_on_edge if end.edge_id == eid else 1.0
            if i == 0 and start.edge_id == eid:
                frac = max(0.0, end_frac - start.fraction_on_edge)
            else:
                frac = min(frac, end_frac)
        total += edge.travel_time_min * edge.weight_multiplier * frac
    return total if total > 0 else base_minutes
