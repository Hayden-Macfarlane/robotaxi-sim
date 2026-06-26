"""Action and selection mode catalogs for the rule engine UI."""

from __future__ import annotations

from fleet_routing.v2.models import ActionMeta, ParamFieldMeta, RulePhaseV2, SelectionMeta


ACTION_CATALOG: list[ActionMeta] = [
    ActionMeta(
        id="assign_nearest_available",
        plain_label="Assign nearest available car",
        industry_label="Assign nearest idle or repositioning vehicle",
        description="Send the closest eligible car, including cars that are repositioning but can be redirected to the rider.",
        phases=[RulePhaseV2.DISPATCH],
    ),
    ActionMeta(
        id="assign_nearest_idle",
        plain_label="Assign nearest idle car",
        industry_label="Assign nearest idle vehicle only",
        description="Send the closest idle eligible car. Cars that are repositioning are not considered.",
        phases=[RulePhaseV2.DISPATCH],
    ),
    ActionMeta(
        id="assign_vehicle",
        plain_label="Assign vehicle (advanced)",
        industry_label="Assign vehicle to trip",
        description="Legacy action with explicit preempt-reposition toggle.",
        phases=[RulePhaseV2.DISPATCH],
        param_schema={
            "preempt_reposition": ParamFieldMeta(
                type="bool",
                plain_label="Include repositioning cars",
                description="Allow vehicles currently repositioning to be assigned.",
                default=True,
            ),
        },
    ),
    ActionMeta(
        id="hold",
        plain_label="Hold",
        industry_label="Hold (no action)",
        description="Do nothing for matching subjects.",
        phases=[RulePhaseV2.DISPATCH, RulePhaseV2.REPOSITION, RulePhaseV2.FACILITY],
    ),
    ActionMeta(
        id="reposition_to_point",
        plain_label="Reposition to point",
        industry_label="Reposition to geographic point",
        description="Send vehicle to a specific lat/lon staging point.",
        phases=[RulePhaseV2.REPOSITION],
        param_schema={
            "lat": ParamFieldMeta(type="float", plain_label="Latitude", default=30.27),
            "lon": ParamFieldMeta(type="float", plain_label="Longitude", default=-97.74),
        },
    ),
    ActionMeta(
        id="reposition_to_zone",
        plain_label="Reposition to zone",
        industry_label="Reposition to zone centroid",
        description="Send vehicle to the staging point of a named zone.",
        phases=[RulePhaseV2.REPOSITION],
        param_schema={
            "zone": ParamFieldMeta(type="string", plain_label="Zone name", default=""),
        },
    ),
    ActionMeta(
        id="reposition_to_best_deficit",
        plain_label="Reposition to best deficit",
        industry_label="Reposition to highest-deficit zone",
        description="Send vehicle to the zone with the largest supply deficit.",
        phases=[RulePhaseV2.REPOSITION],
    ),
    ActionMeta(
        id="reposition_to_nearest_density_floor",
        plain_label="Reposition with density floor",
        industry_label="Reposition to nearest density floor",
        description="Find nearest area meeting minimum vehicle density.",
        phases=[RulePhaseV2.REPOSITION],
        param_schema={
            "min_density_ratio": ParamFieldMeta(
                type="float",
                plain_label="Min density ratio",
                description="Minimum local density ratio for target area.",
                default=0.5,
            ),
            "radius_km": ParamFieldMeta(
                type="float",
                plain_label="Search radius",
                description="Search radius in kilometers.",
                default=1.0,
                unit="km",
            ),
        },
    ),
    ActionMeta(
        id="send_to_facility",
        plain_label="Send to facility",
        industry_label="Send vehicle to depot/facility",
        description="Route vehicle to the nearest facility for charging or service.",
        phases=[RulePhaseV2.REPOSITION, RulePhaseV2.FACILITY],
    ),
    ActionMeta(
        id="release_from_facility",
        plain_label="Release from facility",
        industry_label="Release vehicle from facility",
        description="Return a facility-held vehicle to street service.",
        phases=[RulePhaseV2.FACILITY],
    ),
    ActionMeta(
        id="cancel_trip",
        plain_label="Cancel trip",
        industry_label="Cancel pending trip",
        description="Cancel a pending trip request.",
        phases=[RulePhaseV2.DISPATCH],
    ),
]

SELECTION_CATALOG: list[SelectionMeta] = [
    SelectionMeta(
        id="all_matching",
        plain_label="All matching",
        industry_label="All matching subjects",
        description="Apply action to every subject that matches the condition.",
        requires_metric=False,
    ),
    SelectionMeta(
        id="most_crowded",
        plain_label="Most crowded",
        industry_label="Most crowded in radius",
        description="Pick the subject in the densest idle cluster.",
        requires_metric=False,
        param_schema={
            "radius_km": ParamFieldMeta(
                type="float",
                plain_label="Cluster radius",
                default=0.8,
                unit="km",
            ),
        },
    ),
    SelectionMeta(
        id="least_crowded",
        plain_label="Least crowded",
        industry_label="Least crowded in radius",
        description="Pick the subject in the sparsest area.",
        requires_metric=False,
        param_schema={
            "radius_km": ParamFieldMeta(type="float", plain_label="Radius", default=1.0, unit="km"),
        },
    ),
    SelectionMeta(
        id="one_per_cluster",
        plain_label="One per cluster",
        industry_label="One subject per cluster",
        description="Select one representative from each idle cluster.",
        requires_metric=False,
        param_schema={
            "radius_km": ParamFieldMeta(type="float", plain_label="Cluster radius", default=0.8, unit="km"),
        },
    ),
    SelectionMeta(
        id="highest_metric",
        plain_label="Highest metric",
        industry_label="Subject with highest metric value",
        description="Pick subject with the highest value of a chosen metric.",
        requires_metric=True,
    ),
    SelectionMeta(
        id="lowest_metric",
        plain_label="Lowest metric",
        industry_label="Subject with lowest metric value",
        description="Pick subject with the lowest value of a chosen metric.",
        requires_metric=True,
    ),
    SelectionMeta(
        id="best_dispatch_score",
        plain_label="Best dispatch score",
        industry_label="Best dispatch match score",
        description="Pick vehicle with the best dispatch match score for the trip.",
        requires_metric=False,
        phases=[RulePhaseV2.DISPATCH],
    ),
    SelectionMeta(
        id="round_robin_zone",
        plain_label="Round robin by zone",
        industry_label="Round-robin per zone",
        description="Rotate selection fairly across zones.",
        requires_metric=False,
    ),
]


def all_action_meta() -> list[ActionMeta]:
    """Return the full action catalog."""
    return list(ACTION_CATALOG)


def all_selection_meta() -> list[SelectionMeta]:
    """Return the full selection mode catalog."""
    return list(SELECTION_CATALOG)
