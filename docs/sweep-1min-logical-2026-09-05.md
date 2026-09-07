# 1-min Logical Sweep — 2026-09-05 (09:10 → 10:00)

**Scope:** `exec:1min` only. Full history `data/nifty_1min.csv` `101,310` rows `2025-08-01` → `2026-09-04` (`270` trading days, `264` traded), `data/nifty_5min.csv` `20,262`, `nifty_daily.csv` `271`. Bias via `backend/src/bias.py:364` `compute_bias` (daily overview `backend/src/overview.py:153` + closing `bias.py:41`), gap via `intraday.py:149` `classify_case`.

**Engine:** `backend/src/intraday_1m_standalone.py:36` `simulate_day_1min` (Walker `backend/src/walker.py:103`, FirstSwing `backend/src/firstswing.py:70` `SwingEngine` `timeCap 09:29 minBars 14`). Fixes applied this session:

* **2nd-trade re-arm** `intraday_1m_standalone.py:509` post-loss finds next same-direction swing (`_find_swing(ref_end+1, ref_dir)` stitching `firstswing.py:726`), updates `ref_*`, `entry_swing_confirmed_idx`, resets `pivot_break_count=0` keeps `broken_pivot_levels` (not clear — `550` poison marks from `pivot_marked_broken:684` stay), `cur_swing=found_dir` for same-direction retry (long→long, short→short).
* **Pivot counting** `intraday_1m_standalone.py:690` entry trigger now `if fs2_dir is not None` (covers aggressive 2nd-trade via new FS3) and aggressive `793` requires `p.idx > entry_swing_confirmed_idx` (FS mark) + `!= confirm_pivot_idx`, so FS's own chop pivot (`firstswing.py:165` `last_confirm_hit`) never counts as 1st break. `required_breaks = 2 if conservative else 1` `821` unchanged (`docs/entry theory.md:26`).
* **Filters added** `intraday.py:74` `DEFAULT_CFG` `max_entries=2`, `entry_cutoff="15:15"`, `second_trade_after="sl_only"` (`sl_only|loss|any_non_target|always`), `intraday_1m_standalone.py:619` gate `fs_gate_ok`, `cur time < cutoff`, `second_allowed`, `intraday_shared.py:38` BE gate; `backend/server.py:510` `/api/intraday/backtest` + `562` `/api/intraday/{date}` expose, `frontend/src/lib/api.ts:372` `BacktestParams`, `frontend/src/components/IntradayPanel.tsx:10` UI, `frontend/src/app/chart/page.tsx:48` `loadSavedIntradayFilters`.

## Sweeps Run

### 1) Quick 128 combos — `backend/sweep_1min_mp.py:quick_grid:35` via `backend/sweep_1min_mp.py` 4 workers, 103s, ~0.81s/cfg

`sl [avg,prev_pivot] × rr [2,3] × min [0,13] × BE [0,1] × gap 0.27 × ft true × max [1,2] × cutoff [15:15,12:00] × second [sl_only,always]`

* Output `backend/sweep_results_20260905_084242.json/.csv`

Top by `total_R`:

1. `+26.37R` `26.2% PF1.07` `512` trades `prev_pivot rr3.0 min0 BE0 gap0.27 ft true max2 15:15 always` — tight `min0` not tradable.
2. `+24.57R` `34.0%` `prev_pivot rr2.0 min0 BE0`
3. `+21.76R` `32.4%` `avg rr2.0 min0 BE0`

`max1` → `264 trades -23.94R`; `max2 sl_only 15:15` → `358 +2.11R` (was `-17R` before fix); `max2 always` → `516 +18R`. `cutoff 12:00` was `-11R` vs `+2R` for `15:15`.

### 2) Smart logical 152 combos — `backend/sweep_1min_smart.py` 8 workers, 74s, `min≥13` only

Grid `sl [avg,prev_pivot,swing_end] × rr [2,3] (+4 extra probes) × min [13,15,20] × BE [0,1] × gap [0.27,0.35] × second [sl_only,always]` fixed `max2 15:15 ft true`, plus 8 extra `rr4` probes.

* Output `backend/sweep_smart_20260905_092551.json/.csv`

Top by `total_R` (logical `min≥13`):

1. `+35.19R` `14.3% PF1.15` `516` trades `prev_pivot rr4.0 min13 BE1.0 gap0.27 always` — best before 2nd fix
2. `+33.34R` `21.6% PF1.09` `prev_pivot rr4.0 min13 BE0`
3. `+26.55R` `21.4%` `prev_pivot rr4.0 min15 BE0`
4. `+23.70R` `21.1%` `avg rr4.0 min13 BE0`
5. `+18.31R` `32.0%` `avg rr2.0 min13 BE0 gap0.35 always` — best winrate logical

`swing_end` worst `-32.98R`. `BE` irrelevant for `rr2` (`<rr` gate false), `gap 0.27` ≈ `0.35`.

### 3) Current best after 2nd-trade pivot fix (re-run direct `run_backtest_1min:743`)

Same filters as #1 but after `p.idx > entry_swing_confirmed_idx` fix (commit ~09:45):

* `prev_pivot rr4.0 min13 BE1.0 gap0.27 ft **true** max2 15:15 always` → **`+45.72R 14.3% PF1.15 516 trades 308/208 SL187 C2C165 eod5`** — you confirmed `516 14.3% +45.72` FT ON.
* Same with `ft false` → `515 15.3% +45.72R SL254 C2C182 eod6` — your earlier `515 15.3% +45.72R 254/182` (FT OFF). `FT` toggle swaps `SL↔C2C` but same `R` for `rr4` (since `ft_fail` `465` only within 2 bars).
* Quick/smart `35.19R` was stale (pre-fix).

**Most profitable logical (`min≥13`, tradable) now is the `45.72R` config above**, not the `26R` `min0` tight one. `FT ON` vs `OFF` tie on `R` for this combo.

## Exact Filter to Reproduce `+45.72R`

IntradayPanel → Experiment → Apply (all `backend/src/intraday.py:74` defaults else):

* `SL: Pivot / ECL ±1pt` `sl_mode=prev_pivot`
* `Exec: Precise 1-Min` `execution=1min`
* `Target: 1:4` `rr_target=4.0`
* `Min SL: 13 pts` `min_sl_pts=13` (widen ` <13` → `13`, `intraday_1m_standalone.py:410`)
* `Breakeven: 1R (1:1)` `breakeven_r=1.0`
* `Gap ≥0.27%` `gap_pct=0.27` (`0.0027`)
* `FT-fail: ON` (or OFF — both `+45.72R` for this combo) `ft_fail_enabled=true/false`
* `Max Trades: 2` `max_entries=2`
* `Cutoff: 15:15` `entry_cutoff="15:15"` (open trade still to `sl/target/eod` `EOD_EXIT 15:15`)
* `2nd: Always` `second_trade_after="always"` (`sl_only` was `+9.75R` #13)
* `Trail: Off`, `Need opposite swing: ON`, `Swing traverse: ON`

API: `GET /api/intraday/backtest?sl_mode=prev_pivot&execution=1min&rr_target=4.0&min_sl_pts=13&breakeven_r=1.0&gap_pct=0.27&ft_fail_enabled=true&max_entries=2&entry_cutoff=15:15&second_trade_after=always&sl_pivot_buffer=1.0&swing_traverse=true&need_opp_swing=true&trailing=off&entry_method=pivot_break` (`backend/server.py:544`)

Stats `270` days `264` traded `516` trades `win 14.3%` `avg +0.09R` `PF 1.15` `308/208` `target69 sl187 c2c165`.

Best *winrate* logical is `avg rr2.0 min13 BE0 gap0.27 always` `+18.31R 32.0% 516 trades`.

## Next

* Full logical `3456` grid (`default_grid:47` `sl 4×rr3×min3×BE3×gap2×ft2×max2×cutoff2×second2`) was killed at `760/3456` (`46min` est 4 workers). A pruned logical sweep (`sweep_1min_logical.py` `1728` combos `min 13/15/20` only, `23min` on 8 workers) is ready to run till `22:00` to confirm no `min15/20` `BE1.5` `gap0.35` `rr3` beats `+45R`. The `152` smart already covers the top region.
* Pending `sweep_1min_logical.py` with `8` workers (`09:10` start) was `KILLED` per user — not running. Re-launch with `logical 1728` or `full 3456` on demand.

Files: `backend/sweep_1min.py`, `backend/sweep_1min_mp.py`, `backend/sweep_1min_smart.py`, `backend/sweep_1min_logical.py`, outputs `backend/sweep_results_*.json/.csv`, `backend/sweep_logical_out.txt`.
