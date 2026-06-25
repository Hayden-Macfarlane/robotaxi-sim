"""Minimal discrete-event simulation engine: typed events, heap queue, time advance.

Adapted from apex-logistics event_engine — standalone copy; do not import across repos.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum


class EventType(StrEnum):
    """Robotaxi simulation event categories."""

    DEMAND_TICK = "DEMAND_TICK"
    TRIP_REQUEST = "TRIP_REQUEST"
    VEHICLE_ARRIVE = "VEHICLE_ARRIVE"
    REPOSITION = "REPOSITION"


@dataclass(order=True)
class Event:
    """Single instantaneous occurrence in simulation time."""

    timestamp: float
    event_type: EventType = field(compare=False)
    entity_id: str = field(compare=False)
    payload: dict[str, object] = field(compare=False, default_factory=dict)


class SimulationEngine:
    """Heap-backed future-event list with explicit time advance on each step."""

    current_time: float
    _event_queue: list[Event]

    def __init__(self, *, initial_time: float = 0.0) -> None:
        """Create an engine with optional starting clock and an empty queue."""
        self.current_time = initial_time
        self._event_queue: list[Event] = []

    def schedule_event(self, event: Event) -> None:
        """Insert ``event`` into the internal heap ordered by ``event.timestamp``."""
        heapq.heappush(self._event_queue, event)

    def step(self) -> Event | None:
        """Pop the earliest event, advance ``current_time``, and return it."""
        if not self._event_queue:
            return None
        event = heapq.heappop(self._event_queue)
        self.current_time = event.timestamp
        return event

    def run_until(self, target_time: float) -> Iterator[Event]:
        """Yield events while their time is at most ``target_time``."""
        while self._event_queue and self._event_queue[0].timestamp <= target_time:
            next_event = self.step()
            if next_event is None:
                break
            yield next_event

    def peek_next_time(self) -> float | None:
        """Return timestamp of the next queued event, if any."""
        if not self._event_queue:
            return None
        return self._event_queue[0].timestamp

    def cancel_events_for_entity(
        self,
        entity_id: str,
        *,
        event_type: EventType | None = None,
    ) -> int:
        """Remove queued events for ``entity_id``; optionally filter by ``event_type``."""
        kept: list[Event] = []
        removed = 0
        for event in self._event_queue:
            if event.entity_id == entity_id and (
                event_type is None or event.event_type == event_type
            ):
                removed += 1
                continue
            kept.append(event)
        if removed:
            heapq.heapify(kept)
            self._event_queue = kept
        return removed
