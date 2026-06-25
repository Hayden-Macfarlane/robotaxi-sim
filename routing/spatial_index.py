"""Grid spatial index for snap-to-street queries."""

from __future__ import annotations

from dataclasses import dataclass

from core_data.models import GeoPoint, RoadEdge
from routing.geo import project_point_on_segment


@dataclass(frozen=True)
class SnapResult:
    """Point projected onto the nearest street segment."""

    edge_id: str
    origin_node_id: str
    destination_node_id: str
    segment_index: int
    fraction_along_edge: float
    point: GeoPoint
    distance_km: float


class StreetSpatialIndex:
    """Bucket edge geometry segments into a lat/lon grid for fast nearest lookup."""

    def __init__(
        self,
        edges: dict[str, RoadEdge],
        *,
        cell_deg: float = 0.01,
        max_snap_km: float = 0.5,
    ) -> None:
        """Index all edge geometry segments."""
        self._edges = edges
        self._cell_deg = cell_deg
        self._max_snap_km = max_snap_km
        self._segments: list[tuple[str, int, GeoPoint, GeoPoint, str, str]] = []
        self._grid: dict[tuple[int, int], list[int]] = {}
        self._build()

    def _build(self) -> None:
        for edge_id, edge in self._edges.items():
            geom = edge.geometry
            if len(geom) < 2:
                continue
            for i in range(len(geom) - 1):
                idx = len(self._segments)
                a, b = geom[i], geom[i + 1]
                self._segments.append((edge_id, i, a, b, edge.origin_id, edge.destination_id))
                for cell in self._cells_for_segment(a, b):
                    self._grid.setdefault(cell, []).append(idx)

    def _cells_for_segment(self, a: GeoPoint, b: GeoPoint) -> set[tuple[int, int]]:
        min_lat = min(a.lat, b.lat)
        max_lat = max(a.lat, b.lat)
        min_lon = min(a.lon, b.lon)
        max_lon = max(a.lon, b.lon)
        cells: set[tuple[int, int]] = set()
        lat = min_lat
        while lat <= max_lat + self._cell_deg:
            lon = min_lon
            while lon <= max_lon + self._cell_deg:
                cells.add(self._cell_key(lat, lon))
                lon += self._cell_deg
            lat += self._cell_deg
        return cells

    def _cell_key(self, lat: float, lon: float) -> tuple[int, int]:
        return (int(lat / self._cell_deg), int(lon / self._cell_deg))

    def snap_to_network(self, lat: float, lon: float) -> SnapResult | None:
        """Return nearest point on any indexed street segment within max distance."""
        center = self._cell_key(lat, lon)
        candidate_indices: set[int] = set()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                bucket = self._grid.get((center[0] + dr, center[1] + dc))
                if bucket:
                    candidate_indices.update(bucket)
        if not candidate_indices:
            candidate_indices = set(range(len(self._segments)))

        best: SnapResult | None = None
        for idx in candidate_indices:
            edge_id, seg_i, a, b, origin_id, dest_id = self._segments[idx]
            point, frac, dist_km = project_point_on_segment(lat, lon, a, b)
            if dist_km > self._max_snap_km:
                continue
            snap = SnapResult(
                edge_id=edge_id,
                origin_node_id=origin_id,
                destination_node_id=dest_id,
                segment_index=seg_i,
                fraction_along_edge=frac,
                point=point,
                distance_km=dist_km,
            )
            if best is None or snap.distance_km < best.distance_km:
                best = snap
        return best
