"""Demand generator tests."""

from __future__ import annotations

from demand.generator import DemandGenerator


def test_rush_hour_multiplier() -> None:
    """Morning rush should exceed overnight demand."""
    gen = DemandGenerator()
    rush = gen.time_of_day_multiplier(8.0)
    night = gen.time_of_day_multiplier(3.0)
    assert rush > night


def test_expected_trips_scales_with_dt() -> None:
    """Longer intervals expect more trips."""
    gen = DemandGenerator()
    short = gen.expected_trips(0.25, 12.0)
    long = gen.expected_trips(1.0, 12.0)
    assert long > short


def test_spawn_returns_geo_points() -> None:
    """Spawned trips should be lat/lon pairs with a valid route."""
    from fixture_loader import load_fixture_router

    router = load_fixture_router()
    gen = DemandGenerator()
    gen.set_seed(99)
    for hour in range(20):
        pair = gen.maybe_spawn_trip(router, sim_time_h=float(hour), dt_hours=1.0)
        if pair is not None:
            origin, dest = pair
            assert origin.lat != 0.0
            assert router.route_between(origin.lat, origin.lon, dest.lat, dest.lon) is not None
            return
    raise AssertionError("expected at least one trip spawn in 20 hours")
