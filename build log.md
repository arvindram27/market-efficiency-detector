# Build Log — Market Efficiency Detector (MED)

> Living record of progress, decisions, and the path toward the PRD v3.0 deliverables.
> Updated as each milestone completes. Spec: [`docs/MED_PRD_v3_0_Business_Ready.docx`](docs/MED_PRD_v3_0_Business_Ready.docx)

## Project snapshot

| | |
|---|---|
| Project | Market Efficiency Detector (MED) |
| Spec | PRD v3.0 — Business-Ready Revision (September 2026) |
| Core metric | Price Adjustment Latency (PAL) = T_efficient − T_event |
| Product | PAL-derived event-driven statistical arbitrage signal (paper-traded) |
| Current status | **v0 vertical slice + Streamlit PAL explorer — complete & tested** |
| Stack (current) | Python 3.11+ · numpy · pydantic · VADER · SQLite — free, offline, zero keys |
| Repo | public, `market-efficiency-detector` |

## Deliverables roadmap (PRD §7 ladder)

| Version | Theme | Exit criterion | Status |
|---|---|---|---|
| **v0 — Vertical slice** | Prove PAL computes **and discriminates** end-to-end | CLI demo + Streamlit PAL explorer + 25 tests green | ✅ **Done (2026-10-15)** |
| **v1 — Solo Analyst** | PAL on ~50 real NSE/SGX events; calibrate thresholds | Finding published (Medium) | ⬜ pending |
| **v2 — Dual-Agent Live** | LangGraph Statistician + Contextualist on a streaming bus | Live pipeline + Streamlit demo deployed | ⬜ pending |
| **v2.5 — Signal Layer** | Cost-aware, validated signal (entry/exit/sizing) | Backtest of record + kill criteria evaluated | ⬜ pending |
| **v3 — Production Swarm** | Forecaster, SHAP, RAG, Airflow research plane | Preprint submitted | ⬜ pending |

## Progress log

| Date | Milestone | What changed | Status |
|---|---|---|---|
| 2026-10-15 | v0 vertical slice | Created `med/` package: synthetic data generator, Statistician, Contextualist, Decision Maker, SQLite store, pipeline, CLI demo; 23 tests; README + non-advice disclaimer | ✅ |
| 2026-10-15 | Streamlit PAL explorer | Added `app.py` + `ui/charts.py` (Altair): scenarios, interactive playground, and stored-events views; `streamlit` added as a `demo` extra | ✅ |
| 2026-10-15 | Streamlit screenshots | Captured all 3 tabs into `docs/screenshots/` and embedded them in the README | ✅ |
| 2026-10-22 | Desktop-res screenshots | Re-captured all 3 tabs at 1600×1000 via headless Playwright (system Edge); replaces the earlier 700×840 viewport captures | ✅ |

## What v0 proves (and what it doesn't)

**Proves:** PAL computes end-to-end from a price series + event timestamp, and the classifier
*discriminates* — the seeded demo yields `PAL(slow) ≈ 43 min > PAL(fast) ≈ 2 min`, and a
qualifying headline with no price move is suppressed to `INCONCLUSIVE`.

**Does not (yet) prove:** that this holds on real NSE/SGX data, or that the delay is worth
anything after transaction costs. Those are v1 and v2.5 respectively — deliberately ordered
"metric first" per the PRD.

## Key decisions (and why)

1. **T_efficient pinned explicitly.** The PRD references "the tier-specific stability rule in
   §1.3 of v2.0" (a document we don't have). v0 defines it as: *first bar after T_event where
   close stays within `0.5 · σ_pre · equilibrium` for 5 consecutive bars.*
2. **"Efficient" anchored to equilibrium, not "price went quiet."** Equilibrium = median close
   over the final 20 bars. This avoids conflating "fully absorbed" with "never reacted."
3. **Negative controls built in.** Tests assert `PAL(slow) > PAL(fast)` and
   `no-event → INCONCLUSIVE`, so the slice proves discrimination, not just plumbing.
4. **Plain-Python orchestration now; LangGraph later.** Agents are typed, pure functions, so the
   LangGraph upgrade (v2) is a mechanical re-wiring, not a rewrite.
5. **Measurement vs. signal kept separate.** `PALEvent` is measurement-only; signal fields
   (sizing, stop, capacity) arrive in v2.5 without a schema migration.
6. **Provenance from day one.** Every row stamps `data_vintage`, `generator_seed`, `git_sha`
   (PRD §5.3 / §10 reproducibility discipline).
7. **Thresholds are documented placeholders.** The algorithm is the deliverable; the specific
   band/class numbers must be calibrated on real data in v1.

## How to run

```bash
pip install -e ".[dev]"      # core + pytest
python -m med.demo           # end-to-end PAL report (3 synthetic scenarios)
pytest                       # 23 tests

# Web demo
pip install -e ".[demo]"     # adds streamlit
streamlit run app.py         # PAL explorer (scenarios / playground / stored events)
```

## Test results (2026-10-15)

```
25 passed
- test_contextualist   (7): taxonomy, news_weight, sentiment sign
- test_decision_maker  (5): trigger gate + suppression reasons
- test_pipeline        (4): PAL discrimination, INCONCLUSIVE, provenance, determinism
- test_statistician    (6): sigma, z-score, equilibrium, T_efficient (incl. cap path)
- test_storage         (1): SQLite round-trip
- test_ui              (2): chart layer counts (skipped without the demo extra)
```

## Next concrete steps

1. **v1** — replace synthetic-only with the optional `yfinance` NSE/SGX path
   (`med/data/yfinance_source.py` is already written, needs a live run + calibration);
   collect ~50 events; publish the finding.
2. **v2** — swap `med/pipeline.py` for a LangGraph graph (Statistician ∥ Contextualist →
   Decision Maker); add a streaming bus and wire the existing Streamlit explorer to it.
3. **v2.5** — Signal Generator node + `trade-signals` topic; cost model + vectorbt backtest;
   write kill criteria (§5.5) to the repo *before* running the sweep.

## Compliance guardrails (PRD §10)

Research prototype only. All signals are paper-traded; no broker credentials exist anywhere in
this codebase. Past simulated performance is not indicative of future results, and nothing here
is investment advice. If this moves toward third-party distribution or live capital, obtain
professional advice on SEBI (India) and MAS (Singapore) requirements first.
