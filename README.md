<p align="center">
  <img src="docs/assets/med-logo.png" alt="MED silver and graphite 3D title" width="420" />
</p>

<h1 align="center">Market Efficiency Detector</h1>

<p align="center">A research project on price adjustment after news</p>

MED started as a small Price Adjustment Latency demo. It now includes a separate timing study with clearer candle boundaries and explicit gaps in the data.

This is a research prototype. It is not a validated market efficiency detector or a trading system.

## Two separate paths

**Legacy PAL demo**

`med/` calculates Price Adjustment Latency and stores results in SQLite. `med_spark/` is its Spark extension. The Streamlit app explores synthetic scenarios.

**mt1 timing study**

[`research/mt1/`](research/mt1/README.md) uses complete candles over a fixed 90 minute window. The final 20 complete candles define a retrospective reference price.

The price move trigger and the five candle stability rule have separate outcomes. Missing data stays visible. Unknown historical arrival times stay unknown.

mt1 does not replace the legacy result fields. Its Spark adapter calls the same Python calculation rather than a second independent algorithm.

## Try the synthetic example

Using an existing Python 3.11 or newer environment

```text
cd research/mt1
python -B synthetic_demo.py
python -B -m unittest tests_timing.test_mt1 tests_spark_review.test_transport tests_spark_review.test_demo -v
```

No API key or market data is needed. The example makes its own candles in memory.

The legacy demo remains available from the repository root with its dependencies installed

```text
python -m med.demo
```

## What we checked

- Synthetic tests cover boundaries and missing data
- Local Spark checks preserve fields and nulls and timestamp strings
- One private fixture passed through Spark with an exact Python result match

The Spark path shares the Python evaluator. These checks do not prove independent numerical correctness or scale or market efficiency. The reference price is retrospective. Candle close times are not actual alert arrival times.

[Method and verification](research/mt1/README.md) explain the scope and limits.

## Data boundary

Only synthetic examples are included for mt1. Provider data and derived private results are excluded. Nothing here is investment advice.
