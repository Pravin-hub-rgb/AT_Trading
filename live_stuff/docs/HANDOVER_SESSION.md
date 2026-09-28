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


## 4. The M2 retraction — read before touching any sizing number

`sMZX` (`1.5^count` on M2/ZC/X) was the repo's only lever that ever passed at
scale (6/6, champion +346.5 IS / +130.4 OOS). **The user caught that its
load-bearing flag is forward-looking, and they were right.**

- `cur_mag_atr = |seg.end_px − seg.start_px| / atr15` reads the swing's **END**
  price. `backend_check_wd_days.py:108` asserts `fs_at_idx >= seg.end_idx` —
  the swing confirms at/after the end bar, while the entry fires at B2/flip,
  **before** it ends. The number does not exist at decision time.
- `CAPITAL_STAGE_PLAN.md` had already recorded all of this: send-time
  replacement agrees only **77.5%** (bar: 95%), fires on **0-6 trades of
  76-500**, `mag_so_far` → 0/6, `ramp_so_far` → 0/6, and **"a send-time
  replacement for M2 was searched for and does not exist."**
  **I failed to read this before building on the number.**
- My 50-draw matched-count shuffle null showed the flags beating random size
  assignment 49-50/50. I called it SELECTION. **The null cannot separate skill
  from look-ahead** — a feature encoding the trade's own future beats a random
  null every time.
- Decomposition: **M2 alone is 4/4** (the look-ahead flag), ZC 1/4, X 2/4 but
  its OOS "passes" are on 7 and 9 trades, **M2-free ZC+X is 3/4** (fails
  is/champion at 80th percentile, 10/50 shuffles beat it).

**New standing rule: a matched-count null is NECESSARY BUT NOT SUFFICIENT.**
Any feature touching future bars needs an explicit causality audit of its
inputs **before** the arm is run. → `SMZX_LOOKAHEAD_RETRACTION.md`

## 5. Three traps that produced spectacular fake numbers

1. **Degenerate risk denominator.** A stop near the fill makes R explode. A
   real harness printed **avg +19.4R, net +9700R** before being caught. Any
   stop closer than ~0.25 × ATR is inside the noise. Guard: exclude and
   *count* the excluded trades, never average them in.
2. **Comparing across buckets without a constant denominator.** The user
   caught this: for a long the original stop sits at the swing LOW, and by FS
   price has moved away, so `|entry − sl|` **grows with swing size** and R
   gets divided by a bigger number. That made "big swings are worst" look
   like a finding; the claim had to be partially retracted. Fix: report a
   **size-neutral measure** (`% move`) alongside R, and hold the denominator
   constant (1.0 × ATR) when comparing across scales.
3. **Wrong-cohort bugs** (worth memorising):
   - `entry_idx`/`exit_idx` are **NOT c1h indices** (`entry_idx=204` resolves
     to 2023-01-09 for a trade entered 2023-01-02, true index 50). Use
     **timestamps**.
   - Per-scope feature maps leaking — a loop that leaves the last scope's map
     in the module makes the *other* era's arms look trades up in the wrong
     table. Symptom: `gray 0` in one era, normal in the other. Re-seed per
     cell.
   - Drawdown computed on **sorted** R silently reports `max_dd 1.0`. Walk the
     curve in **time order**.

## 6. Process rules this repo enforces

- **Controls first.** Assert reference ledgers before any verdict; abort on
  mismatch. `exp_b1_entry.py` does this.
- **Never edit `backend/src/btc/btc_engine.py`.** Rebuild it in memory with
  `types.ModuleType` + `exec`, install into `sys.modules` **before** the craze
  loader imports it. See `exp_sl_tighten.py`, `exp_b1_entry.py`.
- **Match anchors with exact indentation, assert count == 1.** The 8-space
  anchor is a substring of the 12-space one — bare-text matching silently
  double-patches.
- **GRAY, not skip** (Rule 18): trade runs to completion, P&L → r=0, slot
  held, **loss streak must still advance** (`exp_gray_streak=True`), cooldown
  untouched. Skipping frees the slot and admits a worse replacement (wick
  gate: skip −39.0R vs gray +28.1R in IS).
- **Same sign in both eras** on both lanes, or it is closed. This session
  produced seven such IS/OOS flips.
- Report **ex-best-3/5** on anything tail-dependent.
<!-- HANDOVER3 -->

