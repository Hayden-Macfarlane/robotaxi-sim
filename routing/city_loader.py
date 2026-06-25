"""Load preprocessed city graph JSON into Pydantic models."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from core_data.models import Facility, RoadEdge, RoadNode
from routing.city_router import CityRouter

_DEFAULT_CITY = "austin"


def city_data_dir(city: str | None = None) -> Path:
    """Return the directory containing ``nodes.json`` and ``edges.json`` for a city."""
    name = (city or _DEFAULT_CITY).lower()
    root = Path(__file__).resolve().parents[1]
    standard = root / "data" / "cities" / name
    if standard.exists():
        return standard
    fixture = root / "tests" / "fixtures" / name
    if fixture.exists():
        return fixture
    return standard


def _city_slug(city: str | None = None) -> str:
    """Normalize city slug from argument or ``ROBOTAXI_CITY`` env."""
    return (city or os.environ.get("ROBOTAXI_CITY") or _DEFAULT_CITY).lower()


@lru_cache(maxsize=8)
def _load_city_graph_cached(name: str) -> tuple[tuple[RoadNode, ...], tuple[RoadEdge, ...]]:
    """Load graph JSON for ``name`` (internal cache key is the resolved slug)."""
    data_dir = city_data_dir(name)
    nodes_path = data_dir / "nodes.json"
    edges_path = data_dir / "edges.json"
    if not nodes_path.exists() or not edges_path.exists():
        msg = f"City graph not found at {data_dir}; run scripts/build_city_graph.py"
        raise FileNotFoundError(msg)

    with nodes_path.open(encoding="utf-8") as f:
        raw_nodes = json.load(f)
    with edges_path.open(encoding="utf-8") as f:
        raw_edges = json.load(f)

    nodes = tuple(RoadNode.model_validate(n) for n in raw_nodes)
    edges = tuple(RoadEdge.model_validate(e) for e in raw_edges)
    return nodes, edges


def load_city_graph(city: str | None = None) -> tuple[tuple[RoadNode, ...], tuple[RoadEdge, ...]]:
    """Load ``nodes.json`` and ``edges.json`` for the given city slug (cached)."""
    return _load_city_graph_cached(_city_slug(city))


def clear_city_graph_cache() -> None:
    """Clear cached graph payloads and routers (for tests that need a cold load)."""
    _load_city_graph_cached.cache_clear()
    _get_city_router_cached.cache_clear()


@lru_cache(maxsize=8)
def _get_city_router_cached(name: str) -> CityRouter:
    """Return a cached router for ``name``."""
    nodes, edges = _load_city_graph_cached(name)
    return CityRouter(list(nodes), list(edges))


def get_city_router(city: str | None = None) -> CityRouter:
    """Return a cached ``CityRouter`` for ``city`` (spatial index built once)."""
    return _get_city_router_cached(_city_slug(city))


def load_facilities(city: str | None = None, router: object | None = None) -> dict[str, Facility]:
    """Load ``facilities.json`` and snap each anchor to the street network."""
    name = _city_slug(city)
    data_dir = city_data_dir(name)
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
