"""Tests for deadzone coverage filler."""

from __future__ import annotations

from core_data.models import NetworkPolicy, Vehicle, VehicleState
from dispatch.deadzone import (
    deadzone_fill_ratio,
    find_deadzones,
    nearest_idle_asset_km,
    passes_deadzone_fill_ratio,
    pick_deadzone_fill_decision,
)
from fixture_loader import load_fixture_router


def test_nearest_idle_asset_km() -> None:
    vehicles = {
        "a": Vehicle(id="a", state=VehicleState.IDLE, lat=30.0, lon=-97.0, current_node_id="n"),
        "b": Vehicle(id="b", state=VehicleState.IDLE, lat=30.1, lon=-97.1, current_node_id="n"),
    }
    dist = nearest_idle_asset_km(30.05, -97.05, vehicles)
    assert dist is not None
    assert dist < 20.0


def test_deadzone_fill_ratio_uses_adjustments() -> None:
    policy = NetworkPolicy(
        deadzone_size_adjustment_km=0.5,
        deadzone_travel_adjustment_km=0.5,
        deadzone_fill_ratio_threshold=1.0,
    )
    ratio = deadzone_fill_ratio(2.0, 2.0, policy)
    assert ratio == 2.5 / 2.5
    assert passes_deadzone_fill_ratio(2.0, 2.0, policy)


def test_find_deadzones_when_assets_far() -> None:
    router = load_fixture_router()
    bbox = router.zone_bounding_boxes()
    assert bbox
    zone = next(iter(bbox))
    min_lat, max_lat, min_lon, max_lon = bbox[zone]
    lat = (min_lat + max_lat) / 2
    lon = (min_lon + max_lon) / 2
    vehicles = {
        "v1": Vehicle(
            id="v1",
            state=VehicleState.IDLE,
            lat=lat + 0.5,
            lon=lon + 0.5,
            current_node_id="n-a",
            idle_since_h=0.0,
        ),
    }
    policy = NetworkPolicy(
        deadzone_filler_enabled=True,
        max_distance_from_nearest_asset_km=0.5,
    )
    deadzones = find_deadzones(router, vehicles, policy)
    assert len(deadzones) >= 1
    assert all(d.size_km > 0 for d in deadzones)


def test_pick_deadzone_fill_respects_ratio_threshold() -> None:
    router = load_fixture_router()
    zones = list(router.zone_bounding_boxes().keys())
    assert len(zones) >= 2
    z1 = zones[1]
    b1 = router.zone_bounding_boxes()[z1]
    lat1 = (b1[0] + b1[1]) / 2
    lon1 = (b1[2] + b1[3]) / 2
    vehicles = {
        "solo": Vehicle(
            id="solo",
            state=VehicleState.IDLE,
            lat=lat1,
            lon=lon1,
            current_node_id="n-b",
            idle_since_h=0.0,
        ),
    }
    import random

    strict = NetworkPolicy(
        deadzone_filler_enabled=True,
        max_distance_from_nearest_asset_km=0.5,
        deadzone_fill_ratio_threshold=20.0,
        reposition_idle_min=1.0,
    )
    assert pick_deadzone_fill_decision(
        vehicles["solo"],
        router,
        strict,
        vehicles,
        sim_time_h=10.0,
        claimed=set(),
        rng=random.Random(1),
    ) is None

    loose = NetworkPolicy(
        deadzone_filler_enabled=True,
        max_distance_from_nearest_asset_km=0.5,
        deadzone_fill_ratio_threshold=0.01,
        max_reposition_min=500.0,
        reposition_idle_min=1.0,
    )
    fill = pick_deadzone_fill_decision(
        vehicles["solo"],
        router,
        loose,
        vehicles,
        sim_time_h=10.0,
        claimed=set(),
        rng=random.Random(1),
    )
    assert fill is not None
    assert fill.fill_ratio >= loose.deadzone_fill_ratio_threshold
