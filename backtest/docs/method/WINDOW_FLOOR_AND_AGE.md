# Window floor (raised), and W1 — is window age a feature?

Date: 2026-10-10. Harness: `exp_window_age.py`.

Two items the cycle left open. The floor sweep had been run and its result lost to
a bug hunt that turned out to be my own false claim; W1 is the queue's own open
question about window duration.

---

# 1. The window floor — raised only

With the causality question settled, the floor's legal direction is **up**.
Raising it waits longer before a new window is tradeable and cannot admit anything
the causal gate rejected.

| floor | `champ_long` | neg | `mcloff` | `mcloff_htf15` | `sig_multi` |
|---:|---|---:|---:|---:|---:|
| **2700 (shipped)** | +773.0 | **2025-H1** | +837.5 | +893.5 | +696.2 |
| 3600 | +778.7 | 2025-H1 | +841.7 | +895.8 | +687.0 |
| **5400** | **+780.6** | 2025-H1 | **+841.2** | **+896.0** | +686.1 |
| **7200** | +778.7 | **NONE** | +835.0 | **+897.1** | +697.5 |
| 10800 | +741.6 | NONE | +811.9 | +879.0 | +671.3 |
| 14400 | +743.0 | NONE | +806.9 | +863.3 | +630.1 |

**The shipped 2700 is slightly too tight, not too loose.** Every book gains R up
to 5400 — `champ_long` +773.0 → +780.6, `mcloff` +837.5 → +841.2,
`mcloff_htf15` +893.5 → +896.0 — then declines. Past 10800 all four are clearly
worse, so 5400 is the peak and 7200 is the far side of it.

**Two things worth separating.** The first few hundred seconds of a window are
where the signal is least formed, and waiting them out is worth roughly +7R on the
champion for **18 fewer trades**. That is a real, cheap improvement and it needs no
new idea.

**But only `champ_long` has a negative cell to fix, and it needs floor 7200** — at
which point the net has already started falling. The other three were clean at
2700 and stay clean. So the floor's value as a *negative-cell fix* is confined to
the one book whose cell `max_consecutive_losses=0` already fixes for free.

**The honest reading: the floor is a small, legitimate refinement (+5 to +8R), and
it is not the answer to the negative-cell problem.** It was nearly presented as the
answer by an earlier version of this work, on the strength of a 900-second
misreading. It is not.

---

# 2. W1 — is window age a feature?

The queue's own falsifier: *a median age shift with no change in realised R means
age is not a feature.* So the test is whether splitting trades by window age
changes realised R.

**Median window age at entry is 2.2–2.4 days on every book** — that part is flat.
The R per trade is not.

| age bucket | `champ_long` | `mcloff_htf15` | `sig_multi` |
|---|---:|---:|---:|
| 12–36h | **1.455** | **1.820** | 0.526 |
| 36–96h | 0.898 | 1.025 | 1.545 |
| 96–240h | 1.274 | 1.369 | 1.084 |
| 240h+ | 1.051 | 1.150 | **4.465** |
| win rate, 240h+ | 41.2% | 40.2% | **58.2%** |

## the finding, and why it is not yet a lever

**The direction is opposite between the families, and that is the finding.**

The champ books earn most from **young** windows (1.455 and 1.820 R/trade in the
first 36h, their worst cells are the middle). The sig book earns almost nothing
there — 0.526 R/trade — and its best cell is the **oldest** bucket at **4.465
R/trade on 58.2% win rate**, roughly 3× its own average.

**Age moves R a lot. But it moves it in opposite directions, so there is no single
rule to extract.** A filter "trade young windows" helps the champ books and would
destroy `sig_multi`; "trade old windows" does the reverse.

**And the honest caveat, which is the reason this is not a candidate:** the
`sig_multi` figure rests on **55 trades**. A 4.465 R/trade bucket on n=55 has a
standard error of roughly 0.9R per trade, so the true value could plausibly be
2.5 or 6.5. Picking it out of a 4-bucket table I chose myself is exactly the
selection pressure this project keeps getting burned by — `biasmom05` is the
record of what that costs.

## what would settle it

The queue asked whether age is a feature and, in effect, answered: **yes, strongly
and family-specifically.** What it did not do is produce a lever that survives
both directions.

Three things would need to hold for an age filter to be adoptable:

1. **the effect is not a small-sample artefact** — the 240h+ bucket needs the same
   treatment `mcloff` got: re-derive, then a period control on it, the way
   `biasmom05` was killed.
2. **the buckets are pre-registered, not chosen after seeing the table.** Four
   buckets on a log-ish scale is a reasonable prior, but it was chosen after the
   result existed here.
3. **the direction holds out of sample**, which means forward data, not 2021-22.

**Until then this is a documented observation, not a book.**

---

# 3. Queue updates

| item | before | now |
|---|---|---|
| `P4 — sweep cap_days` | `[ ]` open | **closed** — swept 3/7/10/14/21; 21 clears the negative cell, and see the floor row above for the adjacent question |
| `W1 — window duration` | `[ ]` open | **answered, not closed** — age is a feature, direction is family-specific, effect not yet reliable enough to build on |

---

# verification

| check | result |
|---|---|
| `exp_window_age.py` | 24 floor arms + 4 age profiles, progress-barred |
| floor direction | raised only; lowering is a lookahead and was not run |
| causality | `exp_decision_instant.py` — 0 real violations across 8 books |
| pins | unchanged; no book was modified |

*Shipping book unchanged: 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS,
one negative half-year, window floor 2700 untouched.*