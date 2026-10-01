# FS-ENTRY RISK CONTROL — the user was right, and the claim needed qualifying

The user caught a real confound in `FS_ENTRY.md`:

> "SL kaha par place hai original pe woh toh lowest of the swing toh big
> swing ke liye bahut badha hoga, toh half of the swing rakhe toh?"

Correct. The original stop for a long sits at the swing's LOW. By the time FS
confirms, price has moved away from it, so `|fs_close − sl|` **grows with
swing size**. R divides by that risk, so a big swing shows a smaller R for an
identical price move. The earlier "big swings are worst" was partly measuring
my own stop placement, not the swing.

## Four measures, only one of which is stop-free

| measure | risk denominator | stop-dependent? |
|---|---|---|
| **% move** | none | **no — the clean one** |
| R fixed | 1.0 × ATR15 | yes |
| R half (user's suggestion) | swing midpoint | yes |
| R orig (earlier run) | far stop at swing low | yes, and confounded with swing size |

## Results

### is/champion (n=314)

| bucket | n | **% move** | R fixed | R half | R orig |
|---|---|---|---|---|---|
| small | 105 | +0.619 | +1.769 | −1.576 | +0.571 |
| mid | 105 | +0.567 | **+2.830** | +2.795 | +0.654 |
| BIG | 104 | **+0.329** | +2.213 | +0.510 | +0.216 |

### oos/champion (n=179)

| bucket | n | **% move** | R fixed | R half | R orig |
|---|---|---|---|---|---|
| small | 60 | +0.536 | +2.178 | −5.901 | +0.923 |
| mid | 60 | **+0.824** | +3.222 | +6.204 | +0.527 |
| BIG | 59 | **+0.291** | +0.385 | +8.554 | +0.118 |

### is/utcsat / oos/utcsat

| cell | % move small / mid / BIG | R fixed small / mid / BIG |
|---|---|---|
| is/utcsat | +0.625 / +0.788 / **+0.293** | +2.013 / +4.437 / +1.839 |
| oos/utcsat | +0.227 / +0.969 / **−0.002** | +1.893 / +3.583 / +0.073 |

## What survives and what does not

**What does NOT survive — my headline was too strong.** I wrote "M2's sign
inverts 4/4" off the `R orig` column. That column is confounded. Under a fair
constant-ATR risk, is/champion actually has **BIG (+2.213) beating small
(+1.769)** — a local reversal of what I reported. The claim as stated was
built on the weakest available measure.

**What DOES survive — the direction holds on the stop-free measure.** `% move`
contains no stop and no risk normalisation at all, and it says big swings
confirmed at FS deliver the **least** price movement in **4/4 cells**:

| cell | small | mid | BIG |
|---|---|---|---|
| is/champion | +0.619 | +0.567 | **+0.329** |
| is/utcsat | +0.625 | +0.788 | **+0.293** |
| oos/champion | +0.536 | +0.824 | **+0.291** |
| oos/utcsat | +0.227 | +0.969 | **−0.002** |

So the honest statement is narrower than what I wrote: **once a swing is
confirmed big, there is genuinely less left in it** — that much is not a stop
artefact. What *was* an artefact is the magnitude I quoted, and the clean
ordering under fixed risk is **mid best, BIG worst in 3/4**.

**The half-stop suggestion does not work, for a concrete reason.** Putting the
stop at the swing midpoint leaves, for a small swing, a risk that is almost
zero — the midpoint of a small swing is right next to the FS price. Result:
the stop is hit **84–93% of the time** on small swings, and the R values
degenerate to nonsense (−1.58, −5.90, −5.91). It is not a usable placement.
This also shows why the large positive R-half numbers on BIG swings in OOS
(+8.55, +9.55) must not be read as a discovery: they come with a 53–61%
stop-hit rate and are the same near-zero-denominator artefact in the opposite
direction.

## Corrected verdicts

- **"M2's sign inverts 4/4"** — RETRACTED as stated. It depended on a
  confounded measure and reverses locally under fair risk.
- **"A confirmed big swing has the least left in it"** — stands 4/4 on % move,
  which has no stop in it at all.
- **The user's specific fix (half stop)** — tested, does not work, for the
  reason above.
- Everything from the earlier chain (M2 is forward-looking; the shuffle null
  cannot see look-ahead; the FS-time exit is dead) is unaffected — none of it
  depended on this normalisation.

## Status

**NOT ADOPTED.** Descriptive only. The lesson recorded: when comparing buckets
of different scales, the risk denominator must be held constant or the
comparison is measuring the stop, not the signal.

## Files
- `backtest/tests/exp_fs_entry_risk.py` → `_fs_entry_risk_control.json`
- `backtest/docs/FS_ENTRY.md` — the run whose headline this qualifies
