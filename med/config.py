"""Configuration for the MED vertical slice.

All thresholds here are documented **placeholders**. They must be calibrated on
real NSE/SGX data in v1 (per PRD §2.3 / v2.0 §1.3). The single most important
definition — how "the market has absorbed the event" is declared — is pinned
explicitly here rather than left as a dangling v2.0 reference.
"""
from __future__ import annotations

from pydantic import BaseModel


class MedConfig(BaseModel):
    # ---- Statistician ---------------------------------------------------
    lookback_bars: int = 60          # pre-event window for sigma estimation
    event_window_seconds: int = 300  # confirmation window after t_event (PRD §2.3)
    z_threshold: float = 2.0         # |z| > 2.0 within 300s (PRD §2.3)

    # ---- T_efficient stability rule (PRD v2.0 §1.3, pinned here) --------
    # T_efficient = first bar after t_event where close stays within
    #   band = band_sigma_mult * sigma_pre * equilibrium
    # for `consecutive_bars` consecutive bars.
    band_sigma_mult: float = 0.5
    consecutive_bars: int = 5

    # ---- Observation caps by tier (PRD §2.3) ---------------------------
    cap_seconds: dict[str, int] = {
        "LARGE": 90 * 60,
        "MID": 120 * 60,
        "SMALL": 180 * 60,
    }

    # ---- Equilibrium anchor (what "efficient" is benchmarked against) ---
    # The post-event equilibrium price is the median close over the final
    # `equilibrium_tail_bars` of the observation window (PRD recommendation:
    # anchor to a model of equilibrium, not "returns went quiet").
    equilibrium_tail_bars: int = 20

    # ---- PAL classification thresholds (seconds) by tier ---------------
    # (fast_max, normal_max); above normal_max => SLOW. Placeholders.
    pal_thresholds: dict[str, tuple[int, int]] = {
        "LARGE": (10 * 60, 40 * 60),
        "MID": (10 * 60, 40 * 60),
        "SMALL": (15 * 60, 45 * 60),
    }

    # ---- Synthetic generator defaults (the free/mock data path) ---------
    synth_bar_seconds: int = 60
    synth_pre_bars: int = 60
    synth_post_bars: int = 240
    synth_sigma: float = 0.0015            # per-bar log-return volatility
    synth_immediate_sigma: float = 2.5     # instantaneous event move (σ) — the "surprise"
    synth_residual_sigma: float = 1.5      # remaining adjustment (σ) that decays
    synth_noise_frac: float = 0.15         # post-event noise as a fraction of sigma
    synth_start_price: float = 100.0
