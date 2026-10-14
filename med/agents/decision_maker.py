"""Decision Maker — trigger gate (PRD §2.3) + PAL classification.

The gate requires ALL of:
    news_weight == HIGH
    event_type in {EARNINGS, MACRO, M&A}
    |z| > z_threshold within the confirmation window

Direction is taken from the sign of the price move. Sentiment/price agreement
is a v2.5 concern and is intentionally deferred (see PRD §2.3).
"""
from __future__ import annotations

from med.types import Direction, EventClassification, EventType, GateResult, NewsWeight

_TRADEABLE_EVENT_TYPES = frozenset({EventType.EARNINGS, EventType.MACRO, EventType.M_A})

# Suppression reasons match PRD §4.4's suppressed_reason vocabulary.
_LOW_CONF = "LOW_CONF"
_EVENT_TYPE = "EVENT_TYPE"
_NO_PRICE_MOVE = "NO_PRICE_MOVE"


def evaluate_gate(
    *,
    z_score: float,
    event_type: EventType,
    news_weight: NewsWeight,
    z_threshold: float,
) -> GateResult:
    if news_weight != NewsWeight.HIGH:
        return GateResult(trigger_passed=False, suppressed_reason=_LOW_CONF)
    if event_type not in _TRADEABLE_EVENT_TYPES:
        return GateResult(trigger_passed=False, suppressed_reason=_EVENT_TYPE)
    if abs(z_score) <= z_threshold:
        return GateResult(trigger_passed=False, suppressed_reason=_NO_PRICE_MOVE)
    direction = Direction.LONG if z_score > 0 else Direction.SHORT
    return GateResult(trigger_passed=True, direction=direction, suppressed_reason=None)


def classify_pal(
    pal_seconds: float | None,
    tier: str,
    thresholds: dict[str, tuple[int, int]],
) -> EventClassification:
    """Classify PAL. ``None`` (cap hit) => INCONCLUSIVE."""
    if pal_seconds is None:
        return EventClassification.INCONCLUSIVE
    fast_max, normal_max = thresholds.get(tier, (10 * 60, 40 * 60))
    if pal_seconds <= fast_max:
        return EventClassification.FAST
    if pal_seconds <= normal_max:
        return EventClassification.NORMAL
    return EventClassification.SLOW
