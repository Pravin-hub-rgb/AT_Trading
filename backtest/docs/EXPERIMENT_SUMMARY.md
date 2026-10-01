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
- [x] **Statistical arbitrage (Paradigm B) — BTC/ETH(-SOL) spread book** — **TESTED + DEAD 2026-09-27 (checklist 24.89, log row 94):** pre-registered 24-arm grid (4 hedges x 6 bands; OLS/PCA hedges, next-close fills, OU half-life gate, K1-K7 kill table incl. corr-vs-v18). v18 controls exact before any stat result (500/+325.8 IS, 279/+70.1 OOS net); structural identities 24/24. **24/24 arms fail** — primary A1xB1: IS 522t **-131.3R** / OOS 219t **-58.7R** (K1+K2+K3+K4 both eras); gross itself -39.6R (no edge pre-cost) and 150.7R of the 190.0R loss is cost drag (sigma p50 0.57% → risk$ ~$85/trade vs $19 round trip = 0.21R/trade). Positive: corr vs v18 spans -0.289..+0.262 across all 36 evaluated cells — the book is genuinely independent of the engine, just unprofitable (constraint = gross edge + cost/risk, not correlation). No arm adoptable. Harness `backtest/tests/exp_stat_arb.py` → `_stat_arb_results.json`.
- [x] **Flow/positioning data edge (Paradigm 1) - Binance UM metrics (OI, taker L/S, toptrader L/S)** - **TESTED + DEAD 2026-09-27 (checklist 24.90, log row 95):** first non-OHLCV information axis in this repo. Phase 1 descriptive screen (6 features, era-local terciles, pre-registered S1+S2+S3): **1/6 survives - `top_ls_1h`** (Q3-Q1 -0.08/-0.45/-0.05/-0.35%, monotone all 4 cells; OI-change/divergence all fail sign-stability). Phase 1b path-true (trailing 30d quantiles, next-open entry, 0.095% RT, K1-K7 kill table): **0/2 arms pass** - B_h16 IS 4925t **-429.3R** (gross +40.8 vs cost 467.9), OOS -57.0R; B_h96 OOS +13.9R but K3 DD 44.9R, IS -80.4R. **The edge is real but sub-cost: +0.008R/trade gross vs 0.095R round trip.** Causal pairing bugfix (one-bar lookahead) caught by the path-true alignment control and corrected pre-commit; Phase 1 re-run, first run discarded. Data 602,471 rows 2021-2026, 0 gaps; v18 controls exact. Harnesses `exp_flow_descriptive.py` + `exp_flow_pathtrue.py` -> `_flow_descriptive_results.json` + `_flow_pathtrue_results.json`.
- [x] **Cross-sectional 16-alt rotation (Paradigm 2) - relative strength across Binance perps** - **TESTED + DEAD 2026-09-27 (checklist 24.91, log row 96):** first cross-sectional axis in this repo; data backfilled 2021-01..now (32 files, fapi). Phase 1 (5 features, daily terciles, pre-registered S1+S2+S3): **1/5 survives - `mom_90d`** (spreads +0.15/+0.05/+0.40/+0.67% across oos/is x 1d/7d, monotone all 4 cells - the cleanest descriptive signal of this batch). Phase 2 path-true (next-close entry, 0.095% RT/leg, K1-K7 kills): **0/4 arms pass** - LS_h7 closest and net-positive BOTH eras (OOS 79 cohorts +19.8R Sh 0.30 with 2022Q3 -15.9R -> K2+K4; IS 166 +67.3R Sh 1.01 but K7 corr 0.3051>0.3 - momentum beta overlaps v18's tape); LS_h1 -4.6/-24.8R; LO_h7 +62.4/+92.1R but DD 120/152R (long-beta leverage, not edge). Data fetch-bug incident (timestamp-only overwrite) caught same-session and repaired by full fapi re-fetch with validation gates. Harnesses `exp_xs_rotation.py` + `exp_xs_rotation_pathtrue.py` -> `_xs_rotation_results.json` + `_xs_rotation_pathtrue_results.json`.
- [x] **Carry/funding harvest (Paradigm 3) - BTC funding + basis income** - **TESTED + DEAD 2026-09-27 (checklist 24.92, log row 97):** 80+80 monthly funding/premium zips (2020-26). Phase 1 (5 features, carry rule dir=-sign, era-local day terciles, pre-reg S1+S2+S3): **1/5 survives - `prem_1d`** (-46.7/-18.6/-121.9/-167.2bp across oos/is x 1d/7d, monotone 4/4: negative basis is a CONTRARIAN buy signal). Phase 2 path-true (contiguous book, turnover-aware costs - 0.095% RT only on flips, K1-K7 with pre-reg K5 deviation for held books): **0/2 arms pass** - h1 OOS 549 cohorts -19.5R (K1-K4) / IS 1157 +58.4R (Sh 0.44, DD 68.9 -> K2/K3/K4); h7 -6.9R / -20.0R (K1-K4 both eras). Turnover thesis validated (4-30 flips total over years) but carry's directional risk doesn't pay for itself; funding stays a COST line, not income. Harness `exp_carry_descriptive.py` + `exp_carry_pathtrue.py` -> `_carry_descriptive_results.json` + `_carry_pathtrue_results.json`.
- [x] **Event-driven trades (Paradigm 4) - scheduled macro calendar (known WHEN, never WHAT)** - **TESTED + DEAD 2026-09-27 (checklist 24.93, log row 98):** 382 exact-UTC known-in-advance US events (CPI/PPI/NFP/JOLTS/FOMC/GDP/PCE, 2021-26); date_only families excluded up front (political, fed speeches). Phase 1 (7 types x 4 windows = 28 candidates, causal bar-end anchors, S1+S2+S3): **2/28 survive - `ppi|post1`** (long 1h after PPI: +0.43/+0.06%, cons 0.67/0.62, n 18/37) and **`fomc|pre24`** (long 24h before FOMC: +1.75/+0.04%, cons 0.75/0.60, n 12/25). Phase 2 path-true (0.095% RT per event, K1-K7, K5=n events >=12/24): **0/2 arms pass** - both PASS OOS (fomc +19.9R wr 75% Sh 1.53; ppi +5.9R wr 61% Sh 1.14) but negative IS (fomc -1.5R, ppi -1.2R, K1+K4): drifts are real in the 2021-22 regime and decayed below cost in 2023-26 (ppi IS mean +0.06% < 0.095% RT). Harnesses `exp_event_descriptive.py` + `exp_event_pathtrue.py` -> `_event_descriptive_results.json` + `_event_pathtrue_results.json`.
- [x] **Portfolio ensemble of alive kings (Paradigm 5) - decision phase over Stage G** - **TESTED + DEAD 2026-09-27 (checklist 24.94, log row 99):** 4 flat reference lanes (champion/utcsat/fullstack/age10), a-priori priority, membership rule |corr_IS| <= 0.90 vs kept lanes, house-style K1-K7 with K7 = Calmar strictly above champion (corr-vs-v18 N/A by construction). Controls green (v18 PASS; all 4 lane runs exactly match documented nets: 500/+325.8, 454/+358.9, 200/+310.7, 130/+435.7 IS). **RESULT: NO ENSEMBLE - every king is collinear with the champion on IS (utcsat 0.981, fullstack 0.912, age10 0.931 daily-R corr, all > 0.90); membership retained only the champion; arms never evaluated (pre-registered degenerate path).** The flat kings are ONE stream; decorrelation exists only in the Stage-B stacks (age10-cand corr 0.08 vs flat 0.93) so the stack ensemble question stays open under Stage G's descriptive status. Harness `exp_ensemble_pathtrue.py` -> `_ensemble_pathtrue_results.json`.
- [x] **Cross-asset transfer to Binance ETH/SOL perps (Paradigm 6) - the distinct test 24.16 demands** - **TESTED + CANDIDATE 2026-09-27 (checklist 24.95, log row 100):** 4 frozen flat lanes (champion/utcsat/fullstack/age10) on NEW data - Binance fapi ETHUSDT/SOLUSDT perps, raw fapi precision in data/alt-fut (SOL 4dp kept; lossy scan-fut/prefix-truncated eth-fut unused), eras mirrored from bybit loaders (IS 2023-01..2026-09-13, OOS 2021-01..2022-12), bybit BTC cost convention unchanged; 24.82 transfer rule (net>0 AND n>=30 both eras, 8 units) primary, K1-K7 secondary with pre-registered differential exemption vs the bybit reference cells. Controls green: identity gate IDENTICAL, v18 control exact (500/+325.8 IS, 279/+70.1 OOS), 8/8 bybit ledger exact, exact slice parity both assets both eras, 0 gaps across all 6 files. **RESULT: transfer 6/8 - ETH utcsat fails IS (-7.4R), SOL fullstack fails OOS (-17.4R), the other 6 pass; kills_clean only 2/8 - age10 x both assets (sole literal-K6 pass wr 0.44-0.55, Sharpe 1.13-1.99, maxDD <= 13.2R); SOL dominates (1106.1R vs 426.5R net), ETH OOS monthly corr 0.59-0.71 vs SOL -0.28..+0.31.** VERDICT: CANDIDATE - candidate for the user's adoption decision, NOT auto-adopted; six passing units mostly counted-kill-tainted, ETH economics thin (champion IS +16.0R/431t, Sharpe 0.08). Stage 17 single-vs-multi split does not reproduce. Harness `exp_cross_asset_transfer.py` -> `_cross_asset_transfer_results.json`.
- [x] **Gray re-test of Stage B's REAL wick gate - the predicate everyone tested was the WRONG one** - **TESTED 2026-09-27 (checklist 24.96, log row 101):** Stage B qualified wick_atr12@short<6.026 on the 1h feature plane (12 closed 1h bars, cutoff entry+900, ATR14-1h) flagging 74/62/35/36 trades, cohort net -28.1/-25.7/-19.8/-23.8, removal +28.1/+25.7/+19.8/+23.8 PASS 4/4 - but every follow-up (exp_wick_short_pathtrue, exp_cascade_tax_test, gray children) computed the wick on 15m bars including the entry bar with raw<=6.03: a different cohort (112 vs 74, opposite sign), hence 'gray does NOT rescue the wick gate' (ee8a42b/5c50917) judged the wrong gate and the -78.6R cascade tax conflated cohort swap with cascade. Controls green (parity exact both planes). **RESULT: with the real predicate, gray (seq-identical 6/6, cascade_term 0.00) live dNet = +28.1/+25.7/+19.8/+23.8 - EXACTLY post-process, proving seq-identical gray books the post-process book (harness raw-only +10.5/+13.1/+15.5/+19.3 + never-placed-fill cost relief); path-true same cohort -39.0/-12.6/+7.5/+24.0 (cascade tax IS-heavy, ~0 OOS); old 15m cohort under live accounting: OOS -70.1/-70.2/-30.2 negative under any accounting - old dead verdict stands for that cohort.** VERDICT: G-RULE PASS 4/4 on Stage B lanes, FAIL all-6 (is/age10 -2.0); adoption ruling requested from the user (pre-registered), nothing adopted. Harness `exp_gray_wick1h.py` -> `_gray_wick1h.json`.
- [x] **Wick 1h deep investigation - the real 1h gate survives an independent audit; HOLD is about the forward gate, not the mechanism** - **TESTED 2026-09-27 (checklist 24.97, log row 102):** independent recompute reproduced Stage B (parity 4/4 exact after fixing `w<=thr` -> strict `w<6.026` and a `stable_window_ck_u` key-collision that had stored the OOS-only window 5.0-7.2). CORRECTED: ck_u both-eras window 5.0-5.4 | 5.6-6.4 (14 steps, hole 5.5), cliff 6.4->6.5, flips IS 6.4/6.4/6.1 OOS 7.2/7.2/6.6, all-6 = 6.1 only (-0.29R n22, post-hoc); ex-best negative 6/6 at 6.026; age10 "structural" RETRACTED (nested = same n=20 cohort, ex-best -3.875 = single +5.9R winner) -> insufficient data, default-off. HOLD - sole blocker forward gate 5/50; threshold not frozen. Harnesses `exp_wick1h_audit.py` -> `_wick1h_audit.json`, `exp_wick1h_deep.py` -> `_wick1h_deep.json`. NOT ADOPTED (RESEARCH_POLICY).

---

## Untested Families (backlog) — added 2026-09-25

Entry-side re-entry/timing families are exhausted; the position-sizing / add-on backlog below was the last untested class and is now FULLY TESTED as of 2026-09-26 (pyramid Phase 2 CLOSED, revenge DEAD):

- [x] **Pyramid / scale-in** - **TESTED + CLOSED 2026-09-26 (checklist 24.87, log row 92):** Phase 1 offline walk 1/6 (24.43) did NOT survive the real engine. Phase 2 ran the frozen 5-arm list (`PYRAMID_PHASE2_DESIGN.md`; Model A child trades, runtime loader patch - no shared file edited): **every arm fails the pre-registered 6/6 rule (V1 1 lane, V2 2 lanes, V3 2 lanes + robustness fail, V4 swing_confirm 0 lanes - champion OOS book +70.2 -> -17.2) -> FAMILY CLOSED**, no kwarg shipped, no default changed.
- [x] **Revenge re-entry at the ORIGINAL entry level** - **TESTED + DEAD 2026-09-25 (checklist 24.44, log row 37):** 8/8 cells negative at the descriptive gate (touch IS -29.7/OOS -23.3 champion, age10 -9.8/-9.1); 5th reclaim-adjacent family failure; path-true Phase 2 NOT run per pre-registration.
- [x] **Same-window second entry AFTER a WIN** — **TESTED + CLOSED as gate 2026-09-25** (cohort study, era-flip: IS rewin = book engine (+282R), OOS rewin negative (−13R); drop-rewin helps OOS, destroys IS — no both-sides filter; age10 rewin + both eras but n=6+6; see checklist 24.61, log 54, harness `exp_rewin_cohort.py`).
- [x] SL-candle reclaim re-entry (break of the SL-giving 15m candle) — **TESTED + DEAD 2026-09-25** (Phase 1 descriptive gate, 8/8 cells negative; see SL_RECLAIM_REENTRY.md, checklist 24.38, log row 32).
- [x] Dip-then-reclaim confirmation entry — **TESTED + DEAD 2026-09-25** (checklist 24.34, log row 24).
- [x] Retest limit-below-entry fill — OPEN CANDIDATE (exp_retest_fill=0.25, age10 lane only, default-off).

---

## M2 Bigleg Sizing — Deployment Note (added 2026-09-25)

**Survivor:** entry-causal flag `cur_mag_atr >= 3` (swing magnitude ≥ 3 ATR at entry) → size ×1.5 on flagged trades (16–29% of the book). Post-process backtest (R-unit sizing, trade list byte-identical): **6/6 cells net+ both eras, curve_better TRUE all** — champion dNet +153.5/+31.5 (calmar 4.34→5.45 / 1.81→2.31), utcsat +131.0/+30.8, age10 +117.1/+18.8; ulcer down everywhere, DD never meaningfully worse. First surviving new-edge candidate of the 2026-09-25 session (checklist 24.60, log 53, harness `exp_m2_size_phase2.py`, JSON `_m2_size_phase2_results.json`).

**USER NOTE (2026-09-25): this is a capital-scaling lever — apply WHEN CAPITAL HAS GROWN.** With present capital keep normal 1× sizing everywhere. Once the account justifies larger notionals, this was the pre-approved sizing rule: **1.5× lot on bigleg setups (swing ≥3 ATR), 1× on everything else** — but **DISPROVEN 2026-09-26 (checklist 24.85): the flag is NOT known at send time** (`cur_mag_atr` reads the swing segment's END price; `backend_check_wd_days.py:108` confirms confirmation lands at/after end), the order-time bridge reproduces only 77.5% of backtest flags (send-time fires 0–6 of 12–133) and no send-time replacement clears the pre-registered rule. **The whole cur_mag_atr queue (M2, ramp_mag, uMZX, sMZX, count_linear) is non-deployable as measured** — a new send-time-computable feature is required before any live sizing. The 6/6 backtest numbers above stay valid ONLY as backtest numbers (sizing exemption); SL/trail/partial logic unchanged.

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
  **PATH-TRUE UPDATE (24.81): the thr=1.15/1.20 recommendation is RETRACTED
  for adoption - the vol gate rerun path-true FAILS G-RULE 3/6 (champion OOS
  sign flip +3.6->-4.6); see the GateSize bullet above.**

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
  **PATH-TRUE UPDATE (24.81): RETRACTED - path-true G-RULE FAIL 3/6 (kept
  ~79%, avg/DD worse in 3 cells, champion OOS sign flip); combined sizing+gate
  also FAILS 4/6 vs flat. Only the M2-style SIZING flags survive (exempt).**

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

- **Sizing-function shapes (Stage Shapes, 24.80) - ramp_mag PASS 6/6,
  count_linear PASS 6/6, vol_target FAIL (2 of 3 tested arms PASS).**
  Same flat books; controls M2_15/uMZX reproduce 24.78/24.79 exactly (6/6).
  Threshold-free ramp clamp(1+0.25*(cur_mag_atr-2),1,2) BEATS binary M2 in
  all 6 cells: champion +267.3/+54.1 dNet IS/OOS (vs +152.7/+29.1), utcsat
  +260.3/+53.6, age10 +201.0/+26.1; raw DD OOS improves (53.2->48.0 champ,
  29.4->24.3 utcsat), IS <=2.9R deeper; sizes ~half the book (shape, not
  flag; levered stakes). count_linear (1+0.5*count cap 2.0): +276.8/+87.0,
  +280.2/+100.2, +228.8/+26.4 - beats union uMZX, still below the 1.5^count
  stack sMZX on net 6/6; raw DD deeper 5/6 (+0.1..+5.1R), curve 6/6.
  vol_target (inverse-ATR, book-median normalizer) net up 6/6 but curve
  FALSE x3 (champ IS ulcer 14.62->29.82, DD 27.7->38.8; utcsat IS DD
  21.2->27.8; age10 OOS ulcer 31.55->73.74) - FAIL on the pre-registered
  rule. Recorded, NOT adopted (RESEARCH_POLICY); ramp/count queued for the
  adoption checkpoint.

- **Gate x size PATH-TRUE (Stage GateSize, 24.81) - gate FAILS path-true,
  combined NOT adoptable, M2 marginal robust.**
  vol7_prev7<=1.20 injected pre-state-mutation (identity IDENTICAL x6, formula
  parity 0/1692, flat_M2 control = 24.78 x6). G-RULE on the gated book: FAIL
  3/6 - kept 77.7-80.0% everywhere (band fine) but avgNet drops (champion IS
  0.652->0.603, utcsat IS 0.791->0.752, age10 OOS 0.569->0.412) and champion
  IS maxDD 27.7->42.6 (post-process had 27.7->27.0; ulcer 14.62->358.02).
  CASCADE vs Z3 post-process dNet: champion IS -61.1->-87.4, champion OOS
  +3.6->-4.6 SIGN FLIP, utcsat IS -60.5->-86.0, utcsat OOS +15.0->+10.8 -
  **Z3 vol-gate recommendation RETRACTED (post-process = upper bound; SECOND
  confirmation after Stage B wick 0/4).** COMBINED gate+M2 vs FLAT: FAIL 4/6
  (champion IS +34.6 but curve False - DD 27.7->44.9; age10 OOS -12.7, M2
  nAff 6 SMALL-N; passes utcsat IS +46.6, age10 IS +7.3, champion OOS +18.0,
  utcsat OOS +33.9). MARGINAL M2 on the gated book: PASS 6/6 (+122.0/+132.6/
  +98.5 IS, +22.6/+23.0/+6.6 OOS) - the sizing edge survives any book; the
  gate's chain cascade is the sole failure. Recorded, NOT adopted
  (RESEARCH_POLICY).

- **Cross-instrument transfer (Stage CrossInstrument, 24.82) - base edge
  transfers WEAKLY (3/3 by rule), M2 + uMZX flags transfer frozen (6/6),
  ZC + X do not.**
  Frozen champion params on Binance BTCUSDT perp, same era windows as
  bybit (data/btc-fut backfilled 2021-26 from fapi, 0 gaps, 1h volume
  present; Bybit cost model both venues; bybit controls 12/12 exact).
  Base: champion 490t/+255.4 IS (0.78x bybit) & 286t/+17.8 OOS (0.25x,
  avg +0.06R/trade - thin), utcsat 451t/+208.1 & 258t/+7.6 (0.13x),
  age10 118t/+182.6 & 78t/+94.2 (2.18x OOS - only lane beating bybit
  OOS); trade counts within dn -12..+7 of bybit, but binance IS curve
  much rougher (ulcer 110/103/10.9 vs 14.6/11.6/3.9, DD ~2x). Flags
  on binance (6-cell rule): M2 PASS (+113.1/+31.7, +90.1/+31.4,
  +32.5/+36.1), uMZX PASS (+122.6/+43.2, +95.1/+37.8, +54.8/+46.6);
  ZC FAIL (champion/utcsat IS curve FALSE - bybit-volume-derived 0.846
  ratio threshold not portable), X FAIL (OOS cells False, thin
  everywhere). "Architecture universal" SUPPORTED for engine/structure
  + M2/uMZX sizing, NOT for edge magnitude or ZC/X thresholds.
  Recorded, NOT adopted (RESEARCH_POLICY); cross-instrument caveat
  joins the slice-5 adoption checkpoint.

Cross-cutting: (1) combinations (M2 + ONE Z flag + X/Y) were UNTESTED at
24.77 - NOW RUN (24.79: all 4 combo arms PASS 6/6, see the combination-
matrix bullet above; sizing-function SHAPE (binary threshold vs ramp vs vol-target vs flag-count) was UNTESTED - NOW RUN (24.80: ramp_mag + count_linear PASS 6/6, vol_target FAIL, see the shapes bullet above); (2) OOS deltas inherit the Study-2 weak-OOS-baseline luck caveat;
(3) all survivors are post-process R-unit sizing - live implementation is order-time lot
sizing, no entry feedback either way; path-true-removal confirmations now TWO
(wick 0/4; vol gate G-RULE 3/6 - 24.81) (4) exploratory labels travel with every number. (5) cross-instrument transfer now run (24.82): base edge positive on Binance perp 3/3 by rule but weak (0.13-0.78x bybit net, IS ulcer 4-8x); M2 + uMZX transfer 6/6 frozen, ZC/X thresholds do not.
**Nothing adopted - adoption decisions are the user's (RESEARCH_POLICY: no automatic gate).**
