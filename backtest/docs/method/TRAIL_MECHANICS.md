# Trail Mechanics — `half` + `delay1` (story explainer)

**Status:** research explainer. Kwargs default-off; open candidate on multi, not adopted.
**Harness:** `backtest/tests/exp_trail_slower.py`
**Patch:** `backtest/tests/test_experiments_craze.py:1183-1256` (coarse + fine × long + short)
**Engine ratchet (baseline):** `backend/src/btc/engines/htf_ltf/v18_streak_halt.py:626-644` (coarse), `:668-686` (fine) — D3 ordering: ratchet applies BEFORE SL check on the same bar.

---

## Setup

Entry at **100**, long. Swing-low SL at **80** → risk = 20. One R = 20.

Trail ka kaam: jab price upar jaaye, SL ko peeche se khinchna (profit lock). Bas yahi khel.

---

## Baseline (no flags)

Naya swing high confirm hua **90** pe:

```
if sl_cur < cand: sl_cur = cand   # 80 → 90, full jump, usi bar pe
```

- **Faida:** SL tight → jaldi lock.
- **Nuksan:** abhi sirf +10 move tha (½R bhi nahi); chhoti si pullback pe trail-hit → trade gaya, bada move baad mein.

---

## `exp_trail_half=1` — "aadha step"

```
if sl_cur < cand: sl_cur = 0.5 * (sl_cur + cand)
```

| mode | SL after cand=90 | next cand=95 |
|---|---|---|
| baseline | **90** (full) | 95 |
| half | **85** (midpoint of 80 & 90) | `0.5*(85+95)=90` |

Har baar **sirf mid-point** tak chalta hai → **wider trail**, chhoti pullback pe bacha rehta hai, asymptotically cand ke paas jaata hai.

---

## `exp_trail_delay_r` — "pehle prove kar, phir trail"

Ratchet se pehle gate:

```
unrealized = (best - entry) * direction / risk
if unrealized < exp_trail_delay_r: skip this event
```

- **`best`** = peak favorable excursion (MFE), raw price level nahi — lekin example mein milta hai: `(120-100)/20 = +1.0R`.
- Threshold se pehle aaye events **gayab** — baad mein back-fill nahi hote.
- Fine (1m) path: `exp_trail_delay_prevbar` on ho toh prev-bar best use karta hai (causality audit flag).

**Example (delay1=1.0):** peak 105 → 0.25R → SL **80 hi** rahega. Jab best ≥ **120** (+1R) → ratchet chalu.

---

## `exp_trail_skip_n` — pehle N events fek do

`_trail_skip_rem` init = `exp_trail_skip_n` (`test_experiments_craze.py:779`); pehle N trail events decrement + ignore (`:1194-1195`). Pure event counter, R se independent.

---

## `half + delay1` (combo jo kaam kiya)

1. **Pehle +1R wait** (delay) — trail bilkul off jab tak trade prove na kare.
2. **Phir aadha-aadha chalna** (half) — trail on, lekin har baar sirf mid-point.

**Worked story:**

> Entry 100, SL 80. Price 110 pe swing, 115 pe swing — **kuch nahi hua** (1R = 120 abhi baaki).
> Price **122** → +1.1R → trail ON.
> Cand 125 → SL 80 se seedha nahi, `mid(80,125)=102.5`.
> Cand 135 → `mid(102.5,135)=118.75`.
> Ultimately 150 pe trail/TP — bich mein chhoti pullback pe SL ~102 pe raha, trade zinda.

---

## Results (path-true IS 2023-26 / OOS 2021-22)

| config | IS Δ vs baseline | OOS Δ | note |
|---|---|---|---|
| champ (multi) | **+103.8R** (325.8→429.6) | **+19.6R** (70.2→89.8) | CURVE PASS BOTH |
| utcsat (multi) | **+52.2R** (358.9→411.1) | **+26.9R** (60.2→87.1) | CURVE PASS BOTH |
| age10 (single) | −13.1R | −15.7R | CURVE FAIL — universal nahi |

- Equity: champ IS DD 27.7→27.0, ulcer 14.6→12.4, calmar 3.20→4.34; OOS 2021 yearly gross **−11 → +11**.
- **Causality (Stage 19, CHECKLIST 24.24):** strict-prevbar MFE gate = original results identical (champ IS 466t/+429.63, OOS 271t/+89.78) — no same-bar leak, no retroactive rewrite.
- **Status:** OPEN RESEARCH CANDIDATE on multi only; default-off; legacy 30R screen irrelevant (research policy: no fixed ship gate).

Artifacts: `_trail_slower_results_{is,oos}.json`, `_equity_quality_results.json`, `_trail_half_delay1_causality_results_{is,oos}.json`.

---

## ATR trail — already DEAD, dobara mat khod

Idea: swing trail ki jagah `sl = best − k × ATR(14)` (jaise k=0.1/1.0).

| ref | result |
|---|---|
| LA9 `exp_la9_atr_trail.py` | **DEAD −43R … −271R**, all configs |
| `method/EXPERIMENT_LOG.md:38` | "Swing trail kills ATR trail" |
| `method/LOSS_AUTOPSY.md:295` | "Trail variants (tighten, **ATR trail**, delay) kill monsters" |

**Note:** `sl_buf_atr=0.01` = **initial SL buffer** (pivot + 0.01×ATR14), entry placement — already live, alag cheez. Trail family = swing trail + half/delay modulation, not ATR-distance.

---

## One-line cheat sheet

| flag | meaning |
|---|---|
| baseline | har swing pe seedha SL khinch |
| `exp_trail_half=1` | har baar aadha step (midpoint), wider |
| `exp_trail_delay_r=1.0` | pehle +1R prove, phir trail chalu |
| `exp_trail_skip_n=N` | pehle N trail events skip |
| `half+delay1` | pehle prove, phir dheere-dheere lock |

Related: `signal/EQUITY_CURVE_STUDY.md` §5.1, `method/CHECKLIST.md` 24.20/24.23/24.24, `method/EXPERIMENT_LOG.md` 2026-09-24 rows, `method/STRATEGY_STATE_OF_PLAY.md` ~:396, `method/RESEARCH_POLICY_CORRECTION.md`.
