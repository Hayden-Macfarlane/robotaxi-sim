"""Named operator scenario presets for quick policy tuning."""

from __future__ import annotations

from core_data.models import NetworkPolicy, ScenarioPreset


def scenario_policy_patch(preset: ScenarioPreset) -> dict[str, object]:
    """Return ``NetworkPolicy`` field overrides for ``preset``."""
    if preset == ScenarioPreset.RUSH_HOUR:
        return {
            "scenario_preset": preset,
            "base_trips_per_hour": 42.0,
            "surge_multiplier": 1.8,
            "auto_dispatch_enabled": True,
            "auto_reposition_enabled": True,
            "post_trip_reposition_enabled": True,
            "proactive_staging_enabled": True,
            "reposition_lead_min": 45.0,
            "reposition_idle_min": 8.0,
            "max_idle_per_zone": 2,
            "target_supply_by_zone": {"downtown": 3, "campus": 2, "airport": 2},
        }
    if preset == ScenarioPreset.LOW_DEMAND:
        return {
            "scenario_preset": preset,
            "base_trips_per_hour": 10.0,
            "surge_multiplier": 1.0,
            "reposition_idle_min": 25.0,
            "max_idle_per_zone": 4,
            "auto_reposition_enabled": False,
        }
    if preset == ScenarioPreset.CONCERT_SURGE:
        return {
            "scenario_preset": preset,
            "base_trips_per_hour": 36.0,
            "surge_multiplier": 2.5,
            "reposition_lead_min": 60.0,
            "proactive_staging_enabled": True,
            "forecast_rising_threshold": 1.0,
            "target_supply_by_zone": {"downtown": 4, "campus": 3},
        }
    if preset == ScenarioPreset.MAINTENANCE_HEAVY:
        return {
            "scenario_preset": preset,
            "condition_drain_per_km": 0.2,
            "condition_drain_per_trip": 1.2,
            "low_condition_pct": 35.0,
            "maintenance_service_min": 45.0,
            "charge_aware_dispatch": True,
            "min_battery_pct_for_trip": 30.0,
        }
    if preset == ScenarioPreset.AIRPORT_PEAK:
        return {
            "scenario_preset": preset,
            "base_trips_per_hour": 30.0,
            "surge_multiplier": 1.6,
            "target_supply_by_zone": {"airport": 4, "downtown": 2},
            "zone_demand_weights": {"airport": 5.0, "downtown": 2.5},
            "reposition_lead_min": 50.0,
        }
    return {"scenario_preset": ScenarioPreset.CUSTOM}
