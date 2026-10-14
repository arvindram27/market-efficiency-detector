"""MED — Price Adjustment Latency (PAL) Explorer.

Streamlit demo for the v0 vertical slice. Reuses the core Pipeline unchanged.

Run from the project root:
    streamlit run app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure `med` and `ui` are importable regardless of the launch directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from med.config import MedConfig
from med.data.synthetic import build_demo_scenarios, generate_price_series
from med.pipeline import Pipeline
from med.storage.sqlite_store import PalStore
from med.types import NewsEvent
from ui.charts import pal_chart

_DISCLAIMER = (
    "Research prototype only. All signals are paper-traded; past simulated "
    "performance is not indicative of future results; not investment advice."
)

st.set_page_config(page_title="MED — PAL Explorer", page_icon="📈", layout="wide")

config = MedConfig()
store = PalStore("data/med.db")
pipeline = Pipeline(config=config, store=store)

# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.title("MED 📈")
    st.caption("Market Efficiency Detector")
    st.markdown("**PAL** = T_efficient − T_event")
    st.divider()
    st.markdown(f"*{_DISCLAIMER}*")
    st.divider()
    st.markdown("[README](README.md) · [Build log](build log.md)")

st.title("Price Adjustment Latency — PAL Explorer")
st.caption(
    "How long does the market take to absorb an information event? "
    "Fast vs slow adjustment, measured from a seeded synthetic price path."
)

tabs = st.tabs(["Scenarios", "Playground", "Stored events"])


# --------------------------------------------------------------------------- #
# Tab 1 — Canonical scenarios
# --------------------------------------------------------------------------- #
def _run_scenario_table() -> dict[str, object]:
    scenarios = build_demo_scenarios(config)
    rows: list[dict] = []
    results: dict[str, object] = {}
    for s in scenarios:
        res = pipeline.run(
            s.news_event, s.bars, tier=s.tier.value, seed=s.seed, vintage="synthetic-v0.1"
        )
        results[s.name] = res
        pe = res.pal_event
        rows.append(
            {
                "Scenario": s.name,
                "Event type": pe.event_type.value,
                "News weight": pe.news_weight.value,
                "z-score": round(pe.z_score, 2),
                "PAL (min)": None
                if not res.gate.trigger_passed or pe.pal_seconds is None
                else round(pe.pal_seconds / 60, 1),
                "Class": pe.pal_class.value,
                "Suppressed": None if res.gate.trigger_passed else res.gate.suppressed_reason,
            }
        )
    return {"rows": rows, "results": results, "scenarios": scenarios}


with tabs[0]:
    st.subheader("Canonical scenarios")
    st.markdown(
        "`fast` and `slow` share the same instantaneous surprise (both trigger "
        "`|z| > 2.0`); they differ only in how long the *residual* adjustment takes. "
        "`no_event` has a qualifying headline but no price move, so the trigger gate "
        "suppresses it."
    )
    out = _run_scenario_table()
    st.dataframe(pd.DataFrame(out["rows"]), width="stretch", hide_index=True)

    for s in out["scenarios"]:
        st.markdown(f"**{s.name}**")
        st.altair_chart(pal_chart(s.bars, out["results"][s.name].pal_event, config))


# --------------------------------------------------------------------------- #
# Tab 2 — Interactive playground
# --------------------------------------------------------------------------- #
with tabs[1]:
    st.subheader("Interactive playground")
    st.markdown("Drag the sliders to change the event and watch PAL respond live.")

    c1, c2, c3 = st.columns(3)
    with c1:
        immediate = st.slider("Event magnitude (σ)", 0.0, 6.0, 2.5, 0.1)
    with c2:
        residual = st.slider("Residual adjustment (σ)", 0.0, 4.0, 1.5, 0.1)
    with c3:
        rate = st.slider(
            "Adjustment speed κ (per bar)", 0.005, 1.0, 0.05, 0.005, format="%.3f"
        )

    seed = 42
    series = generate_price_series(
        seed,
        adjustment_rate=rate,
        immediate_sigma=immediate,
        residual_sigma=residual,
        config=config,
    )
    event = NewsEvent(
        event_id=f"playground-{seed}",
        ticker="ACME",
        ts_published=series.t_event,
        headline="Acme Q3 earnings beat estimates, profit up 40%",
        source="synthetic",
    )
    res = pipeline.run(event, series.bars, tier="MID", seed=seed, vintage="synthetic-v0.1")
    pe = res.pal_event

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("z-score", f"{pe.z_score:.2f}")
    m2.metric(
        "PAL (min)",
        "--" if pe.pal_seconds is None else f"{pe.pal_seconds / 60:.1f}",
    )
    m3.metric("Class", pe.pal_class.value)
    m4.metric(
        "Trigger",
        "PASS" if res.gate.trigger_passed else f"suppressed ({res.gate.suppressed_reason})",
    )

    st.altair_chart(pal_chart(series.bars, pe, config))


# --------------------------------------------------------------------------- #
# Tab 3 — Stored events (SQLite)
# --------------------------------------------------------------------------- #
with tabs[2]:
    st.subheader("Stored events")
    st.markdown("Rows persisted to SQLite (`data/med.db`) by the pipeline.")
    events = store.list_all()
    if not events:
        st.info("No events stored yet — run the **Scenarios** tab first.")
    else:
        rows = [
            {
                "event_id": e.event_id,
                "ticker": e.ticker,
                "tier": e.tier.value,
                "event_type": e.event_type.value,
                "news_weight": e.news_weight.value,
                "z_score": round(e.z_score, 2),
                "pal_seconds": round(e.pal_seconds, 1) if e.pal_seconds is not None else None,
                "pal_class": e.pal_class.value,
                "data_vintage": e.data_vintage,
                "generator_seed": e.generator_seed,
            }
            for e in events
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

store.close()
