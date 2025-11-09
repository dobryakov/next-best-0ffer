from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExplanationContext:
    """Контекст для формирования причины выдачи оффера."""

    customer_id: str
    customer_segments: list[str]
    variant: str
    channel: str | None


def build_offer_reason(product_id: str, position: int, context: ExplanationContext) -> str:
    """Генерирует человеко-читаемое объяснение для предложенного оффера."""

    segment = context.customer_segments[0] if context.customer_segments else "general"
    channel = context.channel or "omni"
    return (
        f"variant={context.variant};segment={segment};channel={channel};"
        f"rank={position + 1};product={product_id}"
    )


