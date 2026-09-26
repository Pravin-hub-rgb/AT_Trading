# Capital Stage Plan - what must be true before real money

> Created 2026-09-26 after Stage CrossInstrument (CHECKLIST 24.82). This is
> THE reference for the capital queue. Everything recorded here is
> BACKTEST / NOTION level - no real capital is involved yet. All figures are
> extracted programmatically from the result JSONs (sources: section 7); do
> not hand-edit numbers - regenerate from JSONs if a result changes.

## 1. The Gate (non-negotiable, applies to EVERY candidate)

- **Forward n >= 50 pre-registered trades before ANY candidate is adopted.**
  Current forward slice: 0/50. Nothing is adopted, partially adopted, or
  'adopted with a caveat'.
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

## 3. Capital preconditions - what each candidate needs before deployment

**Common to ALL candidates:**

- **Every sizing number above is POST-PROCESS on backtest books.** The
  sizing exemption (sizing never changes which trades fire, so post-process
  == path-true) makes these numbers valid AS BACKTEST NUMBERS ONLY. It does
  NOT mean live lot sizing is correct.
- **Order-time sizing bridge: NOT BUILT** (section 4a). This is the single
  hard engineering precondition, and it applies before forward n counts.
- **Forward n >= 50**: 0/50.

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

- **(a) Order-time sizing bridge - never built, never tested.** How
  cur_mag_atr is read at send time, what lot it maps to, rounding, min-lot:
  none of it exists. Build + test BEFORE any live sizing, not after. This is
  the only engineering item in this document.
- **(b) Thin OOS margins on Binance perp (STRUCTURAL LIMIT - do not
  re-test):** champion OOS 286t +17.8R = +0.062 R/trade, utcsat 258t
  +7.6R = +0.029 R/trade - too thin to distinguish from zero. Recorded as a property of the venue transfer, not an
  experiment to repeat (user ruling 2026-09-26).
- **(c) age10 OOS anomaly - THE ONLY SANCTIONED RETEST:** bybit OOS 76t +43.2R vs binance OOS 78t +94.2R = 2.18x,
  while every other lane DECLINED (0.25x champion, 0.13x utcsat; IS ratios
  0.78/0.58/0.42). One lane doubling while the rest halve is more likely
  luck - check whether a few trades drive it. Not yet done (deferred by user).
- **(d) Cross-instrument base edge is weak overall.** Portability evidence
  applies to the SIZING FLAGS (M2/uMZX), not to edge magnitude: binance base
  net is 0.13-0.78x bybit on 5 of 6 lane/era cells (24.82), IS curve ~4-8x
  rougher (ulcer). Do not quote 'edge transfers' without that qualifier.
- **(e) Study-2 weak-OOS-baseline luck caveat (24.77)** applies to every OOS
  delta in this document.

## 5. Tested and FAILED - do not re-run (records, not candidates)

| Item | Failure | Evidence |
|------|---------|----------|
| **ZC** (vol7_prev7 <= 0.846 standalone) | Portability: bybit-volume-derived ratio threshold does NOT transfer (binance IS curve FALSE: ulcer 110 -> 134 champion); ALSO fails strict 6/6 on bybit via age10 OOS | 24.82 / 24.79 |
| **X** (parent risk_pct < 1.0 standalone) | Thin everywhere: binance OOS champion dNet -1.0 cell False; bybit age10 OOS 0 flags / 0.0 | 24.82 / 24.79 |
| **vol_target** (inverse-ATR sizing) | curve_better FALSE x3 (champ IS ulcer 14.62->29.82) despite net up 6/6 | 24.80 |
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
- CHECKLIST 24.78-24.82, LOG rows 84-87, EXPERIMENT_SUMMARY bullets
- Generator: built by script with anchor asserts; regenerate rather than edit figures.
