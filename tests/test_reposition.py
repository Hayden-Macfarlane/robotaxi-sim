"""Tests for fleet repositioning zone helpers."""

from __future__ import annotations

from core_data.models import NetworkPolicy, Vehicle, VehicleState
from dispatch.reposition import (
    default_target_supply_by_zone,
    reposition_benefit,
    should_post_trip_reposition,
    surplus_idle_vehicles,
    vehicle_zone,
    zone_cap,
)
from fixture_loader import load_fixture_router


def test_default_target_supply_splits_by_zone_weights() -> None:
    zones = ["downtown", "central", "northwest"]
    targets = default_target_supply_by_zone(12, zones, {})
    assert sum(targets.values()) == 12
    assert targets["downtown"] >= targets["central"] >= targets["northwest"]


def test_zone_cap_per_zone_override() -> None:
    policy = NetworkPolicy(max_idle_per_zone=5, max_idle_by_zone={"downtown": 2})
    assert zone_cap(policy, "downtown") == 2
    assert zone_cap(policy, "northwest") == 5


def test_reposition_benefit_gates_long_deadhead() -> None:
    policy = NetworkPolicy(min_reposition_benefit=0.5, value_per_trip=2.0, deadhead_cost_per_min=0.15)
    assert reposition_benefit(3.0, 2.0, policy) > policy.min_reposition_benefit
    assert reposition_benefit(0.2, 30.0, policy) < policy.min_reposition_benefit


def test_surplus_idle_vehicles_returns_excess() -> None:
    router = load_fixture_router()
    lat, lon = 30.20, -97.80
    zone = vehicle_zone(
        Vehicle(id="x", state=VehicleState.IDLE, lat=lat, lon=lon, current_node_id="n-a"),
        router,
    )
    policy = NetworkPolicy(max_idle_by_zone={zone: 2})
    vehicles = {
        f"v-{i}": Vehicle(
            id=f"v-{i}",
            state=VehicleState.IDLE,
            lat=lat,
            lon=lon,
            current_node_id="n-a",
            idle_since_h=float(i),
        )
        for i in range(5)
    }
    supply = {zone: 5}
    surplus = surplus_idle_vehicles(vehicles, router, policy, supply)
    assert len(surplus) == 3


def test_should_post_trip_reposition_at_cap() -> None:
    router = load_fixture_router()
    from demand.generator import DemandGenerator

    demand = DemandGenerator()
    policy = NetworkPolicy(max_idle_per_zone=2)
    assert should_post_trip_reposition(
        "central",
        router,
        policy,
        demand,
        sim_time_h=10.0,
        supply_by_zone={"central": 2},
        pending_by_zone={},
    )
    assert not should_post_trip_reposition(
        "central",
        router,
        policy,
        demand,
        sim_time_h=10.0,
        supply_by_zone={"central": 1},
        pending_by_zone={},
    )
