"""Local batch demo: v0 demo scenarios -> Spark -> PAL rows -> Delta.

Run from the project root:

    python -m med_spark.demo_batch

This module never touches the v0 SQLite store.
"""

from __future__ import annotations

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from med.data.synthetic import build_demo_scenarios
from med_spark.batch import compute_pal_events
from med_spark.delta_store import DeltaPalStore

DEFAULT_VINTAGE = "synthetic-v0.1"

# Explicit schemas - nothing is inferred from the Python objects.
EVENTS_SCHEMA = StructType(
    [
        StructField("scenario", StringType(), False),
        StructField("event_id", StringType(), False),
        StructField("ticker", StringType(), False),
        StructField("ts_published", TimestampType(), False),
        StructField("headline", StringType(), False),
        StructField("source", StringType(), False),
        StructField("ts_ingested", TimestampType(), True),
        StructField("tier", StringType(), False),
        StructField("seed", LongType(), True),
        StructField("vintage", StringType(), False),
    ]
)

BARS_SCHEMA = StructType(
    [
        StructField("scenario", StringType(), False),
        StructField("ts", TimestampType(), False),
        StructField("open", DoubleType(), False),
        StructField("high", DoubleType(), False),
        StructField("low", DoubleType(), False),
        StructField("close", DoubleType(), False),
        StructField("volume", DoubleType(), False),
    ]
)


def build_spark() -> SparkSession:
    """Local Spark session with the Delta session extension and catalog configs."""
    builder = (
        SparkSession.builder.appName("med-spark-batch")
        .config(
            "spark.sql.extensions",
            "io.delta.sql.DeltaSparkSessionExtension",
        )
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.sql.session.timeZone", "UTC")
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def _naive_utc(value):
    """Spark TimestampType is timezone-less; supply naive UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    from datetime import timezone

    return value.astimezone(timezone.utc).replace(tzinfo=None)


def scenario_frames(spark: SparkSession, config=None, vintage: str = DEFAULT_VINTAGE):
    """Build the ``events`` and ``bars`` frames from the v0 demo scenarios."""
    scenarios = build_demo_scenarios(config)

    event_rows = []
    bar_rows = []
    for scenario in scenarios:
        news = scenario.news_event
        event_rows.append(
            (
                scenario.name,
                news.event_id,
                news.ticker,
                _naive_utc(news.ts_published),
                news.headline,
                news.source,
                _naive_utc(news.ts_ingested),
                scenario.tier.value,
                scenario.seed,
                vintage,
            )
        )
        for bar in scenario.bars:
            bar_rows.append(
                (
                    scenario.name,
                    _naive_utc(bar.ts),
                    float(bar.open),
                    float(bar.high),
                    float(bar.low),
                    float(bar.close),
                    float(bar.volume),
                )
            )

    events = spark.createDataFrame(event_rows, schema=EVENTS_SCHEMA)
    bars = spark.createDataFrame(bar_rows, schema=BARS_SCHEMA)
    return events, bars


def main() -> None:
    """Run the batch, append the rows to Delta, and print the table."""
    spark = build_spark()
    try:
        events, bars = scenario_frames(spark)
        result = compute_pal_events(events, bars)
        store = DeltaPalStore(spark)
        store.save(result)
        print(f"Saved {store.count()} PAL row(s) to {store.base_path}")
        store.list_all().show(truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
