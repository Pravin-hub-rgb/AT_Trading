# Capital Stage Plan - what must be true before real money

> Created 2026-09-26 after Stage CrossInstrument (CHECKLIST 24.82). This is
> THE reference for the capital queue. Everything recorded here is
> BACKTEST / NOTION level - no real capital is involved yet. All figures are
> extracted programmatically from the result JSONs (sources: section 7); do
> not hand-edit numbers - regenerate from JSONs if a result changes.

## 1. The Gate (non-negotiable, applies to EVERY candidate)

- **Forward n >= 50 pre-registered trades before ANY candidate is adopted.**
  Current forward slice: **5/50 scored** (CHECKLIST 24.70: 5 trades, net
  -3.83R, PF 0.22). Nothing is adopted, partially adopted, or
  'adopted with a caveat'. At the realised ~12 trades/month, n >= 50 needs
  roughly 4 more months.
- Backtest IS/OOS + cross-instrument results are QUEUE evidence only -
  they order the queue, they never clear it.
- No live sizing of any kind before the order-time sizing bridge (section 4a)
  **exists and is tested.** The queue below is therefore a capital roadmap,
  not a deployment list.

## 2. The Queue (priority order - NOT adoption order)

dNet IS/OOS per lane (champion / utcsat / age10), bybit, x1.5 sizing on flat
books, 6-cell rule = dNet>0 AND curve_better in all 3 lanes x 2 eras.

| # | Candidate | Rule | dNet IS/OOS (all 3 lanes) | Backtest | Cross-venue (24.82) |
|---|-----------|------|---------------------------|----------|---------------------|
| 1 | **M2** | x1.5 if cur_mag_atr >= 3.0 | +152.7/+29.1, +147.5/+31.3, +113.0/+21.3 | PASS 6/6 | PASS 6/6 on Binance perp (binance dNet +113.1/+31.7 champion) |
| 2 | **sMZX** | x1.5^count on M2/ZC/X (stack) | +346.5/+130.4, +341.2/+146.6, +270.3/+29.9 | PASS 6/6 | not run cross-venue (combo stage) - includes dropped ZC, see 3/5 |
| 3 | **uMZX** | x1.5 if any(M2,ZC,X) (union) | +165.5/+49.5, +171.3/+56.8, +145.9/+19.2 | PASS 6/6 | PASS 6/6 on Binance perp (binance dNet +122.6/+43.2 champion) |
| 4 | **ramp_mag** | clamp(1+0.25*(cur_mag_atr-2),1,2) - threshold-free | +267.3/+54.1, +260.3/+53.6, +201.0/+26.1 | PASS 6/6 | not run cross-venue |
| 5 | **count_linear** | 1+0.5*count(M2,ZC,X), cap 2.0 | +276.8/+87.0, +280.2/+100.2, +228.8/+26.4 | PASS 6/6 | not run cross-venue - includes dropped ZC, see 3/5 |

Notes:
- Queue order is the 2026-09-26 user ruling: M2 rank-1 (only candidate with
  full 6/6 + cross-venue 6/6 + marginal-on-gated 6/6 evidence); sMZX strongest
  raw net; uMZX the strongest cross-venue-tested combo; ramp_mag beats binary
  M2 in every cell (24.80) but has no cross-venue run yet.
- Backtest magnitude context (champion dNet): sMZX +346.5/+130.4 vs M2 +152.7/+29.1 - the stack's larger number is NOT a reason to jump the queue
  (1.5^count = levered stakes; raw DD deeper in 3 stack cells, 24.79).
- Stack-book validation (24.83): ALL 5 queue shapes also PASS 6/6 when
  applied to the Stage-B candidate stack books (champ/uts half+delay1+skipD,
  age10 retest_0.25); rank order unchanged (sMZX > count_linear > ramp_mag >
  uMZX > M2 binary), so the flat-book ranking holds on both books. sMZX on
  the champion stack book: 429.6->802.8 IS / 110.5->277.7 OOS. vol_target
  fails on BOTH books (24.80 + 24.83) - closed (section 5).

## 3. Capital preconditions - what each candidate needs before deployment

**Common to ALL candidates:**

- **Every sizing number above is POST-PROCESS on backtest books.** The
  sizing exemption (sizing never changes which trades fire, so post-process
  == path-true) makes these numbers valid AS BACKTEST NUMBERS ONLY. It does
  NOT mean live lot sizing is correct.
- **Order-time sizing bridge: BUILT AND TESTED - M2 BLOCKED** (section 4a).
  The bridge test ran and M2's flag is NOT reproducible at send time (46.5%
  agreement against a 95% bar). Every remaining queue candidate keys off
  cur_mag_atr the same way, so **none of them is deployable as measured** until
  the feature is redefined to be live-computable and re-validated. This applies
  before forward n counts.
- **Forward n >= 50**: 5/50 scored.

**Per candidate:**

- **M2**: bridge must read cur_mag_atr at order-send time over the same
  window/cutoff the backtest used (trade_rows path, obs_ts = entry+900), map
  the >=3.0 predicate to a lot multiplier x1.5, with rounding + min-lot rules.
  Rank-1: this is the first thing to bridge.
- **sMZX / uMZX / count_linear**: depend on flags M2 + ZC + X evaluated at
  send time. ZC is DROPPED as a standalone (section 5) for portability - its
  definition inside these combos remains exactly as tested (Bybit-derived
  vol7_prev7 <= 0.846). Re-deriving ZC thresholds on other data = NEW
  pre-registered experiment, not a silent change.
- **ramp_mag**: continuous read of cur_mag_atr at send time, no threshold -
  simpler bridge than M2 (no predicate), but no cross-venue evidence yet.
- None of the queue candidates has EVER been evaluated against a live order
  ticket. Bridge test = compare bridge-computed lot vs backtest-implied
  multiplier on a replayed trade set, 0 drift allowed.

## 4. Open risks

- **(a8) The wide-SL sizing idea - the user's original, first sizing thesis -
  is REFUTED, and it was testable this whole time because SL is known at
  entry.** `exp_sl_width_sizing.py` -> `_sl_width_sizing.json` sizes the top
  half of `sl_width_pct = |entry_price - sl| / entry_price` (per-book median
  split, no hand-picked threshold). Unlike M2 this reads only values the engine
  fixes at entry (`v18_streak_halt.py:732-733`) - no `seg.end_px`, so it is
  causal and deployable in principle. Bybit base ledgers reproduce 24.85;
  identity gate IDENTICAL.

  | cell | n_wide | wide avgR | narrow avgR | wide WR | narrow WR | claim |
  |---|---|---|---|---|---|---|
  | is/champion | 250 | **+0.216** | +1.565 | 32.8% | 27.2% | **no** |
  | is/utcsat | 227 | **+0.373** | +1.682 | 34.4% | 27.3% | **no** |
  | is/age10 | 65 | **+0.715** | +6.616 | 49.2% | 58.5% | **no** |
  | oos/champion | 140 | **+0.200** | +0.559 | 35.0% | 20.9% | **no** |
  | oos/utcsat | 127 | **+0.210** | +0.523 | 37.8% | 21.4% | **no** |
  | oos/age10 | 38 | +0.801 | +0.642 | 52.6% | 26.3% | yes |

  **CLAIM HOLDS 1/6. ARM PASSES 0/6.**

  The thesis was "bigger SL => higher success rate, so size those up". The
  success-rate half is *partly* real - in the two OOS cells wide-SL trades win
  35.0%/37.8% against 20.9%/21.4% narrow, a large consistent margin. But **avgR
  runs the other way in 5 of 6 cells**, because the wide-SL winners are small:
  they get stopped less often but trail out on small gains, while the narrow-SL
  book carries the 3R runners. Win rate without R is not an edge. That is why
  the arm is scored on avgR, and why the pre-registered claim test was checked
  *before* the sizing result rather than after it.

  The sizing arm fails for the Stage-M M1 reason in its purest form: flagged
  avgR is **below** the per-cell book mean in 5 of 6 cells, so `leverage_trap` is
  true. The +27.0/+42.4/+23.2 IS dNet is pure leverage on a worse-than-average
  cohort, and it sits at the **0.0th percentile** against a matched-count
  random null in **all six cells** - worse than picking trades at random. A
  random subset of the same size passes `curve_better` **100%** of the time,
  which is the 24.87 mechanism surfacing again in a fourth independent
  harness.

  All four readings of the SL-width idea are now closed:
  - remove wide-SL trades (ANCHOR_BASIS_AUDIT 3e) - failed, path cascade
  - size up a broad flag (Stage M / M1) - failed, leverage trap
  - size up tight SL instead (Stage X / A) - passed 4/4 but on n=7/9 OOS
  - size up wide SL directly (this run) - failed 0/6, avgR 0.0th pct vs null

  What survives is the 24.87 mechanism, now confirmed three times over: a
  matched random null passes `curve_better` in essentially every cell on these
  books, so dNet+curve alone cannot certify a sizing feature.

- **(a9) SL-width: the user is RIGHT that a healthy range exists, and GRAY MODE
  WORKS - but the range is the OPPOSITE end, and no gate band passes.**
  `exp_sl_width_buckets.py` -> `_sl_width_buckets.json` (descriptive, costs-aware
  via `net_r`, all 6 ledger controls exact) settles the "which band is healthy"
  question the gate was built on:

  | sl_width % band | n | avgR | WR | net |
  |---|---|---|---|---|
  | **0.00-0.25** | 54 | **+7.871** | 31.5% | **+425.0** |
  | 0.25-0.40 | 118 | +2.192 | 27.1% | +258.6 |
  | 0.40-0.55 | 129 | +0.903 | 15.5% | +116.5 |
  | 0.55-0.70 | 178 | +0.465 | 34.3% | +82.8 |
  | 0.70-0.90 | 178 | +1.277 | 33.7% | +227.4 |
  | 0.90-1.20 | 293 | +0.091 | 22.5% | +26.6 |
  | 1.20-1.60 | 254 | +0.461 | 32.7% | +117.0 |
  | 1.60+ | 488 | +0.082 | 35.9% | +40.2 |

  **The tightest band is by far the best: 1.7% of trades carrying +425R**, at
  avgR 7.9 versus 0.08-1.3 for everything wider. That is the whole edge in one
  line - the runner is a *tight-stop* runner, and width is the enemy. This is the
  mirror image of (a8): the same idea, and it inverts cleanly.

  It is **not monotonic** - 0.70-0.90 (+1.277) beats both neighbours - so there
  is no single "healthy range" cut, and the two deepest bands (0.00-0.25,
  0.25-0.40) hold only 172 trades total. A gate on "wide" is therefore a gate
  on the losing side, and a gate on "tight" throws away most of the book.

  `exp_sl_width_gate.py` -> `_sl_width_gate.json` then ran the gray-mode gate for
  real, in the engine, and **0 of 36 arms pass** (3 bands x 2 streak designs x 6
  cells). Failure counts: dNet<=0 in 36/36, avg/trade worse in 36/36, kept<55%
  in 34/36, maxDD worse in 30/36. Two bands keep >55% yet still fail on every
  other rule, because a gray wide-SL trade forfeits a winner and the kept book
  loses more than the gray book gave up.

  **The gray mechanism itself works and is the reusable part.** The trade is
  run to completion inside the engine, so `busy_until` (v18:743), the loss
  streak (v18:713-722) and `cooldown_bars` (v18:744-745) all still update -
  the slot is NOT refilled, which is the one thing a post-process removal
  (Stage B, Z3) can never do. `seq_identical=True` is reported per cell and is
  the property to watch. The identity gate held IDENTICAL (patched-off ==
  shipped, 340t/+225.3R) on both runs.

  One implementation note worth keeping: the super-set engine contains
  `sl0=sl; sl_cur=sl; best=entry` at **two different indents** (the main entry
  path at 8 spaces, the 5m/retest delayed path at 12). Gating only the first
  silently lets every retest-path trade through. The harness asserts both
  anchors and replaces them with newline-anchored matching, because the 8-space
  form is a substring of the 12-space one.

- **(a10) Fine SL ladder: 3%+ is genuinely dead, and GRAY MODE does NOT rescue the
  wick gate.** `exp_sl_fine_cascade.py` -> `_sl_fine_cascade.json`. The previous
  autopsy's top band was `1.60-99.00` - a 37%-wide bucket with 488 trades, so
  everything above 2% was invisible inside it. Splitting the tail (all six
  ledger controls exact, costs-aware `net_r`):

  | sl_width % | n | avgR | WR | net |
  |---|---|---|---|---|
  | 0.00-0.25 | 54 | +7.871 | 31.5% | +425.0 |
  | 0.25-0.40 | 118 | +2.192 | 27.1% | +258.6 |
  | 0.40-0.55 | 129 | +0.903 | 15.5% | +116.5 |
  | 0.55-0.70 | 178 | +0.465 | 34.3% | +82.8 |
  | 0.70-0.90 | 178 | +1.277 | 33.7% | +227.4 |
  | 0.90-1.20 | 293 | +0.091 | 22.5% | +26.6 |
  | 1.20-1.60 | 254 | +0.461 | 32.7% | +117.0 |
  | 1.60-2.00 | 170 | +0.222 | 33.5% | +37.7 |
  | 2.00-2.50 | 131 | +0.004 | 33.6% | +0.5 |
  | 2.50-3.00 | 76 | +0.311 | 52.6% | +23.7 |
  | **3.00-5.00** | 78 | **-0.107** | 34.6% | **-8.4** |
  | **5.00+** | 33 | **-0.402** | 21.2% | **-13.3** |

  **3%+ is negative in the aggregate and in 5 of 6 cells** (only oos/age10
  rescues 2.5-3.0). 2.0-3.0 is flat, not negative - the damage starts at 3%, not
  2%. So a "very wide SL" gate is worth roughly **-21R** on this book: too small
  to matter and pointing the wrong way.

  **Q2 - the cascade experiment, run under gray mode.** The user correctly
  recalled `exp_cascade_tax_test.py` (H2): the wick removal scored +28.1R
  post-process but **-50.5R path-true**, a -78.6R cascade at 280% of the direct
  effect, and that the same removal turns **positive (+5.61R)** once the three
  stateful carriers are switched off. That is exactly the shape a gray trade
  should fix, so the wick gate was re-run as gray: trade runs to completion,
  P&L suppressed, carriers untouched, threshold frozen at 6.03/12.

  | cell | gray n | kept | dNet | seq_identical |
  |---|---|---|---|---|
  | is/champion | 113 | 77.9% | **-30.1** | no |
  | is/utcsat | 108 | 78.0% | **-83.5** | no |
  | is/age10 | 30 | 76.9% | -24.5 | **yes** |
  | oos/champion | 62 | 77.6% | **-91.6** | no |
  | oos/utcsat | 61 | 77.1% | -90.9 | no |
  | oos/age10 | 18 | 76.3% | -32.2 | **yes** |

  **dNet is negative in 6 of 6 cells**, and the prediction held: gray lands
  between the two known bounds (+28.1 post-process, -50.5 path-true) rather than
  on either. But it is negative, and the reason is visible in the raw R of the
  flagged cohort: **+1.9R and +24.5R on the two IS books** - the wick-flagged
  trades were net *profitable*. Graying them forfeits winners, so the "cascade
  tax" was never the only term; the direct effect was negative too. The
  post-process +28.1R was an artefact of the slot refilling, not of an edge.

  `seq_identical` is False on the four multi books and True only on age10, so
  gray mode is **not** universally cascade-free for a mid-sequence gate: on the
  busier books the cooldown/streak timeline still shifts enough to move a
  downstream entry. The mechanism holds where the book is sparse.

  Both questions answered, both negative. The gray mechanism remains sound and
  reusable (identity gate IDENTICAL, and it is the only way to make a gate that
  does not refill slots), but there is no edge underneath either the SL-width or
  the wick gate to rescue.

  - **(a11) CORRECTED - the -44R was MY BUG, not a property of gray mode. The
  user's arithmetic was right and the run now behaves exactly as they said it
  would.** In the first pass of this gate the harness patched the engine with

      if cooldown_bars > 0 and r_multiple < 0 and not _isgray:

  i.e. it SUPPRESSED the cooldown for gray trades. That is backwards. A gray
  trade still happens - it holds its slot, advances the loss streak and should
  start its cooldown exactly like a real loss. Suppressing it shifted the
  cooldown timeline, let worse trades in, and produced a spurious -44R that I
  then wrote up as a structural finding about gray mode being "necessary but
  not sufficient". **That conclusion was wrong and is retracted.**

  The user caught it by simple arithmetic: graying 3%+ removes 111 trades whose
  raw R is only about -17R, so how can dNet be -44R? It cannot. The gap was my
  patch. The same suppression is present in `exp_sl_width_gate.py` and
  `exp_sl_fine_cascade.py` and **their conclusions about gray mode are affected
  too** - re-run before quoting them.

  Cooldown is no longer gated. The harness now also computes the identity that
  makes this class of bug impossible to miss:

      d_net  ==  -raw_r_grayed  +  cascade_term
      cascade_term = d_net + raw_r_grayed   (must be 0.00 when clean)

  Corrected results, `gray_ge_3.0` (one-sided, 0.25-2.00 untouched):

  | cell | gray | kept | dNet | raw R | cascade | seqID | pass |
  |---|---|---|---|---|---|---|---|
  | is/champion | 14 | 97.2% | +0.39 | -0.39 | **0.00** | yes | no (DD) |
  | is/utcsat | 15 | 96.7% | +1.39 | -1.39 | **0.00** | yes | **yes** |
  | is/age10 | 2 | 98.5% | +1.49 | -1.48 | 0.00 | yes | **yes** |
  | oos/champion | 39 | 86.0% | +5.78 | -5.78 | **0.00** | yes | **yes** |
  | oos/utcsat | 33 | 87.0% | +8.48 | -8.48 | **0.00** | yes | **yes** |
  | oos/age10 | 8 | 89.5% | -0.51 | +0.51 | 0.00 | yes | no (dNet) |

  **`gray_ge_3.0`: G-RULE 4/6, dNet>0 in 5/6, seq_identical 6/6, cascade term
  EXACTLY 0.00 in every cell.** Total dNet **+17.0** = -raw(-17.0) + cascade
  **(+0.0)**. The accounting closes to the cent, which is the proof that gray
  mode really is cascade-free - the trade sequence is untouched, so the only R
  that leaves the book is the gray cohort's own.

  `gray_ge_2.5` is worse (G-RULE 2/6, total -11.4) and correctly so: widening
  the gate to 2.5% starts graying the 2.5-3.0 band, whose raw R is **+11.4**,
  i.e. that band is profitable and the gate is now deleting winners. This is
  the same lesson as (a9) - the gate has to be one-sided and tight.

  So gray mode **works exactly as designed**: the 3%+ tail is a real, cleanly
  removable drag worth about +17R with no cascade and no slot refill. It is
  still **not adopted** - 4/6 is short of the gate, oos/age10's 8 grayed trades
  are net positive so the gate bites a winner there, and +17R over 1,592 trades
  is immaterial next to a 5/50 forward gate. But the mechanism claim is now
  proven rather than assumed.

  - **(a12) RE-RUN of (a9) and (a10) after the cooldown fix. The 0/36 and the
  "gray cannot rescue the wick gate" verdicts SURVIVE - but now they are real
  measurements rather than artefacts of my bug.** Both harnesses were re-run
  with the cooldown suppression removed and the cascade guard added.

  **Re-run of the wick gate** (`exp_sl_fine_cascade.py`, 24.86 predicate frozen
  at 6.03/12): cascade term is **+0.00 in all 6 cells**, `seq_identical` **6/6**,
  dNet **-6.7 / -7.0 / -24.5 / -78.0 / -78.1 / -32.2** - negative everywhere.
  So the earlier conclusion holds for the right reason this time: the wick
  gate really does lose, because the flagged cohort was net profitable, not
  because of a phantom cascade. **The wick gate is genuinely dead.**

  **Re-run of the SL-width gate** (`exp_sl_width_gate.py`, 3 bands x 2 streak
  designs x 6 cells): still **0/36**, and the accounting now closes exactly.

  | arm | G-RULE | seqID | total dNet | -raw | max abs cascade |
  |---|---|---|---|---|---|
  | b_040_090 / streakON | 0/6 | **True** | -1091.0 | +1091.0 | **0.000** |
  | b_040_120 / streakON | 0/6 | **True** | -1019.8 | +1019.8 | **0.000** |
  | b_055_120 / streakON | 0/6 | **True** | -1176.6 | +1176.6 | **0.000** |
  | b_040_090 / streakOFF | 0/6 | False | -1126.1 | +1018.1 | 40.486 |
  | b_040_120 / streakOFF | 0/6 | False | -1132.9 | +985.3 | 66.169 |
  | b_055_120 / streakOFF | 0/6 | False | -1193.2 | +1085.0 | 63.218 |

  **Every `streakON` arm is exactly cascade-free** (max abs cascade term 0.000
  across all 36 of its cells), which is the cleanest possible proof that the
  gray mechanism itself is sound. And the 0/36 verdict is now **honest**: the
  grayed cohort is worth **+1,019R to +1,177R** in aggregate, so a band gate
  that keeps only 17-58% of the book is throwing away more than a thousand R of
  real profit. The wide-SL gate is dead for a real reason, not a bug.

  **Second design question, answered by the data rather than by me:**
  `exp_gray_streak=True` is the only correct setting. `streakOFF` is a genuine
  bug - when a gray trade does not advance the loss streak, a stale
  `halt_skip_next` set by an earlier real loss is still pending, and the engine
  consumes it by skipping the NEXT real entry (v18:580-583). That is the only
  remaining source of a non-zero cascade term, and it is fully explained by it.

  Net effect on the research programme: nothing is rescued, and the three
  gray-mode gates (wide SL, 3%+ tail, wick) are all **CLOSED** - but now on
  evidence that closes to the cent, and with the mechanism validated rather
  than merely claimed.

  - **(a6) ETH-ledness produced a 6/6 that the NULL CONTROL KILLED. Do not read
  24.88 as a pass.** `exp_eth_ledness.py` -> `_eth_ledness.json` sized BTC
  trades on ETH-minus-BTC return divergence (1h, fully-closed bars only, hard
  zero threshold, L in 24/168h). Bybit base ledgers reproduced 24.85, and on
  the pre-registered Bybit gate three arms cleared 6/6 - `E_lead` on **both**
  venues.

  Two things in that JSON did not look right, so it was not accepted at face
  value. `d_max_dd` is **negative in 22 of 24 cells** - the drawdown gets deeper
  almost everywhere, and every pass rode the `d_ulcer>0.5 OR d_calmar>0.05`
  branches, never `d_max_dd>0.5`. `E_lag` passes 6/6 with ulcer -9.21 and
  d_max_dd -19.68, carried entirely by a calmar ratio. And the flag is not
  picking winners: `mean_r_flagged / book_mean` is 0.76 / 0.79 / 0.65 / 0.72 /
  0.97 / 1.43, below 1.0 in five of six cells, on a cohort that is ~45% of the
  book.

  `exp_eth_ledness_null.py` -> `_eth_ledness_null.json` then ran the decisive
  test: x1.5 on a **random subset matched to each real arm's flagged count**,
  200 seeds per cell, 24 cells.

  | measure | value |
  |---|---|
  | cells where the RANDOM null passes `curve_better` | **24 / 24** |
  | mean random-null `curve_better` pass rate | **83.8%** (72.5 - 96.5) |
  | mean percentile of the real ETH arms | **49.5** (8.5 - 93.5) |
  | arms beating their own null at >=90th pct in all 6 cells | **0 / 4** |

  `E_lead` - the arm that passed on both venues - sits at the **8.5th**
  percentile in is/champion and **9.5th** in is/utcsat, i.e. **worse than a
  random pick of the same size**: real dNet +54.2 against a null median of
  +101.4.

  **The mechanism, stated generally: dNet>0 and `curve_better` are close to
  automatic for ANY ~45% subset of a profitable book.** Upsize a profitable
  cohort by 1.5x and the subset's R sum stays positive; ulcer and calmar both
  move favourably enough to clear absolute thresholds. On these books a 6/6
  sizing result therefore carries almost no information about the feature - the
  gate is measuring the base book, not the lever.

  ETH-LEDNESS is CLOSED. This is a stronger outcome than a plain fail: it shows
  the 6/6 sizing gate on this book is **not falsifiable by dNet+curve alone**
  and needs a matched-null comparison to carry any meaning.

- **(a7) The same logic invalidates the ZCX headline, and the ZCX family is
  CLOSED with it.** 24.86's 5/6 and 24.87's cap sweep are sizing results on the
  same books judged by the same two gates. ZCX was never shown to beat a matched
  random null, and 24.86's dNet was positive in 22/24 cells *on a ~45% cohort* -
  exactly the condition under which a null does as well. The "dNet is real and
  only curve shape fails" reading of 24.86 is therefore **not safe**. ZCX closes
  **unadopted**: no arm passed the pre-registered 6/6, and the family was never
  validated against a null. The only survivor from the ZCX line is the negative,
  mechanism-level finding in (a5): curve deltas are linear in (cap-1) and
  `d_max_dd` is negative because the flagged cohort sits on the base drawdown.

  **Standing rule adopted from this: no sizing arm on these books is reported as
  a pass without a matched-count random null.** Re-run the null before quoting
  any dNet from `_sizing_combo_results.json`, `_zx_causal_combo_results.json`,
  `_zx_cross_venue_results.json` or `_zx_sizecap.json` as evidence of edge.

- **(a) Order-time sizing bridge - BUILT AND TESTED 2026-09-26, RESULT:
  BLOCKED.** `exp_m2_live_bridge.py` -> `_m2_live_bridge.json`. This was the one
  hard engineering blocker and it does not clear.

  M2's feature is `cur_mag_atr = |seg.end_px - seg.start_px| / atr15`, where
  `end_px` is the swing segment's END price. That end price is **confirmed to be
  forward-looking**: `backend_check_wd_days.py:108` asserts `fs_at_idx >=
  seg.end_idx`, i.e. a swing's FS/SUS confirmation happens at or AFTER the end
  bar. A live process cannot know `end_px` when it sends the order.

  Replacing it with the last closed 15m close reproduces the backtest flag on
  **77.5%** of trades (worst cell 72.0%) against a pre-registered bar of 95% /
  90%. More decisive than the agreement: the send-time reader fires on only
  **0-6 trades out of 76-500**, where the backtest flags 12-133. The signal
  essentially vanishes.

  | cell | n | backtest flag | send-time flag | agree | send dNet |
  |---|---|---|---|---|---|
  | is\|champion | 500 | 128 | 6 | 75.6% | +3.5R |
  | is\|utcsat | 454 | 133 | 6 | 72.0% | +3.5R |
  | is\|age10 | 130 | 25 | 0 | 80.8% | 0.0R |
  | oos\|champion | 279 | 48 | 1 | 83.2% | 0.0R |
  | oos\|utcsat | 253 | 47 | 0 | 81.4% | 0.0R |
  | oos\|age10 | 76 | 12 | 0 | 84.2% | 0.0R |

- **(a2) A send-time replacement for M2 was searched for and does not exist.**
  `exp_m2_sendtime_feature.py` -> `_m2_sendtime_feature.json` tested two
  redefinitions that read only send-time data, against the 6-cell rule plus a
  flag-coverage band of 5-40% (below it there is no selection; above it, it is
  the M1 leverage trap from 24.58):

  | arm | send-time? | result | why |
  |---|---|---|---|
  | `M2_oracle` (seg.end_px) | no | 4/6 | reference only, not deployable |
  | `mag_so_far` binary at 3.0 | yes | **0/6** | flags 0-1.3% - the threshold is unreachable mid-swing |
  | `ramp_so_far` 0.25 slope | yes | **0/6** | flags 100% - pure leverage, the M1 trap |

  So M2's edge is not "big swings are good" in any form computable before the
  trade is placed - it is specifically that the swing **finishes** large. That
  is a real property of the backtest and a hard limit on live deployment.

- **(a3) The M2-free causal combo was found and tested: ZC x X.** M2 was not the
  only flag in the queue - `ZC` (vol7_prev7 <= 0.846) and `X` (parent risk_pct
  < 1.0) also feed the combos, and **neither reads `seg.end_px`**: ZC is a
  7-day-vs-prior-7-day volume ratio, X is a configured window risk value. But
  every combo in `exp_sizing_combo.py` (uMZ, uMZX, sMZ, sMZX) *contains* M2, so
  the causal pair had never been tested alone. `exp_zx_causal_combo.py` ->
  `_zx_causal_combo_results.json` runs it, with a pre-registered 5-40% coverage
  band and the same 6-cell rule:

  | arm | causal? | 6/6 | champion dNet IS/OOS | note |
  |---|---|---|---|---|
  | `uZX` x1.5 on ZC or X | yes | **5/6** | +124.0 / +33.6 | age10 OOS curve FALSE |
  | `sZX` x1.5^count(ZC,X) | yes | **5/6** | +133.6 / +86.4 | age10 OOS curve FALSE |

  Both clear the rule on champion AND utcsat in BOTH eras, and on age10 IS -
  the first send-time-computable sizing arm to do so anywhere in this queue.
  The single failing cell is age10 OOS, and it fails on shape, not profit:
  dNet **+5.05**, maxDD **-1.50** (better), but **ulcer -9.87** (worse) on 22
  flagged trades. The lever makes money there while making the curve rough.

  This is NOT a pass, and NOT an adoption. Three reasons, all structural:
  (1) 5/6 under the pre-registered rule - one cell short; (2) ZC itself was
  already dropped as a standalone for cross-venue portability (24.82 - a
  Bybit-volume threshold that did not transfer to Binance), so any ZC-led arm
  needs a fresh cross-venue run before it means anything; (3) the age10 OOS
  delta is +5R on a 130-trade book - well inside noise.

- **(a4) The cross-venue run REFUTES the portability objection but not the
  curve problem.** `exp_zx_cross_venue.py` -> `_zx_cross_venue_results.json`
  re-ran ZC / X / uZX / sZX on Binance perp (24.82 data, era windows mirrored,
  threshold **not** re-derived - that would defeat the point of a transfer
  test). Bybit control passed: base ledgers and the uZX dNet reproduce 24.86
  exactly, so the harness is not the problem.

  | arm | Binance 6/6 | champion dNet IS/OOS | note |
  |---|---|---|---|
  | `uZX` | **no** | +52.2 / +23.7 | dNet positive, curve FALSE on IS |
  | `sZX` | **no** | +64.7 / +23.7 | same shape |

  The finding is more specific than "it does not transfer". **dNet is positive
  in 22 of 24 Binance cells** - the profit effect is real and venue-robust. What
  fails is exclusively `curve_better`, and it fails on the two large IS books
  (champion and utcsat, 187 and 169 flagged trades) while the small age10 book
  passes on all four arms. So 24.82's "ZC does not transfer" was measuring curve
  degradation, not the absence of profit.

  That does **not** rescue the lever. The rule is the rule: 6/6 was
  pre-registered, ZCX is not 6/6 on either venue, and it is not 6/6 on Binance
  either. What the run does establish is that the failure is a **shape** problem
  in one consistent direction, not noise - which is the profile a future
  size-cap or capped-add variant could attack, and not the profile of a dead
  idea.

  What it does establish: the queue was never five levers, it was **one
  forward-looking lever wearing five hats**. With M2 removed there is still
  positive, reproducible, *live-computable* signal - it just does not yet clear
  the same bar M2 was held to.

- **(a5) The size-cap attack is REFUTED, and the reason is structural, not a
  matter of picking a better cap.** `exp_zx_sizecap.py` -> `_zx_sizecap.json`
  swept the multiplier over 1.00 / 1.10 / 1.20 / 1.25 / 1.30 / 1.40 / 1.50 on
  both arms, both venues, both eras. Post-process sizing, so per the sizing
  exemption in `AGENT_COORDINATION.md` this is a real measurement - no engine
  rerun, trade keys identical. Bybit control passed again (base ledgers +
  uZX@1.50 reproduce 24.86).

  | cap | Binance curve cells | Bybit curve cells |
  |---|---|---|
  | 1.00 (base) | 0/12 | 0/12 |
  | 1.10 - 1.40 | 8/12 | 10/12 |
  | 1.50 | 9/12 | 10/12 |

  **No cap passes 6/6 on either venue. The curve-cell count is essentially flat
  in the cap** - and that flatness was *predicted before the run*, in the
  harness docstring, from the arithmetic of `curve_better`:

  - `apply_cap` scales `r_multiple`, so the arm's whole equity curve scales.
    Therefore `d_max_dd` and `d_ulcer` must be **linear in (cap - 1)**, while
    `d_calmar` is ~**invariant** (net and dd both scale, their ratio does not).
  - `curve_better` tests **absolute** thresholds (`d_max_dd>0.5` OR
    `d_ulcer>0.5` OR `d_calmar>0.05`), so a smaller cap can only ever score a
    *smaller* curve delta. Capping cannot flip the gate; it can only shrink the
    miss.

  The measurement confirms it to four decimals on Binance - mean absolute
  deviation from linear **0.0048**, max **0.047** over 72 comparisons (Bybit is
  noisier at 0.30 mean because its flagged cohorts are smaller). Champion IS
  `d_max_dd` walks -2.2539 / -4.5078 / -11.2695 at cap 1.10 / 1.20 / 1.50 -
  ratios 1.0000 / 2.0000 / **5.0000**. Exactly linear.

  So the hypothesis in (a4) was **wrong in an instructive way**: the failure is
  not "1.5x is too hot". `d_max_dd` is **negative** and grows with the cap,
  which means the flagged cohort sits *on top of* the base book's deepest
  drawdown - upsizing it makes the drawdown deeper, not shallower. champion IS
  and utcsat IS stay `curve_better=False` at **every** cap from 1.10 to 1.50,
  while all four OOS cells and age10 pass at every cap. The cell pattern is
  cap-invariant, so no sizing setting reaches it.

  Two things this run *does* settle. dNet is **robust** - removing the single
  best trade leaves it unchanged in all 24 cells (`d_net == d_net_no_best`,
  best trade sits outside the flagged cohort), so the profit is not a
  one-winner artifact. And the ZC/X profit effect is confirmed at **every** cap,
  on both venues: dNet is real, it is just inseparable from the drawdown it
  amplifies. **The size-cap family is CLOSED.** Anything that attacks the shape
  has to change *which* trades are sized, not how much.

  **Net position: the queue splits in two.** M2, ramp_mag, and the M2 component
  of uMZX/sMZX/count_linear are non-deployable as measured (feature-definition
  problem, not rounding). ZC/X are deployable and promising but unadopted at
  5/6. Neither can be adopted anyway: the untouched forward gate is at 5/50
  trades, net -3.83R.

- **(b) Thin OOS margins on Binance perp (STRUCTURAL LIMIT - do not
  re-test):** champion OOS 286t +17.8R = +0.062 R/trade, utcsat 258t
  +7.6R = +0.029 R/trade - too thin to distinguish from zero. Recorded as a property of the venue transfer, not an
  experiment to repeat (user ruling 2026-09-26).
- **(c) age10 OOS anomaly - THE ONLY SANCTIONED RETEST:** bybit OOS 76t +43.2R vs binance OOS 78t +94.2R = 2.18x,
  while every other lane DECLINED (0.25x champion, 0.13x utcsat; IS ratios
  0.78/0.58/0.42). One lane doubling while the rest halve is more likely
  luck - check whether a few trades drive it.
  **RESOLVED 2026-09-26 - CONCENTRATED, luck-shaped.** `exp_age10_anomaly.py`
  -> `_age10_anomaly.json` (pre-registered rule, all cells reported):

  | book | n | net | best | top-5 share | trades >=+3R | WR |
  |---|---|---|---|---|---|---|
  | oos bybit | 76 | +43.2R | +13.60 | 99.2% | 10 | 39.5% |
  | oos binance | 78 | +94.2R | +22.21 | **71.8%** | 15 | 47.4% |
  | is bybit | 130 | +435.7R | +55.73 | 50.2% | 34 | 53.8% |
  | is binance | 118 | +182.6R | +56.69 | 75.7% | 21 | 43.2% |

  Trigger fired: top 5 trades carry 71.8% of the binance OOS net. Dropping the
  single best trade leaves +72.0R. Five of 78 trades produce most of a number
  that is 2.18x the bybit reference - so **the 2.18x is a property of one
  sample, not a venue property, and must not be quoted as "age10 transfers
  well".** Note the bybit OOS book is even more concentrated (99.2%), so this
  is a thin-sample property of the lane, not something Binance introduced.
  Diagnostic only: it neither promotes nor demotes age10 or M2.
- **(d) Cross-instrument base edge is weak overall.** Portability evidence
  applies to the SIZING FLAGS (M2/uMZX), not to edge magnitude: binance base
  net is 0.13-0.78x bybit on 5 of 6 lane/era cells (24.82), IS curve ~4-8x
  rougher (ulcer). Do not quote 'edge transfers' without that qualifier.
- **(e) Study-2 weak-OOS-baseline luck caveat (24.77)** applies to every OOS
  delta in this document.
- **(f) The 5 forward trades scored so far LOST money** (net -3.83R, PF 0.22,
  all 5 shorts into a rising market, 24.70). n=5 is far too small to conclude
  anything in either direction - that is exactly why the contract fixes n >= 50
  and pre-registered R5 = "NO VERDICT at n<50". Recorded here so this number is
  not later mistaken for evidence against the queue: it is not, and it is not
  evidence for it either. **Do not tune anything in response to it** - the
  contract forbids that at any n.

## 5. Tested and FAILED - do not re-run (records, not candidates)

| Item | Failure | Evidence |
|------|---------|----------|
| **ZC** (vol7_prev7 <= 0.846 standalone) | Portability: bybit-volume-derived ratio threshold does NOT transfer (binance IS curve FALSE: ulcer 110 -> 134 champion); ALSO fails strict 6/6 on bybit via age10 OOS | 24.82 / 24.79 |
| **X** (parent risk_pct < 1.0 standalone) | Thin everywhere: binance OOS champion dNet -1.0 cell False; bybit age10 OOS 0 flags / 0.0 | 24.82 / 24.79 |
| **vol_target** (inverse-ATR sizing) | curve_better FALSE x3 (champ IS ulcer 14.62->29.82) despite net up 6/6 - fails on the stack book too (24.83) | 24.80 / 24.83 |
| **Z3 vol gate** (vol7_prev7 <= 1.20 path-true) | G-RULE FAIL 3/6; combined vs FLAT FAIL 4/6; post-process-removal upper-bound rule, 2nd confirmation (after Stage B wick 0/4). Z3 recommendation RETRACTED | 24.81 |
| **Stage B removals** | 0/4 (post-process removal = upper bound under exp_mltf) | LOG row 81 |
| **regime10** | Small (+0.9/+3.2), lane-shaped - SKIP for the capital queue; docs only | user ruling 2026-09-26 |
| X flag variants, Z-family gates, flip96, B-removal cascade | Already closed | SUMMARY dead-families list |

'Tested, not portable' / 'failed' labels travel with these - a future
'M2 best, drop everything else' claim does not revive them, and a future
'retest ZC with a new threshold' is a NEW pre-registered experiment.

## 6. Rulings of 2026-09-26 (user, RESEARCH_POLICY)

1. **Adopt M2 / ramp / stack now?** NOT NOW - forward gate (n >= 50) not met.
   M2 stays rank-1 in the queue for when it clears. Nothing adopted before
   the forward gate.
2. **Z flags?** DROP ZC (portability failure + bybit age10 failure). X stays
   dead - do not revive. Both kept in docs as 'tested, not portable'.
3. **Retest scope?** ONE thing: the age10 OOS anomaly (4c). Thin Binance OOS
   margins = structural limit, flagged not re-tested.
4. **regime10?** SKIP for the capital queue (docs only).
5. **Live order-time sizing bridge?** YES - critical path, built and tested
   BEFORE any live sizing.
   META: no full evidence package - the queue above is sufficient. Risk gets
   reduced by (c) the age10 check, (b) forward data to n >= 50, (a) the
   bridge - not by re-arranging backtest paper.

## 7. Sources (numbers are extracted, not typed)

- `live_stuff/tests/_sizing_combo_results.json` (24.79) - M2/ZC/X/uMZ/uMZX/sMZ/sMZX verdicts
- `live_stuff/tests/_sizing_shapes_results.json` (24.80) - ramp_mag/vol_target/count_linear
- `live_stuff/tests/_gate_size_pathtrue.json` (24.81) - Z3 gate G-RULE/combined/marginal
- `live_stuff/tests/_cross_instrument_results.json` (24.82) - transfer, flags, age10 anomaly
- `live_stuff/tests/_shapes_stack_results.json` (24.83) - all 5 queue shapes re-scored on the stack books
- CHECKLIST 24.78-24.83, LOG rows 84-88, EXPERIMENT_SUMMARY bullets
- Generator: built by script with anchor asserts; regenerate rather than edit figures.
