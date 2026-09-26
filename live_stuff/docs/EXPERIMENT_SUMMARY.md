# Experiment Summary — Mode-Level Sweep (2026-09-22)

## For the Other Bot

You proposed 5 ideas for mode-level alternatives. We implemented and tested **all 5**, plus 2 additional variations. Here are the results.

---

## The B2 vs FLIP Finding (Your Most Important Insight)

This is confirmed and documented in `STRATEGY_STATE_OF_PLAY.md` Section 7A.

| Signal | IS | OOS | Verdict |
|---|---|---|---|
| **B2** | 185t +14.7R / DD 43.1 | 90t **+38.8R** / DD 8.6 | **ROBUST** |
| **FLIP** | 159t **+193.6R** / DD 15.0 | 81t **-18.4R** / DD 19.0 | **CURVE-FITTED** |

The IS profit is inflated by FLIP. B2 is the only OOS-robust signal type. This changes everything about how we think about the engine.

---

## Your 5 Ideas — Results

### Idea 1: B2-only mode (`htf_dir` — actually we used direction, not pure B2-only)
- **What we tested:** 1h swing direction selects B2/FLIP windows. UP → B2, DOWN → FLIP.
- **Raw OOS: -52.2R** — DEAD
- **With mag3+wknd+bm05: +41.4R** — marginally better than baseline (+42.4R) but worse
- **Verdict: DEAD.** Swing direction is too correlated with trend, overtrades in wrong direction.

**Note:** Pure B2-only was also tested earlier via `b2_vs_flip_chop` at ct=0 (all chop → always B2). Raw OOS: **-13.9R**. Dead. B2 alone doesn't work — the regime split IS the edge.

### Idea 2: Window UNION (`union`) — **NEW KING**
- **What we tested:** Every 15m signal checked against BOTH B2 and FLIP HTF windows simultaneously.
- **Raw OOS: -12.0R** — Dead raw (too many trades)
- **With mag3+wknd+bm05: +63.2R OOS** — **BEST RESULT OF THE SESSION**
- **How it works:** The original `b2_vs_flip_chop` restricts entries to one window set (B2 in chop, FLIP in trend). The union mode opens both windows. The mag3 filter then selects the high-conviction trades from the combined pool.
- **Why it works:** There are profitable B2 trades inside FLIP windows and vice versa. The original mode was throwing them away by restricting to one window set. The union captures these cross-window opportunities.
- **Concern:** 2021 +51.2R vs 2022 +12.0R (asymmetric). More investigation needed.

**Full numbers:**
```
union + mag3+wknd+bm05:
  IS:  124t, +288.4R, DD=7.5, NET/DD=38.31
  OOS:  55t, +63.2R, DD=6.0, NET/DD=10.53
  IS/OOS: 4.6x
  2021: +51.2R | 2022: +12.0R
```

### Idea 3: 1h swing magnitude selector (`htf_mag`)
- **What we tested:** Large 1h swing (>0.5%) → B2 windows. Small → FLIP windows.
- **Raw OOS: -13.9R** — DEAD
- **With mag3+wknd+bm05: +33.8R** — worse than baseline
- **Sweep across thresholds (0.002 to 0.015):** All negative or marginal. Best was +16.2R at mag>0.012 (raw).
- **Verdict: DEAD.** The magnitude doesn't help select the mode. The chop indicator captures something magnitude doesn't.

### Idea 4: 15m swing direction selector (`ltf_dir`)
- **What we tested:** 15m chain's last confirmed swing direction selects B2/FLIP.
- **Raw OOS: -29.3R** — DEAD
- **With mag3+wknd+bm05: +12.1R** — terrible
- **Verdict: DEAD.** 15m direction is too noisy and reactive.

### Idea 5: Dynamic chop threshold (`dynamic_chop`)
- **What we tested:** Instead of fixed chop threshold, use rolling percentile. When chop is at the 83rd-84th percentile of its 28-day distribution → B2 windows.
- **Raw OOS: +50.8R at pct>84** — **RUNNER-UP**
- **With mag3+wknd+bm05: +49.2R at pct>83** — still strong
- **How it works:** The adaptive threshold adjusts to the current chop regime. When chop is relatively high compared to recent history, B2 windows are used. When chop is relatively low, FLIP windows. Same structural edge as fixed threshold, but adapts automatically.
- **IS/OOS ratio: 3.8x** — less curve-fitted than baseline (4.4x)
- **Concern:** Sensitive to exact percentile. pct>84 gives +50.8R, pct>85 drops to +18.8R.

**Fine sweep (raw base):**
```
pct>78: OOS +38.5R  DD 25.3
pct>80: OOS +45.7R  DD 23.5
pct>81: OOS +46.9R  DD 21.3
pct>82: OOS +47.8R  DD 21.4
pct>83: OOS +47.6R  DD 17.8  ← best DD
pct>84: OOS +50.8R  DD 19.2  ← best NET
pct>85: OOS +18.8R  DD 20.1  ← cliff
```

---

## 2 Additional Ideas Tested

### Inverted htf_mag (`htf_mag_inv`)
- **What we tested:** Large 1h swing → FLIP windows (strong reversal). Small → B2 windows (continuation).
- **Raw OOS: +16.2R at mag>0.012** — marginal
- **With mag3+wknd+bm05: +40.8R** — slightly below baseline
- **Verdict: Marginal.** Not worth pursuing.

### FLIP Quality Gate (`flip_quality`)
- **What we tested:** B2 windows always allowed. FLIP windows only when previous 1h swing was large (above threshold).
- **Raw OOS: +23.2R at ct=60** — same as b2_vs_flip_chop at ct=60
- **With mag3+wknd+bm05: +46.2R at ct=60** — slightly above baseline (+42.4R)
- **Verdict: Marginal.** The quality gate helps slightly but doesn't beat union or dynamic_chop.

---

## Complete Results Table (all modes, with mag3+wknd+bm05)

| Mode | IS_n | IS_NET | OOS_n | OOS | OOS DD | N/D | IS/OOS |
|---|---|---|---|---|---|---|---|
| **union + filters** | **124** | **+288.4R** | **55** | **+63.2R** | **6.0** | **10.53** | **4.6x** |
| flip_quality ct=60 + filters | 83 | +184.3R | 32 | +46.2R | 4.0 | 11.55 | 4.0x |
| baseline ct=58 + filters | 82 | +188.4R | 32 | +42.4R | 4.0 | 10.61 | 4.4x |
| htf_mag_inv + filters | 82 | +192.3R | 32 | +40.8R | 4.0 | 10.20 | 4.7x |
| dynamic pct>83 + filters | 79 | +187.3R | 33 | +49.2R | 4.0 | 12.30 | 3.8x |
| htf_dir + filters | 89 | +174.5R | 35 | +41.4R | 7.0 | 5.92 | 4.2x |
| flip_quality ct=40 + filters | 75 | +160.3R | 33 | +39.2R | 5.0 | 7.86 | 4.1x |
| htf_mag + filters | 74 | +160.9R | 34 | +33.8R | 7.0 | 4.85 | 4.8x |
| ltf_dir + filters | 82 | +175.8R | 30 | +12.1R | 8.6 | 1.41 | 14.5x |

---

## Why Ideas 1, 3, 4 Fail

They use **signal properties** (direction, magnitude) to select the mode. The edge is specifically about the **market regime** (choppiness), not the signal itself. The chop indicator captures something about market structure that direction and magnitude don't.

**The structural insight:** B2 (confirmation) works in choppy markets. FLIP (reversal) works in mild chop. Neither works everywhere. The chop-based switch is the correct mechanism. Ideas that try to replace chop with something else lose the edge.

## Why Union + Filters Works

The union mode allows entries in BOTH B2 and FLIP HTF windows simultaneously. The mag3 filter then selects the high-conviction trades from both pools.

**The key insight:** There are profitable B2 trades inside FLIP windows and vice versa. The original `b2_vs_flip_chop` mode was throwing them away by restricting to one window set. The union captures these cross-window opportunities.

The reason union fails raw (-12.0R) but succeeds with filters (+63.2R) is that the union doubles the opportunity pool, including many noise trades. The mag3 filter (which removes small swings < 3x ATR) eliminates the noise and keeps only the high-conviction entries from both window sets.

---

## Current Best Config

```
mode=union, ext_stop_r=1.5, chop_thresh=61.8, cooldown_bars=10
exp_skip_weekend=1, exp_min_swing_ratio=3.0, exp_bias_momentum_min=0.5

IS:  124t, +288.4R, DD=7.5, NET/DD=38.31
OOS:  55t, +63.2R, DD=6.0, NET/DD=10.53
2021: +51.2R | 2022: +12.0R
IS/OOS: 4.6x
```

**Baseline to beat: +63.2R OOS with similar or better DD.**

---

## NEW: Creative Idea Sweep (2026-09-22)

After testing your 5 ideas, we brainstormed 12 more creative directions (AI-assisted). Three needed no new data and were implemented directly in the engine:

### Entropy mode (Idea L) — NEW KING
- Routes based on Shannon entropy of 1h returns
- Low entropy → B2 (predictable), High entropy → FLIP (random)
- **Raw OOS: +104.9R** (IS/OOS=0.71, anti-overfit)
- **Filtered OOS: +82.3R** (IS/OOS=1.31, PASS)
- **Beats union (+63.2R) by +19.1R OOS**

### Fractal Dimension mode (Idea K)
- Routes based on Hurst exponent of 1h candles
- **Raw OOS: +122.6R** (IS/OOS=0.95, anti-overfit)
- **Filtered OOS: +75.2R** (IS/OOS=1.42, PASS)

### Session mode (Idea H)
- Routes based on time-of-day (Asia→B2, London/NY→FLIP)
- CT-insensitive
- **Raw OOS: +83.1R** (IS/OOS=1.62)
- **Filtered OOS: +74.7R** (IS/OOS=0.97, anti-overfit)

### Full Results (sorted by OOS)
```
RAW:
  b2_vs_flip ct=65   Net +143.6  Ratio 0.77 ANTI
  fd ct=70           Net +151.9  Ratio 0.95 ANTI
  fd ct=58           Net +133.9  Ratio 0.85 ANTI
  entropy ct=50      Net +143.5  Ratio 0.94 ANTI
  entropy ct=61      Net +91.9   Ratio 0.71 ANTI

FILTERED:
  entropy ct=61      Net +161.2  Ratio 1.31 PASS  <-- KING
  entropy ct=65      Net +169.4  Ratio 1.42 PASS
  fd ct=50           Net +157.1  Ratio 1.42 PASS
  union ct=55        Net +254.3  Ratio 3.00 FIT (overfit risk)
```

---

## What's Left

- [x] Test Ideas B (funding rate), A (HMM) — DEAD
- [x] Test Ideas D (ensemble), E (transition detection), F (GARCH) — all DEAD as universal improvements (2026-09-23)
- [x] Test Idea G (ETH/BTC ratio) — DEAD (2026-09-23)
- [x] B3 structure confirmation — DEAD both-sides (2026-09-23)
- [x] Swing engine mismatch (#1) — FIXED 2026-09-23 (PSE re-feed stitch = compute_btc_swings; 15m 87/87, 1h 118/118 PERFECT; identity green). Replay harness still 0/29 = Issue #10 (30d rolling window), not engine.
- [x] Live 30d rolling window vs full-history chains (Issue #10) — FIXED 2026-09-23: L1 open-HTF kept in `to_intervals`, L3 `_rebase_swings_to_window` + L5 open-swing append in live_loop; seed depth 20.8d = 100% match, continuous PSE 99.9%, windowed sim 83.3% reproduction (was 0%); smoke 351t/+211.7R PASS. Harness `exp_issue10_window.py`.
- [ ] Test Idea C (OI change) — DROPPED (user: no 2023 OI data)
- [x] Volume data re-fetch — DONE 2026-09-23 (`refetch_with_volume.py`, Bybit linear): 15m/1h/5m/4h/1m all ~99.9% non-zero volume; loaders + smoke 351t/+211.7R + identity 340t/+225.3R all green
- [x] Volume autopsy + path-true gates — DEAD 2026-09-24 (trade-list B2-low-rvol/pct-Q1 looked good; path-true fails both-sides on champion/king/swingpause; winners vs losers volume medians identical). OOS volume also re-fetched (unseen 15m/1h). Harnesses `exp_volume_autopsy.py` / `exp_volume_path.py`.
- [x] Volume trail/exit + router (dry-hold exit/BE, no-spike abort, climax, quiet↔flip router) — DEAD 2026-09-24 (loss autopsy shows dry holds lose / flood holds win, but every path-true variant fails both-sides: router dIS −206, dry-exit dIS −93, nospk dIS −59; climax no-op on fine path). Smoke 351t/+211.7R PASS. Volume family fully closed. Harness `exp_volume_trail_path.py`.
- [x] A4 pullback gate (skip 1.5–3R off leg extreme) — DEAD 2026-09-24 (autopsy avgR −0.54 n=24 looked good; path-true A4 dIS −67..−252 all thresholds, lb30 OOS +27 but dIS −62 fails both-sides). Price-space gates (legskip + pullback) both closed. Harness `exp_pullback_path.py`.
- [x] Fast-death pre-entry proxy (LOSS_AUTOPSY §4) — DEAD 2026-09-24 (104 fast deaths all exactly −1R; best fast% bins are either already-dead families or have monster slow cohorts — no causal feature separates without killing runners; +100R ceiling remains theoretical). Harness `exp_fastdeath_autopsy.py`.
- [x] Era-specific behavior investigation (State-of-Play §11) — DIAGNOSED 2026-09-24: 2021 is the bleed year (not 2022); OOS-ex-FTX ≈ flat (champ +8.1 / king −4.3) so OOS edge is crisis-alpha; FLIP avgR collapses −1.16 both bases while B2 holds; longs die OOS / shorts improve; market ATR 1.6–2× higher; mid-holds flip. No era-hardcode gate proposed (would kill IS longs). Harness `exp_era_split_autopsy.py`.
- [x] HTF lb=20 granularity sweep (exp31_lb 14/20/30) — NO-OP 2026-09-24 (champion/king/swingpause all mode=atr_high; chop lookback does not affect ATR%-based routing; identical results all lb). lb family closed on production path. Harness `exp_remaining_ideas.py`.
- [x] Structure Evolution path-true (swing mag/frequency gates) — DEAD 2026-09-24 (mag_min 0.80/1.00 kills IS −60..−122 on swingpause, worse on multi; freq_max no-op — formula yields ≪4). Kwargs `exp_struct_mag_min`/`exp_struct_freq_max` KEPT default-off.
- [x] MTF Regime path-true (1h swing dir confirm, exp_mtf_mode 1/2) — DEAD 2026-09-24 (multi OOS up but IS collapses; swingpause mode=1 dIS −18 / dOOS +67.9 fails both-sides). Same family as 1h-momentum/htf4-confirm. Kwargs `exp_mtf_mode` KEPT default-off. Harnesses `exp_remaining_ideas.py` + `exp_remaining_finish.py`.
- [x] Mean reversion / compression — CLOSED 2026-09-24 (entry-quality budget §3h; MR lookahead-broken in test_new_paradigms.py; compression no edge; not run path-true).
- [x] B3 limit-order salvage (b3_mode=limit, retrace-to-signal-close) — DEAD 2026-09-24 (multi dIS −160/−173 all k; swingpause only both-sides pass +8.5/+14.4 ≈ 2R/yr ≪ +30R/yr ship, absolute OOS still −2.6; k=4/8/12 identical — fills cluster ≤4 bars). Closes B3 both-sides family. Kwargs `b3_mode` KEPT default-off. Harness `exp_remaining_finish.py`.
- [x] (i) anchor-lb30 stress battery + per-year/both-halves — DONE 2026-09-24 (`exp_closeout_battery.py`): lb30 w0 n=349 NET +170.5 WR 27.5% PF 1.59 PIN OK; per-year 2023 −1.0 / 2024 +95.6 / 2025 +27.3 / 2026 +48.5 (all-years-positive FAIL — 2023 −1.0 ≈ breakeven); both-halves PASS H1 +69.0 / H2 +101.5; cost ×1.5 +133.7 / ×2.0 +96.9 / ×3.0 +23.3 all positive. Pins re-baselined post-`ee574f9` trail-ordering fix (fine nets ~−26R).
- [x] (ii) concurrency-cap design for mltf leaders — DONE 2026-09-24: offline N4 cap3 on their-OPTIMAL +4.3R / −1.5R DD (+326.8 NET / DD 21.8) + path-true `exp_maxconc_path.py` cap5 FREE (champion/king dIS +1.1 / dOOS 0.0). Design pick: offline cap3 + path-true exp_max_concurrent=5 as live risk limit.
- [x] (iii) cd0 latency validation for OPTIMAL — DONE 2026-09-24 (`exp_closeout_battery.py`): OPT-cd0 n=515 NET +296.7 — no latency collapse vs cd10.

---

## Untested Families (backlog) — added 2026-09-25

Entry-side re-entry/timing families are exhausted; these remain GENUINELY untested (position-sizing / add-on class):

- [ ] **Pyramid / scale-in** — add to a WINNING open trade at causal add-triggers (e.g., new 15m swing confirm, +1R milestone). Zero experiments ever run; engine has no add mechanic (single fill per trade). Would need: add-fill path, split exits, per-add risk accounting.
- [ ] **Revenge re-entry at the ORIGINAL entry level** — after SL, re-enter at the original entry price (Phase B limit-fill touched this on the WAIT side; entry-after-loss at same level with original SL not run standalone).
- [x] **Same-window second entry AFTER a WIN** — **TESTED + CLOSED as gate 2026-09-25** (cohort study, era-flip: IS rewin = book engine (+282R), OOS rewin negative (−13R); drop-rewin helps OOS, destroys IS — no both-sides filter; age10 rewin + both eras but n=6+6; see checklist 24.61, log 54, harness `exp_rewin_cohort.py`).
- [x] SL-candle reclaim re-entry (break of the SL-giving 15m candle) — **TESTED + DEAD 2026-09-25** (Phase 1 descriptive gate, 8/8 cells negative; see SL_RECLAIM_REENTRY.md, checklist 24.38, log row 32).
- [x] Dip-then-reclaim confirmation entry — **TESTED + DEAD 2026-09-25** (checklist 24.34, log row 24).
- [x] Retest limit-below-entry fill — OPEN CANDIDATE (exp_retest_fill=0.25, age10 lane only, default-off).

---

## M2 Bigleg Sizing — Deployment Note (added 2026-09-25)

**Survivor:** entry-causal flag `cur_mag_atr >= 3` (swing magnitude ≥ 3 ATR at entry) → size ×1.5 on flagged trades (16–29% of the book). Post-process backtest (R-unit sizing, trade list byte-identical): **6/6 cells net+ both eras, curve_better TRUE all** — champion dNet +153.5/+31.5 (calmar 4.34→5.45 / 1.81→2.31), utcsat +131.0/+30.8, age10 +117.1/+18.8; ulcer down everywhere, DD never meaningfully worse. First surviving new-edge candidate of the 2026-09-25 session (checklist 24.60, log 53, harness `exp_m2_size_phase2.py`, JSON `_m2_size_phase2_results.json`).

**USER NOTE (2026-09-25): this is a capital-scaling lever — apply WHEN CAPITAL HAS GROWN.** With present capital keep normal 1× sizing everywhere. Once the account justifies larger notionals, this is the pre-approved sizing rule: **1.5× lot on bigleg setups (swing ≥3 ATR), 1× on everything else** — flag is known at signal time, so it is live-implementable with no look-ahead; SL/trail/partial logic unchanged. Deployment = order-time sizing only; no engine change needed.

*Document generated 2026-09-22. All numbers on post-trail-ratchet-fix engine.*

---

## Edge Sizing Candidates - Stage X / Stage Y / Stage Z Test Record (added 2026-09-25)

Context: user-approved HTF research batch V -> W -> X -> Y (2026-09-25). From it, **two new
entry-causal sizing flags were tested as edge candidates** (post-process x1.5 on flagged
trades, trade list byte-identical, engine untouched). Both are recorded here as CANDIDATES.
**The final "which is better" comparison (X vs Y vs Z vs M2 vs B bigleg, risk-adjusted) COMPLETED 2026-09-26 - see the Comparison section at the end of
this file.** Nothing adopted yet (RESEARCH_POLICY: no automatic gate).

### Candidate X - parent-window risk_pct < 1.0%  (checklist 24.71, log 71)

Flag: child trade's governing 1h window has stop distance < 1.0% of price (known causally at
window open; parent-map coverage 99.8-100%). Flagged share: 9.2%/8.6% IS, **2.5%/3.6% OOS**.
Origin: 1h break-quality study (5 measures), only this one did not era-flip.

| cell | flag | net baseline -> arm (delta) | maxDD | ulcer | calmar | PF | curve |
|---|---|---|---|---|---|---|---|
| IS champion | 46/500 | 325.8 -> 349.6 (**+23.9**, +7.3%) | 27.7->29.7 (+2.0) | 14.62->11.59 | 3.202->3.205 | 1.81->1.85 | TRUE |
| IS utcsat | 39/454 | 359.0 -> 382.3 (**+23.4**, +6.5%) | 21.2->22.2 (+1.0) | 11.55->9.06 | 4.619->4.698 | 2.01->2.04 | TRUE |
| OOS champion | 7/279 | 70.2 -> 106.8 (**+36.6**, +52%) | 53.2->50.4 (-2.8) | 213.61->212.61 | 0.659->1.060 | 1.34->1.52 | TRUE |
| OOS utcsat | 9/253 | 60.2 -> 99.7 (**+39.5**, +66%) | 29.4->28.3 (-1.1) | 110.29->100.05 | 1.025->1.762 | 1.33->1.54 | TRUE |

**PASS 4/4 on the pre-registered rule (dNet>0 AND curve_better in all 4 multi cells) WITH the
PRE-REGISTERED SMALL-N CAVEAT: OOS flag = 7 and 9 trades only.** IS side: net +6-7% but DD
deepens 1-2R; OOS side: big uplift AND DD improves. Companion gates (skip risk_pct 1-2%, skip
vol_ratio<0.75) both era-flipped -> closed. Harness `exp_htf_break_sizing.py` ->
`_htf_break_sizing_results.json`.

### Candidate Y - ema4h_bucket = pullback_toward_ema  (checklist 24.72, log 72)

Flag: entry-causal 4h EMA20 extension state - price sitting between the EMA and -0.5 ATR
below it (pulling back INTO the 4h EMA). Flagged share: 13-15% of the book, ALL cells
(healthy n: 71/60/29 IS, 42/37/21 OOS). Origin: Stage 12 boundary/EMA autopsy open item
("positive both eras all three, not adopted without pre-registered path-true test");
Stage-12 descriptives reproduced EXACTLY (6/6) as pre-flight sanity.

| cell | flag | net baseline -> arm (delta) | maxDD | ulcer | calmar | PF | curve |
|---|---|---|---|---|---|---|---|
| IS champion | 71/500 | 325.8 -> 384.5 (**+58.7**, +18.0%) | 27.7->30.0 (+2.3) | 14.62->15.02 | 3.202->3.486 | 1.81->1.91 | TRUE |
| IS utcsat | 60/454 | 358.9 -> 419.1 (**+60.1**, +16.7%) | 21.2->24.9 (**+3.7**) | 11.55->11.83 | 4.619->4.592 (-0.027) | 2.01->2.12 | **FALSE** |
| IS fullstack (ref) | 29/200 | 310.7 -> 362.7 (+52.0, +16.7%) | 14.0->14.5 (+0.5) | 11.22->11.42 | 6.044->6.812 | 2.99->3.20 | TRUE |
| OOS champion | 42/279 | 70.2 -> 89.0 (**+18.9**, +26.9%) | 53.2->53.6 (+0.4) | 213.61->**145.46** | 0.659->0.831 | 1.34->1.41 | TRUE |
| OOS utcsat | 37/253 | 60.2 -> 81.2 (**+21.0**, +34.9%) | 29.4->26.2 (-3.2) | 110.29->82.29 | 1.025->1.548 | 1.33->1.42 | TRUE |
| OOS fullstack (ref) | 21/140 | 16.9 -> 30.7 (+13.8, +82%) | 37.3->39.7 (+2.4) | 60.05->52.66 | 0.226->0.387 | 1.15->1.25 | TRUE |

**FAIL on the strict pre-registered rule (3/4 multi cells): IS utcsat curve_better = FALSE**
(all three curve components marginally negative: maxDD +3.7R deeper, ulcer +0.28, calmar
-0.027) even though **dNet>0 in ALL 6 cells**. Companion arms closed: skip aligned_far_extended
(IS -66.5/-72.5 vs OOS +5.0/+14.6 = era-flip), skip opposite_ema (removal negative 4/4 multi -
opposite_ema is path-true PROFITABLE; the Stage-12 "fade far from EMA" reading is CLOSED),
A+B combo (IS bleed dominates). Harness `exp_ema4h_pullback_sizing.py` ->
`_ema4h_pullback_sizing_results.json`.

### Candidate Z - regime-structure flags A/B/C (checklist 24.73, log 75)

Flag: three entry-causal 1h structure conditions from the 24-feature Z1 regime-structure
autopsy (pre-registered survivor rule: same-sign 4/4 cells + monotone >=3/4 + n>=15; 3/24
survived; tercile edges IS-pooled, applied unchanged to OOS):
- **Z-A:** `er50 <= 0.0767` - 50-bar 1h Kaufman efficiency ratio, low = choppy tape. ~33% flagged.
- **Z-B:** `wick_gt3x_pct12 > 33.3` - share of last 12 1h bars whose total wick > 3x body
  (rejection-heavy / indecision tape). ~24% flagged.
- **Z-C:** `vol7_prev7 <= 0.846` - rolling 7d volume below prior 7d (participation contracting).
  ~33% flagged.

| cell | flat net | Z-A delta (n) | Z-B delta (n) | Z-C delta (n) | curve A/B/C |
|---|---|---|---|---|---|
| IS champion | 325.8 | **+110.3** (167) | **+74.1** (121) | **+106.5** (166) | TRUE/TRUE/TRUE |
| IS utcsat | 358.9 | **+110.5** (142) | **+71.9** (112) | **+112.3** (146) | TRUE/TRUE/TRUE |
| OOS champion | 70.2 | **+17.3** (84) | **+18.3** (70) | **+32.2** (81) | TRUE/TRUE/TRUE |
| OOS utcsat | 60.2 | **+23.4** (81) | **+23.4** (62) | **+40.4** (76) | TRUE/TRUE/TRUE |

**PASS 4/4 on the pre-registered rule (dNet>0 AND curve_better in all 4 multi cells) for ALL
THREE flags, no small-N (flagged n 62-167).** Equity nuance: maxDD is deeper in every one of
the 12 cells (0.4-8.6R; worst: Z-C OOS champion 53.2->61.8, Z-A IS utcsat 21.2->26.7) - the
curve passes via ulcer/calmar/sortino improvements (e.g. Z-A IS ulcer 14.62->12.38, Z-C OOS
calmar 0.659->0.828), except Z-C IS champion ulcer mildly worse (14.62->15.62, calmar carries
it). Companion gate D (skip vol7_prev7>1.064) FAILED era-flip as predicted (IS -71.5/-67.2
curve False, OOS +10.8/+23.4) -> closed. Harness `exp_regime_structure_sizing.py` ->
`_regime_structure_sizing_results.json`; full record `REGIME_STRUCTURE_AUTOPSY.md`.

**Z3 trade-reduction gate (checklist 24.74, log 77):** user goal pre-registered (500 ->
~400ish trades, avg R/trade same-or-better) tested as keep `vol7_prev7 <= thr` for 10
thresholds x 4 cells (`exp_vol_threshold_gate.py` -> `_vol_threshold_gate_results.json`).
**G-RULE (kept 70-90% AND avgNet/trade >= base AND maxDD <= base, all 4 cells) PASS at
thr=1.15 and thr=1.20.** thr=1.20: n 398/360/216/196 (77-80% kept), avgNet/trade
+0.665/+0.829/+0.342/+0.386 vs flat +0.652/+0.791/+0.251/+0.238, maxDD
27.0/19.7/38.2/20.8 vs 27.7/21.2/53.2/29.4, dNet -61.1/-60.5 IS but **+3.6/+15.5 OOS**.
thr=1.15: 74-76% kept, avgNet + DD better 4/4, dNet -66.6/-56.6 IS, +0.8/+14.9 OOS.
0.846-1.10 miss kept>=70%; 1.25/1.30 fail avgNet (IS champ dips below base). IS total
net costs 17-19% at the passers (skipped tail net-positive IS, below average); all 10
arms reported (exploratory threshold ranking).

**Z3b flags A/B gate sweep (checklist 24.75, log 78):** same G-RULE applied to the
other two survivors (`exp_ab_gate_sweep.py` -> `_ab_gate_sweep_results.json`).
**G-RULE PASS: `er50 <= 0.20` ONLY - and EXPLORATORY/knife-edge** (added post-hoc
after 0.1989 missed the 70% kept floor by 0.2pp; 0.205 fails utcsat IS DD by 0.2R):
kept 73/71/72/76%, avgNet +0.722/+0.966/+0.293/+0.326 vs flat +0.652/+0.791/
+0.251/+0.238, maxDD 25.7/20.3/28.7/20.0 vs 27.7/21.2/53.2/29.4, dNet -60.7/-47.8
IS, -11.6/+2.1 OOS (HIGH selection risk; OOS champion below flat). **wick>=25 FAIL**
(only goal-zone arm; champ IS DD 27.7->29.9) - wick stays sizing-only. **Z3 volume
gate (1.15/1.20) remains the recommended reduction gate** (pre-registered grid,
better OOS net).

### Candidate B - bleed removals (checklist 24.76, log 80)

**Stage B "bleed autopsy" (user goal pre-registered): find a bucket with NET NEGATIVE R in
all 4 cells (champion/utcsat x IS/OOS), remove it, baseline strictly better (net up, trades
down, avg/trade up). FINAL AFTER CAUSALITY AUDIT **AND PATH-TRUE RERUN: 0/4 removal PASS - BOTH the original
"4/4 PASS" and the post-audit 2/4 are RETRACTED.** The two survivors were post-process ledger skips; through the
real engine they fail 0/4 (OOS champion goes negative).** Phase-0: 74 Z1 buckets = ZERO 4/4-negative -> 30 new
features (114 buckets) on the untouched HTF chain-state plane. Harness
`exp_bleed_autopsy.py` -> `_bleed_autopsy_results.json`; FIND = n>=15 AND share<=35% AND
sumNet<0 x4; REMOVAL PASS = dNet>0 AND avgNet>=base AND n<base AND curve_better x4 (both
pre-registered). 4 qualifiers; post-audit results:

| removal | dNet IS c/u | dNet OOS c/u | verdict |
|---|---|---|---|
| **wick_atr12@short <= 6.03** | +28.1 / +25.7 | +19.8 / +23.8 | **RETRACTED - PASS 4/4 post-process, FAIL 0/4 path-true** (dNet -50.6/-54.5/-78.0/-59.6, OOS champ net +70.2->-7.8) |
| **flips96@short = 4-5** | +8.2 / +14.0 | +12.8 / +11.6 | **RETRACTED** - same short-side removal lever as the wick gate, so the same path-true failure is expected; not rerun separately |
| chain_r_so_far < 0 | +19.7 / +20.1 | +16.4 / +10.0 | **FAIL** - is\|utcsat DD 21.2->26.2, calmar 4.619->3.940, curve False (3/4 cells pass) |
| chain_wl_streak = -1 | +12.9 / +17.2 | +11.7 / +9.5 | **FAIL** - same cell (calmar 4.619->3.910) |

**Causality bug (post-run audit `verify_bleed_causality.py` -> `_bleed_autopsy_CLOSEDONLY.json`):**
the original `enrich_sequential` folded each trade's final net R at ENTRY order; with
exp_mltf concurrent positions still-open trades' outcomes leaked into chain/prev state
(203 prior-open observations across 178 trades - same bug class the loss-streak work already
fixed). Closed-only fix (`exit_ts <= cutoff`) applied to the harness in place; a fresh run
reproduces the audit JSON byte-for-byte. Chain buckets remain 4/4-negative DESCRIPTIVELY
after the fix (nets -19.7/-20.1/-16.4/-10.0) but their removals fail the equity rule - the
leaky version was partly right by accident (the leak flattered the chain features). Masked
candidates are pure market structure (z1_compute), no trade state -> PASS stands. Full
record `BLEED_AUTOPSY.md` (incl. 9.9 audit).

### Risk statement (user note, 2026-09-25)

User: "utna delta aa raha hai toh kuch toh risk dega" - correct; each candidate's risk, in words:

- **X:** OOS uplift rests on **7-9 trades** (one OOS monster can dominate the +36.6/+39.5);
  IS side deepens DD 1-2R; flag band emerged after a 5-measure search where 4 measures
  era-flipped -> selection risk non-zero. Small-n caveat is PRE-REGISTERED and must travel
  with the flag wherever quoted.
- **Y:** healthy flag share, but IS utcsat pays +3.7R DD for +60.1 net (up-sized pullback
  losers land inside drawdown stretches); bucket is 1 of 5 EMA buckets (it was pre-flagged by
  Stage 12 BEFORE this test, which limits - but does not eliminate - selection risk).
- **Both:** post-process R-unit sizing (live implementation = order-time lot sizing; no entry
  feedback either way); x1.5 on ~10-15% of the book = ~1.1-1.15x average exposure.
- **Z:** the three flags are ONE correlated family (low ER, wick-heavy indecision, contracting volume all mark the same quiet tape; share overlap heavy) - stacking them would double/triple-size the same trades; deploy at most ONE flag or cap combined exposure. maxDD deeper in all 12 cells (0.4-8.6R) even where curve passes; OOS dNet (+17..+40) rides the weak OOS baseline that Study 2 (log 74) showed is luck-consistent. Descriptive + path-true done same session; edges IS-derived only (no OOS peeking).
- **Z capital-scaling lever (Z3, M2-style):** present capital 1x everywhere; the A/B/C
  1.5x flags are a FUTURE lever - when capital grows/flexible apply 1.5x lot on ONE
  chosen flag (union of the three = 63-65% of book - do not stack), 1x on everything
  else. When capital/risk-budget is tight: take only `vol7_prev7 <= 1.20` (~400/500
  trades, avg/trade same-or-better, DD lower 4/4; 1.15 for a deeper cut). Sizing flag
  + gate combined = UNTESTED.- **Stage B bleed removals (post-audit):** only the two masked short-side removals PASS;
  the chain removals failed the pre-registered rule under corrected closed-only enrichment
  (is|utcsat DD 21.2->26.2) and are retracted to descriptive-only. Remaining risks: 114
  buckets x 4 cells scanned (4/4-negative FIND is strict but selection risk not zero);
  the two PASSers likely overlap on the same short trades - combining UNTESTED; post-process
  only (no chain re-timing); OOS lifts ride the weak OOS baseline (Study 2 luck caveat).
  Meta-risk: one lookahead leak WAS caught post-run in this stage's own harness - any
  chain/prev-state feature must go through the closed-only audit every time it appears.
- **Both vs M2:** M2 bigleg is still the front-runner (6/6 strong pass, flag 16-29%, ulcer
  down everywhere). These two are recorded candidates, NOT adopted.

### Comparison - X vs Y vs Z vs M2 vs B (completed 2026-09-26, end-of-session per user)

Basis: same instrument/eras (Bybit BTCUSDT; IS 2023-26, OOS 2021-22). Flat multi baseline where
noted: champion 500t/+325.8/DD27.7 IS, 279t/+70.2/DD53.2 OOS; utcsat 454t/+358.9/DD21.2 IS,
253t/+60.2/DD29.4 OOS. X/Y/Z/M2 are POST-PROCESS SIZING (x1.5 on flagged trades, trade list
byte-identical): the numbers are real measurements under the sizing exemption (sizing never
changes which trades fire, so post-process = path-true by construction; three verified
conditions, AGENT_COORDINATION.md). B is a REMOVAL: only an engine path-true run counts - it
scored 0/4 and is dead. No new runs were made for this comparison; every figure is re-read from
the artifacts named under each candidate. dNet = arm net minus baseline net on the same book.

| rank | candidate (flag) | flag share | dNet IS c/u | dNet OOS c/u | curve record | DD cost | OOS flagged n | exposure |
|---|---|---|---|---|---|---|---|---|
| 1 | **M2 bigleg** cur_mag_atr>=3.0 | 16-29% | **+153.5 / +131.0** (flat +152.7 / +147.5) | **+31.5 / +30.8** (flat +29.1 / +31.3) | **6/6 TRUE** stack AND flat (age10 +117.1/+18.8; flat +113.0/+21.3) | dDD -2.1..+0.45 stack; flat deeper only u IS | 41 / 38 stack, **48 / 47 flat** (age10 5 / 12) | 1.1-1.2x |
| 2 | **Z-C** vol7_prev7<=0.846 | ~33% | +106.5 / +112.3 | **+32.2 / +40.4** | TRUE x4 | maxDD deeper x4 (OOS c 53.2->61.8) | 81 / 76 | 1.1-1.2x, ONE Z flag only |
| 2 | **Z-A** er50<=0.0767 | ~33% | **+110.3 / +110.5** | +17.3 / +23.4 | TRUE x4 | maxDD deeper x4 (IS u 21.2->26.7) | 84 / 81 | same |
| 2 | **Z-B** wick_gt3x_pct12>33.3 | ~24% | +74.1 / +71.9 | +18.3 / +23.4 | TRUE x4 | maxDD deeper x4 | 70 / 62 | same |
| 3 | **Y** ema4h pullback_toward_ema | 13-17% | +58.7 / +60.1 | +18.9 / +21.0 | **3/4 FAIL** (utcsat IS FALSE) | IS utcsat DD 21.2->24.9 (+3.7R) | 42 / 37 | ~1.08x |
| 4 | **X** parent risk_pct<1.0 | 9.2/8.6% IS, 2.5/3.6% OOS | +23.9 / +23.4 | +36.6 / +39.5 | 4/4 TRUE | IS +1.0..+2.0R deeper; OOS improves | **7** | ~1.05x |
| DEAD | **B** wick_atr12@short / flips96 REMOVAL | 14.8% / smaller | (pp only +28.1/+25.7) | (pp only +19.8/+23.8) | **0/4 path-true** | n/a - retracted | n/a | none (removal) |

Verdicts:

- **M2 = front-runner, flat-confirmed.** Largest edge; the only candidate whose raw maxDD never
  deepens (dDD -2.1..+0.45) while ulcer/sortino/PF improve in all 6 cells - flag enrichment
  means the larger size lands on higher-avgR trades. Healthy OOS flagged n (41/38), 100% row
  coverage. BOOK NOTE: Stage O measured M2 on the Stage-B stack book (half+delay1
  [+skip_decisive OOS]), not flat: 466/428/94t at +429.6/+411.1/+489.3 IS, 217/194/50t at
  +110.5/+94.6/+65.8 OOS. FLAT-BOOK CONFIRMING RUN (checklist 24.78, log 83):
  PRE-REGISTERED PASS 6/6 - flat dNet +152.7/+147.5/+113.0 IS, +29.1/+31.3/+21.3 OOS
  (champion/utcsat/age10), ledger assertions 4/4, identity IDENTICAL, ulcer down 6/6,
  raw DD improved in 3 cells, unchanged in 2, deeper only utcsat IS (21.2->23.0); OOS
  flagged n 48/47/12 - larger than the stack book's 41/38/5. The edge reproduces
  book-independently (champion gap <= 2.4R; utcsat flat IS is +16.5 BETTER); age10
  OOS flagged n = 5 stack / 12 flat (lane small-n either way).
  User note stands: 1x present capital; the 1.5x-on-bigleg lever is pre-approved for when
  capital has grown.
- **Z = strong second, pick ONE.** All three flags PASS 4/4 with healthy n (62-167); Z-C has
  the best OOS deltas (+32.2/+40.4), Z-A the best IS (+110.3/+110.5), Z-B the smallest. Cost:
  raw maxDD is deeper in all 12 cells (0.4-8.6R) - the curve passes via ulcer/calmar/sortino,
  not raw DD. The three flags are ONE correlated family (same quiet tape; union 63-65%):
  deploy at most ONE, never stack. Same M2-style capital lever documented (1.5x on one chosen
  flag when capital grows).
- **Y = near-miss, not promotable.** dNet>0 in all 6 cells (2nd-largest IS edge, healthy n
  71/60/42/37) but the pre-registered rule failed on utcsat IS (maxDD +3.7R, ulcer +, calmar
  -). Family closed for gates; arm A stays recorded-not-promoted.
- **X = passes, weakest evidence.** 4/4 TRUE but the smallest edge, IS DD deepens 1-2R, and
  the entire OOS lift rests on flagged n=7/9 (the pre-registered small-n caveat travels) after
  4/5 sibling measures era-flipped.
- **B = dead.** Engine path-true 0/4 (OOS champion net +70.2 -> -7.8); the descriptive buckets
  were correct, but the slot-blocking cascade under exp_mltf is 280-494% of the direct effect -
  bigger than the edge being removed. flips96 retracted by extension (same lever). Do not
  re-test.

- **Combination matrix (Stage Combo, 24.79) - ALL 4 COMBO ARMS PASS 6/6.**
  M2 x ZC(vol7_prev7<=0.846) x X on the flat books, union vs stacked modes,
  pre-registered same rule (dNet>0 AND curve_better all 6 cells). Strongest
  sMZX (x1.5^count): champion +346.5/+130.4 dNet IS/OOS (book 325.8->672.3,
  70.2->200.5), utcsat +341.2/+146.6 (358.9->700.1, 60.2->206.8), age10
  +270.3/+29.9 (435.7->706.0, 43.2->73.2). Union uMZX milder (+165.5/+49.5
  champion). Raw maxDD deeper in 3 stack cells (champion OOS 53.2->56.2) but
  ulcer/calmar/sortino improve in all 18 combo cells. Singles re-scored: M2
  6/6; ZC age10-OOS curve FAIL; X age10-OOS no-op (nAff=0), X n=7/9 caveat
  travels into combos. Recorded, NOT adopted (RESEARCH_POLICY).

Cross-cutting: (1) combinations (M2 + ONE Z flag + X/Y) were UNTESTED at
24.77 - NOW RUN (24.79: all 4 combo arms PASS 6/6, see the combination-
matrix bullet above); (2) OOS deltas inherit the Study-2 weak-OOS-baseline luck caveat;
(3) all survivors are post-process R-unit sizing - live implementation is order-time lot
sizing, no entry feedback either way; (4) exploratory labels travel with every number.
**Nothing adopted - adoption decisions are the user's (RESEARCH_POLICY: no automatic gate).**
