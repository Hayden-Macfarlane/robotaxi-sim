"""Build and export city road graphs for robotaxi routing.

Uses OSM via osmnx when available; falls back to a curved pseudo-street graph
with edge geometry so the repo works without network after first build.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GRAPH_SCHEMA_VERSION = 2

# Austin, TX approximate bbox
AUSTIN_BBOX = {
    "north": 30.45,
    "south": 30.15,
    "east": -97.55,
    "west": -97.85,
}


def _zone_for_lat_lon(lat: float, lon: float) -> str:
    """Assign a demand zone from position within the Austin bbox."""
    from routing.zones import zone_for_point

    return zone_for_point(lat, lon)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    earth_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return earth_km * 2 * math.asin(math.sqrt(a))


def _geometry_length_km(geometry: list[dict[str, float]]) -> float:
    """Sum segment lengths along a coordinate polyline."""
    total = 0.0
    for i in range(len(geometry) - 1):
        a, b = geometry[i], geometry[i + 1]
        total += _haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    return total


def _curved_edge_geometry(
    na: dict,
    nb: dict,
    *,
    bulge: float = 0.002,
    segments: int = 6,
) -> list[dict[str, float]]:
    """Build a curved street centerline between two nodes."""
    mid_lat = (na["lat"] + nb["lat"]) / 2 + bulge * (nb["lon"] - na["lon"])
    mid_lon = (na["lon"] + nb["lon"]) / 2 - bulge * (nb["lat"] - na["lat"])
    points: list[dict[str, float]] = []
    for i in range(segments + 1):
        t = i / segments
        u = 1.0 - t
        lat = u * u * na["lat"] + 2 * u * t * mid_lat + t * t * nb["lat"]
        lon = u * u * na["lon"] + 2 * u * t * mid_lon + t * t * nb["lon"]
        points.append({"lat": round(lat, 6), "lon": round(lon, 6)})
    return points


def build_synthetic_curved_streets(*, rows: int = 10, cols: int = 10) -> tuple[list[dict], list[dict]]:
    """Create a curved street mesh inside the Austin bbox (dev fallback)."""
    lat_span = AUSTIN_BBOX["north"] - AUSTIN_BBOX["south"]
    lon_span = AUSTIN_BBOX["east"] - AUSTIN_BBOX["west"]
    nodes: list[dict] = []
    index: dict[tuple[int, int], str] = {}

    for r in range(rows):
        for c in range(cols):
            wobble_lat = 0.015 * math.sin(c * 0.9) * lat_span
            wobble_lon = 0.015 * math.sin(r * 0.7) * lon_span
            nid = f"n-{r}-{c}"
            lat = AUSTIN_BBOX["south"] + (r + 0.5) * lat_span / rows + wobble_lat
            lon = AUSTIN_BBOX["west"] + (c + 0.5) * lon_span / cols + wobble_lon
            zone = _zone_for_lat_lon(lat, lon)
            nodes.append({"id": nid, "lat": round(lat, 6), "lon": round(lon, 6), "zone": zone})
            index[(r, c)] = nid

    edges: list[dict] = []
    eid = 0

    def _add(a: str, b: str, na: dict, nb: dict, *, bulge_sign: float = 1.0) -> None:
        nonlocal eid
        geometry = _curved_edge_geometry(na, nb, bulge=0.0015 * bulge_sign)
        dist_km = max(0.05, _geometry_length_km(geometry))
        time_min = max(0.5, dist_km / 30.0 * 60.0)
        eid += 1
        edges.append({
            "id": f"e-{eid}",
            "origin_id": a,
            "destination_id": b,
            "distance_km": round(dist_km, 4),
            "travel_time_min": round(time_min, 2),
            "weight_multiplier": 1.0,
            "geometry": geometry,
            "name": f"Dev St {eid}",
            "highway": "residential",
        })

    for r in range(rows):
        for c in range(cols):
            a = index[(r, c)]
            na = next(n for n in nodes if n["id"] == a)
            if c + 1 < cols:
                b = index[(r, c + 1)]
                nb = next(n for n in nodes if n["id"] == b)
                _add(a, b, na, nb, bulge_sign=1.0)
                _add(b, a, nb, na, bulge_sign=-1.0)
            if r + 1 < rows:
                b = index[(r + 1, c)]
                nb = next(n for n in nodes if n["id"] == b)
                _add(a, b, na, nb, bulge_sign=-1.0)
                _add(b, a, nb, na, bulge_sign=1.0)

    return nodes, edges


def _linestring_to_geometry(line) -> list[dict[str, float]]:
    """Convert shapely/osmnx LineString coords (lon, lat) to GeoPoint dicts."""
    coords = list(line.coords)
    return [{"lat": round(float(y), 6), "lon": round(float(x), 6)} for x, y in coords]


def try_osmnx_austin() -> tuple[list[dict], list[dict]] | None:
    """Download full Austin drive network with edge geometry."""
    try:
        import osmnx as ox
    except ImportError:
        return None

    try:
        g = ox.graph_from_bbox(
            bbox=(
                AUSTIN_BBOX["west"],
                AUSTIN_BBOX["south"],
                AUSTIN_BBOX["east"],
                AUSTIN_BBOX["north"],
            ),
            network_type="drive",
            simplify=True,
        )
        g = ox.add_edge_speeds(g)
        g = ox.add_edge_travel_times(g)
    except Exception:
        return None

    nodes: list[dict] = []
    node_map: dict[int, str] = {}
    for nid, data in g.nodes(data=True):
        sid = f"osm-{nid}"
        node_map[nid] = sid
        lat = float(data.get("y", data.get("lat", 0.0)))
        lon = float(data.get("x", data.get("lon", 0.0)))
        nodes.append({
            "id": sid,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "zone": _zone_for_lat_lon(lat, lon),
        })

    edges: list[dict] = []
    eid = 0
    for u, v, _key, data in g.edges(keys=True, data=True):
        ou = node_map.get(u)
        dv = node_map.get(v)
        if ou is None or dv is None:
            continue
        geom = data.get("geometry")
        if geom is not None:
            geometry = _linestring_to_geometry(geom)
        else:
            nu = next(n for n in nodes if n["id"] == ou)
            nv = next(n for n in nodes if n["id"] == dv)
            geometry = [{"lat": nu["lat"], "lon": nu["lon"]}, {"lat": nv["lat"], "lon": nv["lon"]}]
        dist_km = _geometry_length_km(geometry)
        if dist_km <= 0:
            length_m = float(data.get("length", 100.0))
            dist_km = max(0.01, length_m / 1000.0)
        time_min = float(data.get("travel_time", max(30.0, dist_km * 1000 / 8.0)) / 60.0)
        eid += 1
        edges.append({
            "id": f"e-{eid}",
            "origin_id": ou,
            "destination_id": dv,
            "distance_km": round(dist_km, 4),
            "travel_time_min": round(max(0.1, time_min), 2),
            "weight_multiplier": 1.0,
            "geometry": geometry,
            "name": str(data.get("name", "") or ""),
            "highway": str(data.get("highway", "") or ""),
        })

    if len(nodes) < 10 or len(edges) < 10:
        return None
    return nodes, edges


def write_city(city: str, nodes: list[dict], edges: list[dict]) -> Path:
    """Write graph JSON to ``data/cities/{city}/``."""
    out = ROOT / "data" / "cities" / city
    out.mkdir(parents=True, exist_ok=True)
    meta = {"schema_version": GRAPH_SCHEMA_VERSION, "source": "osm"}
    with (out / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    with (out / "nodes.json").open("w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=2)
    with (out / "edges.json").open("w", encoding="utf-8") as f:
        json.dump(edges, f)
    return out


def main() -> None:
    """Build Austin city graph (OSM if possible, else curved dev streets)."""
    city = "austin"
    result = try_osmnx_austin()
    if result is None:
        print("Using curved dev street graph (install osmnx for real OSM graph)")
        nodes, edges = build_synthetic_curved_streets()
        meta_source = "synthetic"
    else:
        print("Built graph from OpenStreetMap (full Austin bbox)")
        nodes, edges = result
        meta_source = "osm"
    out = write_city(city, nodes, edges)
    meta_path = out / "meta.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump({"schema_version": GRAPH_SCHEMA_VERSION, "source": meta_source}, f, indent=2)
    print(f"Wrote {len(nodes)} nodes, {len(edges)} edges → {out}")


if __name__ == "__main__":
    main()
