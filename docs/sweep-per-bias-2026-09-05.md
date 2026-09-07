# Per-Bias Smart Sweep — 2026-09-05 (11:13 → 11:34)

**Scope:** `exec:1min` only, `270` days, `min≥13` logical, `108` combos per bias × `6` biases = `648` total, `8` workers, `682s` wall (`~1.05s` per cfg). Grid `sl [avg,prev_pivot,swing_end] × rr [2,3,4] × min [13,15,20] × BE [0,1] × gap [0.27,0.35] × ft true × max2 15:15 always` fixed `swing_traverse true need_opp true` (`backend/sweep_per_bias.py:1`).

**Engine:** `backend/src/intraday_1m_standalone.py:509` 2nd-trade fix, `backend/src/bias.py:640` `compute_bias_with_mode` dispatcher.

---

## Best per Bias (Logical, min≥13)

| Bias Mode | Best Total_R | WR% | PF | Trades | sl | rr | min | BE | gap | ft | Max | Cutoff | 2nd |
|-----------|--------------|-----|----|--------|----|----|-----|----|-----|----|-----|--------|
| **daily_swing** (original `bias.py:364`) | **+35.19** | 14.3 | 1.15 | 516 | prev_pivot | 4.0 | 13 | 1.0 | 0.35 | true | 2 | 15:15 | always |
| **ema_daily_10** (`close>EMA10 → long`) | **+51.95** | 22.7 | 1.15 | 516 | prev_pivot | 4.0 | 15 | 0 | 0.27 | true | 2 | 15:15 | always |
| **ema_daily_5** | **+56.73** | 15.0 | 1.25 | 519 | prev_pivot | 4.0 | 15 | 1.0 | 0.27 | true | 2 | 15:15 | always |
| **ema_5min_20_50** (`EMA20>50 cross`) | **+74.74** | 16.3 | 1.33 | 515 | prev_pivot | 4.0 | 13 | 1.0 | 0.27 | true | 2 | 15:15 | always |
| **opposite_first** (`B→bearish S→bullish`) | **+82.28** | **35.6** | 1.30 | 519 | **avg** | **2.0** | 13 | 0 | 0.27 | true | 2 | 15:15 | always |
| **streak_3_1_1** (daily color 3-1-1) | **+96.41** | 24.4 | 1.28 | 512 | prev_pivot | 4.0 | 15 | 0 | 0.27 | true | 2 | 15:15 | always |

**Top per bias detailed:**

**daily_swing**
1. `+35.19R` `14.3%` `prev_pivot rr4 min13 BE1 gap0.35`
2. `+33.34R` `21.6%` `prev_pivot rr4 min13 BE0 gap0.27` (tied)
3. `+26.55R` `21.4%` `prev_pivot rr4 min15 BE0`

**ema_daily_10**
1. `+51.95R` `22.7%` `prev_pivot rr4 min15 BE0 gap0.27` (was `+38R` with same filters but `min13 BE1` in earlier single-point test `fix/test_ema_5min.py`)
2. `+45.62R` `33.8%` `avg rr2 min13 BE0` — best winrate for this bias

**ema_5min_20_50**
1. `+74.74R` `16.3%` `prev_pivot rr4 min13 BE1`
2. `+63.53R` `16.3%` `prev_pivot rr4 min20 BE1`
3. `+62.37R` `23.0%` `prev_pivot rr4 min13 BE0`

**opposite_first**
1. `+82.28R` `35.6%` `avg rr2 min13 BE0` — **best winrate overall**
2. `+74.34R` `27.1%` `prev_pivot rr3 min13 BE0`

**streak_3_1_1**
1. `+96.41R` `24.4%` `prev_pivot rr4 min15 BE0` — **best total_R overall**
2. `+91.03R` `24.1%` `avg rr4 min15 BE0`

**ema_daily_5**
1. `+56.73R` `15.0%` `prev_pivot rr4 min15 BE1`

---

## How Master Dropdown Uses Them

`frontend/src/lib/biasPresets.ts:1` auto-generated from this sweep (`sweep_per_bias_best_*.json`):

```ts
BIAS_PRESETS = {
  daily_swing: { sl_mode:"prev_pivot", rr_target:4, min_sl_pts:13, breakeven_r:1, gap_pct:"0.35", ... }, // +35R
  ema_daily_10: { sl_mode:"prev_pivot", rr_target:4, min_sl_pts:15, ... }, // +51R
  ...
  streak_3_1_1: { sl_mode:"prev_pivot", rr_target:4, min_sl_pts:15, ... }, // +96R
}
```

* `frontend/src/components/IntradayPanel.tsx:395` **Master Bias** select `BIAS_MODES` `api.ts:359` — onChange loads `BIAS_PRESETS[v]` into all `local*` states (`sl/rr/min/BE/gap/ft/max/cutoff/second`) and shows `Apply` — clean, not messed. Selecting `EMA Daily 10` instantly shows its `+51R` filters, not `daily_swing`'s `+35R`.
* `frontend/src/app/chart/page.tsx:1168` same master in chart top bar + `EMA` toggle `chart_ema_on` auto-ON for `ema_*` (`useEffect` on `bias_mode`). `EMA` lines `EMAPrimitive.ts:1` toggleable: `EMA` button `f59e0b` shows `5:#f59e0b 10:#10b981 20:#60a5fa 50:#a78bfa` for `daily 5/10/20` vs `5min 20/50`.
* Trades + swings + EMA all overlay: `StockChart.tsx:998` `PositionPrimitive` for trades, `EMAPrimitive` for EMA.

**To see each on chart:**

1. `http://127.0.0.1:3002/chart` → top bar `MASTER BIAS` → pick `Streak 3-1-1` → `EMA` auto ON (if `ema_*` else manual) → `IntradayPanel` shows `Max Trades:2 Cutoff:15:15` etc auto-set to that bias's best → `Apply` → chart bias arrows (`Bias` toggle) + trades boxes + EMA lines update. Do for each `daily_swing`, `ema_daily_10`, `ema_5min_20_50`, `opposite_first`, `streak`.

**Files:** `backend/sweep_per_bias.py` (648, 682s), outputs `backend/sweep_per_bias_*_*.json` per bias + `sweep_per_bias_best_*.json` + `frontend/src/lib/biasPresets.ts` (presets). `fix/ideas.md:9` T1-T6 already logged, `fix/test_crazy*.py` for streak/EMA.

Next: Full `3456` logical with `ft false` etc or keep this `648` smart as final logical best per bias?
