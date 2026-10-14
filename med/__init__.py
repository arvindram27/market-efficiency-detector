"""Market Efficiency Detector (MED) — Price Adjustment Latency vertical slice.

Proves the PRD v3.0 core claim end-to-end on free, deterministic data:
    PAL = T_efficient - T_event, classified FAST / NORMAL / SLOW / INCONCLUSIVE.
"""
from __future__ import annotations

__version__ = "0.1.0"

from med.config import MedConfig
from med.types import (
    ContextualResult,
    Direction,
    EventClassification,
    EventType,
    GateResult,
    NewsEvent,
    NewsWeight,
    PALEvent,
    PriceBar,
    RunResult,
    Scenario,
    Tier,
)
from med.pipeline import Pipeline
from med.data.synthetic import build_demo_scenarios

__all__ = [
    "__version__",
    "MedConfig",
    "PriceBar",
    "NewsEvent",
    "EventType",
    "EventClassification",
    "NewsWeight",
    "Direction",
    "Tier",
    "PALEvent",
    "ContextualResult",
    "GateResult",
    "RunResult",
    "Scenario",
    "Pipeline",
    "build_demo_scenarios",
]
