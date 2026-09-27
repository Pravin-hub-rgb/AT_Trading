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
