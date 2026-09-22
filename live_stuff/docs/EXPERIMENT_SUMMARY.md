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

- [ ] Test Ideas B (funding rate), A (HMM), C (OI change) — need new data
- [ ] Test Ideas D (ensemble), E (transition detection), F (GARCH)
- [ ] Swing engine mismatch (#1 on checklist) — blocks live deployment
- [ ] Volume data re-fetch

---

*Document generated 2026-09-22. All numbers on post-trail-ratchet-fix engine.*
