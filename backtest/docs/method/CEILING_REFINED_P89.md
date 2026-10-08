# The ATR% ceiling, re-derived post-C17 — and the adaptive percentile, run for the first time

Date: 2026-10-08. Engine post-C17. Harness: `exp_ceiling_refined.py`.
Lanes: `champion_multi_sw10`, `utcsat_multi_sw10`. M = 193.4R.

## First finding: the whole ceiling chain was un-runnable

P69, P85, P87 and P88 all measured on pre-C17 pins. Every one of those harnesses
carries a hard control gate and today all four abort:

```
CONTROL FAILED champion_multi_sw10 is - STOP
```

The drift, against a ±1.5R tolerance:

| lane | era | harness asserts | registry now | net drift |
|---|---|---|---|---|
| champion | IS | 500t / +325.8R | 502t / +279.3R | **−46.5R** |
| champion | OOS | 279t / +70.1R | 287t / +63.4R | −6.7R |
| utcsat | IS | 453t / +279.5R | 462t / +321.4R | **+41.9R** |
| utcsat | OOS | 254t / +66.9R | 260t / +75.3R | +8.4R |

The 46.5R IS drift on the champion lane is larger than the entire effect the
ceiling was being studied for. Nothing downstream of P69 was trustworthy until
this re-derivation, and every number below is post-C17 with the control asserted
against the live registry pin.

## Second: P87 named its own next experiment and it was never run

P87's verdict says the obvious next move is "a pre-registered grid re-read" —
all four ceilings under P87's own instrument, because 0.40% was a peak of a
four-point grid and P69 never tested the family. That is now run.

## Third: the adaptive percentile is built here for the first time

Nemotron's PROPOSAL_CEILING_REFINED exists only inside a transcript pasted into
`NEXT_ROUND_BRIEF.md`. It proposes making the ceiling **regime-relative** — drop
the top X% of trailing ATR% within a trailing window rather than trades above an
absolute ATR% level — as the fix for P88's IS failure. No file, no harness, no
prior run. Its reasoning is sound: an absolute level drops a different population
depending on where volatility happens to sit, whereas a percentile always drops
the same relative population.

## Absolute ceiling, P69's grid, under P87's instrument

| ceiling | champ IS dNet | b | champ OOS dNet | b | utcsat IS dNet | b | utcsat OOS dNet | b |
|---|---|---|---|---|---|---|---|---|
| 0.30% | −122.3 | −0.13 | +10.2 | +1.48 | −97.0 | +0.52 | +2.3 | +1.66 |
| **0.40%** | **+2.9** | **+0.51** | **+33.2** | **+1.03** | **+9.8** | **+0.95** | **+20.4** | **+1.12** |
| 0.50% | +1.8 | +0.32 | +34.9 | +0.83 | −1.9 | +0.48 | +22.5 | +0.94 |
| 0.60% | −1.7 | +0.03 | +21.3 | +0.55 | +0.4 | +0.46 | +14.0 | +0.68 |

**Post-C17 the picture is materially better than P88 recorded.** 0.40% is now
positive in **all four cells** (+2.9 / +33.2 / +9.8 / +20.4), where P88 had IS
negative on both lanes. b is positive in 15 of 16 cells. That is a real change,
and it is entirely attributable to the base moving, not to the feature.

## Adaptive percentile — first run, ever

Drop the top X% of trailing ATR% within a 90-day window.

| keep ≤ pct | champ IS dNet | b | champ OOS dNet | b | utcsat IS dNet | b | utcsat OOS dNet | b |
|---|---|---|---|---|---|---|---|---|
| 60 | −64.5 | +0.37 | +14.2 | +0.68 | −27.6 | +0.97 | +18.2 | +0.84 |
| 70 | −47.4 | +0.25 | +11.9 | +0.64 | −33.2 | +0.64 | +8.3 | +0.64 |
| 80 | −4.2 | +0.54 | +0.5 | +0.29 | −2.2 | +0.81 | +1.8 | +0.43 |

**The proposal does not work, and it fails in-sample, which the absolute ceiling
no longer does.** Every percentile arm is negative in IS on both lanes.

## Why the percentile loses where the absolute level wins — this is the finding

| regime | n | champ IS abs@0.40 | champ IS pct@70 | mean R |
|---|---:|---:|---:|---:|
| low | 191 | +117.5 | +117.5 | +0.62 |
| mid | 155 | +142.1 | +134.2 | +0.87 |
| **high** | 155 | **+22.9** | **−19.4** | **+0.18** |

The whole difference is in the high-vol tercile. The absolute 0.40% ceiling keeps
67 of 155 high-vol trades and nets **+22.9R**. The percentile at 70 keeps almost
none of them and nets **−19.4R**.

**The absolute level is not dropping "high volatility" — it is dropping "volatility
above 0.40%, which in this data means high volatility in absolute terms only."**
In IS the high-vol tercile still contains profitable trades, and the absolute
level leaves most of them alone. The percentile always removes the top third of
whatever is currently volatile, so it removes a third of that tercile too, and
those were profitable.

OOS it inverts: the absolute level keeps almost nothing in the high tercile (0 of
65) and the percentile's −3.2R comes from a small residual.

> **An absolute ceiling and a relative one select different populations, and
> which one is right depends on whether the volatile trades are losing — which
> is P88's finding restated. The percentile does not fix that; it forces a
> fixed fraction out of every regime, including the ones where the volatile
> trades are fine.**

## Verdict

**Family FAILS. Nothing adopted.** No arm passes the pre-registered criterion in
even one cell — the criterion requires net better in both eras AND b > 0 AND all
three instruments agreeing in sign.

Three things worth keeping:

1. **P88's verdict was pre-C17 and is now partly superseded.** Post-C17 the
   absolute 0.40% ceiling is positive in all four cells. The family-wise failure
   recorded at P88 was measured against a base that had a 46R error in it.
2. **The adaptive percentile, run for the first time, does not fix the IS leg** —
   it makes it worse. Nemotron's reasoning was right about *why* an absolute level
   is fragile, but the replacement it proposed is worse, not better.
3. **A re-run is not a re-derivation.** Every ceiling result in the repo predates
   C17, and three of them would have reported different conclusions had the base
   been correct.

## Limitations

- **Both lanes are the same data.** Four cells across two correlated lanes is a
  pattern, not independence.
- The 90-day percentile window was fixed in advance and not searched. Varying it
  now would be a grid search on a family that already failed in both eras.
- The `b_boot_*` bootstraps are run at 2000 draws with cluster resampling and
  refitting; they inherit the assumption that the cluster is the unit of
  independence.
- The high-vol tercile OOS cell has 65 and 60 trades, so its per-cell numbers
  are noisy. The regime table is descriptive and is not itself a result.
- **The champion lane measured here is `champion_multi_sw10`, which is not the
  book being traded.** `fsent_champ_long` is a different book (528t/+533.4R IS).

**Nothing adopted. No book added, no pins changed, no registry entry touched.**