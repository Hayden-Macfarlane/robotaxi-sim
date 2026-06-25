"""Vehicle–trip matching by ETA."""

from __future__ import annotations

from dataclasses import dataclass

from core_data.models import NetworkPolicy, TripRequest, Vehicle, VehicleState
from fleet.health import is_dispatch_eligible
from routing.city_router import CityRouter


@dataclass(frozen=True)
class MatchCandidate:
    """Scored vehicle assignment for a pending trip."""

    vehicle_id: str
    eta_min: float
    score: float


def pick_best_vehicle(
    trip: TripRequest,
    vehicles: dict[str, Vehicle],
    router: CityRouter,
    *,
    surge_multiplier: float = 1.0,
    policy: NetworkPolicy | None = None,
) -> MatchCandidate | None:
    """Return the best idle vehicle for ``trip`` by pickup ETA, or None."""
    pol = policy or NetworkPolicy()
    best: MatchCandidate | None = None
    for vehicle in vehicles.values():
        if vehicle.state != VehicleState.IDLE:
            continue
        if not is_dispatch_eligible(vehicle, pol):
            continue
        eta = router.travel_time_between_points(
            vehicle.lat,
            vehicle.lon,
            trip.origin.lat,
            trip.origin.lon,
        )
        if eta is None:
            continue
        score = -eta * surge_multiplier
        if best is None or score > best.score:
            best = MatchCandidate(vehicle_id=vehicle.id, eta_min=eta, score=score)
    return best
