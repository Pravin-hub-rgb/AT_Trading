# ENTRY-TIME AUTOPSY — the one "signal" that survived is calendar time

Date: 2026-09-28. `exp_entry_time_autopsy.py`, `exp_swingno_time_check.py`
→ `_entry_time_autopsy.json`, `_swingno_time_check.json`. 48.7s + 48.6s.
Controls exact both eras.

## What was different about this run

Thirty-one closed rows in this repo are all the same shape: take the
shipped book, bucket it, notice a bucket differs, gray the other. **Nobody
had asked the prior question — is there any signal at all?** So this was
run as a diagnostic, with each feature explicitly tagged ENTRY-legal or
LEAK, before any gate was built.

The tag matters because of the M2 retraction: a feature that separates
without being causal shipped a false 4/4 once. Separability is necessary
and nowhere near sufficient.

## The tail is real and cleanly separated

| era | n | top decile median R | bottom decile median R | monsters ≥10R |
|---|---|---|---|---|
| IS | 500 | **+7.41R** | −1.00R | 17 |
| OOS | 279 | **+6.42R** | −1.00R | 6 |

## The finding: exactly one entry-legal feature separates, in both eras

| feature | AUC IS | AUC OOS |
|---|---|---|
| **`swing_no`** | **0.831** | **0.918** |
| regime_flip | — | 0.704 (OOS only → era-specific) |
| dir_long | 0.580 | 0.426 |
| bar_body/close_pos | 0.576 | 0.503 |
| hour | 0.472 | 0.432 |
| kind_b2 / kind_flip | 0.470 / 0.530 | 0.556 / 0.444 |

For calibration, the deliberately-leaky features (`_leak_r`,
`_leak_outcome_win`, `_leak_bars_held`) all score **AUC 1.0** — as they
must, since they read the answer. So the legal features are nowhere near
the trivial ceiling, and `swing_no` at 0.83/0.92 stands out sharply.

**This looked like the find of the session. It is not.**

## Why `swing_no` is not a signal

`swing_no` is a chain index, so it rises with wall-clock time. Measured
directly:

    corr(swing_no, calendar index) = +1.000   (IS)
    corr(swing_no, calendar index) = +1.000   (OOS)

**It IS time, exactly.** A gate on it is a disguised "trade only after
<date>", which is not deployable — nobody knows at the start of a sample
which half will be good.

Controlling for calendar position collapses the effect:

| | pooled AUC | within-calendar-decile AUC |
|---|---|---|
| IS | 0.831 | **0.613** (dec2) / **0.637** (dec8) |
| OOS | 0.918 | (n too small to bucket) |

**0.83 → 0.62.** The pooled number was inflated by the time trend.

The calendar profile itself explains nothing: median R is **−1.0 in every
single decile** in both eras (OOS dec5/6/7 at −0.57/−0.61/+0.06 is noise,
not a trend). So the effect is not "the market got better over time" in any
smooth sense.

What is actually happening: **the winners cluster in certain calendar
periods while the median trade is −1R everywhere.** That is a statement
about *when the market trended*, not about any individual trade's
entry-time properties.

## Verdict

- **`swing_no` is dead as a signal.** It is time, and the residual
  within-window effect (AUC 0.61-0.64) is weak and not a per-trade edge.
- **No entry-legal feature separates the tail beyond time.** Across nine
  candidate features — mark kind, regime channel, direction, bar shape,
  hour, weekend — nothing clears the bar in both eras.
- **This closes the filter search from the other end.** The prior 31 rows
  each showed a bucket that "looked" different. This shows that on
  entry-time information, **essentially nothing does.** The buckets that
  looked different in those experiments were measuring calendar and
  regime, not a trade-level property.

That is the most useful thing this session produced about the 15m book:
it is a **negative** result with a clean control, and it means further
entry-side filter search on this book has a low prior.

## Discipline notes

- **A control caught a real bug before any number was believed.** The
  first run printed MISMATCH on a perfectly healthy book because the
  reference +325.8R is NET and the harness sums GROSS (+445.2R). The
  check now asserts the trade COUNT and prints both figures.
- The `swing_no` result was deliberately **not** turned into a gate. The
  same reflex that built the M2 headline would have made "AUC 0.92, both
  eras!" the finding. Measuring what the feature *is* came first.
- A `NameError` in the report comprehension and a `_leak` scoping slip were
  both caught by running rather than reading.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
