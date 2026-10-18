# Breakeven and trail — removing the choice instead of predicting it

## The knife-edge this is meant to escape

The `htf_rr` sweep landed on its own break-even:

```
extension rate, measured   79% ......... 97%
break-even extension rate                80%   ^^^^^^
```

A parameter sitting there gives opposite answers in two markets for no
structural reason, and no predictor can repair it because the population
changed rather than the trades. Eight candidate signals were tested; all
eight flipped between eras. That is what a knife-edge does to anything
applied to it.

`htf_rr` welds two decisions: how far to aim, and what happens on failure.
The stop is the swing start, so failure costs full risk and 4R needs to
happen about 80% of the time to break even. That 80% is the fragility.

`breakeven_r` at `v7_timecap.py:119` already existed and was hardcoded to
0.0 at every call site. With the stop at entry a failure costs 0R instead of
-1R and the required carry rate falls toward zero. The decision stops
mattering because the downside stops existing.

This is the only option tested so far that requires **no prediction**, which
is also why it can work at an effective sample size of two books and two
eras. It is not automatically better — breakeven converts some genuine
winners into scratches, and a swing trail gives back part of the run.

## Aggregate net R across eight books

### htf_rr=3, trail=off

| breakeven_r | sum IS | sum OOS | beats shipped in both |
|---|---:|---:|---|
| off (shipped) | +4851 | +2251 | - |
| 0.5 | +3508 | +1718 | no |
| 1 | +3864 | +2225 | no |
| 1.5 | +4157 | +2283 | no |
| 2 | +4868 | +2207 | no |

### htf_rr=3, trail=swing

| breakeven_r | sum IS | sum OOS | beats shipped in both |
|---|---:|---:|---|
| off (shipped) | +3224 | +1494 | - |
| 0.5 | +2524 | +1348 | no |
| 1 | +2778 | +1567 | no |
| 1.5 | +2728 | +1623 | no |
| 2 | +2780 | +1551 | no |

### htf_rr=4, trail=off

| breakeven_r | sum IS | sum OOS | beats shipped in both |
|---|---:|---:|---|
| off (shipped) | +4518 | +2526 | - |
| 0.5 | +3552 | +1847 | no |
| 1 | +3718 | +2279 | no |
| 1.5 | +3959 | +2317 | no |
| 2 | +4597 | +2347 | no |

### htf_rr=4, trail=swing

| breakeven_r | sum IS | sum OOS | beats shipped in both |
|---|---:|---:|---|
| off (shipped) | +3224 | +1494 | - |
| 0.5 | +2524 | +1348 | no |
| 1 | +2778 | +1567 | no |
| 1.5 | +2728 | +1623 | no |
| 2 | +2780 | +1551 | no |

### htf_rr=5, trail=off

| breakeven_r | sum IS | sum OOS | beats shipped in both |
|---|---:|---:|---|
| off (shipped) | +4816 | +2378 | - |
| 0.5 | +3389 | +1774 | no |
| 1 | +3718 | +2223 | no |
| 1.5 | +3911 | +2288 | no |
| 2 | +4562 | +2242 | no |

### htf_rr=5, trail=swing

| breakeven_r | sum IS | sum OOS | beats shipped in both |
|---|---:|---:|---|
| off (shipped) | +3224 | +1494 | - |
| 0.5 | +2524 | +1348 | no |
| 1 | +2778 | +1567 | no |
| 1.5 | +2728 | +1623 | no |
| 2 | +2780 | +1551 | no |

---

## Reading it

The comparison that matters is not breakeven against off at the same
target. It is **best breakeven + trail at any target** against **the
shipped configuration**, because the whole claim is that removing the
downside beats picking the right target.

If breakeven wins in both eras, the recommendation is structural rather
than numerical: the target stops being a lever that has to be guessed, and
the knife-edge that made `htf_rr` look regime-dependent disappears. If it
only wins in one, it is the same knife-edge wearing a different hat and the
answer is still to freeze at the shipped configuration.

Nothing here is adopted regardless. This changes the risk profile of every
book and would need the same battery re-run before anyone considered it.
