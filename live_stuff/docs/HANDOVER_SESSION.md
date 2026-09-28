# HANDOVER — full session context, for a fresh agent

Written 2026-09-28 at commit `c34286b`. Read this before touching anything.

This is a **single-instrument (BTCUSDT_BYBIT) swing-trend system** with
low win rate (~26-30%) and heavy tail concentration. It is a research
checkout with a strict not-adopted policy. Production is untouched.

---

## 0. The one-paragraph version

The user asked for many improvements. **Every entry-side, sizing, exit and
stop direction tested this session failed, and each failure is now documented
with the number that killed it.** Two bugs in my own harnesses were caught and
fixed mid-run. The user themselves caught a third (a risk-normalisation
confound) which forced a retraction. The only genuinely open research
direction is a **1-minute setup/entry layer** — the system currently detects
setup and enters on 15m, and 1m is used only for trail/exit.

---

## 1. The base book (the thing every experiment is measured against)

| lane | IS | OOS |
|---|---|---|
| champion (`champion_multi_sw10`) | 500t, **+325.8R**, WR 27.8%, PF 1.81, maxDD 27.7, calmar 3.20 | 279t, **+70.2R**, WR 27.2%, PF 1.34, maxDD 53.2, calmar 0.66 |
| utcsat (`utcsat_multi_sw10`) | 454t, **+358.9R**, WR 29.1%, PF 2.01, maxDD 21.2, calmar 4.62 | 253t, **+60.2R**, WR 28.9%, PF 1.33, maxDD 29.4, calmar 1.02 |

Metrics are **net R** (costs + funding included) via
`run_experiment.net_r` / `exp_equity_quality.equity_quality`. Reference
ledgers are asserted before every run; if they don't match exactly the run
aborts.

Key params (champion): `cooldown_bars=8`, `max_consecutive_losses=3`,
`ext_stop_r=3.0`, `sl_buf_atr=0.01`, `mode="atr_high"`, `chop_thresh=58.0`,
**`exp_mltf=True`**, `exp_persist=7`, plus stack flags `exp_trail_half=1`,
`exp_trail_delay_r=1.0`, `exp_skip_decisive=1`.

---

## 2. Code point map (where everything lives)

All under `C:\Users\Pravin\Desktop\main\AT_Trading`.

| what | where |
|---|---|
| engine source (patched at runtime) | `live_stuff/tests/test_experiments_craze.py` → `build_module()` |
| shared engine module | `backend/src/btc/btc_engine.py` (**never edit** — patch in memory) |
| data loader (bybit) | `exp_5m_confirm.load_book` / `exp_sizing_combo.load_scope` |
| data loader (binance perp) | `exp_cross_instrument_transfer.load_binance` |
| metrics | `exp_equity_quality.equity_quality`, `run_experiment.net_r` |
| sizing arms | `exp_sizing_combo.py` (M2/ZC/X, the `sMZX` family) |
| one-page closed list | `live_stuff/docs/CLOSED_DO_NOT_REPEAT.md` |
| experiment registry | `live_stuff/tests/experiment_registry.py` (`BP`, `EXPERIMENTS`) |

**Entry trigger:** `ltf_sigs=_collect_signals(swings_ltf, "decisive", ...)`
Mark kinds: `{"b2": ("B2",), "flip": ("FLIP",)}.get(entry_break, ("B2","FLIP"))`
— there is **no `"b1"` key**.

**Stop:** anchored on `sl_pivot` (the swing extreme):
`sl = sl_pivot -/+ sl_buf_atr*atr15[i]`, at 12-space indent, exactly one of
each form.

**Timeframes:** `sw10`/`sw15`/`sw20` are **all built from the 15m stream**.
1m (`data["fine"]`) is used only for trail/exit fills.

---

## 3. What was tested this session, and the number that killed it

### Entry side
- **Range position × width gate** (4h/1d/3d/1w, 27 pre-registered tests, 7
  survived on trimmed mean) — **GATE FAILS 4/4**. The gated cohort is the
  book's *best* cohort: WR 41-42% vs 27.8-29.1%, carrying +107.4R/+127.0R in
  IS. Deleting it destroys 121.6R and 141.4R. → `RANGE_PEAK_GRAY.md`
- **sMZX sizing (M2/ZC/X)** — **RETRACTED, look-ahead.** See §4.
- **Vol-targeting** — already failed in repo (24.83), net up 6/6 but curve
  worse ×3.
- **ADX, Kaufman ER, regime/chop/wick filters** — all already dead in repo.
- **B1 entry** — tested properly this session (patched in-memory, controls
  exact). **FAILS.** IS catastrophic at every stop level (is/champion 221t
  −34.9R vs 500t +325.8R; WR 27.8%→17.2%). OOS mildly positive on 69-72
  trades. Era split backwards → fails the same-sign bar. → `B1_ENTRY.md`

### Exit / stop
- **Exit at FS when the swing looks bad** — DEAD 4/4. Every subset's remaining
  R is positive; best case still gives up +3.6R. → `FS_TIME_DECISION.md`
- **Tighter SL (0.5-2.0 × ATR toward entry)** — CATASTROPHIC 4/4. WR −9pts,
  DD 2-4× (is/champion DD 27.7→115.0, calmar 3.20→0.04). → `SL_TIGHTEN.md`
- **Wider SL buffer (0.10/0.25)** — worse 3/4. **Causal SL** — era-flipped.
  **Pivot trail** — catastrophic, oos/champion +70.2→−2.5R.
- The stop has now been attacked from **both** directions; every variant loses.
  `sl_buf_atr=0.01` + swing-pivot stands.

### More trades
- Relax `cooldown_bars`/`max_consecutive_losses` — **0/4**. A5 adds 159 trades
  (+32%) for −136R IS / −68R OOS; ex-best5 goes negative in 3 cells.
  → `TRADE_EXPANSION_AUDIT.md`
- Pyramid, revenge re-entry, rewin cohort, 5m-confirm — all closed in repo
  before this session.

### Already live (important — the user re-proposed this)
- **`exp_mltf=True` IS the "1-minute scaling" idea.** It skips the
  `busy_until` gate and does not hold the slot, so 1m entries fire while a
  position is open. The champion ships with it.
- **Stage 44 (`MARGINAL_PREENTRY_ATLAS.md`) already measured the green
  add-on cohort**: when the HTF trade is in profit, the 1m add-on is
  profitable in all six cells — champion **+109.6R IS / +42.2R OOS**, with
  higher WR/PF than first trades. **The user's instinct was right and it is
  already validated.**
- Stage 47 swept 17 campaign policies; caps improved OOS (+70.2→+95.8) but
  gutted IS. Era split, again.

<!-- HANDOVER2 -->
