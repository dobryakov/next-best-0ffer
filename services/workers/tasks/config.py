from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from kombu import Exchange, Queue


@dataclass(frozen=True, slots=True)
class QueueSpec:
    name: str
    routing_key: str
    exchange: Exchange
    durable: bool = True
    max_priority: int | None = None

    def to_kombu_queue(self) -> Queue:
        return Queue(
            name=self.name,
            exchange=self.exchange,
            routing_key=self.routing_key,
            durable=self.durable,
            max_priority=self.max_priority,
        )


EXCHANGE = Exchange("nbo", type="topic", durable=True)

DEFAULT_QUEUE = QueueSpec(
    name="nbo_default",
    routing_key="nbo.default",
    exchange=EXCHANGE,
)

EVENTS_QUEUE = QueueSpec(
    name="nbo_events",
    routing_key="nbo.events",
    exchange=EXCHANGE,
)

RECOMMENDATIONS_QUEUE = QueueSpec(
    name="nbo_calculation",
    routing_key="nbo.recommendations",
    exchange=EXCHANGE,
    max_priority=10,
)

ALL_QUEUES: Tuple[QueueSpec, ...] = (
    DEFAULT_QUEUE,
    EVENTS_QUEUE,
    RECOMMENDATIONS_QUEUE,
)

TASK_DEFAULTS: Dict[str, object] = {
    "acks_late": True,
    "task_track_started": True,
    "task_default_queue": DEFAULT_QUEUE.name,
    "task_queues": tuple(queue.to_kombu_queue() for queue in ALL_QUEUES),
    "task_default_exchange": EXCHANGE.name,
    "task_default_exchange_type": EXCHANGE.type,
    "task_default_routing_key": DEFAULT_QUEUE.routing_key,
    "broker_connection_retry_on_startup": True,
    "broker_connection_max_retries": None,
    "broker_heartbeat": 30,
    "worker_prefetch_multiplier": 1,
    "task_time_limit": 300,
    "task_soft_time_limit": 240,
    "event_queue_expires": 60,
    "task_routes": {
        "services.workers.tasks.events_ingest.*": {
            "queue": EVENTS_QUEUE.name,
            "routing_key": EVENTS_QUEUE.routing_key,
        },
        "services.workers.tasks.recommendations.*": {
            "queue": RECOMMENDATIONS_QUEUE.name,
            "routing_key": RECOMMENDATIONS_QUEUE.routing_key,
            "priority": 7,
        },
    },
    "task_default_retry_delay": 5,
    "task_annotations": {
        "*": {
            "max_retries": 5,
            "retry_backoff": True,
            "retry_backoff_max": 60,
            "retry_jitter": True,
        }
    },
}

HEALTHCHECK_TIMEOUT = 3  # seconds

BEAT_SCHEDULE = {
    "refresh-feature-store": {
        "task": "services.workers.tasks.maintenance.refresh_feature_store",
        "schedule": 300.0,
        "options": {"queue": DEFAULT_QUEUE.name},
        "enabled": False,
    },
    "retrain-als-model": {
        "task": "services.workers.tasks.training.retrain_als",
        "schedule": 3600.0,
        "options": {"queue": RECOMMENDATIONS_QUEUE.name},
        "enabled": False,
    },
}


