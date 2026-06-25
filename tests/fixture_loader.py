"""Load test fixture city graphs."""

from __future__ import annotations

import json
from pathlib import Path

from core_data.models import Facility, RoadEdge, RoadNode
from routing.city_router import CityRouter

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture_router(name: str = "mini_austin") -> CityRouter:
    """Load a small geometry-rich graph from ``tests/fixtures/{name}/``."""
    base = _FIXTURES / name
    with (base / "nodes.json").open(encoding="utf-8") as f:
        raw_nodes = json.load(f)
    with (base / "edges.json").open(encoding="utf-8") as f:
        raw_edges = json.load(f)
    nodes = [RoadNode.model_validate(n) for n in raw_nodes]
    edges = [RoadEdge.model_validate(e) for e in raw_edges]
    return CityRouter(nodes, edges)


def load_fixture_facilities(name: str = "mini_austin") -> dict[str, Facility]:
    """Load facility anchors from ``tests/fixtures/{name}/facilities.json``."""
    path = _FIXTURES / name / "facilities.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    return {f["id"]: Facility.model_validate(f) for f in raw}
