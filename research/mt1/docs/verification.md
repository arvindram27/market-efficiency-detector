# Verification scope

## Evidence completed before packaging

The development record includes:

- 49 plain Python synthetic tests of the fixed mt1 result and validation contract.
- 17 pure wire/transport tests, including all-field comparison across 19 synthetic
  cases with positive/negative/missing-data/invalid-input/unknown-arrival cases.
- Four actual local Spark synthetic integration tests. They checked the explicit
  full nested schema, exact result envelopes over 1 and 3 partitions, timezone
  invariance (UTC, Asia/Kolkata, America/New_York), null/empty inputs and column
  validation. Passed test IDs, schema and source inventories were checked against
  the reviewed source after the reported execution.
- One private existing-fixture end-to-end composition through the same adapter. The
  Spark record matched the preserved Python record byte-for-byte. Private inputs,
  provider-derived outputs, their numeric results, raw-specific adapter and host
  wrappers are intentionally not in this folder. This is a scoped engineering
  observation, not a public dataset/reproduction claim or economic validation.

The actual Spark checks used Python 3.13.18, PySpark/Spark 4.2.0, Java 17.0.21,
pandas 2.3.3, pyarrow 26.0.1 and delta-spark 4.4.1 already present in the tested
runtime. The adapter uses a regular non-Arrow UDF. It does not configure Delta,
install packages or resolve Maven dependencies. No cross-version/platform or
cluster compatibility guarantee follows from one local runtime.

## Packaging checks

This folder adds four synthetic-demo checks to the original 49 + 17 pure checks:
70 pure tests in total. These do not start Spark or use market data. Packaging did
not repeat the actual Spark or private-data runs. The original evaluator, Spark
adapter/schema and earlier test logic remain unchanged; the opt-in Spark module docstring was
updated to replace stale pre-execution review wording.

The four actual Spark test methods remain supplied separately and opt-in. A pure
suite PASS is not an actual Spark PASS, and all counts here describe different
scoped suites. Do not sum test counts across repeated runs and call that many
unique tests. A future fresh environment needs its own actual runtime verification.

## Reproduction boundary

The public-facing source can reproduce the made-up demo and synthetic tests using
an appropriate existing environment. It cannot reproduce private provider data or
claim that unavailable raw data/actual arrival history is included. Successful
transport checks do not validate a true efficient price, causal effects, market
predictability, profitability or a live decision system.

This is a research module: there is no production ingestion, monitoring, SLO,
security review, cost model, native distributed algorithm or scale benchmark here.
