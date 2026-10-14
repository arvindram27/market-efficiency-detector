"""Typed domain models for the Market Efficiency Detector vertical slice.

These map directly onto the PRD v3.0 §4.4/§4.5 contracts, trimmed to what the
v0 slice actually measures. Signal-layer fields (sizing, stop, capacity) are
deferred to v2.5 and kept out of `PALEvent` so the schema does not need to be
migrated later.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class PriceBar(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class NewsEvent(BaseModel):
    event_id: str
    ticker: str
    ts_published: datetime  # T_event candidate (publication time)
    headline: str
    source: str = "synthetic"
    # PRD §5.3: store both timestamps; use the later of the two as T_event.
    ts_ingested: datetime | None = None


class EventType(str, Enum):
    EARNINGS = "EARNINGS"
    MACRO = "MACRO"
    M_A = "M&A"
    OTHER = "OTHER"


class EventClassification(str, Enum):
    FAST = "FAST"
    NORMAL = "NORMAL"
    SLOW = "SLOW"
    INCONCLUSIVE = "INCONCLUSIVE"


class NewsWeight(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


class Tier(str, Enum):
    LARGE = "LARGE"
    MID = "MID"
    SMALL = "SMALL"


class PALEvent(BaseModel):
    """The core measurement: Price Adjustment Latency for a single event."""

    event_id: str
    ticker: str
    tier: Tier = Tier.MID
    t_event: datetime
    t_efficient: datetime | None = None
    pal_seconds: float | None = None
    pal_class: EventClassification = EventClassification.INCONCLUSIVE
    z_score: float = 0.0
    sigma_pre: float = 0.0
    equilibrium_price: float | None = None
    sentiment_score: float = 0.0
    event_type: EventType = EventType.OTHER
    news_weight: NewsWeight = NewsWeight.LOW
    # Provenance (PRD §5.3 / §10 reproducibility): stamped on every row.
    data_vintage: str = ""
    generator_seed: int | None = None
    git_sha: str | None = None


class ContextualResult(BaseModel):
    event_type: EventType
    news_weight: NewsWeight
    sentiment: float


class GateResult(BaseModel):
    """Trigger gate (PRD §2.3) + direction. Signal fields deferred to v2.5."""

    trigger_passed: bool = False
    direction: Direction = Direction.NONE
    suppressed_reason: str | None = None


class RunResult(BaseModel):
    pal_event: PALEvent
    gate: GateResult


class Scenario(BaseModel):
    """A named, deterministic demo/test scenario (news + price path)."""

    name: str
    news_event: NewsEvent
    bars: list[PriceBar]
    tier: Tier = Tier.MID
    seed: int | None = None
