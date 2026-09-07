# Multi TF — 1H Flip (HTF) + Lower TF Execution (15m / 5m) — NEW STRATEGY

> **HTF:** `1h Flip Fixed 3R cap16` `151tr 39.7% +74.0 base → +57.8 net PF0.78 maxDD10.0` `frontend/src/lib/btcMaster.ts:16` `#1` `v1 cap16` `backend/src/btc/engines/v7_timecap.py:1` `cap 16d 384 bars` `14715 x1h` honest `stream+touchable+one-swing-one-trade+1m` `0.05%+2pt` `14715 x1h` `58780 x15m` `176k x5m` `881k x1m` `BTC_TFS` `btc_config.py:25`.
> **LTF:** `15m Decisive Trail 50` `446tr 21.7% +91.0 → +5.4 net PF1.30 maxDD40.3` `backend/src/btc/btc_engine.py:33` `minBars50` `trailing swing` `BE0` vs `5m Decisive` `557tr +67.9 base 1.26` `fix/btc_ideas.md:100` `minBars14` `fix/btc_ideas.md:40` `B2 +392R` etc. `5m` `3820 swings` `fix/btc_ideas.md:100` `15m` `1304 swings` `fix/btc_15m_trail_decisive_crazy_ideas.md:108`.
> **Idea:** When `1h Flip` is `long` (from its `entry_ts` to `exit_ts` `v7_timecap.py:82` `busy_until`), take `15m`/`5m` `decisive` `long` only inside that window, `short` only when `1h` short — `HTF window` = regime, `LTF` = execution. Outside `1h` position → pause `LTF` (flat gaps `30-40%` `fix/btc_1h_flip_fixed_crazy_ideas.md:31`).
> **Rule:** Each `HTF-LTF` version has its OWN engine `backend/src/btc/engines/htf_ltf/v1_*.py` — `v1` `15m`/`5m` never disturbed. Log here, show in chart via `?htf_ltf=off|15m|5m` on `/api/btc/backtest` & chart dropdown.

---

## Versioning — HTF-LTF

| Ver | Engine file | LTF | Idea | Chart `?htf_ltf=` |
|-----|-------------|-----|------|-------------------|
| **htf_v1_15m** | `backend/src/btc/engines/htf_ltf/v1_15m.py` | **15m Decisive inside 1h Flip cap16** — `decisive50` `trailing swing` `BE0` | `fix/btc_15m_trail...:108` `446tr` | `htf_ltf=15m` |
| **htf_v1_5m** | `backend/src/btc/engines/htf_ltf/v1_5m.py` | **5m Decisive inside 1h Flip cap16** — `5m` `decisive` `minBars14` `trailing swing` | `fix/btc_ideas.md:100` `557tr` | `htf_ltf=5m` |
| htf_v2_15m_ch | `backend/src/btc/engines/htf_ltf/v2_15m_ch.py` | 15m Chandelier `k3.0` inside 1h | `v2_chandelier.py:1` | `htf_ltf=15m_ch` |
| htf_v6_15m_adx | `backend/src/btc/engines/htf_ltf/v6_15m_adx.py` | 15m ADX>25 inside 1h | `v6_adx.py:1` | `htf_ltf=15m_adx` |

Add `htf_v7...` as we brain-storm. Chart `Ver` dropdown (existing `v1..v7`) stays for pure `15m`/`1h` strategies, new `HTF-LTF` dropdown `off|15m|5m` is separate — both can be active.

---

## How It Works

**Data:** `BTC_TFS` `btc_config.py:25` `1h 14715` `15m 58780` `5m 176343` `1m 881k` `continuous` `btc_swing.py:23` `timeCap 00:00` `compute_btc_swings` `btc_swing.py:50` `minBars` `14/20/50`, `compute_btc_flow` `btc_swing.py:156`.

**HTF window:** `1h` `swings1h` `minBars20` `btc_swing.py:50` → `simulate_btc_trades_v7(... cap16 ... fine1m)` `btc_routes.py:250` `v7_timecap.py:22` `cap 16d 384 bars` `market exit` `fine` `bisect_left` `btc_engine.py:195` → `trades1h [(entry_ts, exit_ts, dir)]` `non-overlapping` `busy_until` `btc_engine.py:327`.

**LTF gate:** `ltf_signals = _collect_signals(swings_ltf, "decisive", ..., candles=candles_ltf)` `btc_engine.py:33` `tradeable B2|FLIP` `one swing one trade` `btc_engine.py:93` `touchable SL max high since prev_end` `btc_engine.py:128` + filter `in_pos = bar_ts > htf_entry && bar_ts <= htf_exit && sig_dir == htf_dir` `bisect_right` `interval_starts` `btc_engine.py:340` style.

**Execution:** `busy_ltf` `btc_engine.py:327` separate from `busy_htf` — `htf_busy_until` + `ltf_busy_until` two scalars `htf_ltf/v1_*.py`. `LTF` respects its own `SL/trail/target/1m` `btc_engine.py:179` `sl_cur<cand<lo` `btc_engine.py:248` `fine` `btc_engine.py:195` `SL before target` `gap fill`. `LTF` has `risk_split 0.5` `qty = fixed_rupee / risk` `btc_routes.py:113` `cost_r` per trade `trade_stats` `btc_engine.py:537` `PF/maxDD` per leg + `combined = htf + ltf` weighted.

**Options:** `Strict window` (LTF must exit at HTF `exit_ts` market) vs `Let run` (LTF trail to its own SL). `Bias+Window` hybrid `HTF dir + LTF swing dir`.



---

## Logs

### 2026-09-06 — HTF-LTF v1 created (15m + 5m)

- Created doc, `backend/src/btc/engines/htf_ltf/` `v1_15m.py` `v1_5m.py` isolated, `backend/src/btc/btc_routes.py:148` `?htf_ltf=off|15m|5m` + `frontend/src/lib/btcApi.ts:1` + `frontend/src/app/btc/page.tsx:537` HTF-LTF dropdown (off|15m|5m) — `v1 15m` default, `v1 5m` also.
- HTF `1h cap16 151tr +57.8` `v7_timecap.py:1` + LTF `15m 446tr +5.4` `v1` `5m 557tr +67.9` `fix/btc_ideas.md:100` `15m 1304 swings` `5m 3820` `fix/btc_ideas.md:100`.
- Sweep pending: `TF` `5m vs 15m` `LTF` `decisive50` `minBars 50 vs 14` `trailing swing vs off` `BE0` `PF/maxDD` `long -16.5 short +21.9` `quick_sweep_htf.py:1` `bear -30%` `fix/btc_ideas.md:232`.

