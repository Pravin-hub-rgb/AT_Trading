# CLUSTER-LEVEL AUTOPSY — `max_consecutive_losses=3` is a real peak, and the
# "predictability" test in this file was tautological.

Date: 2026-09-28. `exp_cluster_autopsy.py` → `_cluster_autopsy.json`
156.6s. Controls exact both eras (500t +325.8R / 279t +70.2R).

## What was new about this

Today's entry-time autopsy closed the per-trade view: nine features, one
separated, and it was calendar time. **Filters on individual trades are
done.**

This asks the question nobody has: what does the book look like as a
SEQUENCE. Two specific holes:

1. **`max_consecutive_losses=3` is a hard-coded constant** that has never
   been swept. The closed list says *relaxing* it is 0/4 — but the value 3
   itself was inherited, never chosen, and never tested.
2. **Nobody has measured whether losses cluster**, or whether a streak is
   preceded by anything knowable.

## Result 1 — k=3 is a genuine peak, not an inherited guess

| k | IS net | Δ | IS DD | OOS net | Δ | OOS DD |
|---|---|---|---|---|---|---|
| 0 (no halt) | +308.5R | −17.3 | 32.6 | +60.5R | −9.7 | 59.9 |
| 2 | +248.1R | **−77.7** | 42.7 | +69.2R | −1.0 | 39.6 |
| **3 (shipped)** | **+325.8R** | 0 | **27.7** | +70.2R | 0 | 53.2 |
| 4 | +296.8R | −29.0 | 36.9 | **+75.3R** | **+5.2** | 47.9 |
| 5 | +279.9R | −45.9 | 39.3 | +64.2R | −5.9 | 62.4 |
| 6 | +222.1R | −103.7 | 41.4 | +65.6R | −4.6 | 60.5 |
| 8 | +320.1R | −5.7 | 28.8 | +57.0R | −13.1 | 59.0 |

**IS: k=3 is the maximum, and it is a sharp peak** — k=2 is −77.7R and
k=6 is −103.7R. The curve is not monotone and not flat: 3 is a local
optimum with real curvature either side.

**OOS: k=4 is marginally better (+5.2R).** So the optimum is 3 in the long
era and 4 in the short one. **That is an era difference, not a win for k=4** —
+5.2R on 279 trades is inside the noise band, and switching to 4 on the
strength of it is precisely the "best-of" move this repo forbids. k=3
stands.

**Verdict: the shipped constant survives its first real test.** It was not
tuned, and it does not need retuning. That is a useful negative — it closes
the "maybe the constant is arbitrary" question that has been sitting
unasked.

Note the shape: relaxing the halt to 0 *adds* 57 trades (557 vs 500) and
still nets −17.3R IS, and k=8 also adds 45 trades for −5.7R. The halt
earns its keep on trade count alone, which is consistent with the closed
list's trade-expansion audit.

## Result 2 — my "predictability" test was tautological, and here is the proof

The run printed:

    P(loss | run just STARTED) = 100.0%   vs base 70.0%  -> PREDICTABLE
    a fresh loss run continues 0/98 times (0%)

That reads like a spectacular finding. **It is meaningless, and the
diagnostic is visible in the run itself:** LOSS runs and WIN runs printed
*identical* statistics —

    LOSS runs: n=98, mean 3.57, median 3, max 16, hist {1:32, 2:15, ...}
    WIN  runs: n=98, mean 3.57, median 3, max 16, hist {1:32, 2:15, ...}

Identical to the digit. **A run decomposition of a binary sequence always
alternates**, so "the run after a loss run is a win run" is a tautology, not
an empirical result. My conditional probability was measuring the
definition of a run-length encoding.

The same bug is why "a fresh loss run continues 0/98" is not evidence of
anything: consecutive runs *cannot* have the same label.

**This is recorded rather than quietly fixed** because the failure mode is
the one this repo cares about most — a number that looks like a discovery
and is arithmetic. The correct test is on the TRADE SEQUENCE, not the run
decomposition: P(trade N+1 is a loss | trade N was a loss) against the
unconditional base rate. That has not been run.

**So: is a loss run predictable at its first loss? UNKNOWN.** This file does
not answer it, and its printed "PREDICTABLE" must not be quoted.

## Result 3 — losses do not cluster by month

| era | months | loss share per month | sd | book base |
|---|---|---|---|---|
| IS | 45 | 0.720 | 0.173 | 0.700 |
| OOS | 24 | 0.723 | 0.146 | 0.720 |

Monthly loss share is flat and matches the book base rate in both eras.
**There is no "bad month" regime to gate on** — a month-level loss filter
has nothing to find. Run lengths (median 3 IS / 4 OOS, max 16 / 15) are the
only clustering structure present, and that is exactly what the halt rule
already handles.

## Verdict

- **k=3 confirmed.** First real test of the constant, and it holds. No
  change.
- **No monthly regime gate.** Losses are spread evenly across months.
- **Run-level predictability: open, and the test in this file is invalid.**
  The right test is trade-sequence conditional probability, which is cheap
  and still unrun.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
