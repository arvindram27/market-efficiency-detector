"""Deterministic synthetic price/event generator — the free "mock" data path.

Produces seeded price paths with a controlled event: an instantaneous "surprise"
jump (enough to trigger |z| > threshold) followed by a residual adjustment that
converges to an equilibrium price at a configurable rate. This lets the slice
*prove discrimination* (fast vs slow vs no-event) rather than just plumbing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

from med.config import MedConfig
from med.types import EventType, NewsEvent, PriceBar, Scenario, Tier


@dataclass
class SyntheticSeries:
    bars: list[PriceBar]
    t_event: datetime
    equilibrium: float
    seed: int


def generate_price_series(
    seed: int,
    *,
    adjustment_rate: float,
    immediate_sigma: float,
    residual_sigma: float,
    config: MedConfig | None = None,
    base_time: datetime | None = None,
) -> SyntheticSeries:
    """Generate one deterministic OHLC bar series with a controlled event.

    Pre-event: geometric random walk (vol = sigma). At `t_event` an
    instantaneous log move of `immediate_sigma * sigma` lands; the remaining
    `residual_sigma * sigma` decays exponentially toward the equilibrium price
    at `adjustment_rate` (per bar). Noise is added as `noise_frac * sigma`.
    """
    cfg = config or MedConfig()
    rng = np.random.default_rng(seed)
    if base_time is None:
        base_time = datetime(2026, 1, 5, 9, 15, tzinfo=timezone.utc)

    bar_seconds = cfg.synth_bar_seconds
    pre_bars = cfg.synth_pre_bars
    post_bars = cfg.synth_post_bars
    sigma = cfg.synth_sigma
    noise_frac = cfg.synth_noise_frac
    start = cfg.synth_start_price

    pre_returns = rng.normal(0.0, sigma, pre_bars)
    pre_closes = start * np.exp(np.cumsum(pre_returns))
    p0 = float(pre_closes[-1])

    equilibrium = p0 * np.exp((immediate_sigma + residual_sigma) * sigma)
    p_after = p0 * np.exp(immediate_sigma * sigma)

    post_closes = [p_after]
    for k in range(1, post_bars):
        det = equilibrium - (equilibrium - p_after) * np.exp(-adjustment_rate * k)
        noise = float(np.exp(rng.normal(0.0, noise_frac * sigma)))
        post_closes.append(det * noise)

    closes = list(pre_closes) + post_closes
    bars = [
        PriceBar(
            ts=base_time + timedelta(seconds=i * bar_seconds),
            open=float(c),
            high=float(c),
            low=float(c),
            close=float(c),
            volume=0.0,
        )
        for i, c in enumerate(closes)
    ]
    t_event = base_time + timedelta(seconds=pre_bars * bar_seconds)
    return SyntheticSeries(bars=bars, t_event=t_event, equilibrium=float(equilibrium), seed=seed)


def build_demo_scenarios(config: MedConfig | None = None) -> list[Scenario]:
    """Three named scenarios that discriminate the classifier.

    - ``fast``:     earnings headline, price converges in ~2-3 min  -> FAST
    - ``slow``:     M&A headline,     price converges in ~55 min     -> SLOW
    - ``no_event``: earnings headline, but no actual price move       -> INCONCLUSIVE

    ``fast`` and ``slow`` share the same immediate surprise (so both trigger
    |z| > threshold); they differ only in the residual adjustment rate. The
    ``no_event`` scenario has a qualifying headline but zero price move, so it
    is suppressed by the trigger gate (the "news without price confirmation"
    null case).
    """
    cfg = config or MedConfig()
    base_time = datetime(2026, 1, 5, 9, 15, tzinfo=timezone.utc)

    specs = [
        # name, seed, adjustment_rate, headline
        ("fast", 1, 0.80, "Acme Q3 earnings beat estimates, profit up 40%"),
        ("slow", 2, 0.02, "Acme to merge with Beta Corp in USD 2B all-stock deal"),
        ("no_event", 3, 0.80, "Acme Q3 earnings beat estimates, profit up 40%"),
    ]

    scenarios: list[Scenario] = []
    for name, seed, rate, headline in specs:
        if name == "no_event":
            immediate, residual = 0.0, 0.0
        else:
            immediate, residual = cfg.synth_immediate_sigma, cfg.synth_residual_sigma

        series = generate_price_series(
            seed,
            adjustment_rate=rate,
            immediate_sigma=immediate,
            residual_sigma=residual,
            config=cfg,
            base_time=base_time,
        )
        event = NewsEvent(
            event_id=f"{name}-{seed}",
            ticker="ACME",
            ts_published=series.t_event,
            headline=headline,
            source="synthetic",
        )
        scenarios.append(
            Scenario(name=name, news_event=event, bars=series.bars, tier=Tier.MID, seed=seed)
        )
    return scenarios
