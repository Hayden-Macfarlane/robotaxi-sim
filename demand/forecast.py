"""Per-zone hourly demand forecast curves for proactive fleet staging."""

from __future__ import annotations

from core_data.models import SpecialEvent
from routing.zones import all_zone_names

_RESIDENTIAL = [0.4] * 6 + [0.8] * 12 + [1.0] * 4 + [0.5] * 2
_SUBURBAN = [0.35] * 6 + [0.75] * 12 + [0.95] * 4 + [0.45] * 2

# Hourly multiplier by zone (index 0–23). 1.0 = baseline for that zone.
ZONE_HOURLY_PROFILE: dict[str, list[float]] = {
    "airport": [
        0.3, 0.3, 0.4, 0.5, 0.6, 0.8, 1.2, 1.8, 2.0, 1.6, 1.2, 1.0,
        1.1, 1.2, 1.3, 1.5, 1.8, 2.2, 2.0, 1.5, 1.0, 0.7, 0.5, 0.3,
    ],
    "downtown": [
        0.2, 0.2, 0.2, 0.3, 0.4, 0.6, 1.0, 2.0, 2.5, 2.0, 1.4, 1.2,
        1.3, 1.4, 1.5, 1.8, 2.2, 2.5, 2.0, 1.5, 1.0, 0.7, 0.5, 0.3,
    ],
    "campus": [
        0.2, 0.2, 0.2, 0.3, 0.5, 0.8, 1.6, 2.2, 2.0, 1.6, 1.2, 1.0,
        1.1, 1.4, 1.6, 1.8, 2.0, 1.8, 1.2, 0.8, 0.6, 0.4, 0.3, 0.2,
    ],
    "east_side": [
        0.2, 0.2, 0.2, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.1, 1.2, 1.3,
        1.4, 1.5, 1.6, 1.8, 2.2, 2.6, 3.0, 2.8, 2.0, 1.4, 0.8, 0.3,
    ],
    "riverside": [
        0.3, 0.3, 0.3, 0.4, 0.5, 0.7, 1.0, 1.4, 1.6, 1.4, 1.2, 1.1,
        1.2, 1.3, 1.4, 1.6, 1.9, 2.2, 2.0, 1.6, 1.2, 0.8, 0.5, 0.3,
    ],
    "south_central": [
        0.3, 0.3, 0.3, 0.4, 0.5, 0.7, 1.0, 1.3, 1.5, 1.3, 1.1, 1.0,
        1.1, 1.2, 1.3, 1.5, 1.8, 2.1, 2.3, 2.0, 1.5, 1.0, 0.6, 0.3,
    ],
    "southwest": _SUBURBAN,
    "central": _RESIDENTIAL,
    "westlake": _SUBURBAN,
    "domain": [
        0.3, 0.3, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5, 1.8, 1.6, 1.4, 1.3,
        1.4, 1.5, 1.6, 1.8, 2.2, 2.4, 2.0, 1.5, 1.0, 0.7, 0.5, 0.3,
    ],
    "northwest": _SUBURBAN,
    "northeast": _SUBURBAN,
    "buda": _RESIDENTIAL,
    "kyle": _RESIDENTIAL,
    "unknown": [0.5] * 24,
}

for _zone in all_zone_names():
    ZONE_HOURLY_PROFILE.setdefault(_zone, _RESIDENTIAL)


def zone_hourly_multiplier(zone: str, sim_hour: float) -> float:
    """Return forecast multiplier for ``zone`` at fractional hour-of-day."""
    profile = ZONE_HOURLY_PROFILE.get(zone, ZONE_HOURLY_PROFILE["unknown"])
    hour = sim_hour % 24.0
    idx = int(hour) % 24
    nxt = (idx + 1) % 24
    frac = hour - int(hour)
    return profile[idx] * (1.0 - frac) + profile[nxt] * frac


def event_boost_for_zone(
    zone: str,
    sim_time_h: float,
    events: list[SpecialEvent],
) -> float:
    """Return demand multiplier boost from active special events in ``zone``."""
    boost = 1.0
    for ev in events:
        if ev.zone != zone:
            continue
        if ev.start_h <= sim_time_h < ev.end_h:
            boost = max(boost, ev.demand_multiplier)
    return boost


def forecast_intensity(
    zone: str,
    sim_time_h: float,
    *,
    base_weight: float,
    events: list[SpecialEvent] | None = None,
) -> float:
    """Combined zone weight × hourly curve × event boost."""
    hourly = zone_hourly_multiplier(zone, sim_time_h)
    event_mult = event_boost_for_zone(zone, sim_time_h, events or [])
    return base_weight * hourly * event_mult
