# The four techniques, run on all five scorecard candidates

2026-10-16. Branch `research/four-validation-techniques`.

This exists because of the review in `METHODOLOGY_REVIEW_RESPONSE.md`, which
correctly identified that the four validation techniques had only ever been run
on the two candidates we had already picked. That is the shape of confirmation:
validate what you chose. 106, 108 and 109 were eliminated on net R and drawdown
without ever facing a walk-forward or a survivability test.

So the same battery now runs on all five. Nothing about the shortlist is assumed.

## Headline

**The shortlist was not wrong, but the reasoning behind it was incomplete.**

| | 107 | 110 | 106 | 109 | 108 |
|---|---|---|---|---|---|
| T1 sensitivity — span across grid, IS | **14.2R** | **234.4R** | 15.3R | 14.4R | **9.0R** |
| T1 span, OOS | 35.0R | **205.8R** | 34.1R | 36.6R | **18.4R** |
| T2 walk-forward, re-opt vs registered | wins 3/3 | **loses 3/3** | wins 3/3 | wins 3/3 | wins 3/3 |
| T3 break-even slippage, IS | ~105bps | **~135bps** | ~100bps | ~100bps | ~108bps |
| T3 break-even slippage, OOS | ~115bps | **~165bps** | ~105bps | ~115bps | ~103bps |
| T4 observed DD percentile, IS | 99.8 | 95.8 | 93.6 | 99.4 | **84.4** |
| T4 worst shuffled path, IS | **32.4R** | 34.9R | 35.2R | 44.0R | 39.7R |
| T4 paths breaching 25R, IS | **0.40%** | 2.80% | 2.25% | 2.90% | 3.45% |

**110 is the only candidate that fails a technique. The other four pass T1, T2
and T3, and all five survive T4 with zero paths past 50R.**

That is a real result and it cuts against the shortlist's framing: 110 was not
the "risky but smooth" alternative to a "robust" 107. It is the one candidate
whose parameter surface is demonstrably fragile, and the reason it was carried
was smoothness — which T2 shows is not compensating for that.

---

## T1 — parameter sensitivity

Two axes per book, fine grid, both eras.

| book | axis A | axis B | cells | IS span | OOS span |
|---|---|---|---:|---:|---:|
| 107 | `cooldown_bars` 2–16 | `exp_persist` 5–9 | 35 | 14.2R | 35.0R |
| 108 | `cooldown_bars` 2–16 | `exp_persist` 5–9 | 35 | **9.0R** | **18.4R** |
| 109 | `cooldown_bars` 2–16 | `exp_persist` 5–9 | 35 | 14.4R | 36.6R |
| 106 | `cooldown_bars` 2–16 | `exp_persist` 5–9 | 35 | 15.3R | 34.1R |
| 110 | `exp_trail_skip_n` 0–16 | `exp_persist` 5–9 | 55 | **234.4R** | **205.8R** |

110's span is roughly **15× any other book**. Its `exp_trail_skip_n` runs from
+498R to +733R on IS and +155R to +361R on OOS depending only on the value
chosen, and the two eras invert at the top of the range: IS keeps improving to
skip_n=16 while OOS falls to its worst there. That inversion is what T2 then
finds again, independently.

**108 is the flattest of all** — 9.0R of span on IS and 18.4R on OOS across 35
cells. It was never given credit for this, because it was eliminated on net R
and ulcer before anyone looked.

**The caveat the review raised applies here.** `cooldown_bars` and
`exp_persist` were classified as signal filters and turned out to be nearly
inert — four of the five books barely move when either changes. So the flat
result for 107, 106, 109 and 108 is *partly* a statement about which knobs were
chosen, not purely about the books. The one book with a load-bearing unique
knob, 110, is the one with a cliff. That is suggestive, not conclusive, and the
structural parameters (`mode`, `htf_rr`, `max_positions`) still have no cliff
test on any book.

## T2 — walk forward, re-optimising

Three folds over IS. Train grows, the winner is scored blind on the next window,
and the registered value is scored on the same window for comparison.

| book | fold 1 | fold 2 | fold 3 | verdict |
|---|---|---|---|---|
| 107 | +94.0 vs +91.0 | +99.3 vs +98.4 | +194.2 vs +191.4 | re-opt wins 3/3 |
| 106 | +181.0 vs +172.6 | +90.0 vs +89.7 | +173.7 vs +167.4 | re-opt wins 3/3 |
| 109 | +175.2 vs +168.1 | +94.9 vs +93.9 | +189.0 vs +182.8 | re-opt wins 3/3 |
| 108 | +150.0 vs +140.4 | +101.1 vs +101.0 | +197.9 vs +195.6 | re-opt wins 3/3 |
| **110** | **+34.6 vs +94.1** | +106.0 vs +106.8 | +212.2 vs +219.5 | **re-opt loses 3/3** |

Every fold of 110 selected `skip_n=16, persist=8` — the IS-optimal, OOS-worst
combination — and every fold returned less than simply not tuning. Fold 1 loses
**59R**. For the other four books the re-optimised cell is slightly *better*
than the registered one on every fold, which is what a flat surface looks like.

**106, 109 and 108 produce more trades per fold (175–192) than 107 does
(125–145)**, so this is not a sample-size advantage for the older candidates.

## T3 — stress, engine-level stop slippage

Net after adverse slippage on the exit fill, all four stop/trail sites.

| book | @0 | @50bps | @100bps | @250bps | break-even IS / OOS |
|---|---:|---:|---:|---:|---|
| 107 | +538.4 | +279.6 | +32.9 | −682.3 | ~105 / ~115bps |
| **110** | **+644.0** | **+467.0** | **+261.7** | **−267.1** | **~135 / ~165bps** |
| 106 | +757.0 | +344.6 | +11.8 | −919.0 | ~100 / ~105bps |
| 109 | +764.9 | +342.7 | +11.9 | −952.7 | ~100 / ~115bps |
| 108 | +771.9 | +387.2 | +55.2 | −869.8 | ~108 / ~103bps |

**110 tolerates the most execution friction, by 30–50bps.** This is 110's one
genuine win and the mechanism is coherent: its trades run longer and exit on
trail rather than stop, so there is more room between entry and the adverse
fill.

Slippage also removes trades, which post-hoc cost stress structurally cannot see:
at 1000bps the books lose 33–40% of their trade count, because a worse exit
pushes a stop past the `ext_stop_r` admissibility test at entry.

## T4 — survivability

2000 shuffles of each book's own trades, both eras.

| book | era | observed DD | its percentile | p50 | p95 | worst | worst streak | paths >25R |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 107 | IS | 28.38 | 99.8 | 12.6 | 19.1 | **32.4** | 22 | **0.40%** |
| 107 | OOS | 11.05 | 71.2 | 9.6 | 14.7 | 29.7 | 26 | 0.05% |
| 110 | IS | 23.93 | 95.8 | 15.1 | 23.1 | 34.9 | 25 | 2.80% |
| 110 | OOS | 14.90 | 66.7 | 13.3 | 21.3 | 36.0 | 23 | 1.70% |
| 106 | IS | 22.45 | 93.6 | 15.3 | 23.0 | 35.2 | 25 | 2.25% |
| 106 | OOS | 14.74 | 78.4 | 12.1 | 19.1 | 32.4 | 24 | 0.40% |
| 109 | IS | 29.76 | 99.4 | 15.5 | 23.3 | **44.0** | 24 | 2.90% |
| 109 | OOS | 14.74 | 80.9 | 11.8 | 17.9 | 29.1 | 24 | 0.15% |
| 108 | IS | 20.02 | **84.4** | 15.5 | 23.9 | 39.7 | 28 | 3.45% |
| 108 | OOS | 15.04 | 72.5 | 13.0 | 19.8 | 29.2 | 25 | 0.60% |

**No book has a ruin tail.** Zero of 2000 orderings exceed 50R on any of the
five, in either era.

Two observations worth keeping:

- **107's ordering is the unluckiest of the five** at the 99.8th percentile,
  yet it has the *tightest* bad-ordering tail (0.40% above 25R). Unlucky
  ordering and dangerous ordering are different properties, and 107 is unlucky
  without being dangerous.
- **108's observed drawdown is the most typical** of the five (84.4 percentile)
  — the least flattering and most representative single number here.

This is the i.i.d. shuffle. The block bootstrap in `MONTE_CARLO_SURVIVABILITY.md`
roughly doubles the worst-case drawdown, and both views are reported there.

---

## What this changes

**It weakens the case for 110 substantially.** It was carried as the smooth,
higher-expectancy alternative. T2 shows re-optimising it loses to not
optimising it on all three folds, and T1 shows its parameter surface spans 15×
more than any other book with a genuine cliff and an IS/OOS inversion. The
smoothness that justified carrying it does not compensate for that, and T3 — the
only technique it wins — is a margin of 30–50bps of slippage that may or may not
be consumed by real fills.

**It leaves 106, 108 and 109 exactly where the review says they were: untested
by the right question until now, and now tested.** They pass T1, T2 and T3.
They are not promoted, for a reason that has nothing to do with this battery:
they overlap each other by 85–93%, so they are one bet wearing three names, and
`exp_concentration.md` shows all three share the same December 2023 profile. If
106/108/109 is the answer, then so is "the htffs family", and that is a smaller
claim than three independent candidates.

**It does not settle anything on its own.** The review's central point stands:
all five were already on the scorecard, so running a battery on all five does
not address whether the shortlist should have contained other books at all.
Eight of thirteen multi books were never measured.

## What is still open

| question | status |
|---|---|
| Are 107 / 110 the right pair from all 13 multi books? | **still unanswered** — needs the battery run on the other 8 |
| Selection-bias correction across the full universe | **not attempted** — the largest genuine gap |
| Structural parameters (`mode`, `htf_rr`, `max_positions`) cliff test | **not done** on any book |
| Execution delay, 2020 crisis, market-path Monte Carlo | **not done** |
| 107 vs 110 head-to-head under identical capital | done on both, but 110 now has a T2 failure against it |

## Reproduction

```
exp_four_techniques.py t1   # 2-axis sensitivity, 35-55 cells per book
exp_four_techniques.py t2   # re-optimising walk-forward, 3 folds
exp_four_techniques.py t3   # engine-level slippage sweep
exp_four_techniques.py t4   # 2000 shuffles per book per era
```

Raw: `four_techniques_t1.json` … `four_techniques_t4.json`.

One note on how this was first run: all four techniques were launched
concurrently against a single `four_techniques.json`, and each one read it,
added its key and rewrote it. The result was that three of the four books'
results were lost between processes. Output is now split per technique, and the
affected techniques were re-run sequentially. Recorded because the surviving
numbers looked complete throughout — nothing errored, the JSON was valid, it was
simply a different book's results each time you looked.