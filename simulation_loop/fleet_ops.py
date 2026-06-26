"""Fleet resize and operator alert helpers."""

from __future__ import annotations

import random

from core_data.models import NetworkPolicy, Vehicle, VehicleState
from routing.city_router import CityRouter
from simulation_loop.world_builder import placement_in_zone


def spawn_vehicle(
    router: CityRouter,
    rng: random.Random,
    *,
    vehicle_index: int,
    zones: list[str],
    used_positions: list[tuple[float, float]],
) -> Vehicle | None:
    """Add one idle vehicle spread across ``zones``."""
    shuffled = list(zones)
    rng.shuffle(shuffled)
    for zone in shuffled:
        placement = placement_in_zone(router, zone, rng, used_positions)
        if placement is None:
            continue
        node_id, lat, lon = placement
        used_positions.append((lat, lon))
        vid = f"rx-{vehicle_index:03d}"
        return Vehicle(
            id=vid,
            state=VehicleState.IDLE,
            lat=lat,
            lon=lon,
            current_node_id=node_id,
            idle_since_h=0.0,
        )
    for node_id in router.node_ids:
        node = router.get_node(node_id)
        if node is None:
            continue
        used_positions.append((node.lat, node.lon))
        return Vehicle(
            id=f"rx-{vehicle_index:03d}",
            state=VehicleState.IDLE,
            lat=node.lat,
            lon=node.lon,
            current_node_id=node_id,
            idle_since_h=0.0,
        )
    return None


def resize_fleet(
    vehicles: dict[str, Vehicle],
    target_size: int,
    router: CityRouter,
    rng: random.Random,
    zones: list[str],
) -> dict[str, Vehicle]:
    """Grow or shrink the on-street fleet to ``target_size`` idle/busy vehicles."""
    current = dict(vehicles)
    count = len(current)
    if target_size == count:
        return current
    if target_size < count:
        removable = sorted(
            (v for v in current.values() if v.state in (VehicleState.IDLE, VehicleState.AT_DEPOT)),
            key=lambda v: v.id,
            reverse=True,
        )
        to_remove = count - target_size
        for vehicle in removable[:to_remove]:
            del current[vehicle.id]
        return current
    used = [(v.lat, v.lon) for v in current.values()]
    idx = count + 1
    while len(current) < target_size:
        vehicle = spawn_vehicle(router, rng, vehicle_index=idx, zones=zones, used_positions=used)
        if vehicle is None:
            break
        current[vehicle.id] = vehicle
        idx += 1
    return current


def compute_operator_alerts(
    policy: NetworkPolicy,
    kpis: dict[str, float],
    zone_balance: list[dict[str, object]],
) -> list[dict[str, str]]:
    """Return active operator alert banners from KPIs and zone balance."""
    alerts: list[dict[str, str]] = []
    if policy.alert_avg_wait_min > 0 and kpis.get("avg_wait_min", 0) >= policy.alert_avg_wait_min:
        alerts.append({
            "level": "warning",
            "code": "avg_wait",
            "message": f"Avg wait {kpis['avg_wait_min']:.1f} min exceeds {policy.alert_avg_wait_min:.0f} min target",
        })
    if policy.alert_pending_queue > 0 and kpis.get("pending_trips", 0) >= policy.alert_pending_queue:
        alerts.append({
            "level": "warning",
            "code": "pending_queue",
            "message": f"{int(kpis['pending_trips'])} pending trips — queue above {policy.alert_pending_queue}",
        })
    if (
        policy.alert_utilization_below_pct > 0
        and kpis.get("fleet_utilization_pct", 100) < policy.alert_utilization_below_pct
    ):
        alerts.append({
            "level": "info",
            "code": "low_utilization",
            "message": f"Fleet utilization {kpis['fleet_utilization_pct']:.0f}% below {policy.alert_utilization_below_pct:.0f}%",
        })
    if (
        policy.alert_vehicles_needing_service > 0
        and kpis.get("vehicles_needing_service", 0) >= policy.alert_vehicles_needing_service
    ):
        alerts.append({
            "level": "warning",
            "code": "needs_service",
            "message": f"{int(kpis['vehicles_needing_service'])} vehicles need service",
        })
    if policy.alert_zone_deficit > 0:
        deficits = [
            row for row in zone_balance
            if float(row.get("gap", 0)) >= policy.alert_zone_deficit
        ]
        if deficits:
            zones = ", ".join(str(row["zone"]) for row in deficits[:3])
            alerts.append({
                "level": "warning",
                "code": "zone_deficit",
                "message": f"Zone deficit alert: {zones}",
            })
    return alerts
