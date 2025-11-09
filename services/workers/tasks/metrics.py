from __future__ import annotations

from prometheus_client import Counter, Histogram


_EVENTS_ENQUEUED = Counter(
    "nbo_events_enqueued_total",
    "Количество событий, поставленных в очередь обработки.",
    ["category", "channel"],
)

_EVENTS_PROCESSING_STARTED = Counter(
    "nbo_events_processing_started_total",
    "Количество задач обработки событий, начавших выполнение.",
    ["category"],
)

_EVENTS_PROCESSING_COMPLETED = Counter(
    "nbo_events_processing_completed_total",
    "Количество задач обработки событий с указанием результата.",
    ["category", "outcome"],
)

_EVENTS_PROCESSING_DURATION = Histogram(
    "nbo_events_processing_duration_seconds",
    "Распределение длительности обработки событий.",
    ["category"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
)


def record_event_enqueued(category: str, channel: str) -> None:
    _EVENTS_ENQUEUED.labels(category=category, channel=channel).inc()


def record_event_processing_started(category: str) -> None:
    _EVENTS_PROCESSING_STARTED.labels(category=category).inc()


def record_event_processing_completed(category: str, outcome: str) -> None:
    _EVENTS_PROCESSING_COMPLETED.labels(category=category, outcome=outcome).inc()


def observe_event_processing_duration(category: str, duration_seconds: float) -> None:
    _EVENTS_PROCESSING_DURATION.labels(category=category).observe(duration_seconds)


