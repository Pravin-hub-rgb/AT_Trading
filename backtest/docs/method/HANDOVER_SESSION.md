# HANDOVER — full session context, for a fresh agent


<!-- C17-NOTICE -->
> **C17 NOTICE (2026-10-07).** The figures in this document were measured before
> the C17 gate fix, which removed a lookahead from the HTF window gate and
> invalidated 214 of 215 registry pins. They are kept as the dated record they
> were, and they are **not** what the engine produces today - do not quote them
> as current. Current numbers: `python exp_pinverify.py` (re-derives every pin),
> `docs/method/C17_WINDOW_END_CAUSALITY.md` (what changed and why),
> `docs/multi/MULTI_RANKINGS.md` and `docs/signal/SIGNAL_RANKINGS.md`
> (regenerated from a post-C17 measurement).
------------------------------------------------------------------------------

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
| engine source (patched at runtime) | `backtest/tests/test_experiments_craze.py` → `build_module()` |
| shared engine module | `backend/src/btc/btc_engine.py` (**never edit** — patch in memory) |
| data loader (bybit) | `exp_5m_confirm.load_book` / `exp_sizing_combo.load_scope` |
| data loader (binance perp) | `exp_cross_instrument_transfer.load_binance` |
| metrics | `exp_equity_quality.equity_quality`, `run_experiment.net_r` |
| sizing arms | `exp_sizing_combo.py` (M2/ZC/X, the `sMZX` family) |
| one-page closed list | `backtest/docs/closed/CLOSED_DO_NOT_REPEAT.md` |
| experiment registry | `backtest/tests/experiment_registry.py` (`BP`, `EXPERIMENTS`) |

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
  IS. Deleting it destroys 121.6R and 141.4R. → `method/RANGE_PEAK_GRAY.md`
- **sMZX sizing (M2/ZC/X)** — **RETRACTED, look-ahead.** See §4.
- **Vol-targeting** — already failed in repo (24.83), net up 6/6 but curve
  worse ×3.
- **ADX, Kaufman ER, regime/chop/wick filters** — all already dead in repo.
- **B1 entry** — tested properly this session (patched in-memory, controls
  exact). **FAILS.** IS catastrophic at every stop level (is/champion 221t
  −34.9R vs 500t +325.8R; WR 27.8%→17.2%). OOS mildly positive on 69-72
  trades. Era split backwards → fails the same-sign bar. → `method/B1_ENTRY.md`

### Exit / stop
- **Exit at FS when the swing looks bad** — DEAD 4/4. Every subset's remaining
  R is positive; best case still gives up +3.6R. → `method/FS_TIME_DECISION.md`
- **Tighter SL (0.5-2.0 × ATR toward entry)** — CATASTROPHIC 4/4. WR −9pts,
  DD 2-4× (is/champion DD 27.7→115.0, calmar 3.20→0.04). → `method/SL_TIGHTEN.md`
- **Wider SL buffer (0.10/0.25)** — worse 3/4. **Causal SL** — era-flipped.
  **Pivot trail** — catastrophic, oos/champion +70.2→−2.5R.
- The stop has now been attacked from **both** directions; every variant loses.
  `sl_buf_atr=0.01` + swing-pivot stands.

### More trades
- Relax `cooldown_bars`/`max_consecutive_losses` — **0/4**. A5 adds 159 trades
  (+32%) for −136R IS / −68R OOS; ex-best5 goes negative in 3 cells.
  → `method/TRADE_EXPANSION_AUDIT.md`
- Pyramid, revenge re-entry, rewin cohort, 5m-confirm — all closed in repo
  before this session.

### Already live (important — the user re-proposed this)
- **`exp_mltf=True` IS the "1-minute scaling" idea.** It skips the
  `busy_until` gate and does not hold the slot, so 1m entries fire while a
  position is open. The champion ships with it.
- **Stage 44 (`signal/MARGINAL_PREENTRY_ATLAS.md`) already measured the green
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
- `method/CAPITAL_STAGE_PLAN.md` had already recorded all of this: send-time
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
inputs **before** the arm is run. → `method/SMZX_LOOKAHEAD_RETRACTION.md`

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

## 7. THE OPEN DIRECTION — a 1-minute setup/entry layer

**This is the only genuinely new research left, and the user asked for it
explicitly.**

Today **setup AND entry both happen on 15m.** `sw10`/`sw15`/`sw20` are all
built from the 15m stream. The 1m series (`data["fine"]`) is used only for
trail/exit fills. Nobody has ever run a 1m setup or a 1m-triggered entry.

Verified this session:
- 1m data exists and is large: **1,946,026 bars**, 2023-01-01 → 2026-09-13.
- **1m swings are not computed anywhere** in the engine.
- ~~**BLOCKER:** `_compute_swings(fine, "continuous", min_bars=N)` over the
  full 1.95M bars did not finish in ~2 minutes and the process died —
  memory-bound. **Solve this first; everything else is wasted until then.**~~
  **RESOLVED — the blocker was not real. See §7a.**

Phase 0 options (none chosen, all plausible):
  (a) chunked/windowed swing computation with overlap, stitched at boundaries;
  (b) pre-filter 1m bars (drop low-activity bars) before swinging;
  (c) keep swing detection on 15m, map only entry *timing* onto 1m.
  **None of these were needed — (a) and (b) were solving a problem that does
  not exist. (c) is superseded by the Phase 1 finding below.**

Phase 1: a new kwarg (e.g. `exp_entry_tf="1m"`) substituting `swings_ltf` with
1m swings and reusing the existing `_collect_signals` call — the mark kinds
(B1/B2/FLIP/FS) already exist in the swing structure, so this is wiring, not a
new concept.
**⚠ CORRECTED: this is NOT a self-contained flag flip. Read §7a before
starting — the naive form of this patch silently drops 91% of signals and
silently rescales every bar-counted risk parameter by 15×.**

Phase 2: pre-registered sweep, 1m setup on/off × `exp_mltf` on/off, 4 cells,
full metrics, control asserts the shipped book.

Phase 3: the user's other idea, **now TESTED and CLOSED** — `exp_mltf_green_r`:
fire the 1m add only when the HTF trade is at least kR green. **FAILS 16/16**,
monotone in k; see §7a-3. Do not retune the threshold.

## 7a. Two measured corrections (2026-09-28) — READ BEFORE PHASE 1

Both below are from scripts in `backtest/tests/`, both with control gates,
and both change what Phase 1 should be. Full detail in
`method/PHASE0_1M_SWING_BLOCKER.md`.

### 7a-1. The 1m swing blocker does not exist

`phase0_1m_swing_diag.py` ran the exact call on growing prefixes:

| bars | swings | time_s | µs/bar |
|---|---|---|---|
| 345,600 | 14,719 | 2.68 | 7.75 |
| **1,946,042 (full)** | **90,991** | **18.49** | **9.50** |

Cost is **linear** (time ratios track bar ratios at every step), and the full
1.95M-bar run finishes in **18.5 seconds** at **957 MB** working set, of
which only 162 MB is the swing call — the rest is the 1.95M `FlowCandle`
objects that are already resident. tracemalloc peak is 177 MB. There is no
unbounded accumulator: `bar_highs`/`bar_lows` are cleared at `bars_seen == 1`
and the engine is re-seeded per swing, so per-engine state is bounded by one
swing (~21 bars).

**Likely the harness, not the algorithm** — `exp_s3_forensic._candles` builds
candle dicts *and* `FlowCandle`s (only the latter is needed to swing), and
`_read_tf` holds a full pandas frame plus a sort copy. If someone saw the
original failure, the useful question is *which harness*, not *how to chunk*.

### 7a-2. Phase 1 as written would produce a silently wrong book

`swings_ltf` is **index-coupled to `candles_ltf`**. In the engine:

    bar = ltf_store.pos(sig["bar"])          # CandleStore(candles_ltf)
    if bar < 0 or bar >= len(candles_ltf): continue

`bar` is a position in `candles_ltf`, then indexes `chop_per_ltf`, `atr_pct`,
`candle_ts_ltf` and `atr15`. So passing 1m swings with 15m candles drops
almost every signal via that `continue`. Measured on a 90-day window:

- 1m signals: **5,759**, resolvable in the 15m store: **524 (9.10%)**
- control (15m vs 15m): **411/411 = 100.00%**

No crash, no warning — a quietly near-empty book. That is exactly the class
of silent-failure this repo's process rules exist to prevent.

And passing 1m *candles* too is not neutral, because `candles_ltf` drives the
feature layer and the bar-counted risk params:

- mean ATR%: 15m **0.2594**, 1m **0.0557** → **4.7×**, so `sl_buf_atr=0.01`
  and `chop_thresh=58.0` under `mode="atr_high"` are different gates
- `cooldown_bars=8` → 120 min on 15m, **8 min on 1m**
- `max_consecutive_losses=3` → 45 min → **3 min**
- `sustainBars=7`, `minBars=10` → same 15× collapse
- `ts+900` in the chop/garch lookbacks **hardcodes the 15m bar duration**

**So a 1m layer is a re-parameterisation, not a flag flip.** Phase 1's real
first step is deciding, per parameter, whether it stays in bars (and gets
rescaled) or becomes a duration. That decision must be pre-registered, and
Phase 2's 4-cell sweep is not meaningful until it is made.

### 7a-3. `exp_mltf_green_r` — TESTED, FAILS 16/16, CLOSED

Run 2026-09-28, `exp_mltf_green_r.py`, path-true, controls exact
(500/454/279/253 at +325.8/+358.9/+70.2/+60.2). dNet vs control:

| lane | k=0.25 | k=0.5 | k=1.0 | k=1.5 |
|---|---|---|---|---|
| is/champion | −17.7 | −52.7 | −52.4 | **−117.3** |
| is/utcsat | −19.9 | −53.5 | −58.4 | **−121.0** |
| oos/champion | −36.4 | −66.0 | −77.6 | −76.6 |
| oos/utcsat | −37.5 | −66.6 | −67.9 | −68.2 |

Same sign 16/16, monotone in k on both IS lanes. The gate is not inert — it
blocks 42→108 (champion IS) and the damage scales with the blocking. OOS
goes outright negative at k≥0.5 (PF 0.958-0.965) and **ex-best-5 is
negative in 14/16 cells**, including OOS at k=0.25.

**The sign of the finding is the point.** Stage 44 showed the green add-on
cohort is profitable *in isolation*; this shows that **removing the
non-green ones makes the book worse**. Both hold. Under `exp_mltf` the
blocked add-ons were occupying concurrency slots and suppressing worse
replacements — the documented 3-5× cascade (`AGENT_COORDINATION.md`,
`method/BLEED_AUTOPSY.md`), reached here by a different route than the wick gate
(skip −39.0R vs gray +28.1R).

**Do not retune k** — a monotone 16/16 cannot be flipped by a different
rung. Full detail and the causality audit in `method/MLTF_GREEN_R.md`.

**Nothing adopted.** Production untouched, all flags default-off.



## 7a-4. Second-researcher round: TWO ERRORS FOUND IN MY OWN HANDOVER

Date: 2026-09-28. Full review in `method/SECOND_RESEARCHER_REVIEW.md`; proposals in
`signal/other bots proposal.md` (four independent sets). Every claim below was
verified in code before being accepted.

**1. `chop_thresh=58.0` IS INERT on the shipped lane.** This handover
lists it as a live champion parameter under §1. It is not read.
`v18_streak_halt.py:417-418` under `mode=="atr_high"` consults only
`atr_high_thresh`:

    elif mode=="atr_high":
        use="decisive" if atrp > atr_high_thresh else "flip"

**Consequence:** every `chop_thresh` 58.0 → 57.0 → 55.0 sweep in the
history varied a parameter the champion never reads. Do not reason about
the champion from those deltas.

**2. `sw10`/`sw20` are built from the 1h STREAM, not 15m.** This handover
says at §2: *"sw10/sw15/sw20 are all built from the 15m stream."* That is
wrong. `exp_5m_confirm.py:186-187` passes `_flow(c1h)`. Only `sw15` is
15m. **The 1h chain and the 15m chain are separate instruments**, which
matters for any future work on the HTF layer.

**3. My own "untouched" seed list was three-quarters wrong.** 30m and 2h
are closed (`exp_tf_family.py`, `method/HTF_2H_PLANE_TEST.md`: 30m costs 84R IS /
55R OOS). Scheduled events are closed path-true with ±1-day placebos
(`method/SCHEDULED_EVENTS_AUTOPSY.md`). A reviewer told to verify rather than
trust caught all three.

**4. `data/flow/bookDepth/` exists: 3,617 files, 2023-01 → 2026-09, never
read by any harness.** Depth-band notional, ±1-5%, ~30s. It is a real
unused information set — and it **cannot be used**, because it has no
2021-2022 coverage and so can never satisfy the same-sign-both-eras bar.
Not weak: structurally excluded. Same for the `funding/`, `metrics/`,
`premium1h/` siblings.

### What survives as genuinely open

- **Label/notation redesign** (P1/P2 wave or ZigZag+Elliott instead of
  B1/B2/FLIP/FS). Raised first and independently by all four reviewers.
  The one live idea that changes what the system **sees** rather than
  filtering an exhausted set.
- **Multi-swing 1h bias confirmation.** A 2-of-3 rule on the 1h chain
  intervenes on the *bias timeline*, which no closed row has touched.
- **One family-wise pass on `data/forward/bybit/`.** Better than my own
  "one look per slice" framing: adjudicate all unadopted survivors in a
  single pre-registered pass rather than spending the slice one candidate
  at a time. It is ~60-70 trades, so it can rule on several things but
  confirm none of them.

- **Live size state.** `v18_streak_halt.py` has **zero** hits for
  equity/size/notional/qty. Any sizing change has no execution channel. This
  is engineering, not research.
- **True FS-only engine.** 2900 (IS) / 1634 (OOS) confirmed swings exist; only
  the 314/179 that produced a B2/flip entry have been priced. An FS-only entry
  could be a larger book. Not simulated.
- **Forward gate / independent data.** The champion IS/OOS slices are the most
  inspected data in this repo. Candidates here have looked excellent in IS and
  died on OOS or cross-venue repeatedly.

## 9. What the user contributed (keep listening to these)

The user caught two real errors in my work:

1. **M2 is forward-looking** — I had built a headline on it without reading
   `method/CAPITAL_STAGE_PLAN.md`.
2. **The stop-distance confound** — I had compared swing-magnitude buckets
   without holding the risk denominator constant, and had to retract it.

They also correctly noted the SL should sit *above* the swing low (which led
to the clean negative in `method/SL_TIGHTEN.md`), and that low WR plus tail
concentration is a **feature, not a bug** — which the stop experiment then
proved: tighten the stop and WR drops 9 points while DD rises 4×.

**Ask them before dismissing an idea.** Both errors above were raised by them
and missed by me.

## 10. Status

**NOTHING ADOPTED.** Production untouched, all experimental flags default-off.
Latest commit at time of writing. The one-page closed list is
`closed/CLOSED_DO_NOT_REPEAT.md` — check it before proposing anything.


