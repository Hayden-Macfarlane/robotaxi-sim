"""Stochastic trip demand generation for a single city."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from core_data.models import GeoPoint
from demand.forecast import forecast_intensity
from routing.city_router import CityRouter
from routing.zones import all_zone_names, zone_for_point

ZONE_WEIGHTS: dict[str, float] = {
    "airport": 2.5,
    "downtown": 3.0,
    "campus": 2.6,
    "east_side": 2.4,
    "riverside": 2.0,
    "south_central": 2.2,
    "domain": 2.0,
    "central": 1.6,
    "southwest": 1.2,
    "westlake": 1.3,
    "northwest": 1.0,
    "northeast": 1.0,
    "buda": 0.8,
    "kyle": 0.7,
    "unknown": 0.5,
}

for _zone in all_zone_names():
    ZONE_WEIGHTS.setdefault(_zone, 1.0)


@dataclass
class DemandGenerator:
    """Draw rider trip requests with time-of-day and zone weighting."""

    _rng: random.Random = field(default_factory=random.Random)
    base_trips_per_hour: float = 24.0
    _events: list = field(default_factory=list)

    def set_events(self, events: list) -> None:
        """Attach active special events for boosted spawn rates."""
        self._events = events

    def set_seed(self, seed: int) -> None:
        """Fix RNG for reproducible tests."""
        self._rng = random.Random(seed)

    def time_of_day_multiplier(self, sim_hour: float) -> float:
        """Return global demand multiplier for hour-of-day (legacy helper)."""
        hour = sim_hour % 24.0
        if 7 <= hour < 10 or 16 <= hour < 20:
            return 1.8
        if 10 <= hour < 16:
            return 1.2
        if 0 <= hour < 6:
            return 0.4
        return 1.0

    def zone_spawn_weight(self, zone: str, sim_hour: float) -> float:
        """Return relative spawn weight for ``zone`` at ``sim_hour``."""
        base = ZONE_WEIGHTS.get(zone, 1.0)
        return forecast_intensity(zone, sim_hour, base_weight=base, events=self._events)

    def expected_trips(self, dt_hours: float, sim_hour: float) -> float:
        """Expected number of trips in interval ``dt_hours``."""
        return self.base_trips_per_hour * self.time_of_day_multiplier(sim_hour) * dt_hours

    def _pick_zone(self, zones: list[str], sim_hour: float) -> str:
        weights = [self.zone_spawn_weight(z, sim_hour) for z in zones]
        return self._rng.choices(zones, weights=weights, k=1)[0]

    def _random_point_in_zone(
        self,
        router: CityRouter,
        zone: str,
    ) -> GeoPoint | None:
        boxes = router.zone_bounding_boxes()
        bbox = boxes.get(zone)
        if bbox is None:
            return None
        min_lat, max_lat, min_lon, max_lon = bbox
        lat = self._rng.uniform(min_lat, max_lat)
        lon = self._rng.uniform(min_lon, max_lon)
        if zone_for_point(lat, lon) != zone:
            for _ in range(8):
                lat = self._rng.uniform(min_lat, max_lat)
                lon = self._rng.uniform(min_lon, max_lon)
                if zone_for_point(lat, lon) == zone:
                    break
        return GeoPoint(lat=round(lat, 6), lon=round(lon, 6))

    def maybe_spawn_trip(
        self,
        router: CityRouter,
        *,
        sim_time_h: float,
        dt_hours: float,
    ) -> tuple[GeoPoint, GeoPoint] | None:
        """Return ``(origin, destination)`` geo points if a trip spawns this tick."""
        expected = self.expected_trips(dt_hours, sim_time_h)
        if self._rng.random() > min(1.0, expected):
            return None
        zones = list(router.zone_bounding_boxes().keys())
        if not zones:
            return None
        for _ in range(20):
            origin_zone = self._pick_zone(zones, sim_time_h)
            dest_zone = self._pick_zone(zones, sim_time_h)
            origin = self._random_point_in_zone(router, origin_zone)
            dest = self._random_point_in_zone(router, dest_zone)
            if origin is None or dest is None:
                continue
            if origin.lat == dest.lat and origin.lon == dest.lon:
                continue
            if router.route_between(origin.lat, origin.lon, dest.lat, dest.lon) is None:
                continue
            return (origin, dest)
        return None
