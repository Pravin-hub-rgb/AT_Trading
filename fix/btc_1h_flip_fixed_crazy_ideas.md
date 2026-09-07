# BTC 1h Flip Fixed 3R — Crazy Ideas Lab

> **Focus:** `backend/src/btc/btc_engine.py` `flip1h20` (`1h` `flip` `sl swing` `trailing off` `BE0` `minBars 20` `rr 3`) honest FULL window `Jan-25→Sep-26` `14715 x1h` + `1m-precise fills` + `stream+touchable+one-swing-one-trade` + `0.05%/side+2pt` `14715 x1h`.
> **Honest reality:** `frontend/src/lib/btcMaster.ts:16` `#1 Flip Fixed 3R (1h) — Cap 16d` `151tr 39.7% +74.0 base → +57.8 net` `PF0.78 maxDD10.0` `cap 16d` `16.0d max hold` `101tr +51.2 cap0` old removed. `fix/btc_ideas.md:475` `847tr +19 net` was `15m`.
> **Goal:** Net R max for 1h Flip, but also log `win% / PF / maxDD` `btc_engine.py:537` for each version. Test `cap` `BE` `ADX` `volume` `session` `partial` etc.
> **Rule:** Each 1h flip version gets its OWN engine `backend/src/btc/engines/1h_flip/v*.py` — `v1` never disturbed. Log here, show in chart via `?version=1h_v1..` on `/api/btc/backtest?tf=1h`.

---

## Versioning — 1h Flip

| Ver | Engine file | Idea | Base on | Chart `?version=` | Trades | Win% | Base | Net 0.05% | PF | maxDD |
|-----|-------------|------|---------|-------------------|--------|------|------|-----------|-----|-------|
| **v1** | `backend/src/btc/engines/v7_timecap.py` `cap16` + `btc_engine.py` | **Cap 16d** — market exit at cap `16d 384 bars` `v7_timecap.py:1` | `research_1h_flip.py:1` | `1h_v1` (default) | 151 | 39.7% | +74.0 | **+57.8** | 0.78 | 10.0 |
| v2 | `backend/src/btc/engines/1h_flip/v2_cap15.py` | Cap 15d | `sweep_1h_granular.py:1` | `1h_v2` | 150 | 40.0% | +73.3 | +57.4 | 1.78 | 10.0 |
| v3 | `backend/src/btc/engines/1h_flip/v3_cap30.py` | Cap 30d | `sweep_1h_granular.py:1` | `1h_v3` | 141 | 38.3% | +65.5 | +50.5 | 1.71 | 14.5 |
| v4 | `backend/src/btc/engines/1h_flip/v4_be1.py` | BE1 | `v5_be1.py:1` | `1h_v4` | - | - | - | - | - | - |
| v5 | `backend/src/btc/engines/1h_flip/v5_adx25.py` | ADX>25 | `v6_adx.py:1` | `1h_v5` | 94 | 26.6% | +5.6 | -4.8 | - | - |
| v6 | `backend/src/btc/engines/1h_flip/v6_partial.py` | Partial 30% @1R | `v4_partial.py:1` | `1h_v6` | - | - | - | - | - | - |

Add `v7...` as we brainstorm.

---

## v1 — Cap 16d (LOCKED)

**Engine:** `backend/src/btc/engines/v7_timecap.py:1` `cap_days 16` `cap_bars 384` `market exit` `fine` `bisect_left` `btc_engine.py:195`. `frontend/src/lib/btcMaster.ts:16` `#1` `151tr +57.8 net` `PF0.78` `maxDD10.0` `27 Jan 114d -1R → 16d +0.289R` `research_1h_timecap.py:1`.

**Why cap 16:** `sweep_1h_granular.py:1` `cap 10 +50.3` `12 +39.2` `14 +54.0` `15 +57.4` `16 +57.8 BEST` `18 +57.3` `20 +55.1` `25 +57.5` `30 +50.5` `0 +51.2` — flat top `14-25d` `+0.4R` noise `fix/btc_ideas.md:224` lottery.

**Trades:** `Hold <=15d 94tr +53.1` `<=30d 99tr +60.1` `research_1h_flip.py:1` `>30d 2tr +2.0` `114d` + `44d` — cap frees `busy_until` `btc_engine.py:327` `101→151tr`.

---

## v2 — Cap 15d

**Engine:** `v7_timecap.py` `cap 15` `360 bars`

**Result:** `150tr 40.0% +73.3 → +57.4 PF1.78 maxDD10` `sweep_1h_granular.py:1` — `-0.4R` vs `v1`, PF better `1.78 vs 0.78`.

---

## v3 — Cap 30d

**Result:** `141tr 38.3% +65.5 → +50.5 PF1.71 maxDD14.5` — worse than `v1`.

---

## Sweep Matrix (run for each 1h flip v)

**For each `1h flip` `v` test:**
- `cap` `0/7/10/12/14/15/16/18/20/25/30/45`
- `BE` `0 vs 1` `v5_be1.py:1`
- `ADX` `20/25/30` `v6_adx.py:1` `quick_sweep_htf.py:1` `1h ADX 20 +14.7` `25 -4.8`
- `Volume` `>SMA*1.5` `fix/btc_sweep.py:185` `volume` `x,y` `0,0` `btc_config.py:3` not usable
- `Session` `00-04/04-08/08-12/12-16/16-20/20-24 UTC` `sweep_E2_E5_E8_E9.py:1`
- `Metrics` `Net` `Win%` `PF` `maxDD` `btc_engine.py:537`

**Run:** `python backend/debug/sweep_1h_flip_crazy.py --cap 16` → logs below + `backend/debug/sweep_1h_v*.json`.

**Chart:** `GET /api/btc/backtest?tf=1h&version=1h_v1&min_bars=20` `frontend/src/app/btc/page.tsx:537` `Ver 1h_v1..` `StockChart`.

---

## Logs

### 2026-09-06 — v1 cap16 locked

- `v1` `151tr 39.7% +74.0→+57.8 net` `PF0.78 maxDD10` `cap 16d` `old cap0 101tr +51.2` removed. `backend/src/btc/btc_routes.py:148` `flip1h20` `v7` dispatch `cap16`.
- `v1` never disturbed — each `1h flip` `v` has its own file `backend/src/btc/engines/1h_flip/v*.py`.

### 2026-09-06 — Sweep cap 10-30d 1h Flip Fixed

| Cap | Trades | Win% | Base | Net 0.05% | PF | maxDD | Notes |
|-----|--------|------|------|-----------|-----|-------|-------|
| 0d | 101 | 41.6% | +62.1 | +51.2 | 1.97 | 9.0 | No cap |
| 10d | 159 | 39.0% | +66.7 | +50.3 | - | - | |
| 12d | 158 | 37.3% | +56.1 | +39.2 | - | - | |
| 14d | 151 | 39.1% | +69.9 | +54.0 | - | - | |
| 15d | 150 | 40.0% | +73.3 | +57.4 | 1.78 | 10.0 | |
| **16d** | **151** | **39.7%** | **+74.0** | **+57.8** | **0.78** | **10.0** | **BEST net** |
| 18d | 147 | 39.5% | +73.0 | +57.3 | - | - | |
| 20d | 142 | 39.4% | +70.0 | +55.1 | - | - | |
| 25d | 135 | 40.0% | +71.3 | +57.5 | - | - | Flat top 14-25d |
| 30d | 141 | 38.3% | +65.5 | +50.5 | 1.71 | 14.5 | |

**Takeaway:** Best net `16d +57.8` vs `15d +57.4` `+0.4R` `1 trade` noise `top-25 96%` lottery. `PF` `15d 1.78` > `16d 0.78` — `15d` better risk-adjusted. `v1` lock `16d` as default per user `cap 16 is best best really`.

