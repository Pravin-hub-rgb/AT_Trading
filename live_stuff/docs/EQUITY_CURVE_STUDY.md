# Equity-Curve Quality Study — 2026-09-24 Batch

**Date:** 2026-09-24  
**Status:** STUDY COMPLETE — no automatic production gate; equity lens surfaces two open candidates  
**Harness:** `live_stuff/tests/exp_equity_quality.py`  
**JSON:** `live_stuff/tests/_equity_quality_results.json`  
**Identity gate:** green before any arm (`340t/+225.3R IDENTICAL`)  
**Configs:** `champion_multi_sw10`, `utcsat_multi_sw10`, `age10_dirmatch_swingpause_single_sw10`  
**Scopes:** IS 2023–26 (years=3.67), true OOS 2021–22 (years=2.0)  
**Cost model:** same as production (fee 0.055%/side, entry slip 0.005%, exit slip 0.010%, funding 0.01%/8h)  
**Arms (pre-frozen):** baseline, `half`, `half+delay1`, `delay_r_1.5`, `skip_decisive`

---

## 0. Why this study exists

The 2026-09-24 batch was originally summarized with a fixed `dNet/yr ≥ +30` screen. That number is retained only as historical context; it is not a project rule, pass/fail test, or adoption threshold. This study re-scores the batch under the equity-curve lens.

But the question is not only *"how much more R?"* — it is:

1. **Do we even need +300R more?** Production multi is already ~+326R IS / +70R OOS; best-ever single is +435.7R / DD 5.7. Diminishing returns on absolute R.
2. **Is the equity path smoother / less curve-fitted?** A wider trail that adds IS P&L but also improves 2021 recovery and shallows OOS drawdown may be more valuable than a larger raw R delta on a jagged curve.

This doc re-scores the batch under an **equity-curve lens** and leaves a reusable scoring method for future arms.

---

## 1. Metrics (NET, chronological, closed trades only)

| Metric | Definition | Better |
|---|---|---|
| `net` | Σ net R (same cost model as leaderboard) | higher |
| `max_dd` | peak-to-trough on cumulative net R | lower |
| `max_dd_dur` | trades from DD start to trough | lower |
| `uw_pct` | % of trades equity is below prior peak | lower |
| `ulcer` | RMS of (100·dd/peak) over points with peak>0 | lower |
| `sortino` | net / downside deviation of trade nets | higher |
| `calmar` | (net/years) / max_dd | higher |
| `recovery` | net / max_dd | higher |
| `pos_month_pct` | % of calendar months with net>0 | higher |
| `worst_month` | worst calendar-month net | higher |
| `max_streak` | max consecutive losing trades | lower |
| `pf` | gross wins / gross losses on net R | higher |

**Equity-lens pass (pre-registered in harness):** curve better **AND** net not hurt, both sides.  
Curve better = (`d_max_dd > 0.5`) **OR** (`d_ulcer > 0.5`) **OR** (`d_calmar > 0.05`).  
Net not hurt = `d_net ≥ 0`.

This is intentionally a separate research lens: it asks *"is the path better and not poorer?"*, not whether an invented absolute R/year number was cleared.

---

## 2. Full tables — IS 2023–2026

### champion_multi_sw10

| arm | n | net | maxDD | DDdur | uw% | ulcer | sortino | calmar | m+% | streak | PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 500 | +325.8 | 27.7 | 72 | 90.4 | 14.62 | 328.3 | 3.20 | 51.1 | 16 | 1.81 |
| half | 469 | +428.6 | 30.5 | 56 | 90.8 | 12.40 | 424.7 | 3.83 | 44.4 | 19 | 2.10 |
| **half+delay1** | **466** | **+429.6** | **27.0** | **56** | 90.8 | **12.41** | **424.1** | **4.34** | 44.4 | 19 | **2.10** |
| delay_r_1.5 | 487 | +351.4 | 29.1 | 48 | 89.7 | 13.48 | 346.5 | 3.29 | 51.1 | 16 | 1.87 |
| skip_decisive | 500 | +325.8 | 27.7 | 72 | 90.4 | 14.62 | 328.3 | 3.20 | 51.1 | 16 | 1.81 |

### utcsat_multi_sw10

| arm | n | net | maxDD | DDdur | uw% | ulcer | sortino | calmar | m+% | streak | PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 454 | +358.9 | 21.2 | 40 | 89.7 | 11.55 | 364.9 | 4.62 | 53.3 | 13 | 2.01 |
| half | 431 | +401.0 | 26.8 | 45 | 90.5 | 11.51 | 401.9 | 4.08 | 46.7 | 15 | 2.14 |
| **half+delay1** | **428** | **+411.1** | 23.9 | **29** | 90.0 | **9.84** | **408.4** | **4.69** | 46.7 | **14** | **2.17** |
| delay_r_1.5 | 438 | +378.5 | 23.9 | 44 | **87.2** | 10.70 | 375.7 | 4.31 | **55.6** | 13 | 2.06 |
| skip_decisive | 454 | +358.9 | 21.2 | 40 | 89.7 | 11.55 | 364.9 | 4.62 | 53.3 | 13 | 2.01 |

### age10_dirmatch_swingpause_single_sw10 (best-ever reference)

| arm | n | net | maxDD | DDdur | uw% | ulcer | sortino | calmar | m+% | streak | PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 130 | **+435.7** | **8.7** | **6** | **58.5** | 3.94 | **546.7** | **13.61** | **62.8** | **5** | **7.57** |
| half | 118 | +418.2 | 9.9 | 11 | 63.6 | 3.67 | 494.5 | 11.48 | 58.1 | 10 | 7.02 |
| half+delay1 | 117 | +422.6 | 8.8 | 6 | 62.4 | **2.15** | 491.7 | 13.15 | 60.5 | 7 | 7.07 |
| delay_r_1.5 | 128 | +431.3 | 8.7 | 6 | 59.4 | **2.33** | 504.2 | 13.45 | **64.3** | 5 | 6.89 |
| skip_decisive | 119 | +425.3 | 8.7 | 6 | 58.0 | 4.11 | 526.9 | 13.28 | 62.8 | 5 | 7.93 |

---

## 3. Full tables — true OOS 2021–2022

### champion_multi_sw10

| arm | n | net | maxDD | DDdur | uw% | ulcer | sortino | calmar | m+% | streak | PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 279 | +70.2 | 53.2 | 149 | 95.0 | 213.6 | 78.5 | 0.66 | 37.5 | 15 | 1.34 |
| half | 268 | +72.8 | 46.6 | 131 | 95.2 | 229.7 | 79.3 | 0.78 | 41.7 | 21 | 1.35 |
| **half+delay1** | **271** | **+89.8** | **46.3** | 132 | 95.6 | 242.2 | **95.9** | **0.97** | 37.5 | **15** | **1.42** |
| delay_r_1.5 | 262 | +81.0 | 50.4 | 134 | **94.3** | 215.3 | 87.3 | 0.80 | **41.7** | 15 | 1.40 |
| **skip_decisive** | **222** | **+99.3** | **33.8** | **127** | **91.9** | **82.7** | **111.2** | **1.47** | **40.9** | 15 | **1.62** |

### utcsat_multi_sw10

| arm | n | net | maxDD | DDdur | uw% | ulcer | sortino | calmar | m+% | streak | PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 253 | +60.2 | 29.4 | 66 | 94.5 | 110.3 | 67.3 | 1.03 | 45.8 | 9 | 1.33 |
| half | 242 | +66.3 | 28.9 | 49 | 94.6 | 176.6 | 72.8 | 1.15 | 37.5 | 9 | 1.36 |
| **half+delay1** | **244** | **+87.1** | 29.4 | **48** | 94.7 | 187.3 | **94.5** | **1.48** | 33.3 | 9 | **1.47** |
| delay_r_1.5 | 250 | +72.9 | 30.3 | 65 | **94.0** | 113.8 | 79.3 | 1.20 | **54.2** | 10 | 1.39 |
| **skip_decisive** | **200** | **+76.8** | **24.6** | **42** | **92.5** | **52.2** | **84.9** | **1.56** | **50.0** | 9 | **1.52** |

### age10_dirmatch_swingpause_single_sw10

| arm | n | net | maxDD | DDdur | uw% | ulcer | sortino | calmar | m+% | streak | PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 76 | **+43.2** | **8.6** | **9** | **73.7** | **31.6** | **51.4** | **2.52** | **66.7** | 8 | **1.91** |
| half | 71 | +28.0 | 9.4 | 15 | 81.7 | 88.5 | 31.7 | 1.49 | 54.2 | 8 | 1.57 |
| half+delay1 | 71 | +27.5 | 9.5 | 15 | 81.7 | 93.4 | 30.9 | 1.46 | 54.2 | 8 | 1.56 |
| delay_r_1.5 | 75 | +41.2 | 8.6 | 9 | 76.0 | 45.2 | 47.7 | 2.40 | 62.5 | 8 | 1.84 |
| skip_decisive | 47 | +16.0 | 10.2 | 15 | 80.8 | 345.8 | 17.5 | 0.79 | 45.5 | 7 | 1.47 |

---

## 4. Equity-lens verdicts (curve better AND net not hurt, both sides)

| config | arm | dNet IS/OOS | dDD IS/OOS | dUlc IS/OOS | equity verdict | legacy 30R screen (historical) |
|---|---|---|---|---|---|---|
| champion | half | +102.9 / +2.6 | −2.8 / +6.6 | +2.23 / −16.11 | **CURVE PASS BOTH** | no |
| champion | **half+delay1** | **+103.8 / +19.6** | **+0.7 / +6.9** | **+2.21 / −28.57** | **CURVE PASS BOTH** | no |
| champion | delay_r_1.5 | +25.6 / +10.9 | −1.4 / +2.8 | +1.14 / −1.66 | **CURVE PASS BOTH** | no |
| champion | **skip_decisive** | **0 / +29.2** | **0 / +19.3** | **0 / +130.9** | **CURVE OOS ONLY** | no |
| utcsat | half | +42.0 / +6.1 | −5.6 / +0.5 | +0.04 / −66.27 | CURVE OOS ONLY | no |
| utcsat | **half+delay1** | **+52.2 / +26.9** | −2.7 / −0.1 | +1.71 / −76.97 | **CURVE PASS BOTH** | no |
| utcsat | delay_r_1.5 | +19.6 / +12.6 | −2.8 / −0.9 | +0.85 / −3.55 | **CURVE PASS BOTH** | no |
| utcsat | **skip_decisive** | **0 / +16.6** | **0 / +4.7** | **0 / +58.1** | **CURVE OOS ONLY** | no |
| age10 | half / half+delay1 / delay1.5 / skip_dec | net or curve hurt | — | — | **CURVE FAIL** | no |

**Legacy 30R/yr screen (historical reference only, not a project rule):** 0/12 arms would have cleared it.  
**Equity lens (current research evidence):** 5/12 CURVE PASS BOTH, 3/12 CURVE OOS ONLY (champion skip_decisive, utcsat half, utcsat skip_decisive), 0/12 IS-only.

---

## 5. Findings

### 5.1 `half+delay1` — strongest both-sides equity improvement on multi

Widen trail ratchet to halfway (`exp_trail_half=1`) and delay trail until +1.0R unrealized (`exp_trail_delay_r=1.0`).

**Champion:**
- IS net **+325.8 → +429.6** (+103.8), DD **27.7 → 27.0**, ulcer **14.6 → 12.4**, calmar **3.20 → 4.34**, sortino **328 → 424**, PF **1.81 → 2.10**, DD duration **72 → 56**.
- OOS net **+70.2 → +89.8** (+19.6), DD **53.2 → 46.3**, calmar **0.66 → 0.97**, sortino **78 → 96**, PF **1.34 → 1.42**, max streak **15 → 15** (unchanged).
- **Yearly gross OOS flips 2021:** baseline **−11.0** → half+delay1 **+11.1** (champion); utcsat **+13.2 → +40.3**. 2022 roughly flat (116.7→117.1 / 79.5→81.5).
- IS yearly gross stays positive every year (2023/24/25/26 all >100 on champion arm).

**Utcsat:**
- IS **+358.9 → +411.1**, ulcer **11.55 → 9.84**, DD duration **40 → 29**, calmar flat-to-up.
- OOS **+60.2 → +87.1**, calmar **1.03 → 1.48**, sortino **67 → 95**, PF **1.33 → 1.47**.

**Why it helps the curve:** slower/wider trail lets winners breathe through noise (less premature trail-outs) without the age10-style tight structure. It improves the existing multi equity path even though the original fixed R/year comparison was modest.

**Caveat:** OOS ulcer on champion is *higher* in absolute terms (213→242) because peaks are higher relative to a still-deep early-2021 trough; maxDD and calmar still improve. Monthly win % dips slightly (51→44 IS, 37.5→37.5 OOS). Age10 hates this arm (net hurt both sides) — single already has a tight, high-calmar curve.

**Status:** kwargs KEPT default-off. **OPEN RESEARCH CANDIDATE under equity lens** on multi.

### 5.2 `skip_decisive` — best OOS equity insurance in the batch

Skip entries when `use=="decisive"` (15m ATR% > 0.65 at entry, causal).

**IS:** perfect no-op on multi (0 decisive trades) — identity-preserving.  
**OOS (the whole point):**

| config | net | maxDD | ulcer | calmar | sortino | PF | uw% |
|---|---:|---:|---:|---:|---:|---:|---:|
| champ baseline | +70.2 | 53.2 | 213.6 | 0.66 | 78.5 | 1.34 | 95.0 |
| champ ON | **+99.3** | **33.8** | **82.7** | **1.47** | **111.2** | **1.62** | **91.9** |
| utcsat baseline | +60.2 | 29.4 | 110.3 | 1.03 | 67.3 | 1.33 | 94.5 |
| utcsat ON | **+76.8** | **24.6** | **52.2** | **1.56** | **84.9** | **1.52** | **92.5** |

This is the single biggest OOS curve improvement measured: ulcer roughly **halves**, maxDD −19.4R (champ), calmar more than doubles, and net still rises. It is *exactly* the 2021-style high-vol insurance hypothesized in 24.18 — and it never fires in 2023–26-like markets, so it cannot overfit the IS era.

**Age10:** fires and hurts both sides (net −10/−27, OOS ulcer explodes 31.6→345.8). Do not stack on age10.

**Status:** kwargs KEPT default-off. **OPEN RESEARCH CANDIDATE on multi** (free insurance in high-vol eras). OOS curve evidence is strong; IS is a no-op on the tested multi references.

### 5.3 Cohort variable sizing — mixed, not universal

No separate equity harness (post-process weighted R on fixed trade lists).  
OOS net **falls** on every multi map (champ elite −24, full −28; utcsat elite −32, full −36) → OOS curve must worsen. IS gains are era-dependent (streak cohorts different in 2021–22).  
**Verdict unchanged: NOT ADOPTED** under either lens.

### 5.4 Age10 baseline remains the smoothest curve we have

IS: DD 8.7, ulcer 3.9, calmar 13.6, sortino 547, PF 7.57, max streak 5, 62.8% months positive.  
Almost every experimental arm *degrades* this curve. Treat age10 as a **curve reference**, not a place to bolt on trail tweaks.

### 5.5 Separate research lenses

| Raw P&L comparison | Does the variant improve net R? | Report delta separately; no fixed pass/fail threshold |
| Equity | Is the curve better AND net not hurt on both sides? | 5/12 PASS BOTH, 3/12 OOS ONLY |
| Production need | Is there a demonstrated operational benefit? | No fixed R/year requirement; baseline itself is not independently production-validated |

**Research interpretation (no automatic adoption gate):**

1. Report raw IS/OOS net-R deltas.
2. Report equity-curve changes separately.
3. Treat positive P&L plus improved drawdown/recovery as evidence of potential, not as automatic deployment authorization.
4. Treat harm in an applicable period or configuration as a material caveat.
5. Baseline is a comparison anchor, not an independently production-validated system.

Under this: `half+delay1` and `skip_decisive` (multi only) are **research candidates with positive/equity-supporting evidence**, not automatic production changes.

---

## 6. Decision (this session)

| arm | raw P&L comparison | equity comparison | research status |
|---|---|---|---|
| half+delay1 (multi) | positive IS/OOS net-R delta | PASS BOTH on studied multi curves | **OPEN RESEARCH CANDIDATE**; keep default-off |
| skip_decisive (multi) | positive OOS net-R delta; IS no-op | strong OOS curve improvement | **OPEN RESEARCH CANDIDATE / OOS-specific insurance**; keep default-off |
| delay_r_1.5 (multi) | positive but smaller IS/OOS delta | mixed/curve-supported in studied cells | secondary research candidate |
| half (multi) | positive but config-dependent | mixed | secondary research candidate |
| any age10 stack | hurt in tested cells | no support | closed |
| cohort sizing | OOS net hurt | curve unsupported | closed |

**No production change in this study.** Kwargs remain default-off. Identity + smoke stay green.

---

## 7. Reproduce

```powershell
$env:PYTHONIOENCODING='utf-8'
python -u live_stuff/tests/exp_equity_quality.py
```

Related prior runs (same bases, same equity study cohort):
- `live_stuff/tests/exp_trail_slower.py` → `_trail_slower_results_{is,oos}.json`
- `live_stuff/tests/exp_skip_decisive_ship.py` → `_skip_decisive_ship_results.json`
- `live_stuff/tests/exp_cohort_sizing.py` → `_cohort_sizing_results_{is,oos}.json`

---

## 8. Cross-links

- CHECKLIST 24.18 / 24.19 / 24.20 — raw P&L and equity comparisons
- CHECKLIST 24.23 — this study
- EXPERIMENT_LOG rows for skip_decisive, cohort sizing, trail, equity study
- EXP_LA4_TRAIL_TIGHTEN.md — trail *tighten* is DEAD (kills monsters); this study is trail *widen* / *delay* (opposite direction)
- MASTER_LEADERBOARD §7b — skip_decisive NET tables
- D3_ALIGNMENT_LOOKAHEAD_AUDIT.md — age10 causal caveats (use as reference config only after path-true validation; this study treats registry age10 as the frozen reference used all session)
