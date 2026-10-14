"""Pipeline — plain-Python orchestration chaining the agents end-to-end.

LangGraph is the PRD-mandated upgrade (v2); the agent functions are written as
pure, typed inputs/outputs so wiring them into a LangGraph graph later is a
mechanical change, not a rewrite.
"""
from __future__ import annotations

from med.agents import contextualist, decision_maker, statistician
from med.config import MedConfig
from med.provenance import current_git_sha
from med.storage.sqlite_store import PalStore
from med.types import (
    EventClassification,
    GateResult,
    NewsEvent,
    PALEvent,
    PriceBar,
    RunResult,
    Tier,
)


class Pipeline:
    def __init__(self, config: MedConfig | None = None, store: PalStore | None = None):
        self.config = config or MedConfig()
        self.store = store

    def run(
        self,
        news_event: NewsEvent,
        bars: list[PriceBar],
        *,
        tier: str = "MID",
        seed: int | None = None,
        vintage: str = "synthetic-v0.1",
    ) -> RunResult:
        cfg = self.config
        t_event = news_event.ts_published  # (later: max(ts_published, ts_ingested))

        # --- Statistician -------------------------------------------------
        _, sigma = statistician.pre_event_stats(bars, t_event, cfg.lookback_bars)
        max_abs_z, sign = statistician.event_zscore(
            bars, t_event, sigma, cfg.event_window_seconds
        )
        z_score = sign * max_abs_z
        equilibrium = statistician.compute_equilibrium(bars, cfg.equilibrium_tail_bars)
        t_efficient = statistician.find_t_efficient(
            bars,
            t_event,
            equilibrium,
            sigma,
            cfg.band_sigma_mult,
            cfg.consecutive_bars,
            cfg.cap_seconds[tier],
        )
        pal_seconds = (
            (t_efficient - t_event).total_seconds() if t_efficient is not None else None
        )

        # --- Contextualist ------------------------------------------------
        ctx = contextualist.analyze(news_event)

        # --- Decision Maker -----------------------------------------------
        gate = decision_maker.evaluate_gate(
            z_score=z_score,
            event_type=ctx.event_type,
            news_weight=ctx.news_weight,
            z_threshold=cfg.z_threshold,
        )

        pal_class = self._decide_class(gate, t_efficient, pal_seconds, tier)

        pal_event = PALEvent(
            event_id=news_event.event_id,
            ticker=news_event.ticker,
            tier=Tier(tier),
            t_event=t_event,
            t_efficient=t_efficient,
            pal_seconds=pal_seconds,
            pal_class=pal_class,
            z_score=z_score,
            sigma_pre=sigma,
            equilibrium_price=equilibrium,
            sentiment_score=ctx.sentiment,
            event_type=ctx.event_type,
            news_weight=ctx.news_weight,
            data_vintage=vintage,
            generator_seed=seed,
            git_sha=current_git_sha(),
        )

        result = RunResult(pal_event=pal_event, gate=gate)
        if self.store is not None:
            self.store.save(pal_event)
        return result

    def _decide_class(
        self,
        gate: GateResult,
        t_efficient,
        pal_seconds: float | None,
        tier: str,
    ) -> EventClassification:
        if not gate.trigger_passed:
            return EventClassification.INCONCLUSIVE
        if t_efficient is None:
            # PRD §2.3: the INCONCLUSIVE path is a forced exit, not a dropped trade.
            return EventClassification.INCONCLUSIVE
        return decision_maker.classify_pal(pal_seconds, tier, self.config.pal_thresholds)
