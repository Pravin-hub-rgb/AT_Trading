# RANGE POSITION × RANGE WIDTH — multi-timeframe 2D study

**Question:** A trend system has low WR because markets trend only ~20-30% of
the time. So *where* you enter inside the current range should matter:
mid-range = chop, edge = momentum. Prior art (`BLEED_AUTOPSY.md`) tested
range **position alone** (1D, 4h) and it era-flipped hard (peak entries
+1.78 IS → −0.48 OOS). This study tests the fuller **2D** idea the user
actually described — position × width — across four timeframes, and asks
*why* it flips.

**Verdict up front: 7 of 27 pre-registered comparisons survive, and the
user's original "edges beat the middle" hypothesis survives in 3 of 4
independent lanes. But the windows are nested, not independent, and none
of this touches production yet.** Details and caveats below.

## Method

- **Features** (causal — only 1h bars CLOSED before `entry_ts + 900`):
  - `range_pos = (close − low)/(high − low) × 100` over the window
  - `range_width = (high − low)/ATR14 × 100` over the same window
- **Windows:** 4h (4 bars) · 1d (24) · 3d (72) · 1w (168)
- **2D grid:** position quartile × width tercile (cutoffs fixed from IS
  champion as the reference set — a reference set, not the test set)
- **Books:** champion STACK + utcsat STACK, both eras
- **Judged on TRIMMED MEAN and MEDIAN**, not avgR (Rule 13 — the books are
  tail-concentrated; avgR alone is not trustworthy).

### Pre-registered survivor rule (fixed before running, applied in code)
A comparison SURVIVES only if, across all 4 book cells
(champion/utcsat × IS/OOS):
1. the ordering has the **same sign in both eras** on the trimmed mean, and
2. is **monotone in ≥3 of 4** cells, and
3. both extreme cells have **n ≥ 15**.

Applied by `exp_range_verdict.py` (in code, not in the author's head) so the
author cannot quietly relax it.

## Results — 7 / 27 survivors

| Window | Comparison | IS sign | OOS sign | mono | minN | verdict |
|---|---|---|---|---|---|---|
| 4h | edges − mid @ tight width | 2/2 | 2/2 | 4/4 | 25 | **SURVIVOR** |
| 4h | pos75-100 − pos0-25 @ **wide** width | 2/2 | 2/2 | 4/4 | 18 | **SURVIVOR** |
| 1d | wide − tight @ mid position (50-75) | 2/2 | 2/2 | 4/4 | 16 | **SURVIVOR** |
| 3d | pos75-100 − pos0-25 @ **wide** width | 2/2 | 2/2 | 4/4 | 16 | **SURVIVOR** |
| 3d | wide − tight @ low position (0-25) | 2/2 | 2/2 | 4/4 | 16 | **SURVIVOR** |
| 1w | edges − mid @ normal width | 2/2 | 2/2 | 4/4 | 42 | **SURVIVOR** |
| 1w | edges − mid @ wide width | 2/2 | 2/2 | 4/4 | 38 | **SURVIVOR** |

The 20 non-survivors are dominated by the **position-alone** comparisons
failing to hold their IS sign into OOS — reproducing, on trimmed means and
across four windows, exactly the `BLEED_AUTOPSY` era-flip.

## What this says about the era-flip (mechanism B)

The 2D interaction **partly rescues** the peak-position idea, and the
rescue is the interesting finding:

- **Position alone flips** (1D/4h peak went −0.48 OOS in `BLEED_AUTOPSY`).
- **Position × width survives** at 4h-wide and 3d-wide: "high position
  beats low position" holds in both eras *only* when the range is expanded
  (width tercile 2). At tight/normal width it does not.

Interpretation: peak-position entries failed in 2021-22 not because "peak is
a bad location" but because **peak entries during those years mostly sat in
tight/normal (non-expanded) ranges** — i.e. they were the tail end of a
squeeze, a mean-reversion trap — whereas the high-position trades that
worked were in genuinely expanded ranges. Width is the conditioning variable
that the 1D study was missing.

Note this is an **association consistent with the mechanism, not proof of
it** — era comparison alone cannot establish causation.

## Honest caveats (do not skip)

1. **Windows are nested, not independent.** 4h ⊂ 1d ⊂ 3d ⊂ 1w. Seven
   "survivors" are not seven independent confirmations; 4h and 3d both
   showing "peak wins when wide" is largely one signal seen twice.
2. **Lanes are correlated.** utcsat is a close variant of champion, so
   "2/2 lanes" is not two independent datasets — it is two closely-related
   books over the same underlying trades.
3. **Multiplicity.** 27 pre-registered comparisons were run. 7 survived.
   A strict rule keeps the false-positive rate down, but 7 correlated
   survivors still warrants a replication before belief.
4. **Trades, not signals.** This studies where the *existing* champion
   entered. It does not simulate a gate. A GRAY/skip gate is the *next*
   step and must be run path-true (slot, cooldown, streak still consume).
5. **OOS is already inspected.** Independent `data/btc` replication and
   genuinely forward data are still required before the existing gate moves.

## Status

Descriptive + interaction research on already-simulated books. **No new
entries simulated, no gate proposed, no production change, experimental
flags remain default-off.** The strongest, most self-consistent thread to
carry into a path-true GRAY test is: *suppress/gray peak-position entries
that occur in non-expanded (tight/normal) ranges, where the 1D effect is
weak to harmful in both eras.*

## Files
- `live_stuff/tests/exp_range_pos_width.py` — 2D grid builder
- `live_stuff/tests/exp_range_verdict.py` — pre-registered rule, applied in code
- `live_stuff/tests/_range_pos_width.json` — full grid
- `live_stuff/tests/_range_pos_width_verdict.json` — verdict per comparison
