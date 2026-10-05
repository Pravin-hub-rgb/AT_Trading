# P27 — the STACK, scored with a paired test. The #1 candidate was never scored right.

`exp_stack_paired.py`. Three lanes, both eras, **all six pins exact**.

## Two things I had wrong

**1. I wrote that the exit family was closed.** `method/SMOOTH_BOOK.md` says
*"the entire exit family is closed — trail/half/delay/tighten/partial are
all rejected"* and sends the reader to entry filters instead. That is
**false**. `exp_trail_half` + `exp_trail_delay_r` + `exp_skip_decisive` is
the largest documented improvement in the repo, log 113 reproduced it
24/24, and checklist 24.24 passed a retroactivity audit. Six entry-side
experiments then produced nothing that cleared a bar, and I concluded the
grid was exhausted. **The grid was not exhausted; I was only looking at one
end of the book.**

**2. `method/BASE_BOOK_NULL.md` used the wrong test for it.** It scored +103.8R
against `M` = 479.9R and called it "inside the null". But `M` bootstraps
the book's own **level**, which answers "is this book distinguishable from
a reshuffle of itself" — not "did this change help". A change like this is
a **paired** before/after on largely the same trades, and the book-level
variance that makes `M` 480R wide cancels in the pairing.

## The right test

    d[i] = r_stack[i] - r_baseline[i]     for trades in both books

Move-block bootstrap the **differences** (block 20, 10,000 draws — the
same blocking that made P5 defensible), and ask
`p = P(sum(d*) >= sum(d))`.

## Result

| lane | era | STACK dNet | **exit-only** (shared) | **count effect** | p |
|---|---|---|---|---|---|
| champion | IS | +103.8R | +75.2R | +28.6R | 0.364 |
| champion | OOS | +40.9R | +12.7R | +28.1R | 0.387 |
| utcsat | IS | +52.2R | +45.9R | +6.3R | 0.387 |
| utcsat | OOS | +34.9R | +9.3R | +25.6R | 0.282 |
| age10 | IS | −13.4R | **+34.8R** | **−48.2R** | 0.234 |
| age10 | OOS | **−43.5R** | −15.7R | **−27.9R** | 0.777 |

**No cell clears p<0.05.**

## Three things this says

**1. Most of the headline is count, not exit.** In OOS the count effect is
the larger half on both multi lanes (+28.1R, +25.6R vs +12.7R, +9.3R). And
`skip_decisive` — which supplies that count effect — is a **perfect IS
no-op** (0 decisive trades in 2023–26). Its entire evidence is the **57
OOS trades** it removes.

**2. On age10 the exit rule genuinely helped and the count effect destroyed
it.** `half+delay1` made the shared trades **+34.8R better**; the final
number is still −13.4R because `skip_decisive` deleted **+46.2R** of
winners. OOS it is the same story: 30 trades, **+31.0R** of winners
removed, which is the −43.5R.

**3. `half+delay1` alone is consistent on multi and inconsistent on
single.** champion IS +429.6R / OOS +90.3R, utcsat IS +411.1R /
OOS +87.6R — all four improve. age10 IS −13.1R, OOS −15.7R — both
degrade. This is the same multi-vs-single split the master table records
at `method/MASTER_CANDIDATES_V2.md:177`.

## Caveats

1. **The paired test is new.** It is the right shape for this question and
   it is stated in full, but it has not been through the same usage as `M`.
2. This does **not** say `half+delay1` is worthless — it says its edge is
   not separable from noise at this sample size, and that the documented
   +103.8R is roughly half count-selection on 57 OOS trades.
3. `skip_decisive` is the component to interrogate first, and it is a
   single-book n=57 claim.
4. **Nothing adopted.** No production change.
