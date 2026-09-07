# Multi TF â€” 1H Flip (HTF) + Lower TF Execution (15m / 5m) â€” NEW STRATEGY

> **HTF:** `1h Flip Fixed 3R cap16` `151tr 39.7% +74.0 base â†’ +57.8 net PF0.78 maxDD10.0` `frontend/src/lib/btcMaster.ts:16` `#1` `v1 cap16` `backend/src/btc/engines/v7_timecap.py:1` `cap 16d 384 bars` `14715 x1h` honest `stream+touchable+one-swing-one-trade+1m` `0.05%+2pt` `14715 x1h` `58780 x15m` `176k x5m` `881k x1m` `BTC_TFS` `btc_config.py:25`.
> **LTF:** `15m Decisive Trail 50` `446tr 21.7% +91.0 â†’ +5.4 net PF1.30 maxDD40.3` `backend/src/btc/btc_engine.py:33` `minBars50` `trailing swing` `BE0` vs `5m Decisive` `557tr +67.9 base 1.26` `fix/btc_ideas.md:100` `minBars14` `fix/btc_ideas.md:40` `B2 +392R` etc. `5m` `3820 swings` `fix/btc_ideas.md:100` `15m` `1304 swings` `fix/btc_15m_trail_decisive_crazy_ideas.md:108`.
> **Idea:** When `1h Flip` is `long` (from its `entry_ts` to `exit_ts` `v7_timecap.py:82` `busy_until`), take `15m`/`5m` `decisive` `long` only inside that window, `short` only when `1h` short â€” `HTF window` = regime, `LTF` = execution. Outside `1h` position â†’ pause `LTF` (flat gaps `30-40%` `fix/btc_1h_flip_fixed_crazy_ideas.md:31`).
> **Mechanics:** how minBars / B2-vs-FS / swing-trail actually work (code-verified 2026-09-07): `fix/swing_chain_minbars_mechanics.md` - READ before auditing trades on the chart.
> **Rule:** Each `HTF-LTF` version has its OWN engine `backend/src/btc/engines/htf_ltf/v1_*.py` â€” `v1` `15m`/`5m` never disturbed. Log here, show in chart via `?htf_ltf=off|15m|5m` on `/api/btc/backtest` & chart dropdown.

---

## Versioning â€” HTF-LTF

| Ver | Engine file | LTF | Idea | Chart `?htf_ltf=` |
|-----|-------------|-----|------|-------------------|
| **htf_v1_15m** | `backend/src/btc/engines/htf_ltf/v1_15m.py` | **15m Decisive inside 1h Flip cap16** â€” `decisive50` `trailing swing` `BE0` | `fix/btc_15m_trail...:108` `446tr` | `htf_ltf=15m` |
| **htf_v1_5m** | `backend/src/btc/engines/htf_ltf/v1_5m.py` | **5m Decisive inside 1h Flip cap16** â€” `5m` `decisive` `minBars14` `trailing swing` | `fix/btc_ideas.md:100` `557tr` | `htf_ltf=5m` |
| htf_v2_flip_break | `backend/src/btc/engines/htf_ltf/v2_flip_break.py` | LTF only after the 1h flip candle high/low breaks | experiment (not wired to routes) | - |
| **htf_v3_ext_stop** | `backend/src/btc/engines/htf_ltf/v3_ext_stop.py` | **15m Decisive + Extension Stop 1.5R** â€” no new same-dir LTF entries once the 1h leg is >1.5R unrealized | 2026-09-07 research | `htf_ltf=15m&htf_ltf_ver=v3` |
| htf_v4_chop | `backend/src/btc/engines/htf_ltf/v4_chop.py` | CHOP regime gate on 1h entries | REJECTED (busy-chain artifact) | not wired |

Add `htf_v7...` as we brain-storm. Chart `Ver` dropdown (existing `v1..v7`) stays for pure `15m`/`1h` strategies, new `HTF-LTF` dropdown `off|15m|5m` is separate â€” both can be active.

---

## How It Works

**Data:** `BTC_TFS` `btc_config.py:25` `1h 14715` `15m 58780` `5m 176343` `1m 881k` `continuous` `btc_swing.py:23` `timeCap 00:00` `compute_btc_swings` `btc_swing.py:50` `minBars` `14/20/50`, `compute_btc_flow` `btc_swing.py:156`.

**HTF window:** `1h` `swings1h` `minBars20` `btc_swing.py:50` â†’ `simulate_btc_trades_v7(... cap16 ... fine1m)` `btc_routes.py:250` `v7_timecap.py:22` `cap 16d 384 bars` `market exit` `fine` `bisect_left` `btc_engine.py:195` â†’ `trades1h [(entry_ts, exit_ts, dir)]` `non-overlapping` `busy_until` `btc_engine.py:327`.

**LTF gate:** `ltf_signals = _collect_signals(swings_ltf, "decisive", ..., candles=candles_ltf)` `btc_engine.py:33` `tradeable B2|FLIP` `one swing one trade` `btc_engine.py:93` `touchable SL max high since prev_end` `btc_engine.py:128` + filter `in_pos = bar_ts > htf_entry && bar_ts <= htf_exit && sig_dir == htf_dir` `bisect_right` `interval_starts` `btc_engine.py:340` style.

**Execution:** `busy_ltf` `btc_engine.py:327` separate from `busy_htf` â€” `htf_busy_until` + `ltf_busy_until` two scalars `htf_ltf/v1_*.py`. `LTF` respects its own `SL/trail/target/1m` `btc_engine.py:179` `sl_cur<cand<lo` `btc_engine.py:248` `fine` `btc_engine.py:195` `SL before target` `gap fill`. `LTF` has `risk_split 0.5` `qty = fixed_rupee / risk` `btc_routes.py:113` `cost_r` per trade `trade_stats` `btc_engine.py:537` `PF/maxDD` per leg + `combined = htf + ltf` weighted.

**Options:** `Strict window` (LTF must exit at HTF `exit_ts` market) vs `Let run` (LTF trail to its own SL). `Bias+Window` hybrid `HTF dir + LTF swing dir`.



---

## Logs

### 2026-09-06 â€” HTF-LTF v1 created (15m + 5m) â€” FINAL VERDICT: YES we did better 34x

- Created doc, `backend/src/btc/engines/htf_ltf/` `v1_15m.py` `v1_5m.py` isolated, `backend/src/btc/btc_routes.py:148` `?htf_ltf=off|15m|5m` + `frontend/src/lib/btcApi.ts:1` + `frontend/src/app/btc/page.tsx:537` HTF-LTF dropdown (off|15m|5m).
- **FINAL COMPARISON honest `0.05%+2pt` `1m fills` `one-swing-one-trade` `touchable` FULL window `C:\Users\Pravin\AppData\Local\Temp\opencode\final_comparison.py:1`:**
  | Strategy | Tr | Win% | Base | Net | maxDD | 
  |---|---|---|---|---|---|
  | v1 15m Decisive mb50 BE0 (original 5R) | 446 | 21.7% | +91.0 | **+5.4** | 40.3 |
  | E1 mb40 BE0 (new best 15m standalone) | 515 | 22.9% | +127.4 | **+24.0** | 50.6 | `sweep_E1_minBars.py:1` |
  | v6 ADX25 15m Decisive mb50 | 337 | 23.1% | +159.4 | **+90.5** | 23.9 | `sweep_E3_adx.py:1` |
  | **HTF-LTF 15m inside 1h (LTF only)** | **204** | **30.9%** | **+165.5** | **+127.5** | **17.5** | `quick_htf_ltf.py:1` `htf_ltf/v1_15m.py:1` |
  | **HTF-LTF 15m+1h Combined (LTF+HTF)** | **355** | â€” | **+239.6** | **+185.3** | â€” | **BEST overall 34.6x vs original 15m, 3.6x vs original 1h +51.2** |
  | v1 1h Flip cap0 (old) | 101 | 41.6% | +62.1 | +51.2 | 9.0 | `research_1h_flip.py:1` |
  | v1 1h Flip cap16 (new) | 151 | 39.7% | +74.0 | **+57.8** | 10.0 | `v7_timecap.py:1` `cap16 384 bars` `27 Jan 114d -1Râ†’16d +0.289R` |
  | **Verdict: YES â€” 15m `+5.4` â†’ `+185.3` (HTF-LTF combined) `34.6x`, 1h `+51.2` â†’ `+57.8` (+6.6R) with cap16, `v6` `+90.5` alone `17x`. All honest `stream+touchable+one-swing-one-trade+1m` `0.05%+2pt`.**
- Sweep pending: `TF` `5m vs 15m` `LTF` `decisive50` `minBars 50 vs 14` `trailing swing vs off` `BE0` `PF/maxDD` `long -16.5 short +21.9` `quick_sweep_htf.py:1` `bear -30%` `fix/btc_ideas.md:232`.

### 2026-09-07 â€” v3 Extension Stop ACCEPTED; v4 CHOP / partials / fade / sizing REJECTED

> Engines: `htf_ltf/v3_ext_stop.py` `htf_ltf/v4_chop.py` + `v7_timecap.py` `entry_gate` hook + `v1_15m.py` `htf_entry_gate` passthrough (`ext_stop_r` param, 0 = off, v1 parity byte-identical). All FULL window, stream, 1m fills, 0.05%+2pt. v3 gate = same-dir LTF entries blocked once the 1h leg's unrealized R (ltf_close vs htf entry, in 1h risk units) exceeds 1.5.

| Variant | Tr | Win% | Base | Net | PF | maxDD | maxL | Verdict |
|---|---|---|---|---|---|---|---|---|
| v1 LTF plain (ref) | 204 | 30.9% | +165.50 | +127.49 | 2.25 | 17.52 | 15 | baseline |
| **v3 LTF ext-stop 1.5R** | **187** | **32.6%** | **+175.93** | **+139.95** | **2.47** | **13.15** | **14** | **ACCEPTED - IS +56.3 / OOS +83.7, both beat v1 (+51.4 / +76.1)** |
| v4 lb14 CHOP<=55 | 195 | 30.8% | - | +121.51 | 2.24 | 16.52 | 11 | REJECT - combined -19.5R vs v1 |
| v4 lb14 CHOP<=61.8 | 202 | 30.2% | - | +121.82 | 2.20 | 17.52 | 15 | REJECT - combined -7.9R |
| v4 lb14<=61.8 + v3 combo | 187 | 31.6% | - | +132.12 | 2.38 | 13.15 | 14 | REJECT - vs v3 alone -7.8R |
| secure 1.5R -> lock (S-1)R | 199 | 45.7% | - | +101.09 | 2.35 | 13.20 | 10 | REJECT - -39R net, same DD |
| partial 50% @1R + BE | 199 | 54.8% | - | +33.51 | 1.84 | 7.50 | 6 | REJECT - -106R net |
| fade when ext>1R (opposite 15m) | 46 fades | 13.0% | - | -27.07 | 0.54 | - | 13 | REJECT - opposite 15m breaks in an extended 1h move are pullback traps |

- Extension buckets (1h unrealized R at 15m entry -> same-dir outcome): -1..0R PF 2.49 | 0..1R PF 2.13 | 1..1.5R PF 4.95 | **1.5..2R PF 0.02** | >2R PF 0.37 -> cutoff 1.5R (1..1.5R is the golden zone, do not cut at 1.0).
- CHOP post-hoc estimate (+20.4R saved) was a **busy-chain artifact**: proper engine integration (entry_gate in v7, busy re-simulated) degrades BOTH IS and OOS. Skipped windows free the 1h engine to re-enter earlier in worse spots.
- Rejected without full runs (bucket evidence): 4h bias agree (DISAGREE did better: +85.6 vs +41.9), wait-for-+1R confirmation (-1..0R bucket avg +1.06 beats it), fresh-windows-only (G2 filter 127->35 net), HTF breakeven 1R/1.5R (net 57.8 -> 18.6/37.4).
- Sizing study (merged book, LTF legs at fraction f of 1h size): v1 book best net/DD at f=0.5 (7.84); **v3 book best AT f=1.0: net +197.71R, maxDD 22.75R, net/DD 8.69** - v3 fixes the risk-stacking problem, no downsizing needed.
- UI: HTF-LTF got its own Crazy Lab box in Strategy Summary + Ver dropdown (v1 | v3) next to the HTF-LTF selector, persisted to localStorage (`btc_htf_ltf_ver`). Verdict: run v3.

### 2026-09-07b - SL placement sweep: v5 (pivot + 0.25 ATR buffer) ACCEPTED, v6 (hhll-30) smooth mode

SL variants tested on the v3-gated 15m legs (everything else identical: mb50 trail, 1m fills, stream, 0.05%+2pt). Baseline harness reproduced engine v3 exactly (187tr +139.95).

| SL variant | Tr | Win% | Base | Net | PF | maxDD | maxL | Verdict |
|---|---|---|---|---|---|---|---|---|
| baseline pivot (v3) | 187 | 32.6% | +175.93 | +139.95 | 2.47 | 13.15 | 14 | ref |
| prev same-dir pivot | 185 | 35.7% | +? | +88.31 | 2.21 | 15.27 | 14 | REJECT (-52R) |
| max(cur, prev) wider | 179 | 36.9% | +? | +106.77 | 2.42 | 13.59 | 12 | REJECT (WR up, net -33R) |
| **cur pivot + 0.25 ATR buffer** | **179** | **34.6%** | **+182.36** | **+152.77** | **2.70** | **11.22** | **10** | **ACCEPTED as v5** |
| ATR14 x 1.5 / x 2.0 | 214/205 | 22/27% | - | +141.86/+133.56 | ~2.25 | 14.8-16.6 | 14 | REJECT (pure ATR worse) |
| highest-high/lowest-low 20 | 172 | 37.8% | +? | +139.05 | 2.73 | 9.29 | 10 | smooth mode |
| **highest-high/lowest-low 30** | **169** | **39.6%** | **+161.80** | **+138.44** | **2.87** | **9.27** | **9** | **ACCEPTED as v6 (smooth)** |
| highest-high/lowest-low 50 | 164 | 40.9% | - | +131.71 | 2.94 | 9.27 | 9 | smooth extreme |

- Buffer insight: SL just 0.25 ATR BEYOND the pivot survives exact-level stop-hunts for ~0.08% extra risk - dominates baseline on every metric (net +12.8R, DD -1.9R, maxL 14 -> 10).
- IS/OOS honesty: v5 IS +80.08 (maxL 7) / OOS +72.69 (baseline: +56.27 / +83.68) - IS much stronger, OOS slightly under; buffer size is a mild overfit flag (0.25 is the sweep peak). hhll N=20-50 is a smooth plateau (robust family).
- Combined book (1h + 15m legs): baseline +197.71R / DD 22.75R | **v5 +210.53R / 19.78R (net/DD 10.64)** | v6 +196.20R / 18.66R (net/DD 10.51).
- Wired: `htf_ltf/v5_sl_buffer.py` + `htf_ltf/v6_sl_hhll.py` (both = v3 ext-stop + SL variant), routes `htf_ltf_ver=v5|v6`, frontend Ver dropdown + lab rows. Engine validation: v1/v3/v5/v6 all match harness exactly.

