"""Playback rate converts wall-clock ticks into simulation time."""

from api.server import (
    PLAYBACK_SIM_MINUTES_PER_REAL_SECOND,
    _sim_dt_hours,
    _sim_dt_hours_from_elapsed,
)


def test_default_playback_one_sim_minute_per_real_second() -> None:
    """At 1× speed, one real second advances one simulation minute."""
    assert PLAYBACK_SIM_MINUTES_PER_REAL_SECOND == 1.0
    sim_minutes_per_real_second = 1.0 * PLAYBACK_SIM_MINUTES_PER_REAL_SECOND
    assert sim_minutes_per_real_second == 1.0


def test_typical_trip_duration_at_1x() -> None:
    """An ~80 sim-minute pickup+ride should take ~80s wall-clock at speed 1×."""
    typical_trip_sim_min = 80.0
    sim_minutes_per_real_second = 1.0 * PLAYBACK_SIM_MINUTES_PER_REAL_SECOND
    real_seconds = typical_trip_sim_min / sim_minutes_per_real_second
    assert 75 <= real_seconds <= 85


def test_sim_dt_hours_scales_with_playback_speed() -> None:
    """Doubling playback speed doubles simulation advance per tick."""
    base = _sim_dt_hours(1.0)
    double = _sim_dt_hours(2.0)
    assert double == base * 2


def test_wall_clock_elapsed_advances_one_sim_minute_per_real_second() -> None:
    """Wall-clock helper matches 1 sim minute per real second at 1×."""
    dt_h = _sim_dt_hours_from_elapsed(1.0, 1.0)
    assert abs(dt_h - 1.0 / 60.0) < 1e-9
