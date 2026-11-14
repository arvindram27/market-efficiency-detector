# mt1: retrospective candle timing study

An isolated research module in the MED repository. It studies whether complete
candles form a five-candle streak near a fixed, retrospective reference price.
It does not identify a true efficient price or estimate a verified live alert time.

The repository's existing `med/` and `med_spark/` are the legacy PAL vertical slice.
This folder is a separate versioned study, not a silent correction or replacement
of their output fields. Legacy FAST/NORMAL/SLOW/INCONCLUSIVE classes are not mt1
outcomes. The root README describes that legacy slice. Read this folder's method
and limits when discussing mt1.

## Run a made-up example

From the repository root, using an existing Python 3.11+ interpreter:

```text
cd research/mt1
python -B synthetic_demo.py
python -B -m unittest tests_timing.test_mt1 tests_spark_review.test_transport tests_spark_review.test_demo -v
```

No dependency install, API key, market-data account, network call, private fixture
or file output is needed. All demo candles are made up deterministically in memory.
Synthetic timestamps and the all-zero input digest label a made-up study; they are
not historical provenance. The supplied tests use both synthetic paths and unit
vectors. The commands print JSON or test output only.

These commands are documentation for later use. Adding this folder does not itself
run them, start Spark, install packages, commit or publish anything.

The three example cases illustrate:

- `stable`: no price-move trigger, but a confirmed reference-band streak. The axes
  are independent. Candidate/fifth-candle close delays are 60/300 seconds, while
  the full-study close-based information bound is 90 minutes.
- `no_streak`: no qualifying five-candle streak by the fixed horizon, with null
  pattern coordinates and delays.
- `missing_reference`: reference coverage is missing; the interval is not shortened
  and no reference/stabilization value is invented.

Every example keeps actual provider arrival and event receipt unknown. No example
turns a candle-close lower bound into actual alert availability.

## What is implemented

- Plain Python immutable input types, deterministic validation and exact result
  fields under `med_timing/`.
- Complete-candle, half-open boundaries; separate pre/move/observation/reference
  grids; explicit coverage and unknown information status.
- A bounded, versioned JSON codec and explicit nested PySpark schema under
  `med_timing_spark/`.
- A lazy regular non-Arrow Python UDF adapter that calls the **same Python
  evaluator** once per input row as Spark schedules it. Spark can retry or recompute
  a UDF; no exactly-once guarantee is made.
- Synthetic unit/transport tests and four opt-in actual Spark integration tests.

## Spark use and honest scope

`apply_studies(frame)` accepts a StringType `wire_json` column containing one study
and its candles. `encode_study(study, bars)` creates that bounded wire value.
The returned `mt1` column is an envelope with `schema_version`, `result`, `errors`.
Successful results preserve the complete original mt1 record under `result`.
Validation and malformed-wire errors are distinct, not negative-study outcomes.
Timestamps remain UTC ISO strings rather than native Spark timestamps, avoiding
session-timezone reinterpretation. No arrival or receipt is inferred from retrieval.

This is Spark execution/serialization support, **not an independently implemented
Spark numerical algorithm**. It is not candle-level distributed math, a scale test,
a throughput benchmark, or a production data pipeline. Per-row caps are 10,000
candles and 8 MiB wire text, not a performance guarantee.

An already-available compatible PySpark/Java runtime and importable driver/worker
source are required for actual Spark use. No runtime or dependency setup is done by
this folder. The API uses `useArrow=False` (PySpark 3.5+ surface); only the versions
in [verification](docs/verification.md) were actually exercised.

The opt-in synthetic Spark suite is `tests_spark_review.integration_spark`. Its
`main()` creates a local session and performs actions. It is deliberately outside
normal test discovery. Do not treat the pure tests as proof these Spark tests ran,
or the documented command as permission to start a new run:

```text
python -B -m tests_spark_review.integration_spark
```

## Documents

- [Method and timestamp meaning](docs/method.md)
- [Verification scope](docs/verification.md)
- [Limits, data boundaries and safe claims](docs/limits.md)
- [File inventory](MANIFEST.json)

The code/tests were packaged for review without private provider inputs, derived
real-market records, adapter-specific raw-file pins, credentials, host paths or
execution wrappers. The manifest covers this folder's other supplied files.
