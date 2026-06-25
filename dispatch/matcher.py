"""Vehicle–trip matching by ETA."""

from __future__ import annotations

from dataclasses import dataclass

from core_data.models import NetworkPolicy, TripRequest, Vehicle, VehicleState
from fleet.health import is_dispatch_eligible
from routing.geo import haversine_km
from routing.city_router import CityRouter

# Approximate road-network factor for quick UI ETA ranking (not used for actual dispatch).
_STREET_FACTOR = 1.35
_AVG_SPEED_KMH = 32.0


def _haversine_eta_min(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Estimate driving minutes from straight-line distance."""
    km = haversine_km(lat1, lon1, lat2, lon2) * _STREET_FACTOR
    return km / (_AVG_SPEED_KMH / 60.0)


@dataclass(frozen=True)
class MatchCandidate:
    """Scored vehicle assignment for a pending trip."""

    vehicle_id: str
    eta_min: float
    score: float
    state: VehicleState = VehicleState.IDLE


def _vehicle_dispatch_eligible(
    vehicle: Vehicle,
    policy: NetworkPolicy,
    *,
    include_repositioning: bool,
) -> bool:
    """Return True if vehicle may be considered for trip dispatch."""
    allowed = {VehicleState.IDLE}
    if include_repositioning:
        allowed.add(VehicleState.REPOSITIONING)
    return vehicle.state in allowed and is_dispatch_eligible(vehicle, policy)


def rank_dispatch_candidates(
    trip: TripRequest,
    vehicles: dict[str, Vehicle],
    router: CityRouter,
    *,
    surge_multiplier: float = 1.0,
    policy: NetworkPolicy | None = None,
    include_repositioning: bool = False,
    limit: int = 5,
    use_fast_eta: bool = False,
) -> list[MatchCandidate]:
    """Return vehicles ranked by pickup ETA for ``trip``."""
    pol = policy or NetworkPolicy()
    candidates: list[MatchCandidate] = []
    for vehicle in vehicles.values():
        if not _vehicle_dispatch_eligible(vehicle, pol, include_repositioning=include_repositioning):
            continue
        if use_fast_eta:
            eta = _haversine_eta_min(
                vehicle.lat,
                vehicle.lon,
                trip.origin.lat,
                trip.origin.lon,
            )
        else:
            eta = router.travel_time_between_points(
                vehicle.lat,
                vehicle.lon,
                trip.origin.lat,
                trip.origin.lon,
            )
        if eta is None:
            continue
        score = -eta * surge_multiplier
        candidates.append(
            MatchCandidate(
                vehicle_id=vehicle.id,
                eta_min=eta,
                score=score,
                state=vehicle.state,
            ),
        )
    candidates.sort(key=lambda c: c.eta_min)
    return candidates[:limit]


def pick_best_vehicle(
    trip: TripRequest,
    vehicles: dict[str, Vehicle],
    router: CityRouter,
    *,
    surge_multiplier: float = 1.0,
    policy: NetworkPolicy | None = None,
    include_repositioning: bool = False,
) -> MatchCandidate | None:
    """Return the best vehicle for ``trip`` by pickup ETA, or None."""
    ranked = rank_dispatch_candidates(
        trip,
        vehicles,
        router,
        surge_multiplier=surge_multiplier,
        policy=policy,
        include_repositioning=include_repositioning,
        limit=1,
    )
    return ranked[0] if ranked else None
