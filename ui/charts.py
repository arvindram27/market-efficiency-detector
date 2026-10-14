"""Altair chart builder for the MED Streamlit demo.

Renders an annotated price path: the close line, a red rule at T_event, a green
rule at T_efficient, and a gray equilibrium line + shaded equilibrium band.
Altair ships with Streamlit, so this adds no dependency beyond the `demo` extra.
"""
from __future__ import annotations

import altair as alt
import pandas as pd

from med.config import MedConfig
from med.types import PALEvent, PriceBar


def pal_chart(bars: list[PriceBar], pal_event: PALEvent, config: MedConfig) -> alt.LayerChart:
    df = pd.DataFrame([{"ts": b.ts, "close": b.close} for b in bars])
    max_close = max(b.close for b in bars)

    line = (
        alt.Chart(df)
        .mark_line(color="#1f77b4", strokeWidth=1.6)
        .encode(
            x=alt.X("ts:T", title="Time"),
            y=alt.Y("close:Q", title="Price", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("ts:T", title="Time"),
                alt.Tooltip("close:Q", title="Close", format=".4f"),
            ],
        )
    )

    layers = [line]

    # T_event (red)
    layers.append(
        alt.Chart(pd.DataFrame({"t": [pal_event.t_event]}))
        .mark_rule(color="#d62728", strokeWidth=2, strokeDash=[5, 3])
        .encode(x="t:T")
    )
    layers.append(
        alt.Chart(
            pd.DataFrame({"t": [pal_event.t_event], "y": [max_close], "label": ["T_event"]})
        )
        .mark_text(dy=-6, color="#d62728", fontSize=11, fontWeight="bold")
        .encode(x="t:T", y="y:Q", text="label:N")
    )

    # T_efficient (green)
    if pal_event.t_efficient is not None:
        layers.append(
            alt.Chart(pd.DataFrame({"t": [pal_event.t_efficient]}))
            .mark_rule(color="#2ca02c", strokeWidth=2, strokeDash=[5, 3])
            .encode(x="t:T")
        )
        layers.append(
            alt.Chart(
                pd.DataFrame(
                    {"t": [pal_event.t_efficient], "y": [max_close], "label": ["T_efficient"]}
                )
            )
            .mark_text(dy=-6, color="#2ca02c", fontSize=11, fontWeight="bold")
            .encode(x="t:T", y="y:Q", text="label:N")
        )

    # Equilibrium line + shaded band
    eq = pal_event.equilibrium_price
    if eq is not None:
        band = config.band_sigma_mult * pal_event.sigma_pre * eq
        x0, x1 = bars[0].ts, bars[-1].ts
        layers.append(
            alt.Chart(
                pd.DataFrame({"x0": [x0], "x1": [x1], "y0": [eq - band], "y1": [eq + band]})
            )
            .mark_rect(color="gray", opacity=0.12)
            .encode(x="x0:T", x2="x1:T", y="y0:Q", y2="y1:Q")
        )
        layers.append(
            alt.Chart(pd.DataFrame({"y": [eq]}))
            .mark_rule(color="gray", strokeWidth=1, strokeDash=[2, 2])
            .encode(y="y:Q")
        )

    return alt.layer(*layers).properties(width="container", height=400).interactive()
