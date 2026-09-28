# CLOSED — do not repeat these

One page. Every direction that has been tested and lost, with the number that
killed it. Before starting any new experiment, check this list.

**Status: nothing in this file is adopted. Nothing here is a suggestion.**
These are closed. If one is proposed again, cite the row rather than re-running.

## The two lines that are worth keeping (and are NOT experiments)

1. **Low win rate + tail concentration is a FEATURE, not a bug.** Markets
   trend ~20-30% of the time; a trend system takes many small losses and few
   large wins. Proof, not theory: tightening the SL drops WR 27.8% → 18.8%
   and inflates maxDD 27.7 → 115.0. The wide stop **is** the mechanism that
   lets a 25%-hit-rate book survive. See `SL_TIGHTEN.md`.
2. **The common traps list was right every time.** It predicted every failure
   in this file: exiting early to raise WR, tighter stops, stacking complex
   filters, adding filters for their own sake.

Nothing further to experiment on here. These two are constraints, not
hypotheses.

## Closed — entry / signal side

| direction | result | doc |
|---|---|---|
| Range position × width gate (4h/1d/3d/1w, 27 pre-registered tests, 7 survived) | GATE FAILS 4/4. The gated cohort is the book's **best** cohort: WR 41-42% vs book 27.8-29.1%, carrying +107R/+127R in IS. Deleting it destroys R. | `RANGE_PEAK_GRAY.md` |
| Mid-range avoidance | falsified — middle buckets were profitable OOS | `RANGE_POS_WIDTH.md` |
| ADX > 25 | DEAD, both eras | repo, `exp_oldengines_path` |
| Kaufman Efficiency Ratio (ER24/ER50) | REJECTED — no bucket net-negative; low-ER holds +105R of real winners | repo, `ANCHOR_BASIS_AUDIT` §3f |
| Regime/chop/wick/swing-churn filters | all bucketed, none gates | repo, `REGIME_STRUCTURE_AUTOPSY` |

## Closed — sizing / capital

| direction | result | doc |
|---|---|---|
| Vol-targeting (inverse-vol) | FAILED — net up 6/6 but curve worse ×3 (ulcer 14.62→29.82) | repo, 24.80/24.83 |
| sMZX sizing (M2/ZC/X, 1.5^count) | **RETRACTED — look-ahead.** M2 reads `seg.end_px`, which does not exist at B2/flip entry. The "4/4 selection" was a look-ahead detector, not skill. | `SMZX_LOOKAHEAD_RETRACTION.md` |
| M2-free ZC×X | the only live-computable residue, but 3/4 (fails is/champion) — not pursued | `SMZX_LOOKAHEAD_RETRACTION.md` |
| Add 0.5 at FS | +R, but `add_any` beat `add_M2` 4/4 and `add_BAD` was also +R → **drift, not selection**. Drawdown rises 1.3-1.7×. | `FS_ADD_VS_BASE.md` |
| Cross-venue (Binance perp) | 2/4 — fails the pre-registered bar | `SMZX_BINANCE_REPLICATION.md` |

## Closed — exit / stop

| direction | result | doc |
|---|---|---|
| Exit at FS when the swing looks bad | DEAD 4/4. Every subset's remaining R is positive; exiting always gives up money (+3.6R best case). | `FS_TIME_DECISION.md` |
| Tighter SL (0.5-2.0 × ATR toward entry) | CATASTROPHIC 4/4. WR −9pts, DD 2-4×. Non-monotonic wobble is noise. | `SL_TIGHTEN.md` |
| Wider SL buffer (0.10 / 0.25) | worse 3/4; calmar 3.20→2.90→2.51 | `SL_VARIANTS.md` |
| Causal SL | era-flipped: IS −77.8/−63.2, OOS +9.9/+12.6 | `SL_VARIANTS.md` |
| Pivot trail | catastrophic; oos/champion +70.2 → **−2.5R**, PF 1.34→0.99 | `SL_VARIANTS.md` |
| Half-swing stop | degenerate — for a small swing the midpoint sits inside the noise, hit 84-93% of the time | `FS_ENTRY_RISK_CONTROL.md` |

The stop has now been attacked from **both** directions (tighter and wider)
and every variant loses. `sl_buf_atr=0.01` + swing-pivot stands.

## Closed — more trades

| direction | result | doc |
|---|---|---|
| Relax `cooldown_bars` / `max_consecutive_losses` | 0/4. A5 adds 159 trades (+32%) for −136R IS / −68R OOS; ex-best5 goes **negative** in 3 cells. Both limiters earn their keep. | `TRADE_EXPANSION_AUDIT.md` |
| Pyramid / scale-in | FAMILY CLOSED — V4 −111.3/−87.3, no arm passed both gates | repo, `PYRAMID_PHASE2_DESIGN.md` |
| Revenge re-entry | DEAD 8/8, all cells negative | repo, 24.44 |
| Same-window re-entry (rewin) | era-flipped; no filter survives both sides | repo, 24.61 |
| 5m confirmation | cuts trades 502→351, era-dependent | repo, 24.39 |

## Two traps that produce spectacular fake numbers

Both hit in this work; both are easy to repeat.

1. **Degenerate risk denominator.** A stop that sits near the fill makes R
   explode (avg +19.4R, net +9700R was a real output of a real harness before
   it was caught). Any stop closer than ~0.25 × ATR is inside the noise.
2. **Comparing across buckets without holding the risk denominator constant.**
   This made "big swings are worst" look like a finding when it was partly
   measuring stop distance. The confounded claim had to be retracted.
   `FS_ENTRY_RISK_CONTROL.md`.

Rule: when comparing things of different scale, the denominator must be
constant, or report a size-neutral measure (e.g. % move) alongside R.

## Still open (not closed)

- **B1 entry.** No kwarg fires the entry on B1 — `exp_b1_b2_mode` is a
  blocking filter on the B2 trigger, not a different trigger. Needs a
  signal-selection patch plus a full path-true run. Honestly **unknown**;
  every B1 number produced so far has been an artefact.
- **True FS-only engine.** 2900/1634 confirmed swings exist; only the 314/179
  that produced a B2/flip entry have been priced. An FS-only entry could be a
  larger book. Not simulated.
- **Live size state.** `v18_streak_halt.py` has zero hits for
  equity/size/notional/qty. Any sizing change has no execution channel.

## The one caveat that applies to all of the above

The champion's IS/OOS slices are the most-inspected data in this repo. An
arm can pass everything above and still fail on a genuinely untouched
dataset. Several candidates in this file were killed *only* by OOS or
cross-venue, after looking excellent in IS.
