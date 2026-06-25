"""Tests for per-zone demand forecast curves."""

from __future__ import annotations

from core_data.models import SpecialEvent
from demand.forecast import event_boost_for_zone, forecast_intensity, zone_hourly_multiplier
from demand.generator import DemandGenerator
from dispatch.reposition import expected_demand_by_zone
from fixture_loader import load_fixture_router


def test_airport_peak_higher_than_off_peak() -> None:
    morning = zone_hourly_multiplier("airport", 8.0)
    night = zone_hourly_multiplier("airport", 2.0)
    assert morning > night


def test_east_side_peaks_evening() -> None:
    evening = zone_hourly_multiplier("east_side", 21.0)
    morning = zone_hourly_multiplier("east_side", 9.0)
    assert evening > morning


def test_special_event_boosts_zone() -> None:
    events = [SpecialEvent(id="e1", label="Show", zone="east_side", start_h=20.0, end_h=23.0, demand_multiplier=3.0)]
    boost = event_boost_for_zone("east_side", 21.0, events)
    assert boost == 3.0


def test_lookahead_demand_differs_from_now() -> None:
    router = load_fixture_router()
    demand = DemandGenerator()
    now = expected_demand_by_zone(demand, router, sim_time_h=7.0, pending_by_zone={})
    later = expected_demand_by_zone(
        demand, router, sim_time_h=7.0, pending_by_zone={}, horizon_h=0.5,
    )
    assert now["downtown"] != later["downtown"] or now == later
