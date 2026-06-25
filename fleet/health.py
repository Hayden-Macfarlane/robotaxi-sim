"""Vehicle health wear, service, and dispatch eligibility."""

from __future__ import annotations

import random

from core_data.models import NetworkPolicy, NodeKind, Vehicle, VehicleState

SERVICE_STATES = frozenset({
    VehicleState.CHARGING,
    VehicleState.MAINTENANCE,
    VehicleState.CLEANING,
    VehicleState.AT_DEPOT,
})


def apply_movement_wear(vehicle: Vehicle, route_km: float, policy: NetworkPolicy) -> None:
    """Deplete battery and condition for distance traveled."""
    vehicle.battery_pct = max(0.0, vehicle.battery_pct - route_km * policy.battery_drain_per_km)
    vehicle.condition_pct = max(0.0, vehicle.condition_pct - route_km * policy.condition_drain_per_km)


def apply_trip_complete_wear(
    vehicle: Vehicle,
    policy: NetworkPolicy,
    rng: random.Random,
) -> bool:
    """Apply post-trip cleanliness/condition wear. Returns True if spill occurred."""
    vehicle.cleanliness_pct = max(
        0.0,
        vehicle.cleanliness_pct - policy.cleanliness_drain_per_trip,
    )
    vehicle.condition_pct = max(
        0.0,
        vehicle.condition_pct - policy.condition_drain_per_trip,
    )
    if rng.random() < policy.cleanliness_spill_chance:
        vehicle.cleanliness_pct = policy.cleanliness_spill_floor_pct
        return True
    return False


def service_duration_min(vehicle: Vehicle, facility_kind: str, policy: NetworkPolicy) -> float:
    """Return dwell minutes at a facility before service is complete."""
    if facility_kind == NodeKind.CHARGER.value:
        deficit = max(0.0, 100.0 - vehicle.battery_pct)
        return max(1.0, policy.charge_minutes_to_full * (deficit / 100.0))
    if facility_kind == NodeKind.CLEANING.value:
        return policy.cleaning_service_min
    if facility_kind == NodeKind.MAINTENANCE.value:
        return policy.maintenance_service_min
    return 0.0


def restore_after_service(vehicle: Vehicle, facility_kind: str) -> None:
    """Restore the vehicle metric serviced at ``facility_kind``."""
    if facility_kind == NodeKind.CHARGER.value:
        vehicle.battery_pct = 100.0
    elif facility_kind == NodeKind.CLEANING.value:
        vehicle.cleanliness_pct = 100.0
    elif facility_kind == NodeKind.MAINTENANCE.value:
        vehicle.condition_pct = 100.0


def is_dispatch_eligible(vehicle: Vehicle, policy: NetworkPolicy) -> bool:
    """Return True if vehicle may accept a new trip."""
    if vehicle.state != VehicleState.IDLE:
        return False
    if vehicle.battery_pct <= policy.low_battery_pct:
        return False
    if vehicle.condition_pct <= policy.low_condition_pct:
        return False
    if vehicle.cleanliness_pct <= policy.low_cleanliness_pct:
        return False
    return True


def health_alert(vehicle: Vehicle, policy: NetworkPolicy) -> str | None:
    """Return the highest-priority health issue requiring facility service."""
    if vehicle.cleanliness_pct <= policy.low_cleanliness_pct:
        return "needs_cleaning"
    if vehicle.battery_pct <= policy.low_battery_pct:
        return "low_battery"
    if vehicle.condition_pct <= policy.low_condition_pct:
        return "needs_maintenance"
    return None


def facility_kind_for_alert(alert: str) -> str:
    """Map a health alert to the required facility kind."""
    mapping = {
        "needs_cleaning": NodeKind.CLEANING.value,
        "low_battery": NodeKind.CHARGER.value,
        "needs_maintenance": NodeKind.MAINTENANCE.value,
    }
    return mapping[alert]
