"""Chart builder test — skipped when the `demo` extra (altair) isn't installed."""
from __future__ import annotations

import pytest

pytest.importorskip("altair")

from med.pipeline import Pipeline
from ui.charts import pal_chart


def test_pal_chart_builds_with_expected_layers(config, scenarios):
    res = Pipeline().run(
        scenarios["fast"].news_event,
        scenarios["fast"].bars,
        tier=scenarios["fast"].tier.value,
        seed=scenarios["fast"].seed,
    )
    chart = pal_chart(scenarios["fast"].bars, res.pal_event, config)
    spec = chart.to_dict()
    assert "layer" in spec
    # line + T_event rule + T_event label + T_efficient rule + T_efficient label
    # + equilibrium band rect + equilibrium line = 7 layers
    assert len(spec["layer"]) == 7


def test_pal_chart_without_efficient_drops_its_layers(config, scenarios):
    # Force a cap-hit (T_efficient never reached) with a tiny observation cap.
    from med.config import MedConfig

    cfg = MedConfig(cap_seconds={"LARGE": 90 * 60, "MID": 5 * 60, "SMALL": 180 * 60})
    res = Pipeline(config=cfg).run(
        scenarios["slow"].news_event,
        scenarios["slow"].bars,
        tier=scenarios["slow"].tier.value,
        seed=scenarios["slow"].seed,
    )
    assert res.pal_event.t_efficient is None  # slow converges ~55 min > 5 min cap
    chart = pal_chart(scenarios["slow"].bars, res.pal_event, cfg)
    spec = chart.to_dict()
    # no T_efficient => line + event rule + event label + band + eq line = 5 layers
    assert len(spec["layer"]) == 5
