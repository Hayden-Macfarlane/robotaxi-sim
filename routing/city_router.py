"""Dijkstra shortest-path routing over a city road graph with street geometry."""

from __future__ import annotations

import math
from collections import defaultdict

from core_data.models import GeoPoint, RoadEdge, RoadNode, RouteLeg
from routing.geo import haversine_km, position_along_polyline
from routing.route import build_route_leg, position_on_route
from routing.spatial_index import SnapResult, StreetSpatialIndex


class CityRouter:
    """Directed weighted graph with street-following pathfinding."""

    def __init__(self, nodes: list[RoadNode], edges: list[RoadEdge]) -> None:
        """Build adjacency from static topology."""
        self._nodes = {n.id: n for n in nodes}
        self._edges = {e.id: e for e in edges}
        self._adjacency: dict[str, list[RoadEdge]] = defaultdict(list)
        self._demand_zone_nodes: dict[str, list[str]] | None = None
        self._geo_bounds: tuple[float, float, float, float] | None = None
        for node_id in self._nodes:
            _ = self._adjacency[node_id]
        for edge in self._edges.values():
            self._adjacency[edge.origin_id].append(edge)
        self._spatial_index = StreetSpatialIndex(self._edges)

    @property
    def nodes(self) -> dict[str, RoadNode]:
        """All road nodes keyed by id."""
        return self._nodes

    @property
    def edges(self) -> dict[str, RoadEdge]:
        """All road edges keyed by id."""
        return self._edges

    @property
    def node_ids(self) -> list[str]:
        """List of all node ids."""
        return list(self._nodes.keys())

    def street_geometries(self) -> list[list[GeoPoint]]:
        """Return centerline polylines for map rendering."""
        lines: list[list[GeoPoint]] = []
        seen: set[str] = set()
        for edge in self._edges.values():
            if len(edge.geometry) < 2:
                continue
            key = f"{edge.origin_id}:{edge.destination_id}"
            if key in seen:
                continue
            seen.add(key)
            lines.append(list(edge.geometry))
        return lines

    def get_node(self, node_id: str) -> RoadNode | None:
        """Return a node by id or None."""
        return self._nodes.get(node_id)

    def snap_point(self, lat: float, lon: float) -> tuple[str, GeoPoint]:
        """Snap a coordinate to the nearest street segment or graph vertex."""
        snap = self._spatial_index.snap_to_network(lat, lon)
        if snap is not None:
            node_id = snap.origin_node_id if snap.fraction_along_edge < 0.5 else snap.destination_node_id
            return node_id, snap.point
        node_id = self.nearest_node_id(lat, lon)
        if node_id is None:
            msg = "Graph has no nodes"
            raise RuntimeError(msg)
        node = self._nodes[node_id]
        return node_id, GeoPoint(lat=node.lat, lon=node.lon)

    def snap_to_network(self, lat: float, lon: float) -> SnapResult | None:
        """Return detailed snap result on the street network."""
        return self._spatial_index.snap_to_network(lat, lon)

    def route_between(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> RouteLeg | None:
        """Snap endpoints and return a street-following route."""
        return build_route_leg(
            self._edges,
            self._adjacency,
            self._spatial_index,
            lat1,
            lon1,
            lat2,
            lon2,
            nearest_node_fn=self.nearest_node_id,
        )

    def position_on_leg(self, leg: RouteLeg, progress: float) -> tuple[GeoPoint, float]:
        """Return point and heading on a route leg."""
        return position_on_route(leg, progress)

    def polyline_for_path(self, node_path: list[str]) -> list[GeoPoint]:
        """Convert a node id path to coordinates (legacy helper)."""
        return [
            GeoPoint(lat=self._nodes[nid].lat, lon=self._nodes[nid].lon)
            for nid in node_path
            if nid in self._nodes
        ]

    def position_along_polyline(self, polyline: list[GeoPoint], progress: float) -> GeoPoint:
        """Return the point at ``progress`` along a polyline."""
        point, _ = position_along_polyline(polyline, progress)
        return point

    def travel_time_min(
        self,
        origin_id: str,
        destination_id: str,
    ) -> float | None:
        """Return minimum travel time in minutes between two nodes."""
        if origin_id not in self._nodes or destination_id not in self._nodes:
            return None
        o = self._nodes[origin_id]
        d = self._nodes[destination_id]
        leg = self.route_between(o.lat, o.lon, d.lat, d.lon)
        return leg.travel_time_min if leg else None

    def travel_time_between_points(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        *,
        traffic_multiplier: float = 1.0,
    ) -> float | None:
        """Return minimum travel time in minutes between two arbitrary coordinates."""
        leg = self.route_between(lat1, lon1, lat2, lon2)
        if leg is None:
            return None
        return leg.travel_time_min * traffic_multiplier

    def find_shortest_path(
        self,
        origin_id: str,
        destination_id: str,
    ) -> tuple[list[str], float] | None:
        """Return ``(node_id_path, total_travel_time_min)`` or None if unreachable."""
        if origin_id not in self._nodes or destination_id not in self._nodes:
            return None
        o = self._nodes[origin_id]
        d = self._nodes[destination_id]
        leg = self.route_between(o.lat, o.lon, d.lat, d.lon)
        if leg is None:
            return None
        return leg.node_path, leg.travel_time_min

    def nearest_node_id(self, lat: float, lon: float) -> str | None:
        """Return the node id closest to WGS-84 coordinates."""
        if not self._nodes:
            return None
        best_id = ""
        best_d = math.inf
        for node in self._nodes.values():
            d = (node.lat - lat) ** 2 + (node.lon - lon) ** 2
            if d < best_d:
                best_d = d
                best_id = node.id
        return best_id or None

    def nodes_by_zone(self) -> dict[str, list[str]]:
        """Group node ids by zone label."""
        zones: dict[str, list[str]] = defaultdict(list)
        for node in self._nodes.values():
            zone = node.zone or "unknown"
            zones[zone].append(node.id)
        return dict(zones)

    def nodes_by_demand_zone(self) -> dict[str, list[str]]:
        """Group node ids by highway-aligned demand zone (computed once per router)."""
        if self._demand_zone_nodes is not None:
            return self._demand_zone_nodes
        from routing.zones import zone_for_point

        grouped: dict[str, list[str]] = defaultdict(list)
        for node in self._nodes.values():
            zone = zone_for_point(node.lat, node.lon)
            if zone != "unknown":
                grouped[zone].append(node.id)
        self._demand_zone_nodes = dict(grouped)
        return self._demand_zone_nodes

    def zone_bounding_boxes(self) -> dict[str, tuple[float, float, float, float]]:
        """Return ``(min_lat, max_lat, min_lon, max_lon)`` per zone label."""
        boxes: dict[str, list[float]] = {}
        for node in self._nodes.values():
            zone = node.zone or "unknown"
            if zone not in boxes:
                boxes[zone] = [node.lat, node.lat, node.lon, node.lon]
            else:
                b = boxes[zone]
                b[0] = min(b[0], node.lat)
                b[1] = max(b[1], node.lat)
                b[2] = min(b[2], node.lon)
                b[3] = max(b[3], node.lon)
        return {z: (b[0], b[1], b[2], b[3]) for z, b in boxes.items()}

    def geographic_bounds(self) -> tuple[float, float, float, float]:
        """Return ``(min_lat, max_lat, min_lon, max_lon)`` for the full graph."""
        if self._geo_bounds is not None:
            return self._geo_bounds
        min_lat = min_lon = float("inf")
        max_lat = max_lon = float("-inf")
        for node in self._nodes.values():
            min_lat = min(min_lat, node.lat)
            max_lat = max(max_lat, node.lat)
            min_lon = min(min_lon, node.lon)
            max_lon = max(max_lon, node.lon)
        if min_lat == float("inf"):
            min_lat = max_lat = min_lon = max_lon = 0.0
        self._geo_bounds = (min_lat, max_lat, min_lon, max_lon)
        return self._geo_bounds
