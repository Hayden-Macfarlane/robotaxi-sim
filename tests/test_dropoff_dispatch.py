"""Tests for dropoff-aware dispatch scoring."""

from __future__ import annotations

from unittest.mock import patch

from core_data.models import GeoPoint, NetworkPolicy, TripRequest, TripStatus, Vehicle, VehicleState
from dispatch.matcher import (
    DispatchZoneContext,
    dispatch_zone_context_from_rows,
    pick_best_vehicle,
    rank_dispatch_candidates,
)
from dispatch.reposition import ZoneBalance
from fixture_loader import load_fixture_router
from routing.zones import zone_for_point


def _trip_and_vehicles() -> tuple[TripRequest, dict[str, Vehicle], str, str]:
    router = load_fixture_router()
    origin = router.nodes["n-a"]
    dest = router.nodes["n-c"]
    pickup_zone = zone_for_point(origin.lat, origin.lon)
    dropoff_zone = zone_for_point(dest.lat, dest.lon)
    trip = TripRequest(
        id="t-drop",
        origin=GeoPoint(lat=origin.lat, lon=origin.lon),
        destination=GeoPoint(lat=dest.lat, lon=dest.lon),
        origin_snap_node_id=origin.id,
        destination_snap_node_id=dest.id,
        status=TripStatus.PENDING,
        requested_at_h=0.0,
    )
    vehicles = {
        "at_pickup": Vehicle(
            id="at_pickup",
            state=VehicleState.IDLE,
            lat=origin.lat,
            lon=origin.lon,
            current_node_id=origin.id,
        ),
        "at_dropoff": Vehicle(
            id="at_dropoff",
            state=VehicleState.IDLE,
            lat=dest.lat,
            lon=dest.lon,
            current_node_id=dest.id,
        ),
    }
    return trip, vehicles, pickup_zone, dropoff_zone


def test_dropoff_balance_prefers_vehicle_that_fills_deficit_zone() -> None:
    """Vehicle leaving pickup zone for a deficit dropoff zone ranks higher when ETAs tie."""
    router = load_fixture_router()
    trip, vehicles, _, _ = _trip_and_vehicles()

    def _zones(lat: float, lon: float) -> str:
        if lon <= -97.795:
            return "pickup_zone"
        return "dropoff_zone"

    zone_ctx = DispatchZoneContext(
        supply_by_zone={"pickup_zone": 2, "dropoff_zone": 0},
        gap_by_zone={"pickup_zone": -1.0, "dropoff_zone": 3.0},
        cap_by_zone={"pickup_zone": 3, "dropoff_zone": 5},
    )
    policy = NetworkPolicy(
        dispatch_weight_eta=0.0,
        dispatch_consider_dropoff_balance=True,
        dispatch_weight_dropoff_balance=5.0,
    )
    with patch("dispatch.matcher.zone_for_point", side_effect=_zones):
        ranked = rank_dispatch_candidates(
            trip,
            vehicles,
            router,
            policy=policy,
            zone_ctx=zone_ctx,
            limit=2,
        )
    assert len(ranked) == 2
    assert ranked[0].vehicle_id == "at_pickup"
    assert ranked[0].balance_adjustment < 0
    assert ranked[1].balance_adjustment >= ranked[0].balance_adjustment


def test_dropoff_balance_disabled_uses_eta_only() -> None:
    """When dropoff balance is off, closer vehicle wins regardless of zone gap."""
    router = load_fixture_router()
    trip, vehicles, pickup_zone, dropoff_zone = _trip_and_vehicles()
    zone_ctx = DispatchZoneContext(
        supply_by_zone={pickup_zone: 2, dropoff_zone: 0},
        gap_by_zone={pickup_zone: -1.0, dropoff_zone: 3.0},
        cap_by_zone={pickup_zone: 3, dropoff_zone: 5},
    )
    policy = NetworkPolicy(dispatch_consider_dropoff_balance=False)
    match = pick_best_vehicle(trip, vehicles, router, policy=policy, zone_ctx=zone_ctx)
    assert match is not None
    assert match.vehicle_id == "at_pickup"
    assert match.balance_adjustment == 0.0


def test_dropoff_surplus_penalty_worsens_score() -> None:
    """Assigning into an over-cap dropoff zone increases score (worse rank)."""
    router = load_fixture_router()
    trip, vehicles, pickup_zone, dropoff_zone = _trip_and_vehicles()
    zone_ctx = DispatchZoneContext(
        supply_by_zone={pickup_zone: 1, dropoff_zone: 5},
        gap_by_zone={pickup_zone: 0.0, dropoff_zone: -2.0},
        cap_by_zone={pickup_zone: 3, dropoff_zone: 3},
    )
    policy = NetworkPolicy(
        dispatch_weight_eta=0.0,
        dispatch_consider_dropoff_balance=True,
        dispatch_penalty_dropoff_surplus_min=10.0,
        dispatch_weight_dropoff_balance=0.0,
    )
    ranked = rank_dispatch_candidates(
        trip,
        vehicles,
        router,
        policy=policy,
        zone_ctx=zone_ctx,
        limit=2,
    )
    pickup_candidate = next(c for c in ranked if c.vehicle_id == "at_pickup")
    assert pickup_candidate.balance_adjustment > 0


def test_dispatch_zone_context_from_rows() -> None:
    """Helper builds gap and cap maps from zone balance rows."""
    rows = [
        ZoneBalance(
            zone="downtown",
            supply=1,
            pending_demand=0,
            expected_demand=2.0,
            target_supply=3,
            gap=2.0,
            max_idle=4,
        ),
    ]
    ctx = dispatch_zone_context_from_rows({"downtown": 1}, rows, NetworkPolicy())
    assert ctx.gap_by_zone["downtown"] == 2.0
    assert ctx.cap_by_zone["downtown"] == 4
