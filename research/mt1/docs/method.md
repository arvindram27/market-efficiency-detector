# Method and timestamp meaning

## Fixed prototype parameters

| Parameter | Value |
| --- | --- |
| Candle interval | 60 seconds |
| Pre-event reference scale | 60 complete pre candles, giving 59 log returns |
| Move interval | 300 seconds after publication |
| Observation interval | 5,400 seconds after publication |
| Reference interval | [publication + 4,200s, publication + 5,400s) |
| Reference price | Median close of all complete reference candles |
| Trigger threshold | Strict absolute z greater than 2.0 |
| Stability band | Inclusive absolute close distance at most 0.5 * pre-return sigma * reference price |
| Required streak | 5 consecutive complete observation candles |

These parameters are fixed prototype values, not empirically calibrated constants.
The reference is known retrospectively. A reference-band streak does not establish
that information has been fully absorbed or that a price is economically efficient.

## Boundaries and separate outcomes

Candle timestamps label opens on a UTC epoch-minute grid. A candle is included in a
role only when its entire [open, close) interval is contained in that role's window.
Pre candles must close at or before publication. For an event inside a minute, the
straddling candle is excluded and the lost pre/post seconds are recorded. The move
window then contains fewer than five complete candles; the study does not silently
extend the 300-second interval. The same fixed containment rule applies to the
observation/reference windows.

Observation and reference intentionally overlap: the reference uses the last 20
complete candles in the fixed interval for a minute-aligned publication. A missing
reference candle makes the reference unavailable; no partial median or shorter
window replaces it. Missing pre coverage does not produce a partial sigma. A missing
observation candle does not produce a shortened search.

The gate, reference, coverage, stabilization and information axes are independent.
A gate failure does not erase an otherwise confirmed reference-band streak. A gate
failure also does not prove no price response occurred. Zero or unavailable pre
scale is distinct from a small price move. Structural invalidity produces a
validation-error envelope, not a successful record with a negative classification.

For supported inputs the gate uses the largest absolute standardized log move
within the complete-candle move grid, relative to the last pre close. Headline
classification preserves the reviewed deterministic keyword ordering/substring
rules. It is a heuristic, not a learned or verified interpretation of market news.

## Candidate time, confirmation time and availability

If a streak exists, its first and fifth candle opens/closes are separate fields.
Candidate and confirmation delays are measured from publication to the relevant
candle close. They are pattern coordinates in a retrospective study, not live
reaction or alert latency. If no streak exists, the coordinates/delays stay null.

The complete result depends on pre, move, observation and reference inputs. Its
close-based lower bound is the latest required candle close, typically publication
plus 90 minutes for minute-aligned complete data. Early pattern coordinates do not
make the retrospective reference or complete result available earlier.

Actual result availability is recorded only if event receipt and every required
bar's recorded availability exist. Then their maximum is used. One unknown receipt
or required bar arrival keeps actual availability null. Retrieval time and candle
close do not fill those gaps. Unknown historical information is explicit.

## Spark boundary

The wire codec checks exact field sets and caps, reconstructs Study/Bar objects and
calls the unchanged evaluator. The adapter schema uses strings for UTC ISO times,
nullable numeric/time fields, nonnull array elements and explicit nested records.
Integer values in double-valued output positions are converted to finite doubles.
Schema drift raises rather than silently dropping fields. Malformed-wire errors
carry a fixed error code without echoing payload/exception contents.

The Spark UDF and plain Python path share one evaluator. Agreement demonstrates
transport behavior in the tested environment, not a second mathematical opinion.
