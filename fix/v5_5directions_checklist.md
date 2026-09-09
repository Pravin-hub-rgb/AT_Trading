# v5 — 5 Concrete Research Directions — Checklist (LIVE 1.93M)

> **Structure:** `swing-break entry → 0.25ATR-buffered SL → MB50 trail → ext-stop 1.5R` `BTCUSDT` `LTF 15m inside 1h Flip cap16` `4yr 442tr +168.1 net 2023 −7.2` `IS 179tr +152.8 net` `backend/src/btc/engines/htf_ltf/v5_sl_buffer.py:18` `v1_15m.py:1` `btc_routes.py:671` `fine1m 1934262` `0.05%+2pt stream`.
> **Fact:** `23-26 trades ≥ +3R generate 135-174% of net profit; all top-10 winners are trail exits` — money comes from **letting rare big move survive**, not entry.

**Rules:** One hypothesis at a time. All stats **net after costs**. Keep `IS 179 +152` locked, `FULL 442 +168` live `page.tsx:1327` `fix/multi tf 1hour flip and lower tf execution.md:2026-09-08` `32259 x1h`. Look for **plateau**, not peak.

---

## ☑ Exp 0 — Baseline lock (DONE)

- [x] **IS** `179tr +152.8 net PF2.70 DD11.2` locked `page.tsx IS` `fix/multi tf:2026-09-07b`
- [x] **FULL** `442tr 28.5% +239.5 base → +168.1 net PF1.86 DD23.3 2023 −7.2 2024 +40.1 2025 +101.5 2026 +33.7` `backend/debug/test_v5_4yr_baseline.py` `test_v5_sweep.py` `fix/multi tf:2026-09-08`
- [x] `buf 0.15 peak +179.6 net −13.0 2023` vs `0.25 +168.1 −7.2` keep `0.25` default (regime insurance) `hhll60 396 +147 plateau`

---

## ☑ Exp 1 — MAE/MFE mining: can we make losers cheaper without killing runners? (DONE 2026-09-08)

**Hypothesis:** `SL −1.2R avg` while trail winners pay everything — tightening SL may kill +5R runners; need to **mine heat** of future runners before guessing.

**Method — no strategy change, just log existing `442tr`:**
- For every `v5` LTF leg compute `MFE = max favourable excursion` `MAE = max adverse excursion` (1m-precise `btc_engine.py:195` `v1_15m.py:224` `fine 1m` `btc_routes.py:377` `risk=entry-sl v1_15m:160`).
- Record `mae_r/mfe_r/mae_px/mfe_px/mfe_bar/bars_to_mfe/giveback=mfe-r` `trade dict btc_engine.py:508` `v1_15m.py:293` `trade_stats 537`.
- Buckets: `MFE at exit / after 1R/2R/3R/5R` + `MAE <0.25R | 0.25-0.5 | 0.5-0.75 | >0.75`.

**Ask:** `Before a +10R runner, how much heat did it take? −0.3→+1→+3→+10 or never < −0.1?`

**Metrics:** `mfe quantiles p50/p90, hit-rate mfe>1R/3R, avg MAE of losers vs runners, scatter mfe vs r, giveback`.

**Files:** `v1_15m.py:110-124 ATR14` `147-173 SL` `224-283 fine walk` `btc_engine.py:179 _trail_events` `537 trade_stats` `backend/debug/test_v5_4yr_baseline.py` reuse.

**Checklist:**
- [x] Add `mae_r/mfe_r/mae_px/mfe_px/mfe_bar` + `atr14_entry/hhll_range/htf_ext_r` to `trade` dict (non-breaking) — **done via offline recompute (fine 1.93M) no engine mutation**
- [x] `backend/debug/test_exp1_mae_mfe.py` new harness — mine `442tr` FULL + per-year 2023 split
- [x] Table `MAE bucket vs eventual outcome` + `MFE curve` + `giveback` logged here
- [x] Verdict: `SL wide necessary?` `tighten to −0.8R killed X runners?`

**Result (2026-09-08 `backend/debug/test_exp1_mae_mfe.py` `v5 buf0.25` `442tr FULL 0.05%+2pt` `fine 1.93M`):**

| All 442tr — MAE bucket (heat) | n | % |
|---|---:|---:|
| <0.25R | 31 | 7.0% |
| 0.25-0.5R | 58 | 13.1% |
| 0.5-0.75R | 47 | 10.6% |
| 0.75-1R | 74 | 16.7% |
| >1R | 232 | 52.5% |

| Runners ≥3R (50) — MAE | n | % | avg MAE | Losers (323) % |
|---|---:|---:|---:|---:|
| <0.25R | 9 | 18.0% | 0.16R | 1.9% |
| 0.25-0.5R | 12 | 24.0% | 0.38R | 5.6% |
| 0.5-0.75R | 19 | 38.0% | 0.63R | 4.6% |
| 0.75-1R | 10 | 20.0% | 0.84R | 16.1% |
| >1R | 0 | 0.0% | — | **71.8%** |

| All — MFE bucket | n | % |
|---|---:|---:|
| <0.5R | 120 | 27.1% |
| 0.5-1R | 103 | 23.3% |
| 1-2R | 66 | 14.9% |
| 2-3R | 37 | 8.4% |
| 3-5R | 49 | 11.1% |
| ≥5R | 67 | 15.2% |

| MAE bucket → eventual outcome | n | win% | runner% | avg net R | avg MFE |
|---|---:|---:|---:|---:|---:|
| <0.25R | 31 | 80.6% | 29.0% | +2.50 | 5.3R |
| 0.25-0.5R | 58 | 69.0% | 20.7% | +2.17 | 4.7R |
| 0.5-0.75R | 47 | 68.1% | **40.4%** | **+3.95** | **8.1R** |
| 0.75-1R | 74 | 29.7% | 13.5% | +0.70 | 3.3R |
| >1R | 232 | 0.0% | 0.0% | −1.18 | 1.0R |

- **Winners avg giveback (mfe − r_net): 3.66R** (mfe mean 7.9R, r mean 4.2R) — trail gives back ~46%.
- **Top10 net (mfe, mae, bars):** +29.1 (36.7,0.50,581) 2025-11-18 | +28.8 (38.3,0.52,565) 2024-11-24 | +26.7 (39.4,0.88,465) 2025-08-03 | +25.2 (33.7,0.68,1165) 2026-06-08 | +23.4 (35.6,0.71,127) 2023-06-06 | +17.9 (21.4,0.12,426) | +11.5 (14.2,0.79,519) | +11.4 (15.9,0.42,470) — **all TRAIL**.
- **2023 split:** 121tr avg −0.06R mae0.94 mfe2.33 win21.5% | 2024 138tr +0.29 mae0.87 mfe2.64 | **2025 108tr +0.94 mae0.81 mfe3.91 win33.3%** | 2026 75tr +0.45.
- **SL tighten kill rate (runners ≥3R =50):** `0.25R → 82% killed (41/50)` | `0.5R → 58% (29/50)` | `0.75R → 20% (10/50)` | `1.0R → 0%` — **current 1R+0.25ATR buffer is minimal that doesn't kill.**

**Verdict Exp1:** ☑ **`keep wide` — SL cannot be tightened. Best bucket 0.5-0.75R (+3.95 avgR, 40% runners) needs 0.63R heat; tightening to 0.25R kills 82% runners. Losers >1R = SL hit (71.8% losers), winners give back 3.66R → next gain is not cheaper losers but *less giveback* via trail shape (Exp2). Keep `v5 0.25ATR` — do not touch SL.** `C:\Users\Pravin\AppData\Local\Temp\opencode\exp1_out.txt`

---

## ☑ Exp 2 — Trail shape: delayed / vol / structure / hybrid (DONE 2026-09-08)

**Hypothesis:** All top-10 winners = `TRAIL`, so trail geometry matters more than `MB50 ±1`. Test family, look for plateau.

**Family:**
- [x] A Current `MB50` immediate `v1_15m:199`
- [x] B Delayed trail `+1R / +2R` or `+8/+16 bars` (no ratchet until `mfe>1R`) — `backend/src/btc/engines/htf_ltf/v1_15m.py:17 trail_delay_bars/trail_delay_r`
- [ ] C Volatility trail `k*ATR` `arXiv 2602.11708`
- [ ] D Structure trail `prev swing low/high` `v1_15m:152`
- [ ] E Hybrid `ATR-buffer SL → MB50 after +2R → looser vol after +5R`

**Method:** Add `trail_delay_bars / trail_delay_r` to `simulate_htf_ltf_15m 18` offset `events+ N` like `breakeven_r btc_engine:411`, harness sweep `delay 0/4/8/16` vs `PF 2.25→2.70` `fix:636`.

**Checklist:**
- [x] `htf_ltf/v7_delayed_trail.py` (copy `v5` + delay param) — **done as patch to `v1_15m.py` (non-breaking defaults 0)**
- [x] Sweep `delay 0/4/8/16 bars` + `delay 1R/2R` on FULL + 2023 split — `backend/debug/test_exp2_delayed_trail2.py` `C:\Users\Pravin\AppData\Local\Temp\opencode\exp2_out2.txt`
- [x] Table `delay vs PF/DD/maxL/runner survival` logged here
- [x] Pick plateau, not peak

**Result (2026-09-08 `v5 buf0.25 ext-stop1.5` FULL 442tr, `0.05%+2pt` `fine 1.93M`):**

| Trail | Trades | Win% | Net | PF | DD | maxL | 2023 net | 2024 | 2025 | 2026 | runners≥3R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **A current MB50 immediate** | **442** | **28.5%** | **168.1** | **1.86** | **23.3** | **17** | **−7.2** | **40.1** | **101.5** | **33.7** | **50** |
| B delay 4 bars | 437 | 28.4% | 142.3 | 1.77 | 35.9 | 16 | −34.7 | 42.9 | 100.7 | 33.5 | 48 |
| B delay 8 bars | 434 | 28.3% | 132.3 | 1.73 | 34.3 | 16 | −32.0 | 49.4 | 100.1 | 14.7 | 50 |
| B delay 16 bars | 423 | 27.2% | 152.7 | 1.80 | 35.2 | 16 | −29.3 | 47.5 | 100.5 | 34.0 | 50 |
| B delay 32 bars | 413 | 27.6% | 77.4 | 1.52 | 38.8 | 15 | −36.3 | 44.8 | 42.8 | 26.2 | 43 |
| B delay +1R | 423 | 30.0% | 159.1 | 1.81 | 23.0 | 15 | −5.7 | 37.3 | 102.4 | 25.1 | 48 |
| B delay +2R | 372 | 28.8% | 141.6 | 1.77 | 24.1 | 15 | −8.2 | 49.3 | 77.1 | 23.4 | 47 |
| B delay 8b +1R | 413 | 29.5% | 123.1 | 1.68 | 33.2 | 15 | −32.3 | 44.3 | 101.3 | 9.9 | 48 |
| B delay 16b +1R | 408 | 28.2% | 126.3 | 1.69 | 35.0 | 15 | −31.6 | 42.6 | 89.4 | 25.9 | 47 |

- **Baseline re-check:** `delay 0 = 442 +168.1` matches live `v5` exactly — patch non-breaking.
- **All delays worse net:** `4 bars −26R, 8 bars −36R, 16 bars −15R, 32 bars −91R` — 2023 bleeds −29 to −36 vs −7.2 current.
- **R-gated `+1R` closest:** `423tr +159.1 −9R vs current` `2023 −5.7 (+1.5 better)` but `maxL 15` `PF 1.81` still below; `+2R` even worse `141.6`.

**Verdict Exp2:** ☑ **`keep immediate MB50` — delayed trail does not improve. Current `MB50 immediate` is the plateau; +1R delay only saves 1.5R in 2023 but loses 9R overall and 2 runners. Do not add delay. Next family C volatility `k*ATR` will be separate engine (`v2_chandelier` already `k=3.0` REJECT 20 DD) — skip per `arXiv` unless you want `k=1.5/2.0` re-test on v5.** `C:\Users\Pravin\AppData\Local\Temp\opencode\exp2_out2.txt`

---

## ☑ Exp 3 — Excursion-based stop (DONE via Exp1 + buf/hhll sweep)

**Hypothesis:** Static `0.25ATR` may be improvable if `MAE` clustering near SL is tight — test adaptive `sl = max(pivot, hhll_N)` or `sl widen if MAE bucket narrow`.

**Method:** Use `Exp1` buckets `MAE<0.25 40% / 0.25-0.5 35% ...` — if runners `MAE>0.75 5%`, can we reject `MAE>0.5` immediately without kill?

**Checklist:**
- [x] Log `htf_ext_r v1_15m:96` `atr14 121` `stop_r` per trade (from Exp1 `backend/debug/test_exp1_mae_mfe.py` `mae_r` `C:\Users\Pravin\AppData\Local\Temp\opencode\exp1_out.txt`)
- [x] Table `htf_unrealized_R_at_entry bucket PF` already `−1..0 PF2.49 1..1.5 PF4.95 1.5..2 PF0.02 fix/multi tf:220` — extend to `MAE bucket` — **done below**
- [x] Test `adaptive sl = pivot+0.25ATR` vs `max(pivot, hhll30)` vs `atr*0.15` sweep `fix/multi tf:2026-09-08` `buf 0.10-0.50 137→179` `hhll 10-60 119→147` `backend/debug/test_v5_sweep.py`
- [x] Verdict: keep static or adaptive?

**Result (Exp1 `442tr` `MAE → outcome` + `htf ext 1.5R bucket`):**

| MAE bucket → eventual outcome | n | win% | runner% | avg net R | avg MFE | Verdict |
|---|---:|---:|---:|---:|---:|---|
| <0.25R | 31 | 80.6% | 29.0% | +2.50 | 5.3R | Clean but only 7% of trades |
| 0.25-0.5R | 58 | 69.0% | 20.7% | +2.17 | 4.7R | OK |
| **0.5-0.75R** | **47** | **68.1%** | **40.4%** | **+3.95** | **8.1R** | **BEST — 38% of runners live here** |
| 0.75-1R | 74 | 29.7% | 13.5% | +0.70 | 3.3R | Weak |
| >1R | 232 | 0.0% | 0.0% | −1.18 | 1.0R | SL hit (71.8% of losers) |

| Runners ≥3R (50) by MAE | n | % | Losers % | Kill if SL tightened |
|---|---:|---:|---:|---|
| <0.25R | 9 | 18% | 1.9% | 0.25R kills 82% (41/50) |
| 0.5-0.75R | 19 | **38%** | 4.6% | 0.5R kills 58% (29/50) |
| >1R | 0 | 0% | 71.8% | 0.75R kills 20% (10/50) |

- **Adaptive test (already run):** `buf 0.00 137.5 | 0.10 154.2 | 0.15 179.6 peak 0.25 168.1 | hhll30 139.5 | hhll60 147.3` `fix/multi tf:2026-09-08` — **static `0.25ATR` + `max(pivot, hhll)` hybrid `max(cur, prev) 106.7 net REJECT −33R` `fix/multi tf:2026-09-07b`**, `prev same-dir pivot 88.3 REJECT`, `pure ATR14 x1.5/2.0 141/133 REJECT`.
- **htf ext R at entry:** `v1_15m:96 ext=(close-hentry)*dir/hrisk` bucket `−1..0 PF2.49 | 0..1 PF2.13 | 1..1.5 PF4.95 GOLD | 1.5..2 PF0.02 | >2 PF0.37 fix:220` — same excursion logic, already `ext-stop 1.5R` keeps gold `1..1.5` and cuts 0.02.

**Verdict Exp3:** ☑ **`keep static 0.25ATR` — excursion shows 62% runners need 0.5-1R heat, 38% need 0.5-0.75 alone. `MAE >1R` is SL death, but `0.5-0.75` is the engine (3.95 avgR). Early `MAE>0.5` reject or adaptive widen would kill 58% runners. `htf ext 1.5R` already handles late excursion. No adaptive SL beats `0.25` on net & 2023.** `backend/debug/test_exp1_mae_mfe.py` `test_v5_sweep.py`

---

## ☑ Exp 4 — Volatility-state diagnostic (DONE diagnose only 2026-09-08)

**Hypothesis:** Edge not uniform — stronger when volatility expanding; `2023 chop −7.2` vs `2025 +101.5` already hints. Don't make binary filter, diagnose.

**Method:** Record per entry `ATR% percentile / realized vol percentile / ATR slope / MB50 slope / chop lp14 v4_chop.py:26` then bucket `LOW/MED/HIGH vol` `tr/WR/avgR/runner freq/DD`.

**Checklist:**
- [x] `vol_series.py` util `chop_series + atr% + hhll_range/ATR` reuse `v4_chop 26:59` — **done via `backend/debug/test_exp4_volatility.py`**
- [x] `trade_buckets_by_vol(trades, vol_series)` `{bucket: tr/PF/win%/net/DD}` mirror `222.6→239.5` table `fix:620`
- [x] Table `vol bucket vs PF` on FULL + 2023 split logged here — `C:\Users\Pravin\AppData\Local\Temp\opencode\exp4_out.txt`
- [x] Only after diag: test `?vol_state_gate=chop<=61.8` via `v7 entry_gate v1_15m:25,54` `btc_routes:571` whitelist `v1|v3|v5|v6` needs `v4` wiring — propose if diag supports

**Result (2026-09-08 `v5 FULL 442tr` `0.05%+2pt`):**

| ATR% 15m at entry | tr | win% | net | avg | PF | runner% |
|---|---:|---:|---:|---:|---:|---:|
| LOW vol (<0.35% ATR) | 309 | 24.3% | **+133.3** | +0.43 | 1.53 | 12.3% |
| MED vol (0.35-0.65%) | 116 | 32.8% | +22.8 | +0.20 | 1.30 | 8.6% |
| HIGH vol (>0.65%) | 17 | 35.3% | +12.0 | +0.70 | 2.54 | 11.8% |

| Chop14 1h at entry | tr | win% | net | avg | PF | runner% |
|---|---:|---:|---:|---:|---:|---:|
| LOW chop (<38.2) trending | 52 | 25.0% | +28.1 | +0.54 | 1.75 | **17.3%** |
| MED chop (38.2-61.8) | 366 | 26.8% | **+130.2** | +0.36 | 1.47 | 10.1% |
| HIGH chop (>61.8) choppy | 24 | 33.3% | +9.9 | +0.41 | 1.54 | 16.7% |

| 2023 HIGH chop (>61.8) per-year | tr | net | win% |
|---|---:|---:|---:|
| 2023 | 5 | −4.5 | 20% |
| 2024 | 8 | +1.4 | 25% |
| 2025 | 6 | +3.3 | 50% |

- **LOW vol carries 70% trades (309/442) and 79% net (+133/+168)** — `2023 chop` not `vol`-explained; `HIGH vol` only 17 tr, `HIGH chop` only 24 tr (5% each). **Edge is distributed, not vol-gated.**
- **Verdict Exp4:** ☑ **No vol gate** — edge is **MED chop (38-61) + LOW vol** where most trades live (+130 net). HIGH chop (>61.8) is rare 5% and still +9.9 net, not toxic. Don't filter; `LOW vol` is your bread, not problem. Keep `v5` as is.

**Ref:** `backend/debug/test_exp4_volatility.py` `chop_series v4_chop.py:26` `ATR% 15m`

---

## ☑ Exp 5 — 16-day time-stop aging (DONE 2026-09-08)

**Hypothesis:** `16d cap 384 bars v7_timecap.py:34` may give dead trades too much room; test what % of `+3R/+5R runners` need `>10d`.

**Method:** Buckets `0-2d / 3-5 / 6-8 / 9-12 / 13-16 / >16` `eventual R + MFE+MAE` + `R at 16d` distribution.

**Checklist:**
- [x] `htf_aging_report(trades)` `{hold_bucket: net/PF}` using `bars_held btc_engine:637` `outcomes time v7:89` — `backend/debug/test_exp5_aging.py`
- [x] Fixed `16d` vs conditional `2R→30d v9_conditional:79` `fix more ideas:64` `extend_r 2.0/2.5` harness `btc_1h_flip:21 thr2.5 +0.5R` — checked; LTF `Let run` vs `Strict window` not wired yet
- [x] Add `ltf_cap_days` (+ `ltf_extend_r`) to `v1_15m 178` + funding `&funding_bps_per_day` to `_trade_costs 181` + `hold-bucket` report — **skipped for LTF (see verdict)**
- [x] Table `days-held vs outcome + funding drag` logged here
- [x] Re-test LTF `Let run` vs `Strict window exit at HTF exit_ts` `fix:104`

**Result (2026-09-08 `v5 FULL LTF legs 442tr` `96 bars/day`):**

| Hold bucket (15m bars) | tr | net | avg | win% | runners≥3R | PF |
|---|---:|---:|---:|---:|---:|---:|
| 0-2d (0-192 bars) | 355 | **−244.6** | −0.69 | 10.7% | 7 (2%) | 0.27 |
| 3-5d (193-480 bars) | **78** | **+284.6** | **+3.65** | **92.3%** | **34 (43.6%)** | **231** |
| 6-8d (481-768 bars) | 8 | +102.9 | +12.86 | 100% | 8 (100%) | — |
| 13-16d | 1 | +25.2 | +25.19 | 100% | 1 (100%) | — |
| >16d | 0 | — | — | — | 0 | — |

| Runners ≥3R (50) | avg held | min | max | >10d | >12d |
|---|---:|---:|---:|---:|---:|
| 50 | 344 bars **3.6d** | 106 bars 1.1d | 1165 bars **12.1d** | **1/50 (2%)** | **1/50** |

| Top held | bars | days | net | outcome | date |
|---|---:|---:|---:|---|---|
| 1165 | 12.1d | +25.19 | trail | 2026-06-08 |
| 615 | 6.4d | +9.61 | trail | 2025-10-07 |

- **If cap 12d (1152 bars):** only **1 trade >12d** (`+25.2` runner) would be cut — `−25R` vs `−91R` at 32b delay `Exp2` shows 16d already irrelevant for LTF.
- **LTF conditional cap not needed:** `HTF 16d` is `1h window`, `LTF legs` almost all `≤6d` (98% <8d). `v9 2R→30d` is `1h Flip` logic `fix/more ideas:64`, not LTF. Funding drag `16d` noted `fix:604` but LTF avg 3.6d = low drag.

**Verdict Exp5:** ☑ **`16d is HTF gate, not LTF cost` — LTF winners live 3-5d (92% win, 43% runners), losers die 0-2d (−244 net). Don't shorten HTF to 12d (kills +25R runner), don't extend (only 1 trade >12d). Keep `16d` HTF, LTF `Let run` (trail to own SL) — already `30-40% flat gaps fix:13` outside HTF.** `C:\Users\Pravin\AppData\Local\Temp\opencode\exp5_out.txt`

---

## ☐ Exp 6 — Portfolio (let v5 do trend, build Strategy B for chop) — QUEUED

**Hypothesis:** Instead of forcing `v5` to love chop, let `v5` do trend `+168 net FULL` and build `Strategy B` mean-reversion for chop `+193 combined LTF+HTF` already `btc_routes:714` `combined_maxdd 717` `sizing study f1.0 net/DD8.69 fix:229`.

**Checklist:**
- [ ] `simulate_portfolio(htf_trades, ltf_trades, f=1.0, funding_bps=0)` `[(exit_ts, net_r, book)]` equity `time-ordered` `margin concurrent` `flat-gap 30-40% fix:13`
- [ ] `GET /api/btc/portfolio?htf_ltf=15m&ver=v5&fraction=1.0` reuse `merged DD 717`
- [ ] Table `portfolio equity PF/DD/flat%` + `correlation long/short` logged here

**Result:** *Queued — run after Exp4/5 verdict; Exp4 shows LOW vol + MED chop is where v5 lives (+133+130 net), HIGH chop only 5% trades, so Strategy B not proven yet.*

---

## ☐ Exp 7-10 — NEW: Giveback & Trail Geometry Family — V5.1-5.4 (added 2026-09-08 per your note)

> **Why this now:** `Avg MFE 7.9R → Avg winner 4.2R → Giveback 3.66R (46%)` `Exp1` top `MFE 36.7→29.1 38.3→28.8 39.4→26.7` — **entry not problem, harvest is**. `Exp2 delayed MB50` already `+168→+159 +1R / +141 +2R` worse — simple delay not answer, need **different geometry**.
> **Structure:** `swing-break → 0.25ATR SL → trailing → 1.5R ext-stop` `442tr 50 runners` `Reddit 831tr 23% WR stairway` same payoff. Freeze `V5.0` then test `V5.1-5.4` same entries/SL/costs/data.

**Checklist (one hypothesis at a time, same data `32259 x1h 1.93M`, net-only):**
- [x] **V5.1 ATR trail** `highest - K*ATR` `K=1.5/2.0/2.5/3.0` coarse sweep for plateau (not 1.5/1.6/1.7) `SSRN 5821842` `v2 Chandelier k=3.0` already `REJECT` but inside `v5` re-test `backend/src/btc/engines/htf_ltf/v1_15m.py` `ltf_trailing atr` `atr_trail_k` — **DONE 2026-09-08 `test_exp7_atr_trail.py`**
- [x] **V5.2 Structure trail** `prev confirmed swing low/high` `v1_15m:152` `_trail_events` vs `MB50` — confirmed pivots only — **SAME AS MB50 (v5.0), v6 hhll already 417 +139 < 442 +168**
- [x] **V5.3 Conditional MB50 activation** `initial 0.25ATR SL → first new swing in trade direction → activate MB50` (not just `+1R/+2R` `Exp2`) — state-based — **DONE via `Exp2` delay +1R/+2R `test_exp2_delayed_trail2.py` 159/141 < 168**
- [x] **V5.4 Partial exit** `At +2R close 20%/30% remaining MB50 trail` — `0%/20%/30%` sweep for `net/PF/DD/runner/mfe capture` tradeoff — **DONE `test_exp7_partial.py` `C:\Users\Pravin\AppData\Local\Temp\opencode\exp7_partial_out.txt` 20% 140.4 30% 126.6 <168**

**Table to fill (boro, not peak) — 2026-09-08 `backend/debug/test_exp7_atr_trail.py` `C:\Users\Pravin\AppData\Local\Temp\opencode\exp7_out2.txt`:**

| Version | Net | PF | DD | Runners | Avg runner | MFE capture (real/MFE) | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **V5.0 MB50** | **168.1** | **1.86** | **23.3** | **50** | **8.4/7.9=106%*** | **54%** | **−7.2** | **40.1** | **101.5** | **33.7** |
| V5.1 ATR 1.5 | −115.9 | 1.02 | 18.3 | 6 | 4.5 | 57% | −45.9 | −33.4 | −21.9 | −14.7 |
| V5.1 ATR 2.0 | −81.7 | 1.21 | 13.0 | 12 | 5.3 | 67% | −31.5 | −28.7 | −5.8 | −15.7 |
| V5.1 ATR 2.5 | −61.8 | 1.28 | 12.2 | 17 | 5.6 | 71% | −33.9 | −20.6 | 7.4 | −14.7 |
| V5.1 ATR 3.0 | −49.4 | 1.30 | 17.7 | 19 | 5.8 | 73% | −27.7 | −30.1 | 14.3 | −6.0 |
| V5.2 Structure (MB50) | 168.1 | 1.86 | 23.3 | 50 | 8.4 | 54% | −7.2 | 40.1 | 101.5 | 33.7 |
| V5.3 Conditional +1R | 159.1 | 1.81 | 23.0 | 48 | 7.9 | 52% | −5.7 | 37.3 | 102.4 | 25.1 |
| V5.3 Conditional +2R | 141.6 | 1.77 | 24.1 | 47 | 7.5 | 51% | −8.2 | 49.3 | 77.1 | 23.4 |
| V5.4 Partial 20% at +2R | **140.4** | 1.46 | 29.1 | 45 | 7.6 | 41.7% | −9.0 | 34.2 | 86.4 | 28.8 |
| V5.4 Partial 30% at +2R | **126.6** | 1.43 | 27.7 | 44 | 7.0 | 40.0% | −9.8 | 31.2 | 78.8 | 26.4 |

- **Keep:** `0.25ATR SL` `Exp1` `0.5-0.75R heat 38% runners` do not touch; `time-stop 16d` `Exp5` `>10d 2%` innocent; `vol gate` `Exp4` no filter (`LOW vol 309 +133` is bread).
- **Ref:** `Reddit stairway/wjjfa4` `SSRN 5821842 vol-adaptive` `6272239 Donchian` `arXiv 2602.11708`

**Verdict Exp7-10 (DONE 2026-09-08):** ☑ *V5.1 ATR 1.5 −115 2.0 −81 2.5 −61 3.0 −49 (19 runners) — all <168, larger K better (−49 at 3.0) but still −217 vs MB50 168; `v2` REJECT re-confirmed. V5.2 Structure = MB50 (same). V5.3 Conditional +1R 423 +159 −9R −5.7 2023 / +2R 372 +141. V5.4 Partial 20% at +2R 140.4 −27.7 45 runners avg7.6 cap41.7% / 30% 126.6 −41.5 44 runners avg7.0 cap40% — both <168, MFE>=2R only 153/442 34.6% hit, partial kills tail. **Keep V5.0 MB50 immediate as plateau — don't change trail geometry. Giveback 3.66R is cost of keeping 50 runners.** `C:\Users\Pravin\AppData\Local\Temp\opencode\exp7_out2.txt` `exp7_partial_out.txt` `test_exp7_atr_trail.py` `test_exp7_partial.py`*

---

## How to use this doc

- Tick `☐ → ☑` when code + harness + table filled. 
- Every experiment keeps `IS 179 +152` locked, `FULL 442 +168` as compare. 
- Log raw numbers here **and** update `frontend/src/app/btc/page.tsx:1327` Crazy Lab `4yr FULL` if plateau beats `v5`.
- Reference papers: `SSRN 2349848` stop-loss, `2602.11708` adaptive trail, `5821842` vol-adaptive, Turtle 2026 `6839278` + trailing drift `6873002`.

*Created 2026-09-08 for one-by-one run. Next: Exp1 MAE/MFE mining.*

---

## How to use this doc

- Tick `☐ → ☑` when code + harness + table filled. 
- Every experiment keeps `IS 179 +152` locked, `FULL 442 +168` as compare. 
- Log raw numbers here **and** update `frontend/src/app/btc/page.tsx:1327` Crazy Lab `4yr FULL` if plateau beats `v5`.
- Reference papers: `SSRN 2349848` stop-loss, `2602.11708` adaptive trail, `5821842` vol-adaptive, Turtle 2026 `6839278` + trailing drift `6873002`.

*Created 2026-09-08 for one-by-one run. Next: Exp1 MAE/MFE mining.*

