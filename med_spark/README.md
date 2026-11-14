# med_spark — additive PySpark + Delta Lake extension

This folder is additive. It does not modify or replace the v0 `med` package, its
SQLite store, or any tracked v0 file. The v0 pipeline remains the only place
where PAL is computed; this package calls it.

## Contents

| File | Purpose |
| --- | --- |
| `batch.py` | `compute_pal_events(events, bars, config=None)` — validates the input frames on the driver, then runs the v0 `Pipeline` once per scenario inside `groupBy("scenario").applyInPandas(...)` with an explicit 16-field schema. |
| `delta_store.py` | `DeltaPalStore(spark, base_path="data/delta")` — append-only Delta table; `created_at` is stamped at save time. |
| `demo_batch.py` | `build_spark()`, `scenario_frames(spark)`, `main()` — local batch demo over the v0 demo scenarios. |

## Behaviour

- Validation happens before anything is distributed. A null scenario,
  `event_id`, `ts_published` or bar `ts`; duplicate `event_id` values; more than
  one event row per scenario; and events/bars scenario sets that differ (either
  direction) each raise `ValueError` naming the offenders. Rows are never
  silently multiplied or dropped.
- The per-scenario computation calls the v0 `Pipeline` with `store=None`, so
  the SQLite path is not involved.
- The emitted 16 columns match the v0 SQLite contract; `created_at` is added by
  the Delta store.

## Running locally

```bash
pip install -r requirements-spark.txt   # Java 17+ required
python -m med_spark.demo_batch          # from the project root
```

`med` must be importable on every executor. Locally, run from the project root.
On Databricks serverless, use workspace files and absolute imports
(`med.pipeline`, `med.types`); relative imports are unreliable there.

## Databricks variant

On Databricks the session is already provided — do not build one with
`configure_spark_with_delta_pip` — and Delta is native to the runtime. Maven
coordinates (`spark.jars.packages`) are unsupported on serverless, so install
`delta-spark` from PyPI instead of passing coordinates.

## Status

The files are written but not yet executed. No parity result with the v0
pipeline is claimed here: `tests_spark/` holds the parity, cardinality and Delta
round-trip tests, and they have not been run.
