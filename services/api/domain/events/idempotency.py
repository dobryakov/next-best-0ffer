from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Tuple
from uuid import NAMESPACE_URL, uuid5


@dataclass(frozen=True, slots=True)
class EventFingerprint:
    category: str
    customer_id: str
    product_ids: List[str]
    channel: str
    occurred_at: datetime
    payload: Dict[str, Any]


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _canonical_payload(fingerprint: EventFingerprint, bucket: int) -> str:
    canonical = {
        "category": fingerprint.category,
        "customer_id": fingerprint.customer_id,
        "product_ids": sorted(fingerprint.product_ids),
        "channel": fingerprint.channel,
        "payload": fingerprint.payload,
        "bucket": bucket,
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"))


def _compute_bucket(dt: datetime, window_seconds: int) -> int:
    utc_dt = _ensure_utc(dt)
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    epoch_seconds = int(utc_dt.timestamp())
    return epoch_seconds // window_seconds


def generate_idempotency_token(
    fingerprint: EventFingerprint,
    *,
    window_seconds: int,
) -> str:
    bucket = _compute_bucket(fingerprint.occurred_at, window_seconds)
    payload = _canonical_payload(fingerprint, bucket)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest


def generate_event_identity(
    fingerprint: EventFingerprint,
    *,
    window_seconds: int,
) -> Tuple[str, str]:
    token = generate_idempotency_token(fingerprint, window_seconds=window_seconds)
    event_id = str(uuid5(NAMESPACE_URL, token))
    return event_id, token


