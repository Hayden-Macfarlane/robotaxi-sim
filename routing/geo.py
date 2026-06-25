"""Geographic helpers for street-level routing."""

from __future__ import annotations

import math

from core_data.models import GeoPoint


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two WGS-84 points."""
    earth_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return earth_km * 2 * math.asin(math.sqrt(a))


def polyline_length_km(polyline: list[GeoPoint]) -> float:
    """Total arc length of a coordinate polyline."""
    total = 0.0
    for i in range(len(polyline) - 1):
        a, b = polyline[i], polyline[i + 1]
        total += haversine_km(a.lat, a.lon, b.lat, b.lon)
    return total


def bearing_deg(a: GeoPoint, b: GeoPoint) -> float:
    """Return compass bearing from ``a`` to ``b`` in degrees."""
    lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
    lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def position_along_polyline(polyline: list[GeoPoint], progress: float) -> tuple[GeoPoint, float]:
    """Return point and heading at ``progress`` (0–1) along a polyline by arc length."""
    if not polyline:
        return GeoPoint(lat=0.0, lon=0.0), 0.0
    if len(polyline) == 1 or progress <= 0.0:
        return polyline[0], 0.0
    if progress >= 1.0:
        if len(polyline) >= 2:
            return polyline[-1], bearing_deg(polyline[-2], polyline[-1])
        return polyline[-1], 0.0

    segments: list[tuple[float, GeoPoint, GeoPoint]] = []
    total_km = 0.0
    for i in range(len(polyline) - 1):
        a, b = polyline[i], polyline[i + 1]
        dist = haversine_km(a.lat, a.lon, b.lat, b.lon)
        if dist > 0.0:
            segments.append((dist, a, b))
            total_km += dist
    if total_km <= 0.0:
        return polyline[-1], 0.0

    target_km = progress * total_km
    walked = 0.0
    for dist, a, b in segments:
        if walked + dist >= target_km:
            t = (target_km - walked) / dist if dist > 0 else 0.0
            point = GeoPoint(
                lat=a.lat + t * (b.lat - a.lat),
                lon=a.lon + t * (b.lon - a.lon),
            )
            return point, bearing_deg(a, b)
        walked += dist
    last_a, last_b = segments[-1][1], segments[-1][2]
    return polyline[-1], bearing_deg(last_a, last_b)


def project_point_on_segment(
    lat: float,
    lon: float,
    a: GeoPoint,
    b: GeoPoint,
) -> tuple[GeoPoint, float, float]:
    """Project ``(lat, lon)`` onto segment ``ab``; return point, fraction, distance km."""
    dx = b.lon - a.lon
    dy = b.lat - a.lat
    len_sq = dx * dx + dy * dy
    if len_sq <= 1e-15:
        dist = haversine_km(lat, lon, a.lat, a.lon)
        return GeoPoint(lat=a.lat, lon=a.lon), 0.0, dist
    t = ((lon - a.lon) * dx + (lat - a.lat) * dy) / len_sq
    t = max(0.0, min(1.0, t))
    proj = GeoPoint(lat=a.lat + t * dy, lon=a.lon + t * dx)
    dist = haversine_km(lat, lon, proj.lat, proj.lon)
    return proj, t, dist


def trim_polyline_from_fraction(polyline: list[GeoPoint], start_fraction: float) -> list[GeoPoint]:
    """Return sub-polyline from ``start_fraction`` (0–1) along arc length to end."""
    if not polyline or start_fraction <= 0.0:
        return list(polyline)
    if start_fraction >= 1.0:
        return [polyline[-1]] if polyline else []
    point, _ = position_along_polyline(polyline, start_fraction)
    total = polyline_length_km(polyline)
    target = start_fraction * total
    walked = 0.0
    result = [point]
    for i in range(len(polyline) - 1):
        a, b = polyline[i], polyline[i + 1]
        seg = haversine_km(a.lat, a.lon, b.lat, b.lon)
        if walked + seg >= target:
            result.extend(polyline[i + 1 :])
            break
        walked += seg
    else:
        result.append(polyline[-1])
    return _dedupe_consecutive(result)


def trim_polyline_to_fraction(polyline: list[GeoPoint], end_fraction: float) -> list[GeoPoint]:
    """Return sub-polyline from start to ``end_fraction`` (0–1) along arc length."""
    if not polyline or end_fraction >= 1.0:
        return list(polyline)
    if end_fraction <= 0.0:
        return [polyline[0]] if polyline else []
    point, _ = position_along_polyline(polyline, end_fraction)
    total = polyline_length_km(polyline)
    target = end_fraction * total
    walked = 0.0
    result: list[GeoPoint] = [polyline[0]]
    for i in range(len(polyline) - 1):
        a, b = polyline[i], polyline[i + 1]
        seg = haversine_km(a.lat, a.lon, b.lat, b.lon)
        if walked + seg >= target:
            result.append(point)
            return _dedupe_consecutive(result)
        result.append(b)
        walked += seg
    return _dedupe_consecutive(result)


def merge_polylines(parts: list[list[GeoPoint]]) -> list[GeoPoint]:
    """Concatenate polylines, deduping shared endpoints."""
    merged: list[GeoPoint] = []
    for part in parts:
        if not part:
            continue
        if not merged:
            merged.extend(part)
        else:
            if _same_point(merged[-1], part[0]):
                merged.extend(part[1:])
            else:
                merged.extend(part)
    return merged


def _same_point(a: GeoPoint, b: GeoPoint, eps: float = 1e-6) -> bool:
    return abs(a.lat - b.lat) < eps and abs(a.lon - b.lon) < eps


def _dedupe_consecutive(points: list[GeoPoint]) -> list[GeoPoint]:
    if not points:
        return []
    out = [points[0]]
    for p in points[1:]:
        if not _same_point(out[-1], p):
            out.append(p)
    return out
