"""Statistician agent — the numerical half of the PAL computation.

Pure numpy, no LLM. Responsibilities (PRD §4.2):
  1. Estimate pre-event rolling sigma (and drift) over the lookback window.
  2. Detect the event move: max |z| within `event_window_seconds` of T_event.
  3. Anchor "efficient" to an equilibrium price (median of the tail).
  4. Find T_efficient: first bar where close stays within a sigma band of the
     equilibrium for N consecutive bars (the pinned stability rule).
"""
from __future__ import annotations

import math
from datetime import datetime

import numpy as np

from med.types import PriceBar


def _closes_ts(bars: list[PriceBar]) -> tuple[np.ndarray, list[datetime]]:
    return np.array([b.close for b in bars], dtype=float), [b.ts for b in bars]


def _last_index_before(ts: list[datetime], t_event: datetime) -> int | None:
    """Index of the last bar strictly before t_event (excludes the event bar itself,
    which already contains the surprise move)."""
    idx = None
    for i, t in enumerate(ts):
        if t < t_event:
            idx = i
        else:
            break
    return idx


def pre_event_stats(bars: list[PriceBar], t_event: datetime, lookback_bars: int) -> tuple[float, float]:
    """Return (drift, sigma) of 1-bar log returns over the lookback window ending before t_event."""
    closes, ts = _closes_ts(bars)
    idx = _last_index_before(ts, t_event)
    if idx is None:
        raise ValueError("t_event precedes all bars")
    start = max(0, idx - lookback_bars + 1)
    window = closes[start : idx + 1]
    if len(window) < 2:
        raise ValueError("insufficient pre-event bars to estimate volatility")
    log_returns = np.diff(np.log(window))
    mu = float(log_returns.mean())
    sigma = float(log_returns.std(ddof=1)) if len(log_returns) > 1 else 0.0
    return mu, sigma


def event_zscore(
    bars: list[PriceBar],
    t_event: datetime,
    sigma: float,
    event_window_seconds: int,
) -> tuple[float, float]:
    """Return (max_abs_z, sign) of the cumulative move within the confirmation window.

    ``z`` at bar k is the cumulative log return from T_event standardized by
    ``sigma * sqrt(k)`` — a standard cumulative-abnormal-return z-score.
    """
    closes, ts = _closes_ts(bars)
    ref_i = _last_index_before(ts, t_event)
    if ref_i is None or sigma <= 0:
        return 0.0, 0.0
    ref = closes[ref_i]

    max_abs_z = 0.0
    sign = 0.0
    for i in range(ref_i + 1, len(ts)):
        if (ts[i] - t_event).total_seconds() > event_window_seconds:
            break
        k = i - ref_i
        cum_log_return = math.log(closes[i] / ref)
        z = cum_log_return / (sigma * math.sqrt(k))
        if abs(z) > max_abs_z:
            max_abs_z = abs(z)
            sign = 1.0 if z > 0 else -1.0
    return max_abs_z, sign


def compute_equilibrium(bars: list[PriceBar], tail_bars: int) -> float:
    """Estimate post-event equilibrium price as the median close over the tail."""
    closes, _ = _closes_ts(bars)
    return float(np.median(closes[-tail_bars:]))


def find_t_efficient(
    bars: list[PriceBar],
    t_event: datetime,
    equilibrium: float,
    sigma: float,
    band_sigma_mult: float,
    consecutive_bars: int,
    cap_seconds: int,
) -> datetime | None:
    """First bar at/after t_event where close stays within the equilibrium band
    for `consecutive_bars` consecutive bars. Returns None if the cap is hit first.

    band = band_sigma_mult * sigma_pre * equilibrium
    """
    closes, ts = _closes_ts(bars)
    if sigma <= 0 or equilibrium <= 0:
        return None
    band = band_sigma_mult * sigma * equilibrium

    streak = 0
    first_streak_ts: datetime | None = None
    for i, t in enumerate(ts):
        if t < t_event:
            continue
        if (t - t_event).total_seconds() > cap_seconds:
            break
        if abs(closes[i] - equilibrium) <= band:
            if streak == 0:
                first_streak_ts = t
            streak += 1
            if streak >= consecutive_bars:
                return first_streak_ts
        else:
            streak = 0
            first_streak_ts = None
    return None
