"""Tests for the additive ``med_spark`` batch path.

Skipped entirely when PySpark or Delta are not installed. These tests have not
been run yet: nothing here is a claim about parity.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pyspark")
pytest.importorskip("delta")

import pandas as pd  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

from med.pipeline import Pipeline  # noqa: E402
from med_spark.batch import compute_pal_events  # noqa: E402
from med_spark.delta_store import DeltaPalStore  # noqa: E402
from med_spark.demo_batch import build_spark, scenario_frames  # noqa: E402

# The 16 contract fields shared with med/storage/sqlite_store.py (no created_at).
CONTRACT_FIELDS = (
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

_FLOAT_FIELDS = (
    "pal_seconds",
    "z_score",
    "sigma_pre",
    "equilibrium_price",
    "sentiment_score",
)

_TIMESTAMP_FIELDS = ("t_event", "t_efficient")


@pytest.fixture(scope="session")
def spark():
    session = build_spark()
    yield session
    session.stop()


def _aware_utc(value):
    """Normalize a timestamp representation to aware UTC.

    Collected Spark timestamps come back naive UTC; v0 datetimes are tz-aware
    UTC. Both are mapped to aware UTC here before any comparison.
    """
    if value is None:
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC").to_pydatetime()
    return ts.tz_convert("UTC").to_pydatetime()


@pytest.mark.parametrize("name", ["fast", "slow", "no_event"])
def test_parity_with_v0_pipeline(spark, config, scenarios, name):
    """Every contract field matches the v0 Pipeline for each demo scenario."""
    scenario = scenarios[name]
    expected = Pipeline(config=config, store=None).run(
        scenario.news_event,
        scenario.bars,
        tier=scenario.tier.value,
        seed=scenario.seed,
    ).pal_event

    events, bars = scenario_frames(spark, config=config)
    rows = (
        compute_pal_events(events, bars, config=config)
        .filter(F.col("event_id") == scenario.news_event.event_id)
        .collect()
    )
    assert len(rows) == 1
    row = rows[0]

    assert row["event_id"] == expected.event_id
    assert row["ticker"] == expected.ticker
    assert row["tier"] == expected.tier.value

    # Timestamps: normalize both sides to aware UTC first.
    assert _aware_utc(row["t_event"]) == _aware_utc(expected.t_event)
    # Includes the no_event case, where both sides are None.
    assert _aware_utc(row["t_efficient"]) == _aware_utc(expected.t_efficient)

    if expected.pal_seconds is None:
        assert row["pal_seconds"] is None
    else:
        assert row["pal_seconds"] is not None
        assert abs(row["pal_seconds"] - expected.pal_seconds) < 1e-6

    assert row["pal_class"] == expected.pal_class.value
    assert row["z_score"] == pytest.approx(expected.z_score)
    assert row["sigma_pre"] == pytest.approx(expected.sigma_pre)

    if expected.equilibrium_price is None:
        assert row["equilibrium_price"] is None
    else:
        assert row["equilibrium_price"] == pytest.approx(expected.equilibrium_price)

    # sentiment_score requires the same sentiment backend in both paths;
    # vaderSentiment is a core dependency, so both paths use VADER here.
    assert row["sentiment_score"] == pytest.approx(expected.sentiment_score)

    assert row["event_type"] == expected.event_type.value
    assert row["news_weight"] == expected.news_weight.value
    assert row["data_vintage"] == expected.data_vintage
    assert row["generator_seed"] == expected.generator_seed

    # git_sha is stamped from the executing working directory. Compare only when
    # both runs happened inside the repo; it is None elsewhere by design.
    if row["git_sha"] is not None and expected.git_sha is not None:
        assert row["git_sha"] == expected.git_sha


def test_duplicate_event_id_raises(spark, config):
    events, bars = scenario_frames(spark, config=config)
    duplicated = events.withColumn("event_id", F.lit("duplicate-id"))
    with pytest.raises(ValueError, match="duplicate event_id"):
        compute_pal_events(duplicated, bars, config=config)


def test_two_events_for_one_scenario_raises(spark, config):
    events, bars = scenario_frames(spark, config=config)
    extra = events.filter(F.col("scenario") == "fast").withColumn(
        "event_id", F.lit("fast-extra")
    )
    doubled = events.unionByName(extra)
    with pytest.raises(ValueError, match="more than one event row"):
        compute_pal_events(doubled, bars, config=config)


def test_bars_only_scenario_raises(spark, config):
    events, bars = scenario_frames(spark, config=config)
    extra = bars.filter(F.col("scenario") == "fast").withColumn(
        "scenario", F.lit("orphan")
    )
    with pytest.raises(ValueError, match="scenario sets differ"):
        compute_pal_events(events, bars.unionByName(extra), config=config)


def test_null_event_id_raises(spark, config):
    events, bars = scenario_frames(spark, config=config)
    nulled = events.withColumn("event_id", F.lit(None).cast("string"))
    with pytest.raises(ValueError, match="null scenario/event_id/ts_published"):
        compute_pal_events(nulled, bars, config=config)


def test_delta_round_trip_and_append(spark, config, tmp_path):
    """Rows read back match the written rows; a second save appends."""
    events, bars = scenario_frames(spark, config=config)
    computed = compute_pal_events(events, bars, config=config)
    store = DeltaPalStore(spark, str(tmp_path / "delta"))

    expected_rows = events.count()

    store.save(computed)
    assert store.exists()
    assert store.count() == expected_rows

    written = {r["event_id"]: r for r in computed.collect()}
    read_back = {r["event_id"]: r for r in store.list_all().collect()}

    assert set(read_back) == set(written)
    for event_id, original in written.items():
        restored = read_back[event_id]
        for field in CONTRACT_FIELDS:
            if field in _TIMESTAMP_FIELDS:
                assert _aware_utc(restored[field]) == _aware_utc(original[field])
            elif field in _FLOAT_FIELDS:
                if original[field] is None:
                    assert restored[field] is None
                else:
                    assert restored[field] == pytest.approx(original[field], abs=1e-12)
            else:
                assert restored[field] == original[field]

    store.save(computed)
    assert store.count() == 2 * expected_rows
