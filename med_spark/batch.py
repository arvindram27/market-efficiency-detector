"""Distributed PAL computation for the MED project (additive Spark extension).

The arithmetic is not re-implemented here. Each scenario is handed to the *v0*
``med.pipeline.Pipeline`` inside a pandas UDF, so the metric stays defined in
exactly one place.

Executor import requirement
--------------------------
The function body imports ``med`` on the worker side, therefore ``med`` must be
importable on every executor:

- local: run from the project root so ``med`` is on ``sys.path``;
- Databricks serverless: ship the project as workspace files and use absolute
  imports (``med.pipeline``, ``med.types``). Relative imports are unreliable on
  serverless.

Input contract
--------------
``events`` must carry: scenario, event_id, ticker, ts_published, headline,
source, ts_ingested, tier, seed, vintage.
``bars`` must carry: scenario, ts, open, high, low, close, volume.

``med_spark.demo_batch.scenario_frames`` builds both frames with explicit
schemas, and that is the supported way to produce them.
"""

from __future__ import annotations

import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# The v0 SQLite contract (med/storage/sqlite_store.py) minus ``created_at``,
# which the Delta store stamps at save time.
PAL_COLUMNS = (
    "event_id",
    "ticker",
    "tier",
    "t_event",
    "t_efficient",
    "pal_seconds",
    "pal_class",
    "z_score",
    "sigma_pre",
    "equilibrium_price",
    "sentiment_score",
    "event_type",
    "news_weight",
    "data_vintage",
    "generator_seed",
    "git_sha",
)

# Explicit 16-field schema: nullable exactly where the contract says so.
PAL_EVENT_SCHEMA = StructType(
    [
        StructField("event_id", StringType(), False),
        StructField("ticker", StringType(), False),
        StructField("tier", StringType(), False),
        StructField("t_event", TimestampType(), False),
        StructField("t_efficient", TimestampType(), True),
        StructField("pal_seconds", DoubleType(), True),
        StructField("pal_class", StringType(), False),
        StructField("z_score", DoubleType(), False),
        StructField("sigma_pre", DoubleType(), False),
        StructField("equilibrium_price", DoubleType(), True),
        StructField("sentiment_score", DoubleType(), False),
        StructField("event_type", StringType(), False),
        StructField("news_weight", StringType(), False),
        StructField("data_vintage", StringType(), False),
        StructField("generator_seed", LongType(), True),
        StructField("git_sha", StringType(), True),
    ]
)

EVENTS_COLUMNS = (
    "scenario",
    "event_id",
    "ticker",
    "ts_published",
    "headline",
    "source",
    "ts_ingested",
    "tier",
    "seed",
    "vintage",
)

BARS_COLUMNS = ("scenario", "ts", "open", "high", "low", "close", "volume")


def _to_aware_utc(value):
    """Interpret a (usually naive UTC) timestamp value as an aware UTC datetime."""
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC").to_pydatetime()
    return ts.tz_convert("UTC").to_pydatetime()


def _to_naive_utc(value):
    """Render an aware datetime as naive UTC for Spark's timezone-less TimestampType."""
    if value is None:
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.tz_localize(None).to_pydatetime()


def _require_columns(frame: DataFrame, columns, frame_name: str) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(
            f"{frame_name} is missing required column(s): {', '.join(missing)}"
        )


def _validate(events: DataFrame, bars: DataFrame) -> None:
    """Reject bad input on the driver, before anything is distributed."""
    _require_columns(events, EVENTS_COLUMNS, "events")
    _require_columns(bars, BARS_COLUMNS, "bars")

    bad_events = (
        events.filter(
            F.col("scenario").isNull()
            | F.col("event_id").isNull()
            | F.col("ts_published").isNull()
        )
        .select("scenario", "event_id", "ts_published")
        .limit(20)
        .collect()
    )
    if bad_events:
        details = "; ".join(
            "scenario={!r}, event_id={!r}, ts_published={!r}".format(
                r["scenario"], r["event_id"], r["ts_published"]
            )
            for r in bad_events
        )
        raise ValueError(
            "events contain a null scenario/event_id/ts_published: " + details
        )

    bad_bars = (
        bars.filter(F.col("scenario").isNull() | F.col("ts").isNull())
        .select("scenario", "ts")
        .limit(20)
        .collect()
    )
    if bad_bars:
        details = "; ".join(
            "scenario={!r}, ts={!r}".format(r["scenario"], r["ts"]) for r in bad_bars
        )
        raise ValueError("bars contain a null scenario/ts: " + details)

    duplicate_ids = (
        events.groupBy("event_id")
        .count()
        .filter(F.col("count") > 1)
        .select("event_id", "count")
        .limit(20)
        .collect()
    )
    if duplicate_ids:
        details = ", ".join(
            "{} (x{})".format(r["event_id"], r["count"]) for r in duplicate_ids
        )
        raise ValueError("duplicate event_id value(s): " + details)

    multiple_events = (
        events.groupBy("scenario")
        .count()
        .filter(F.col("count") > 1)
        .select("scenario", "count")
        .limit(20)
        .collect()
    )
    if multiple_events:
        details = ", ".join(
            "{} (x{})".format(r["scenario"], r["count"]) for r in multiple_events
        )
        raise ValueError("more than one event row for scenario(s): " + details)

    event_scenarios = {r["scenario"] for r in events.select("scenario").distinct().collect()}
    bar_scenarios = {r["scenario"] for r in bars.select("scenario").distinct().collect()}
    only_in_events = sorted(event_scenarios - bar_scenarios)
    only_in_bars = sorted(bar_scenarios - event_scenarios)
    if only_in_events or only_in_bars:
        parts = []
        if only_in_events:
            parts.append(
                "scenario(s) in events but not bars: " + ", ".join(only_in_events)
            )
        if only_in_bars:
            parts.append(
                "scenario(s) in bars but not events: " + ", ".join(only_in_bars)
            )
        raise ValueError("events/bars scenario sets differ - " + "; ".join(parts))


def _make_apply_fn(config):
    """Build the per-scenario pandas UDF body (one row out per scenario)."""

    def _compute(pdf: pd.DataFrame) -> pd.DataFrame:
        # Worker-side import: ``med`` must be importable on executors.
        from med.pipeline import Pipeline
        from med.types import NewsEvent, PriceBar

        row = pdf.iloc[0]
        ordered = pdf.sort_values("ts")

        news_event = NewsEvent(
            event_id=row["event_id"],
            ticker=row["ticker"],
            ts_published=_to_aware_utc(row["ts_published"]),
            headline=row["headline"],
            # Preserve source; fall back only if the column is null.
            source=row["source"] if row["source"] is not None else "synthetic",
            ts_ingested=(
                None if pd.isna(row["ts_ingested"]) else _to_aware_utc(row["ts_ingested"])
            ),
        )

        price_bars = [
            PriceBar(
                ts=_to_aware_utc(bar["ts"]),
                open=float(bar["open"]),
                high=float(bar["high"]),
                low=float(bar["low"]),
                close=float(bar["close"]),
                volume=float(bar["volume"]),
            )
            for _, bar in ordered.iterrows()
        ]

        seed = None if pd.isna(row["seed"]) else int(row["seed"])

        # The v0 pipeline, unchanged, with no SQLite store attached.
        result = Pipeline(config=config, store=None).run(
            news_event,
            price_bars,
            tier=row["tier"],
            seed=seed,
            vintage=row["vintage"],
        )
        pe = result.pal_event

        return pd.DataFrame(
            [
                {
                    "event_id": pe.event_id,
                    "ticker": pe.ticker,
                    "tier": pe.tier.value,
                    "t_event": _to_naive_utc(pe.t_event),
                    "t_efficient": _to_naive_utc(pe.t_efficient),
                    "pal_seconds": pe.pal_seconds,
                    "pal_class": pe.pal_class.value,
                    "z_score": pe.z_score,
                    "sigma_pre": pe.sigma_pre,
                    "equilibrium_price": pe.equilibrium_price,
                    "sentiment_score": pe.sentiment_score,
                    "event_type": pe.event_type.value,
                    "news_weight": pe.news_weight.value,
                    "data_vintage": pe.data_vintage,
                    "generator_seed": pe.generator_seed,
                    "git_sha": pe.git_sha,
                }
            ]
        )

    return _compute


def compute_pal_events(events: DataFrame, bars: DataFrame, config=None) -> DataFrame:
    """Compute one PAL row per scenario: ``events JOIN bars`` on scenario.

    Validation runs on the driver first, so a bad frame raises ``ValueError``
    naming the offenders instead of silently multiplying or dropping rows.
    ``config`` is an optional ``med.config.MedConfig`` passed to the v0 Pipeline.
    """
    _validate(events, bars)
    joined = events.join(bars, on="scenario", how="inner")
    return joined.groupBy("scenario").applyInPandas(
        _make_apply_fn(config), schema=PAL_EVENT_SCHEMA
    )
