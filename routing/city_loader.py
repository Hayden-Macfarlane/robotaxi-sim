"""Load preprocessed city graph JSON into Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

from core_data.models import Facility, RoadEdge, RoadNode

_DEFAULT_CITY = "austin"


def city_data_dir(city: str | None = None) -> Path:
    """Return the directory containing ``nodes.json`` and ``edges.json`` for a city."""
    name = (city or _DEFAULT_CITY).lower()
    root = Path(__file__).resolve().parents[1]
    return root / "data" / "cities" / name


def load_city_graph(city: str | None = None) -> tuple[list[RoadNode], list[RoadEdge]]:
    """Load ``nodes.json`` and ``edges.json`` for the given city slug."""
    data_dir = city_data_dir(city)
    nodes_path = data_dir / "nodes.json"
    edges_path = data_dir / "edges.json"
    if not nodes_path.exists() or not edges_path.exists():
        msg = f"City graph not found at {data_dir}; run scripts/build_city_graph.py"
        raise FileNotFoundError(msg)

    with nodes_path.open(encoding="utf-8") as f:
        raw_nodes = json.load(f)
    with edges_path.open(encoding="utf-8") as f:
        raw_edges = json.load(f)

    nodes = [RoadNode.model_validate(n) for n in raw_nodes]
    edges = [RoadEdge.model_validate(e) for e in raw_edges]
    return nodes, edges


def load_facilities(city: str | None = None, router: object | None = None) -> dict[str, Facility]:
    """Load ``facilities.json`` and snap each anchor to the street network."""
    from routing.city_router import CityRouter

    data_dir = city_data_dir(city)
    path = data_dir / "facilities.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    facilities: dict[str, Facility] = {}
    rtr = router if isinstance(router, CityRouter) else None
    for item in raw:
        fac = Facility.model_validate(item)
        if rtr is not None:
            node_id, point = rtr.snap_point(fac.lat, fac.lon)
            fac = fac.model_copy(update={"node_id": node_id, "lat": point.lat, "lon": point.lon})
        facilities[fac.id] = fac
    return facilities
