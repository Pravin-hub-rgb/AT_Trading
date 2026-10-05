# MASTER CANDIDATE TABLE — every live option, with full metrics

**Written 2026-09-27.** Compiled from `method/MASTER_LEADERBOARD.md`,
`signal/EQUITY_CURVE_STUDY.md`, `method/SIZING_CANDIDATES.md`, `method/CAPITAL_STAGE_PLAN.md`,
`signal/STRATEGY_SCORECARD.md`, `signal/WICK_1H_GATE_ADOPTION_RECORD.md`,
`method/WIN_STREAK_STACKING_AUTOPSY.md`, `signal/MARGINAL_PREENTRY_ATLAS.md`. No new runs.

**Legend** — Retention = OOS net ÷ IS net, annualised. `PASS30` = clears the
30% bar. `CURVE` = the pre-registered equity lens (curve better AND net not
hurt, both eras). `live` = computable at order-send time.

---

## 0. The one-screen summary

| # | candidate | lane | IS net | OOS net | retn | DD | PF | WR | CURVE | live | status |
|---|---|---|---:|---:|---:|---:|---:|---:|:--:|:--:|---|
| 1 | **STACK** half+delay1+skipD | multi | +429.6 | **+110.5** | — | **30.6** | 1.55 | — | ✅ | ✅ | **best documented** |
| 2 | **utcsat + half+delay1** | multi | +411.1 | +87.1 | — | 29.4 | 1.47 | — | ✅ | ✅ | strong |
| 3 | **utcsat_multi** (current) | multi | +358.9 | +60.2 | 32% | 22.1 | 1.58 | 29.6% | — | ✅ | shipped-king |
| 4 | **champion_multi** | multi | +325.8 | +70.1 | 41% | 37.3 | 1.59 | 28.0% | — | ✅ | shipped-primary |
| 5 | **wick gate** (gray) | multi | +28.1 | +19.8 | — | 0.00 cascade | — | — | ✅ | ✅ | forward 5/50 |
| 6 | **N3 global_soft** | multi | +331.7 | +90.0 | — | 43.2 | 1.74 | 29.0% | ✅ | ✅ | **excl. STACK** |
| 7 | **age10** | single | +435.7 | +43.2 | — | **8.6** | **7.93** | — | ✅ | ✅ | best curve, no stack |
| 8 | union ct=55 +filt | CRAZE | +267.6 | +53.7 | 20% | **6.0** | **2.92** | **40.0%** | ❌ | ✅ | fails PASS30 |
| 9 | entropy ct=55 +filt | CRAZE | +149.0 | +38.3 | 26% | — | **3.60** | **48.5%** | ❌ | ✅ | fails PASS30 |
| 10 | M2 sizing | all | +152.7 | +29.1 | — | — | — | — | — | ❌ | **bridge failed** |
| 11 | sMZX sizing | all | +346.5 | +130.4 | — | deeper | — | — | — | ❌ | stack-book +802.8/277.7 |
| 12 | ramp_mag sizing | all | +267.3 | +54.1 | — | — | — | — | — | ❌ | beats M2, no cross-venue |
| 13 | count_linear | all | +276.8 | +87.0 | — | — | — | — | — | ❌ | — |
| 14 | Z flags A/B/C | all | sizing | sizing | — | — | — | — | — | ❌ | correlated family |
| 15 | Z3 volume gate | all | — | −4.6 | — | — | — | — | ❌ | — | **retracted** |

---

## 1. MULTI lanes

`champion_multi_sw10` and `utcsat_multi_sw10` are the only two configs in the
repo that clear the retention bar.

### 1a. Base configs, true OOS retention

| config | IS net | OOS net | retention | PASS30 | OOS DD | OOS PF | OOS WR | verdict |
|---|---:|---:|---:|:--:|---:|---:|---:|---|
| **champion_multi_sw10** | +325.8 | **+70.1** | **41%** (53% causal) | ✅ | 37.3 | 1.59 | 28.0% | **PASS — conservative king** |
| **utcsat_multi_sw10** | +359.0 | **+60.2** | **32%** (49% causal) | ✅ | 22.1 | 1.58 | 29.6% | **PASS — king, best DD** |
| chopband_multi | +350.7 | +85.8 | 47% | ✅ | 29.1 | — | 29.0% | ❌ **REJECTED** — fails sw20, 2024-era only |
| fliponly_multi | +242.7 | −17.3 | −14% | ❌ | 46.4 | — | 18.4% | ❌ DEAD |

**Head-to-head (the two kings):**

| metric | IS champion | IS utcsat | OOS champion | OOS utcsat |
|---|---:|---:|---:|---:|
| NET R | +325.8 | **+359.0** | **+70.1** | +60.2 |
| trades | 500 | 454 | 279 | 253 |
| WR | 30.0% | 30.8% | 28.0% | 29.6% |
| PF | 2.38 | **2.62** | 1.59 | 1.58 |
| DD | 17.8 | **14.8** | 37.3 | **22.1** |
| NET/DD | 18.3 | **24.2** | 1.9 | **2.7** |

### 1b. Exit-side stack — the biggest documented improvement

`exp_trail_half=1` + `exp_trail_delay_r=1.0` + `exp_skip_decisive=1`. All three
flags already exist, default 0. **Reproduced 24/24 in log 113.**

| lane | arm | n | net | maxDD | DDdur | ulcer | sortino | calmar | m+% | streak | PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| champion IS | baseline | 500 | +325.8 | 27.7 | 72 | 14.62 | 328.3 | 3.20 | 51.1 | 16 | 1.81 |
| champion IS | half | 469 | +428.6 | 30.5 | 56 | 12.40 | 424.7 | 3.83 | 44.4 | 19 | 2.10 |
| champion IS | **half+delay1** | 466 | **+429.6** | 27.0 | 56 | 12.41 | 424.1 | **4.34** | 44.4 | 19 | **2.10** |
| champion IS | skip_decisive | 500 | +325.8 | 27.7 | 72 | 14.62 | 328.3 | 3.20 | 51.1 | 16 | 1.81 |
| champion IS | **STACK** | 466 | **+429.6** | 27.0 | 56 | 12.41 | 424.1 | **4.34** | 44.4 | 19 | **2.10** |
| champion OOS | baseline | 279 | +70.2 | 53.2 | 149 | 213.6 | 78.5 | 0.66 | 37.5 | 15 | 1.34 |
| champion OOS | half+delay1 | 271 | +89.8 | 46.3 | 132 | 242.2 | 95.9 | 0.97 | 37.5 | 15 | 1.42 |
| champion OOS | **skip_decisive** | 222 | **+99.3** | **33.8** | 127 | **82.7** | 111.2 | **1.47** | 40.9 | 15 | **1.62** |
| champion OOS | **STACK** | 217 | **+110.5** | **30.6** | 132 | 101.2 | 112.7 | **1.35** | 40.9 | 15 | 1.55 |
| utcsat IS | baseline | 454 | +358.9 | 21.2 | 40 | 11.55 | 364.9 | 4.62 | 53.3 | 13 | 2.01 |
| utcsat IS | half | 431 | +401.0 | 26.8 | 45 | 11.51 | 401.9 | 4.08 | 46.7 | 15 | 2.14 |
| utcsat IS | **half+delay1** | 428 | **+411.1** | 23.9 | **29** | **9.84** | 408.4 | **4.69** | 46.7 | **14** | **2.17** |
| utcsat IS | **STACK** | 428 | **+411.1** | 23.9 | 29 | 9.84 | 408.4 | 4.69 | 46.7 | 14 | **2.17** |
| utcsat OOS | baseline | 253 | +60.2 | 29.4 | 66 | 110.3 | 67.3 | 1.03 | 45.8 | 9 | 1.33 |
| utcsat OOS | half+delay1 | 244 | +87.1 | 29.4 | **48** | 187.3 | **94.5** | **1.48** | 33.3 | 9 | **1.47** |
| utcsat OOS | skip_decisive | 200 | +76.8 | **24.6** | 42 | **52.2** | 84.9 | **1.56** | 50.0 | 9 | 1.52 |
| utcsat OOS | **STACK** | 194 | **+94.6** | 29.2 | 42 | 90.5 | 95.2 | **1.47** | 50.0 | 9 | 1.45 |

**Champion STACK: OOS +70.2 → +110.5 (+57%), maxDD 53.2 → 30.6 (−42%).** On the
shipped lane, net and drawdown improve together, and **zero entries are removed
in IS** (n stays 500 on skip_decisive), so the Rule 18 slot-cascade cannot apply.

`skip_decisive` is a **perfect IS no-op** on both multi lanes — 0 decisive trades
in 2023–26. It cannot overfit the IS era because it cannot fire there. Its whole
evidence is 57 OOS trades removed.

### 1c. Wick gate — the gray mechanism

Short-only, `wick_atr12 < 6.026` on the 1h plane, GRAY (trade runs to
completion, P&L suppressed, `r = 0`).

| claim | value |
|---|---|
| net by cell | **+28.1 / +25.7 / +19.8 / +23.8R** (champIS / utsIS / champOOS / utsOOS) |
| Stage B parity | 4/4 exact to 1e-3, hard assert |
| cascade | **0.00 in all cells** |
| seq-identical | 6/6 |
| ex-best-trade robust | 6/6 cells still negative |
| stable window | 5.0–5.4 \| 5.6–6.4 (hole at 5.5) |
| upper cliff | 6.4 → 6.5 |
| IS trades removed | 0 (fires 0 times in IS) |
| **blocker** | **forward gate 5/50** |

**Implementation note that is a real bug risk:** the trade must book `r = 0`
**while still setting `busy_until`, cooldown and the loss streak.** Gating the
cooldown shipped in three harnesses and produced a spurious −44R that was
written up as a structural property of gray mode and later retracted
(`method/CAPITAL_STAGE_PLAN.md` a11). Costs are deducted in-harness but not live; that
gap is `cost_relief`, +17.6R on is/champion.

### 1d. Win-streak N3 — cannot stack with the above

`global_soft_n3` = after 3 completed global wins, block new entries in the
current parent HTF window.

| reference | period | default | + global N3 | Δ | + window N3 | Δ |
|---|---|---:|---:|---:|---:|---:|
| champion | IS | +325.8 | +331.7 | **+5.9** | +328.9 | +3.2 |
| champion | OOS | +70.2 | +90.0 | **+19.8** | +70.2 | 0.0 |
| utcsat | IS | +358.9 | +360.5 | +1.5 | +362.2 | **+3.2** |
| utcsat | OOS | +60.2 | +60.8 | +0.6 | +60.2 | 0.0 |

Champion detail — IS: 500→483 trades, R/trade 0.652→0.687, PF 2.38→2.46, DD
27.7→24.6, tail 17→16 10R+ trades. OOS: 279→262, R/trade 0.251→0.343, PF
1.59→1.74, DD 53.2→**43.2**, **OOS 10R+ tail preserved at 6**.

**`exp_n3_stack.py` (CHECKLIST 24.84): N3 does NOT transfer to the stack book.**
`stack+global_soft_n3` IS dNet **−29.7** on champion, negative on **all three**
stack lanes. IS blocks explode 17 → 56. **N3 and STACK are mutually exclusive.**

Not universal either: pure v18 multi −27.8R IS, fullstack single −38.1R IS.


## 2. SINGLE lanes

### 2a. age10 — the best curve in the repo, and it rejects the stack

`age10_dirmatch_swingpause_single_sw10`. No `exp_mltf`; dir-match + swingpause
filters; ~3.5× fewer trades.

| arm | n IS/OOS | IS net | IS DD | IS ulcer | IS calmar | IS streak | IS PF | OOS net | OOS DD | OOS PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **baseline** | 130 / 76 | **+435.7** | **8.7** | 3.94 | **13.61** | **5** | 7.57 | **+43.2** | **8.6** | **1.91** |
| half | 118 / 71 | +418.2 | 9.9 | 3.67 | 11.48 | 10 | 7.02 | +28.0 | 9.4 | 1.57 |
| half+delay1 | 117 / 71 | +422.6 | 8.8 | **2.15** | 13.15 | 7 | 7.07 | +27.5 | 9.5 | 1.56 |
| delay_r_1.5 | 128 / 75 | +431.3 | 8.7 | 2.33 | 13.45 | 5 | 6.89 | +41.2 | 8.6 | 1.84 |
| skip_decisive | 119 / 47 | +425.3 | 8.7 | 4.11 | 13.28 | 5 | **7.93** | +16.0 | 10.2 | 1.47 |
| **STACK** | 109 / 46 | +422.3 | 8.8 | — | — | — | — | **−0.3** | 12.5 | — |

**The stack destroys age10**: OOS +43.2 → **−0.3**. Every arm is CURVE FAIL or
net-hurt. `delay_r_1.5` is the only one that keeps the curve (DD 8.7, ulcer
2.33, calmar 13.45, streak 5, m+% 64.3) and it is OOS-positive at +41.2.

**age10 is a curve reference, not a place to bolt on trail tweaks.** Almost every
arm degrades it. It also cannot take the wick gate (single not multi, 3.5×
fewer trades, avgR +3.35 vs +0.65).

### 2b. Other single configs — all fail the retention bar

| config | IS net | OOS net | retention | PASS30 | OOS DD | OOS WR | verdict |
|---|---:|---:|---:|:--:|---:|---:|---|
| **king_single** (`fullstack_wage10_cd0`) | +310.7 | +16.9 | 10% | ❌ | 27.9 | 25.0% | fails retention |
| fullstack_single | +282.9 | +21.0 | 14% | ❌ | 25.4 | 25.5% | fails retention |
| wage12_single | +278.6 | +13.0 | 9% | ❌ | 19.1 | 25.3% | fails retention |
| wage10_swingpause_wskip_single | +282.9 | — | — | ❌ | — | 31.4% | single-king IS |
| swingpause_single_sw20 | +120.0 | — | — | ❌ | — | 30.8% | cooldown hurts |
| champion_single_sw20 | +90.1 | — | — | ❌ | — | 29.0% | — |
| champion_single_sw10 | +82.0 | — | — | ❌ | — | 26.3% | — |

**Every single-lane config fails PASS30 (9–14%).** The structural finding on
file: **multi > single on retention, 32–41% vs 9–14%, fewer filters.** The single
book is a curve reference, not a deployment candidate.

Causal-SL OOS (live-honest) improves only the multi kings: champion +70.1 →
**+80.0** (53% retention), utcsat +60.2 → **+72.8** (49%).

## 3. CRAZE lane — better risk, fails retention

| config | IS net | OOS net | retention | PASS30 | OOS DD | OOS PF | OOS WR | note |
|---|---:|---:|---:|:--:|---:|---:|---:|---|
| union ct=55 +filt | +267.6 | +53.7 | 20% | ❌ | **6.0** | **2.92** | **40.0%** | best CRAZE absolute |
| mag3+wknd+bm05 | +196.4 | +47.6 | 24% | ❌ | **4.0** | — | — | balanced years |
| mag3+wknd | +196.3 | +45.6 | 23% | ❌ | 4.0 | — | — | — |
| entropy ct=55 +filt | +149.0 | +38.3 | 26% | ❌ | — | **3.60** | **48.5%** | most consistent new mode |
| entropy ct=61 +filt | +161.2 | +31.4 | 19% | ❌ | — | 2.94 | 42.4% | within-era "king" |
| dualunion | +151.2 | +29.7 | 20% | ❌ | — | 2.67 | 36.4% | 2022 = −1.4R, refuted |
| b2_vs_flip ct=58 +filt | +106.6 | +19.5 | 18% | ❌ | — | 2.68 | 44.4% | — |
| b2_vs_flip ct=58 RAW | +122.1 | +13.0 | 11% | ❌ | — | — | 25.2% | only positive raw on true OOS |
| raw base | +217.9 | +9.9 | 4.5% | ❌ | 30.5 | — | — | 22× curve-fit |

**Highest-WR / lowest-DD family in the repo** — 40–48.5% WR and 4.0–6.0R OOS DD
against the multi kings' 28–29.6% and 22–37R. They fail only the retention
proxy. Per `method/IS_IT_RIGHT.md`, that proxy measures *provenance*, not
*survivability* — and a 6.0R DD book mathematically cannot have a 16-trade losing
streak. Not adoptable, but the master table ranks by net R, which is not the
question that now matters.

| max consec losses | 16 | 13 | 15 | **9** |
| Sharpe | 3.59 | **3.77** | 1.88 | 1.75 |
| worst 12m | +26.4 | **+44.2** | −29.9 | **−6.7** |

## 4. Portfolio-state split — descriptive, but the strongest recurring one

`signal/MARGINAL_PREENTRY_ATLAS.md` Stage 44 marks every entry with the state of the
positions already open at that instant.

| reference | era | bucket | n | net R | avgR | WR | PF |
|---|---|---|---:|---:|---:|---:|---:|
| champion multi | IS | first | 379 | +201.5 | +0.532 | 26.6% | 1.63 |
| champion multi | IS | green add-on | 112 | +109.6 | +0.979 | 38.4% | 2.44 |
| champion multi | IS | red add-on | 7 | +17.2 | +2.451 | 85.7% | 76.08 |
| **champion multi** | **OOS** | **first** | 210 | **−12.5** | −0.060 | 24.8% | **0.92** |
| **champion multi** | **OOS** | **green add-on** | 61 | **+42.2** | +0.693 | 34.4% | **2.08** |
| BASE multi | OOS | first | 183 | +1.5 | +0.008 | 21.9% | 1.01 |
| BASE multi | OOS | green add-on | 26 | +34.9 | +1.341 | 38.5% | 3.44 |

**Champion OOS first entries are −12.5R at PF 0.92; add-ons are +42.2R at
PF 2.08.** Same direction on BASE and utcsat. Green add-ons are profitable in
*every* multi cell and both eras. But red add-ons were *also* profitable, so
blocking red fails, and no prospective gate was justified. **Descriptive only** —
recorded because it is the largest recurring portfolio effect in the repo and it
sits on the shipped lanes.

## 5. Sizing overlay — all five blocked at the bridge

| # | candidate | rule | dNet IS/OOS (3 lanes) | backtest | cross-venue | live? |
|---|---|---|---|:--:|:--:|:--:|
| 1 | **M2** | ×1.5 if `cur_mag_atr >= 3.0` | +152.7/+29.1, +147.5/+31.3, +113.0/+21.3 | 6/6 | **6/6 Binance** | ❌ |
| 2 | sMZX | ×1.5^count on M2/ZC/X | +346.5/+130.4, +341.2/+146.6, +270.3/+29.9 | 6/6 | — | ❌ |
| 3 | uMZX | ×1.5 if any(M2,ZC,X) | +165.5/+49.5, +171.3/+56.8, +145.9/+19.2 | 6/6 | **6/6 Binance** | ❌ |
| 4 | ramp_mag | `clamp(1+0.25(mag−2),1,2)` | +267.3/+54.1, +260.3/+53.6, +201.0/+26.1 | 6/6 | — | ❌ |
| 5 | count_linear | `1+0.5·count`, cap 2.0 | +276.8/+87.0, +280.2/+100.2, +228.8/+26.4 | 6/6 | — | ❌ |

M2 per-lane: champion +153.5/+31.5 curve pass both; utcsat +131.0/+30.8 pass
both; **age10 +117.1/+18.8 pass both.** Flagged 19–29% of the book, carried
35–50% of the monsters.

**All five blocked on one root cause.** `cur_mag_atr` uses `seg.end_px`, which is
**forward-looking** — `backend_check_wd_days.py:108` asserts
`fs_at_idx >= seg.end_idx`. Order-send agreement **46.5% against a 95% bar**.
`exp_m2_sendtime_feature.py` then built `mag_so_far` / `ramp_so_far` and
re-validated: **0/6 clear.** The doc's own conclusion: *"a new feature would be
needed, not a reparameterisation."*

Stack-book figures: sMZX on champion stack **429.6 → 802.8 IS / 110.5 → 277.7
OOS**. `vol_target` fails on both books — closed.

**M1 (`cur_start <= 1`) must never be adopted** — flags 71–88% of trades, its
"gain" is leverage on an already-positive book, flagged avgR is *worse* in key
cells. CHECKLIST 24.58 calls it a leverage trap.

## 6. Z flags — sizing only, one correlated family

| flag | threshold | IS edge | monotone |
|---|---|---|---|
| A `er50` | ≤ 0.0767 | low ER50 = choppy tape wins | 3/4 |
| B `wick_gt3x_pct12` | > 33.3 | high wick>3×body = rejection/indecision | **4/4** |
| C `vol7_prev7` | ≤ 0.846 | declining 7d-vs-prev-7d participation wins | **4/4** |

Pooled: `er50` IS ≤0.08 → +1.62 vs >0.18 → +0.47; `wick_gt3x_pct12` IS >33.3 →
+1.27 vs ≤25 → +0.92; `vol7_prev7` IS ≤0.85 → +1.70 vs >1.06 → +0.72.

**Deploy at most one** — A/B/C mark the same quiet tape, flagged sets overlap
heavily, union is 63–65% of the book.

**The Z3 volume gate is RETRACTED**: post-process PASS, path-true rerun **FAIL
3/6** with champion OOS **sign-flipping** (+3.6 → −4.6). Only sizing flags
survive.

## 7. Rejected — do not revisit

| item | why |
|---|---|
| fliponly_multi | −17.3R OOS |
| dualunion | 2022 −1.4R |
| chopband | fails sw20 validation; 2024-specific |
| B3, room filter, wick reject, ER, risk-width | per-trade gates; all fail full-path |
| wage + mag, swingpause + mag | hurt OOS when stacked with mag3 |
| htf_dir / htf_mag / ltf_dir routing | dead raw; signal-property routing fails |
| raw v18 base | 22× IS/OOS — curve-fit |
| `halt_skip=2` / posthalt3 | trade-list said +18/+11, full-path cascade −3 IS / −7 OOS |
| MAE surgery (BE / half-SL / dead-exit) | all kill winners path-true |
| B2-stale age cut | IS −21.9 / OOS +50.2 — does not transfer |
| pre-entry alignment (dir/age) | era-fit |
| adaptive kind gates (K1/K2/K3) | fail absolute R both eras |
| first-of-window-streak cut | weak WR both eras |
| ATR trail | already dead, do not re-open |
| MA20/30/40 vs MB50 | every alternative gains OOS, loses IS |
| 3%+ fine-SL gray gate | −21R, 0/36 arms pass |
| wide-SL sizing (a8) | avgR inverted 5/6, 0.0th pct vs random null |
| SL reclaim re-entry | dead 8/8 — reclaim triggers now 4/4 dead |
| exp_5m_confirm (log 111) | 0/36 improved, all net-negative |
| 30m/2h agreement predicates | Rule 17 — thread exhausted |

## 8. The binding constraint

**Forward n = 5/50**, pre-registered (`method/FORWARD_TEST_PLAN.md`, CHECKLIST 24.70).
First read: **R1 PARITY PASS / NO VERDICT (n=5).** Study 2 (deflated statistics)
splits by era: **IS passes, OOS fails.**

Every candidate above is blocked on this one number. It accrues passively and no
backtest clears it.

## 9. One open, already-diagnosed task

`method/CAPITAL_STAGE_PLAN.md` a11: the gray cooldown-suppression bug
(`if cooldown_bars > 0 and r_multiple < 0 and not _isgray`) is **still present**
in `exp_sl_width_gate.py` and `exp_sl_fine_cascade.py`. The doc says their
gray-mode conclusions are affected and should be **re-run before quoting**. Both
a9 (SL-width ladder) and a10 (3%+ gate) gray results are therefore flagged.

| OOS years | — | — | −11 / +117 | **+13 / +80** |
| tail −top10 | −3.3 | **+29.8** | −67.9 | −66.0 |

**utcsat wins on every risk dimension**; champion wins on absolute OOS R by one
bad year (2021 = −11) it didn't filter. Recommendation on file: **utcsat is the
better default, champion the no-calendar fallback.** The UTC-Saturday skip is
the structural edge separating them.
