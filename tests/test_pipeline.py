from __future__ import annotations

from med.pipeline import Pipeline
from med.types import EventClassification


def test_pal_discriminates_fast_vs_slow(scenarios):
    """The core claim: PAL(slow) > PAL(fast), and both classify cleanly."""
    pipeline = Pipeline()
    fast = pipeline.run(
        scenarios["fast"].news_event,
        scenarios["fast"].bars,
        tier=scenarios["fast"].tier.value,
        seed=scenarios["fast"].seed,
    )
    slow = pipeline.run(
        scenarios["slow"].news_event,
        scenarios["slow"].bars,
        tier=scenarios["slow"].tier.value,
        seed=scenarios["slow"].seed,
    )

    assert fast.pal_event.pal_seconds is not None
    assert slow.pal_event.pal_seconds is not None
    assert slow.pal_event.pal_seconds > fast.pal_event.pal_seconds

    assert fast.pal_event.pal_class == EventClassification.FAST
    assert slow.pal_event.pal_class == EventClassification.SLOW


def test_no_event_is_inconclusive(scenarios):
    """A qualifying headline with no actual price move => suppressed, INCONCLUSIVE."""
    pipeline = Pipeline()
    res = pipeline.run(
        scenarios["no_event"].news_event,
        scenarios["no_event"].bars,
        tier=scenarios["no_event"].tier.value,
        seed=scenarios["no_event"].seed,
    )
    assert res.gate.trigger_passed is False
    assert res.gate.suppressed_reason == "NO_PRICE_MOVE"
    assert res.pal_event.pal_class == EventClassification.INCONCLUSIVE


def test_provenance_is_stamped(scenarios):
    pipeline = Pipeline()
    res = pipeline.run(
        scenarios["fast"].news_event,
        scenarios["fast"].bars,
        tier=scenarios["fast"].tier.value,
        seed=scenarios["fast"].seed,
    )
    assert res.pal_event.data_vintage == "synthetic-v0.1"
    assert res.pal_event.generator_seed == scenarios["fast"].seed


def test_run_is_deterministic(scenarios):
    """Same seed => byte-identical PAL (PRD §3.2 backtest reproducibility)."""
    a = Pipeline().run(
        scenarios["fast"].news_event, scenarios["fast"].bars,
        tier=scenarios["fast"].tier.value, seed=scenarios["fast"].seed,
    )
    b = Pipeline().run(
        scenarios["fast"].news_event, scenarios["fast"].bars,
        tier=scenarios["fast"].tier.value, seed=scenarios["fast"].seed,
    )
    assert a.pal_event.pal_seconds == b.pal_event.pal_seconds
    assert a.pal_event.pal_class == b.pal_event.pal_class
