# Limits, data boundaries and safe claims

## Safe engineering description

"Built a separate complete-candle retrospective timing-study module with explicit
coverage and unknown-availability fields, deterministic validation, synthetic tests
and an explicit-schema PySpark transport adapter. Checked exact shared-evaluator
output preservation through local Spark."

This is suggested wording for review, not permission to change a resume, send a
message, edit a profile, commit, push or publish. Scope and actual contribution must
remain accurate in the final destination.

Do not claim:

- A validated market-efficiency/inefficiency detector or a true efficient price.
- Causal news absorption, calibrated thresholds, profitable signals or trading use.
- Second-accurate live latency when historical receipt/arrival is unknown.
- Independent Spark-native numerical implementation, candle-level distributed
  computation, scale/throughput or production readiness.
- Databricks verification of mt1. The repository's earlier Databricks demonstration
  concerned the separate legacy extension; no such mt1 run is established here.

## Private and excluded

This folder contains made-up candle generation only. Provider raw candles,
provider-derived result records, private replay files, input-specific adapters,
credentials, local execution wrappers, host paths and private audit artifacts must
not be added. No redistribution permission for provider-derived inputs/results is
established by access to them or by a test passing. New use/publication would need
current terms checked for that audience/content and separate explicit approval.

The source uses a test headline and synthetic timestamps in unit cases; that is not
provider data or a reconstruction of a real market path. The demo itself labels
made-up provenance and unknown arrival/receipt rather than manufacturing history.

## Change boundaries

mt1 lives in this isolated folder. No legacy module, legacy 16-field schema, root
README, package configuration, app UI or earlier evidence is replaced. Root test
and install commands do not automatically discover/run this isolated folder; use
its explicit commands. This avoids accidentally presenting changed semantics under
an old command. A future top-level navigation/packaging change needs its own diff.

After the completed private end-to-end check, more events/runs are not prerequisites
invented for this packaging milestone. The next finishing action is review of this
additive source/docs patch. Copying it into a local checkout is separate from a
commit, push or public portfolio update. Those later actions remain separate gates.
