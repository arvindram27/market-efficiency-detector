from __future__ import annotations

from med.agents import statistician
from med.types import PriceBar


def test_pre_event_stats_positive_sigma(scenarios):
    s = scenarios["fast"]
    mu, sigma = statistician.pre_event_stats(s.bars, s.news_event.ts_published, 60)
    assert sigma > 0
    assert isinstance(mu, float)


def test_event_zscore_detects_surprise(scenarios):
    s = scenarios["fast"]
    _, sigma = statistician.pre_event_stats(s.bars, s.news_event.ts_published, 60)
    max_abs_z, sign = statistician.event_zscore(s.bars, s.news_event.ts_published, sigma, 300)
    # fast scenario has an immediate ~2.5 sigma move -> clearly above 2.0
    assert max_abs_z > 2.0
    assert sign in (1.0, -1.0)


def test_no_event_has_no_qualifying_z(scenarios):
    s = scenarios["no_event"]
    _, sigma = statistician.pre_event_stats(s.bars, s.news_event.ts_published, 60)
    max_abs_z, _ = statistician.event_zscore(s.bars, s.news_event.ts_published, sigma, 300)
    assert max_abs_z <= 2.0


def test_find_t_efficient_within_cap(scenarios):
    s = scenarios["fast"]
    _, sigma = statistician.pre_event_stats(s.bars, s.news_event.ts_published, 60)
    eq = statistician.compute_equilibrium(s.bars, 20)
    t_eff = statistician.find_t_efficient(
        s.bars, s.news_event.ts_published, eq, sigma, 0.5, 5, 120 * 60
    )
    assert t_eff is not None
    assert t_eff > s.news_event.ts_published


def test_find_t_efficient_hits_cap_when_unreachable(scenarios):
    s = scenarios["slow"]
    _, sigma = statistician.pre_event_stats(s.bars, s.news_event.ts_published, 60)
    eq = statistician.compute_equilibrium(s.bars, 20)
    # A tiny cap forces INCONCLUSIVE (the forced-exit path).
    t_eff = statistician.find_t_efficient(
        s.bars, s.news_event.ts_published, eq, sigma, 0.5, 5, 5 * 60
    )
    assert t_eff is None


def test_equilibrium_near_true_equilibrium(scenarios):
    s = scenarios["fast"]
    eq = statistician.compute_equilibrium(s.bars, 20)
    # synthetic equilibrium = start price grown by (immediate+residual)*sigma
    assert eq > 100.0
