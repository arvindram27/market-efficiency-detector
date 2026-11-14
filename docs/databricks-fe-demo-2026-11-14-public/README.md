# Databricks Free Edition demo (2026-11-14)

One-time validation run of the `med_spark` extension on a Databricks Free Edition serverless notebook. This folder is the identifier-sanitized public copy of the archival evidence. The raw originals (with the original identifiers) remain local and are excluded from the intended publication; publication has not happened.

## WARNING: archival reconstruction, not a runnable notebook
- The notebook here is a reconstruction, not a native Databricks export: the code cells are the exact imported source (with identifiers redacted) and the outputs were captured from the rendered notebook and embedded afterward.
- It was NOT executed after redaction, and the `<databricks-user>` placeholder paths are non-functional.
- Do not re-run the original notebook against its existing Delta path: the Delta cell appends rows before its count assertion runs, so on an existing table the write lands before the assert can fail, and the existing 6-row table persists.

## What ran
- Notebook `pal-dbx-fe-demo`, 6 cells (1 markdown + 5 code), Standard v2 / Python 3.11 serverless environment.
- Deps declared in the Environment side pane: `numpy>=1.26,<1.28`, `pydantic>=2.5,<3`, `vaderSentiment>=3.3.2`; the install resolved cleanly (numpy 1.26.4, zero resolver conflicts).
- One Run all after the dependency Apply: "Finished running 5 cells: 5 succeeded" (the 5 code cells).

## Results
- All 7 parity/raise lines PASS, exactly as in local `tests_spark/` runs.
- Delta round-trip preserved all 16 PAL contract fields x 3 synthetic rows.
- A second save of the same 3 events succeeded and the table then held 6 rows: the naive append duplicates records (not idempotent).
- Full stdout: `outputs.txt` (identifier-redacted capture; every result line and number unchanged).

## Honest scope
- Inline notebook asserts (mirroring tests_spark asserts), not a pytest run inside Databricks.
- 3 synthetic events; demo scale. Not scale/production proof; not real-market validation of PAL.
- Parity is internal to each environment. Databricks env: pandas 1.5.3, pyarrow 14.0.1, Spark 4.2.0. Local pins: pandas 2.3.3, pyarrow 26.0.1. No cross-environment compatibility is claimed.
- An earlier declared numpy range (`>=1.26,<3`) resolved to numpy 2.4.6 and the resolver reported conflicts with the environment's databricks-connect 15.4.26 (`<2`) and scipy 1.11.1 (`<1.28`). The declared range was tightened to `<1.28`; the install then resolved cleanly and the run passed.

## Redaction and provenance
- `pal-dbx-fe-demo-sanitized.ipynb`: derived from the archival reconstruction (exact imported source + captured stdout). Two kinds of changes only: (a) source-code identifier redactions - the author's email address in Databricks workspace paths replaced by `<databricks-user>` in 2 code cells and 1 embedded stdout line, no code logic changed; (b) one documentation-only warning added to the opening markdown cell (marked as added). All code and numeric results are otherwise unchanged. NOT executed after redaction.
- `outputs.txt`: the archival verbatim stdout capture with identifiers redacted only (email path, workspace URL/org id, notebook id); not executed afterward.
- `environment.txt`: byte-identical copy of the archival environment record (it contained no identifiers).
