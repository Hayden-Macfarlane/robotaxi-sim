"""Discoverable playbook constant catalog for the rule engine UI."""

from __future__ import annotations

from fleet_routing.v2.models import ConstantMeta


CONSTANT_CATALOG: list[ConstantMeta] = [
    ConstantMeta(
        id="idle_patience_min",
        plain_label="Idle patience",
        industry_label="Idle patience threshold",
        description="Minutes a vehicle may stay idle before reposition rules fire.",
        unit="min",
        default=15.0,
        min=0.0,
        max=120.0,
        related_metrics=["vehicle.idle_minutes"],
        related_rules=["v2-idle-relocate"],
    ),
    ConstantMeta(
        id="forecast_rising_threshold",
        plain_label="Forecast rising threshold",
        industry_label="Forecast rising ratio threshold",
        description="Zone forecast ratio above which staging rules activate.",
        unit="ratio",
        default=1.5,
        min=0.0,
        max=10.0,
        related_metrics=["zone.forecast_rising"],
        related_rules=["v2-forecast-staging"],
    ),
    ConstantMeta(
        id="max_reposition_min",
        plain_label="Max reposition time",
        industry_label="Maximum reposition travel minutes",
        description="Upper bound on reposition travel time before action is rejected.",
        unit="min",
        default=45.0,
        min=1.0,
        max=180.0,
        related_metrics=["pairwise.reposition_travel_min"],
    ),
    ConstantMeta(
        id="min_reposition_benefit",
        plain_label="Min reposition benefit",
        industry_label="Minimum reposition ROI",
        description="Minimum expected benefit score for a reposition move to execute.",
        unit="score",
        default=0.5,
        min=0.0,
        max=10.0,
    ),
    ConstantMeta(
        id="max_distance_from_nearest_asset_km",
        plain_label="Max deadzone distance",
        industry_label="Maximum distance from nearest asset",
        description="Distance beyond which a vehicle is considered in a coverage deadzone.",
        unit="km",
        default=2.0,
        min=0.1,
        max=20.0,
        related_metrics=["vehicle.deadzone_size_km"],
        related_rules=["v2-deadzone-fill"],
    ),
    ConstantMeta(
        id="deadzone_fill_ratio_threshold",
        plain_label="Deadzone fill threshold",
        industry_label="Deadzone fill ratio threshold",
        description="Ratio threshold for triggering deadzone fill reposition.",
        unit="ratio",
        default=1.0,
        min=0.0,
        max=5.0,
    ),
    ConstantMeta(
        id="cluster_radius_km",
        plain_label="Cluster radius",
        industry_label="Idle cluster detection radius",
        description="Radius for detecting crowded idle vehicle clusters.",
        unit="km",
        default=0.8,
        min=0.1,
        max=5.0,
        related_metrics=["vehicle.nearest_idle_km", "vehicle.is_most_crowded_in_radius"],
        related_rules=["v2-break-clusters"],
    ),
    ConstantMeta(
        id="min_density_ratio",
        plain_label="Min density ratio",
        industry_label="Minimum density floor ratio",
        description="Minimum local vehicle density when searching for reposition targets.",
        unit="ratio",
        default=0.5,
        min=0.0,
        max=2.0,
        related_rules=["v2-break-clusters", "v2-deadzone-fill"],
    ),
    ConstantMeta(
        id="max_deadhead_to_pickup_min",
        plain_label="Max deadhead to pickup",
        industry_label="Maximum deadhead minutes to pickup",
        description="Upper bound on empty travel time to reach a trip pickup.",
        unit="min",
        default=20.0,
        min=1.0,
        max=60.0,
        related_metrics=["pairwise.pickup_travel_min"],
    ),
]


def all_constant_meta() -> list[ConstantMeta]:
    """Return the full constant catalog."""
    return list(CONSTANT_CATALOG)


def default_constants() -> dict[str, float]:
    """Build default constant values from catalog defaults."""
    return {c.id: c.default for c in CONSTANT_CATALOG if c.id != "max_deadhead_to_pickup_min"}
