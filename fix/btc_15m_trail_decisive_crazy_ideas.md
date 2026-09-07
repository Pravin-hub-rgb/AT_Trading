# BTC 15m Decisive Trail — Crazy Ideas Lab

> **Focus:** `backend/src/btc/btc_engine.py` `decisive50` (`15m` `decisive` `sl swing` `trailing swing` `BE0` `minBars 50`) honest FULL window `Jan-25→Sep-26` `58780 x15m` + `1m-precise fills` + `stream+churn+touchable` + `one swing one trade` + `0.05%/side+2pt`.
> **Honest reality after fixes:** `fix/btc_ideas.md:475` `847tr +19 net` → `backend/debug/_rerun_master_out.json:1` `446tr +5.3 net` (one-swing-one-trade) → latest `one-swing-one-trade + touchable` `446tr +5.3` still the flagship 15m. `1h Flip Fixed 3R` `101tr +51.2` dominates.
> **Goal:** Net R max, but also log `win% >30 / PF >1.5 / maxDD <8R` `btc_engine.py:537` `trade_stats` for each version. Test `15m vs 1h/4h HTF`, `long/short both vs long-only bias`, `taker 0.05%+2pt vs maker 0.02%`.
> **Rule:** Each version gets its OWN engine file `backend/src/btc/engines/v*.py` — `v1` never disturbed. Log here, show in chart via `?version=v1..vN` on `/api/btc/backtest` & `/api/btc/summary`.

---

## Versioning

| Ver | Engine file | Idea | Base on | Chart `?version=` |
|-----|-------------|------|---------|-------------------|
| **v1** | `backend/src/btc/btc_engine.py` (original) + `btc_swing.py` | **Honest baseline** — one swing one trade + touchable SL (max high since prev_end) + 1m fills + stream+churn | `fix/btc_ideas.md:473` | `v1` (default, never touched) |
| v2 | `backend/src/btc/engines/v2_chandelier.py` | Chandelier ATR trail `k=3.0` (replace pivot ratchet) | `btc_engine.py:179` | `v2` |
| v3 | `backend/src/btc/engines/v3_htf_trail.py` | HTF 1h swing pivots for 15m trail | `btc_swing.py:156` | `v3` |
| v4 | `backend/src/btc/engines/v4_partial.py` | 50/50 Fixed 3R + Trail split | `btc_ideas.md:162` | `v4` |
| v5 | `backend/src/btc/engines/v5_minbars_be1.py` | `minBars 50 BE1` vs BE0 | `btc_swing.py:50` | `v5` |
| v6 | `backend/src/btc/engines/v6_adx.py` | ADX>25 gate | `fix/btc_sweep.py:52` | `v6` |

Add `v7...` as we brain-storm.

---

## How Each Version Works (UI me bhi dikhega)

**v1 Honest Baseline** `backend/src/btc/btc_engine.py:33` — Stream `B2/FLIP` per swing first only `btc_engine.py:93` one swing one trade + touchable SL `max high since prev_end` `btc_engine.py:128` + `1m fills` `btc_engine.py:195` conservative `SL before target` `gap fill`. Entry `break close`, `SL swing start` `risk = entry-sl`, `trailing swing pivots` `btc_engine.py:179` `sl_cur<cand<lo`. `0.05%+2pt` `btc_routes.py:113`. Chart: green win / red loss boxes `PositionPrimitive.ts:1` + L/S badge + white entry dotted line.

**v2 Chandelier** `v2_chandelier.py:1` — Same entry/SL as v1, `trailing = chandelier k*ATR14` `highestHigh - kATR` for long. Replaces `swing pivot` ratchet. Vol-adaptive, wide in bear.

**v3 HTF 1h Trail** `v3_htf_trail.py:1` — `15m` entries, `1h` swings `btc_swing.py:156` `compute_btc_flow 1h` pivots ratchet. Fewer pivots `14715 vs 58780` → slower.

**v4 Partial 50/50** `v4_partial.py:1` — Half qty `fixed 3R` target `btc_engine.py:233` + half `swing trail`. Fee per half. Nets blended `split*Rf + (1-split)*Rt`.

**v5 BE1** `v5_be1.py:1` — Same as v1 but `breakeven 1R` `btc_engine.py:239` `sl=entry` after `+1R`. Converts `-1R` to `0R`.

**v6 ADX>25** `v6_adx.py:1` — `ADX14` `Wilder` `>25` gate at entry bar `v6_adx.py:50`, else skip. Filters chop, allows early flip only in trend.

UI me `Ver` dropdown ke niche `Version Info` card me yahi summary + `trades/win%/PF/maxDD` live dikhega `GET /api/btc/summary?version=v6`.

---

## v1 — Honest Baseline (LOCKED — never edit)

**Engine:** `backend/src/btc/btc_engine.py:33` `_collect_signals` stream + `btc_engine.py:128` opposite-dir touchable `max high since prev_end` + `btc_engine.py:93` one swing one trade + `btc_engine.py:195` 1m fills. `backend/src/btc/btc_swing.py:50` `minBars 50` `timeCap 00:00`.

**Trades FULL window:**
- `15m decisive50` `446tr 21.7% win base +91.0 costs 85.6 net +5.35 PF ~1.06 maxDD ?` `_rerun_master_out.json:1` (pre one-swing: `847tr +19 net` `fix/btc_ideas.md:475`)
- `1h Flip Fixed 3R` `101tr 41.6% +62.1 → +51.2` `frontend/src/lib/btcMaster.ts:1`
- `15m flip50` `390tr 22.1% +90.5 → +8.8` beats decisive on same TF.

**Why 200R → 5R:** `200R` was `final` selection + `signal` fills + zero costs + no churn + no one-swing limit (`fix/btc_ideas.md:35` `+392R 1720tr`). Each honesty layer shaved: `1m fills -33R` `fix/btc_ideas.md:368`, `pre-start churn 769→847` `fix/btc_ideas.md:444`, `one swing one trade 847→446` `btc_engine.py:93`, `touchable SL` `11:30 95281→95465` (`14 Jan`).

**Lacking:** `trail -0.1..-0.5R` `781` `fix/btc_ideas.md:210`, win `21.7%` needs `~3.6R` avg win vs `~1.2R` actual, `cost 94%` of base, `top-25 96%` lottery `fix/btc_ideas.md:224`.

---

## v2 — Chandelier ATR Trail (k=3.0)

**Engine:** `v2_chandelier.py` — `sl_cur = max(sl_cur, highestHigh - k*ATR14)` for long, `lowestLow + kATR` for short. `k=3.0` ATR14 on 15m. Keeps pivot logic for entry SL, replaces `_trail_events` ratchet.

**Hypothesis:** ATR-wide in bear/high-vol prevents `-0.3R` whipsaw, tight in low-vol locks. Should beat pivot `0.2-0.4R` immediate ratchet `fix/btc_ideas.md:210`.

**Sweep:** `k=2.5/3.0/3.5` `net/win%/PF/maxDD` on 15m decisive50 FULL, taker vs maker, long/short both vs long-only (filter shorts when `close < EMA200 1h`?), TF 15m vs trail on 1h ATR.

**Result log:**
| k | TF | Trades | Win% | Base | Net 0.05% | Net 0.02% | PF | maxDD | Long Net | Short Net | Notes |
|---|----|--------|------|------|-----------|-----------|-----|-------|----------|-----------|-------|
| 3.0 | 15m | ? | ? | ? | ? | ? | ? | ? | ? | ? | _run after engine created |
---

## v3 — HTF 1h Pivot Trail

**Engine:** `v3_htf_trail.py` — `events` from `1h swings` (`btc_swing.py:156` `compute_btc_flow` 1h), not 15m. 15m entries, 1h pivots ratchet.

**Hypothesis:** Fewer pivots (`1h 14715 rows` vs `15m 58780`) → slower ratchet, fewer `-0.3R` exits, `B1 HTF` already in `bias_timeline` `btc_engine.py:340`.

**Sweep:** `HTF 1h vs 4h` `net` + `maxDD`.

---

## v4 — Partial 50/50

**Engine:** `v4_partial.py` — `0.5 qty` fixed `3R` `target` + `0.5 qty` swing trail. Fee per half.

**Hypothesis:** Fixed half pays costs, trail half captures tail — best of `fix/btc_ideas.md:162` philosophies. Sniper `D4 +0.478R/tr` `161tr` + `B2 +392R` `1720tr`.

---

## v5 — minBars BE1

**Engine:** `v5_minbars_be1.py` — same as v1 but `breakeven 1R` (`decisive50 BE1` `492tr +46.6 net` `backend/debug/_btc_full_sweep.py:1` vs BE0 `446tr +5.3`).

**Hypothesis:** `BE1` converts `-1R` to `0R` (`fix/btc_ideas.md:90` `+378 vs +298` with BE) — may beat churn.

---

## v6 — ADX Gate

**Engine:** `v6_adx.py` — `ADX14 >25` on 15m allows trail, else skip. Fixes EMA gate `-39R` `fix/btc_sweep_out.txt:64` which blocked reversals.

---

## Sweep Matrix (run for each v)

**For each `v` test:**
- `TF` `15m` (decisive50) `1h` `4h` `bestTf`
- `Bias` `both` vs `long-only` (filter shorts when `EMA200 1h` bear? `fix/btc_ideas.md:232` bear -30%)
- `Cost` `0.05%+2pt taker` `btc_routes.py:113` vs `0.02% maker`
- `Metrics` `Net R` `Win%` `PF` `maxDD` `avgR` `trades` `long/short split`

**Run:** `python backend/debug/sweep_crazy_versions.py --version v2 --tf 15m --cost taker --bias both` → logs below + `backend/debug/sweep_crazy_v2.json`.

**Chart:** `GET /api/btc/backtest?tf=15m&version=v2&min_bars=50&fee_pct=0.05&slippage_pts=2` `frontend/src/app/btc/page.tsx:1` `Version` dropdown `v1..v6` → `StockChart` `trades` + `Strategy Summary` `GET /api/btc/summary?version=v2`.

---

## Logs

### 2026-09-06 — v1 locked (never disturb)

- v1 engine `backend/src/btc/btc_engine.py:33` LOCKED — one swing one trade + touchable SL (max high since prev_end) + 1m fills + stream+churn. `fix/btc_ideas.md:475` `847tr +19 net` → `446tr +5.3 net` after one-swing-one-trade. `1h +51.2 net` dominates.
- Created doc, `backend/src/btc/engines/` with `v2..v6` isolated, `backend/src/btc/btc_routes.py:148` `?version=v1..v6` + `frontend/src/lib/btcApi.ts:1` + `frontend/src/app/btc/page.tsx:1` Version dropdown (v1 default, never disturbs v1). Chart `GET /api/btc/backtest?version=v2` etc.
- v1 untouched — verified via `quick_sweep_v.py` `446tr 21.7% +91.0→+5.3 net PF1.3 maxDD40.3` taker `0.05%+2pt` vs `446tr +55.6 net` maker `0.02%`.

### 2026-09-06 — Sweep v1..v6 on 15m Decisive50 (honest FULL window, one-swing-one-trade, touchable, 1m fills)

**Quick sweep `quick_sweep_v.py` — 15m `decisive50` `minBars50` `trailing` per version, `bias off` `both` directions, `TF 15m`**

| Ver | Engine | Trades | Win% | BaseR | Net 0.05%+2pt | Net 0.02% maker | PF | maxDD | Notes |
|-----|--------|--------|------|-------|--------------|-----------------|-----|-------|-------|
| **v1** | Honest baseline (pivot) | 446 | 22.0% | +91.0 | **+5.4** | **+55.6** | 1.30 | 40.3 | Locked, 200R→5R honest |
| v2 | Chandelier k=3.0 ATR | 1302 | 35.3% | -12.7 | **-269.4** | -118.9 | 0.90 | 20.3 | Too many trades, chandelier too tight on BTC 5 ATR legs — needs tuning k=4-5 |
| v3 | HTF 1h pivots | 236 | 15.7% | -34.1 | **-74.0** | -50.6 | 0.86 | 53.5 | Too slow, gives back |
| v4 | Partial 50/50 | 350 | 25.4% | -14.0 | **-71.6** | -37.8 | 0.94 | 33.2 | Blend not helping yet — fixed half still hit -1R |
| v5 | BE1 (vs v1 BE0) | 515 | 17.5% | +84.8 | **-10.2** | **+45.5** | 1.35 | 30.4 | BE1 helps base but maker only survives — taker still -10 |
| **v6** | **ADX>25 gate** | **337** | **23.4%** | **+159.4** | **+90.5** | **+130.9** | **1.68** | **23.9** | **BEST — ADX filters chop, win% + PF jump, net 90 vs 5** |

**Takeaway:** On honest `15m decisive50`, only `v6 ADX` beats `v1` at taker fees (`+90.5` vs `+5.4`, `PF 1.68` vs `1.30`, `win 23.4%` vs `22.0%`). `v5 BE1` only survives at maker. `v2/v3/v4` need tuning — logged but not promoted. `v1` never disturbed — each `v` has its own file `backend/src/btc/engines/v*.py`.

**HTF + Long/Short split `quick_sweep_htf.py` honest `decisive50` `minBars50` `swing BE0`:**

| Ver | TF | Tr | Win% | Base | Net taker 0.05%+2pt | PF | maxDD | Long Net | Short Net | Notes |
|-----|----|----|------|------|-------------------|----|-------|----------|-----------|-------|
| v1 | 15m | 446 | 21.7% | +91.0 | **+5.4** | 1.30 | 40.3 | -16.5 | +21.9 | 15m both survive, shorts carry |
| v1 | 1h | 181 | 26.0% | -10.9 | -29.0 | 0.92 | 28.2 | -17.0 | -12.0 | 1h decisive trail fails — too slow |
| v1 | 4h | 42 | 16.7% | -21.0 | -23.5 | 0.35 | 25.2 | -13.3 | -10.3 | 4h too few trades |
| **v6** | **15m** | **337** | **23.1%** | **+159.4** | **+90.5** | **1.68** | 23.9 | +27.3 | +63.2 | **Best — ADX filters chop both sides** |
| v6 | 1h | 135 | 28.9% | -16.5 | -30.1 | 0.82 | 23.2 | -24.9 | -5.2 | ADX on 1h also fails |
| v6 | 4h | 30 | 20.0% | -9.5 | -11.6 | 0.56 | 14.4 | -5.9 | -5.6 | - |

**Bias long-only test:** `15m v1` long-only net `-16.5` vs both `+5.4` — shorts needed in bear `fix/btc_ideas.md:232` -30%. `v6` long `+27` short `+63` both positive but shorts dominate — long-only would cut `+63` away.

**Chart:** Select `Ver` dropdown on `http://localhost:3002/btc` (v1 default) → trades/bars + Strategy Summary update via `?version=v6` etc. Each version's trades are isolated. `Version Info` card below Master shows how each version works.

**Next sweeps logged:** `k=2.5/3.5` for v2, `ADX 20/30` for v6, `HTF 4h` for v3 already -74 net — HTF shift not helping 15m decisive.

**Plan sweeps done `sweep_E1_minBars.py:1` `sweep_A1_chandelier.py:1` honest `0.05%+2pt`:**

**E1 minBars 15m decisive BE0** `446tr +5.3` is NOT best — `mb40 BE0 515tr +24.0 net PF1.35 maxDD50.6` best, `mb50 +5.4`, `mb30 -78.1`, `mb20 -149.7`, `mb60 -129.3`, `mb70 -62.3` `sweep_E1_minBars.py:1`. `BE1` all negative `mb50 -10.2` best among BE1. So `E1` winner `mb40 +24` beats `mb50 +5`.

**A1 Chandelier k 2.0-5.0 `mb50`** all negative `k2.0 -252 PF1.05` `k3.0 -269 PF0.90` `k5.0 -262` `sweep_A1_chandelier.py:1` — ATR trail too tight for BTC 5 ATR legs `fix/btc_ideas.md:59`.

**D1 Partial split 0.3/0.5/0.7 `15m decisive` manual blend `common 246` `sweep_D1_partial.py:1`:** `split0.3 -10.6 avg -0.043`, `split0.5 -3.6 avg -0.015`, `split0.7 +3.4 avg 0.014` — vs `v4 350tr -71` `v1 +5.4` `v6 +90.5`, blend not beats ADX, needs proper `busy_until` handling.

**E3 ADX 15m `decisive mb50` `sweep_E3_adx.py:1`:** `ADX20 396tr +56.5 PF1.49`, `ADX25 337tr +90.5 PF1.68 BEST`, `ADX30 282tr +65.4 PF1.64`, `ADX35 213tr +83.9 PF1.84` — `25` best net, `35` best PF. `1h flip mb20` `ADX20 +14.7` `ADX25 -4.8` `ADX30 -1.4` — ADX hurts `1h` flip.

**E2 ATR percentile `sweep_E2_E5_E8_E9.py:1` `15m decisive` `window 20d`:** `>20 282tr -19.3`, `>30 239tr -13.4`, `>50 151tr -7.7` — all negative, filter hurts.

**E5 Session 4H UTC `sweep_E2_E5_E8_E9.py:1` `15m decisive` `16-20 UTC 100tr +131.3 avg1.313 win25/100` `20-24 UTC 72tr +23.0`, `00-04 -16.7`, `04-08 -24.2`, `08-12 -10.9`, `12-16 -4.7` — `16-20 UTC (21:30-01:30 IST)` `EU+US overlap` `fix/btc_sweep_out.txt:64` `19-01 -57` old vs now `+131` — session filter huge.

**E8 Churn `165/1304 12.7%` swings `>=3` pre-start `sweep_E2_E5_E8_E9.py:1`, `E9 ratchet minstep` still `sl_cur<cand<lo` strict `btc_engine.py:179` `0.2R` would need engine change.

**Next:** `E9` `0.2R` + `D1` proper `busy_until` + `E5` `16-20 UTC` as new `v7` candidate — `v1` lock `446tr +5.3` still.

**Garbard check:** `v1 446tr +5.3` unchanged — verified after each sweep, each `v` isolated `backend/src/btc/engines/v*.py`.

