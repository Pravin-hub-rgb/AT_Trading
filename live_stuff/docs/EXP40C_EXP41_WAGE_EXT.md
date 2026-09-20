# EXP 40c / 41 / 42 / 43 / 44 / 45 / 46 / 47 / 48 / 49 — wage gate (w24) × ext_stop: full record, theory, harnesses, results

Experiment dates: 2026-09-19 (40c/41) and 2026-09-20 (42–48). Branch: `experiments/v19-plus`.
Engine (all rows): `backend/src/btc/engines/htf_ltf/v18_streak_halt.py`, mode `b2_vs_flip_chop`.
Instrument: `BTCUSDT_BYBIT` (15m LTF + 1h HTF candles via `load_candles()`, 1m fine data via `_load_fine_1m`). Data span ~1350 days (6 WF segments of ~225d).

> This file is the canonical record of the wage/ext experiment family. Nothing here
> was deleted — both harnesses still run. Companion raw outputs live next to the
> harnesses (see §A file map).

---

## 0. TL;DR verdict

| Rank | Config | Trades | NET (fine) | npt | DD | WF worst seg |
|---|---|---|---|---|---|---|
| 1 | **OPT-cd10 + w24 + ext1.5** | 326 | **+337.7** | **1.04** | **19.2** | **+13.6** (no losing seg) |
| 2 | OPT-cd0 + w0 + ext1.5 | 515 | +322.5 | 0.63 | 23.3 | +9.6 (no losing seg) |
| 3 | OPT-cd10 + w24 + ext2.0 | 350 | +329.8 | 0.94 | 23.2 | +9.7 |
| 4 | OPT-cd10 + w24 + ext2.5 | 383 | +315.5 | 0.82 | 22.2 | +2nd worst − |
| 5 | OPT-cd0 + w24 + ext2.5 | 426 | +302.6 | 0.71 | 25.2 | — |
| 6 | OPT-cd0 + w24 + ext1.5 | 364 | +301.6 | 0.83 | 27.7 | −0.3 |
| 7 | OPT-cd10 + w0 + ext2.5 | 512 | +291.4 | 0.57 | 27.1 | — |
| 8 | lb30 + w0 + ext2.5 | 377 | +231.1 | 0.61 | 24.6 | **−31.1** |
| 9 | A4 + w24 + ext1.5 | 261 | +223.1 | 0.86 | 19.8 | −1.1 |
| 10 | A4 + w0 + ext1.5 | 359 | +203.3 | 0.57 | 24.8 | — |
| 11 | lb30 + w0 + ext1.5 (production base) | 349 | +196.3 | 0.56 | 23.6 | **−29.6** |
| 12 | lb30 + w24 + ext2.5 | 303 | +179.1 | 0.59 | 23.6 | −14.6 |

Three headline conclusions:

1. **"Kill w24" does NOT generalize.** On lb30 the user's instinct was right —
   ext2.5 beats w24 by +52R and w24×wide-ext is the worst combo. But on the OPT
   lanes the knobs flip: **w24 is the single biggest edge on OPT-cd10** (+78R over
   its w0 twin, DD 32.7→19.2) and ext2.5 is poison there (monotonic decline
   337.7 → 329.8 → 315.5 as ext opens). See §4 theory.
2. **The w24×ext interaction is structural, not curve-fit noise:** w0 lanes want
   WIDE ext (lb30-w0: 196.3 → 218.2 → 231.1; OPT-cd10-w0: 259.4 → 269.2 → 291.4,
   both monotonic up), w24 lanes want TIGHT ext (lb30-w24: 185.0 → 197.2 → 179.1;
   OPT-cd10-w24: 337.7 → 329.8 → 315.5, peak at 1.5–2.0). Never mix.
3. **Walk-forward separates the lanes:** only the two OPT leaders have zero losing
   segments. Everything lb30-based bleeds −22 to −31 in segment 1 (oldest data —
   closest thing to true out-of-sample in this design). lb30's ext2.5 gain is a
   back-loaded edge (H1 +95.2 vs H2 +135.9).

**Exp 42 update (2026-09-20, full detail in §13):** wage-threshold sweep
{0,12,18,24,36,48} on 4 lanes. "Kill w24" confirmed lb30-only (argmax 0h
there); 24h is argmax on the other 3 lanes but with ±70R noise between
neighbors — adopt the **18–36h band**, not the point. DD and npt improve
monotonically with wage on every lane. lb14-w24 revalidated (272t +193.7
DD 15.7). 12h is ruled out everywhere except OPT-cd10.

---

## A. File map — every file, what it is, status

Scope: this experiment line (exp40c / exp41 / exp42) plus everything they
import or produce. Deletion policy (§12 rule 6): **nothing in this list gets
deleted** — harnesses stay runnable, outputs stay on disk. The only file ever
deleted in this line is `test_verify_wage.py` (deleted by the second
verification lane, documented in the table).

| File | What it is | Status |
|---|---|---|
| `live_stuff/tests/exp40c_wage_gate.py` | **Exp40c harness** — identity gate + Phase A matrix validation + Phase B coarse 18-cell matrix + Phase C fine 18-cell matrix. Writes `_exp40c_results.json`. Exports `BP` / `fund` / `run_coarse`, reused by exp41 and exp42. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp41_wf_leaders.py` | **Exp41 harness** — Phase 1: missing OPT-cd10 × ext2.0 cells; Phase 2: segmented walk-forward (6 segs, fixed configs) on 8 leader configs. Writes `_exp41_results.json`. Imports `BP/fund/run_coarse` from exp40c. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp42_wage_sweep.py` | **Exp42 harness** — wage-threshold sweep {0,12,18,24,36,48} × {lb30, A4, OPT-cd10, lb14} at ext1.5 + lb14 re-check + segmented WF on the same sweep ledgers. Gates: identity + user coarse matrix + 6 fine pins to exp40c Phase C; aborts on any mismatch. Writes `_exp42_results.json`. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp_n2_chop_veto.py` | **Exp N2 harness** — chop veto bucket-split by chop-at-entry on anchor lb14/lb30 + OPTIMAL, fine fills. Identity-gated. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp_n3_atrpct_veto.py` | **Exp N3 harness** — atrpct 60-80 veto bucket-split by ATR% percentile on anchor lb14/lb30, fine fills. Identity-gated. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp_n4_cap.py` | **Exp N4 harness** — concurrency cap {2,3,4,5} greedy causal post-filter on OPTIMAL fine trade list. Identity-gated. | ✅ RUNNABLE — keep |
| `live_stuff/tests/test_experiments_craze.py` | The **craze module** — builds an instrumented copy of the shipped engine via `build_module()` and patches in experiment knobs (`exp31_lb`, `exp_persist`, `exp_mltf`, `exp_wage_h`, …). The **wage gate lives here** (§3.1 for the exact patch code). | ✅ patched, identity-gated — keep |
| `live_stuff/tests/exp40b_ext25_a4_opt.py` | **STALE legacy runner** — its `main()` predates the current `build_module()` signature (crashes on `build_module(split_mb=True)`; pre-existing, never touched). Superseded by exp40c. Do not run its `main()`. | ⚠️ stale — keep for record only |
| `live_stuff/tests/_tmp_open.py` | Legacy ad-hoc probe (uses the original `test_experiments.py`, no wage/ext knobs). Predates exp40c. | record only — keep |
| `live_stuff/tests/_fix40c2.py` | One-shot patch script: fixed the contradictory wage-gate comment in the craze module, cleaned doc encoding, installed doc §10–§12. | patch audit trail — keep |
| `live_stuff/tests/_fix42.py` | One-shot patch script: repaired exp42's scrambled insert seam (reordered lines). | patch audit trail — keep |
| `live_stuff/tests/_fix_doc_a.py` | One-shot patch script: rewrote §A into the complete file map (this table). | patch audit trail — keep |
| `live_stuff/tests/_doc_tail1.md`, `_doc_tail2.md` | Source text of doc §10–§12, applied by `_fix40c2.py`. | keep |
| `live_stuff/tests/_exp40c_results.json` | Full exp40c matrix, machine-readable (coarse + fine, 18 cells each). | output |
| `live_stuff/tests/_exp40c_out.txt` / `_exp40c_err.txt` | exp40c console log / stderr (err empty on final run). | output |
| `live_stuff/tests/_exp41_results.json` | Full exp41 output (cells + WF), machine-readable. | output |
| `live_stuff/tests/_exp41_out.txt` / `_exp41_err.txt` | exp41 console log / stderr (err empty on final run). | output |
| `live_stuff/tests/_exp42_results.json` | Full exp42 output (sweep + WF), machine-readable. | output |
| `live_stuff/tests/exp43_loss_autopsy.py`, `_exp43_out.txt`, `_exp43_results.json` | **Exp43 harness** — loss autopsy: w24 decomposition (removal vs chain-shift), runner amputation, parent-window inheritance. Gates: identity + matrix + 8 fine pins. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp44_curfew_gate.py`, `_exp44_out.txt`, `_exp44_results.json` | **Exp44 harness** — curfew gate (skip 6–24h band, keep 0–6h + ≥24h), 4 lanes × 4 variants + WF. Gates: identity + matrix + 8 fine pins + canary. §14. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp45_curfew_plateau.py`, `_exp45_out.txt`, `_exp45_results.json` | **Exp45 harness** — curfew edge-plateau grid (lb30) + curf×ext combo + A4 edges + WF. Gates: identity + matrix + 6 fine pins + canaries. §15. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp46_defer_entry.py`, `_exp46_out.txt`, `_exp46_results.json` | **Exp46 harness** — deferred entry (requeue young signals to the defer bar if window alive + SL pivot untouched + ext passes), 3 lanes × 5 variants + WF. Gates: identity + matrix + 6 fine pins + canaries. §16. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp47_yearly_stats.py`, `_exp47_out.txt`, `_exp47_results.json` | **Exp47 harness** — stats board: gross/net/avgR/DD/WR + per-year NET + delta vs anchor, 9 configs. Gates: identity + matrix + 5 fine pins. §17. | ✅ RUNNABLE — keep |
| `live_stuff/tests/exp49_partial_champion.py`, `_exp49_out.txt`, `_exp49_results.json` | **Exp49 harness** - partial exits (exp_partial_r) + champion reproduction (sw10/sw20) + seg6 WF. Gates: identity + matrix + 4 fine pins + canaries. Section 20. | OK RUNNABLE - keep |
| `live_stuff/tests/exp48_leg_progress.py`, `_exp48_out.txt`, `_exp48_results.json` | **Exp48 harness (v2)** — price-space autopsy (bimodal legs) + leg-progress gate (REJECTED). Gates: identity + matrix + 4 fine pins + canaries. §18. | ✅ RUNNABLE — keep |
| `live_stuff/tests/_exp42_out.txt` / `_exp42_err.txt` | exp42 console log / stderr (err empty). | output |
| `live_stuff/tests/_exp40b_out.txt`, `_exp40b_err.txt`, `_exp40b_results.json` | Stale exp40b legacy outputs (from before the current gate). | record only |
| `live_stuff/tests/test_verify_wage.py` | Second verification lane's script that produced §10's numbers — **DELETED by that lane** after running (violation of §12 rule 6). Its numbers were cross-checked against `_exp40c_out.txt` Phase C and match to the decimal. Do not delete replacements. | ❌ deleted by second lane — documented |
| `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` | The shipped engine all rows share. **Never modified.** | production |
| `live_stuff/tests/test_experiments.py` | Original shipped `simulate_v18_experiments` (used by legacy probes like `_tmp_open.py`). Not used by 40c/41/42 (they use the craze module). | untouched |

**Lineage note:** the ORIGINAL deleted Exp40/41 harness (whose gate code was
unrecoverable) is what exp40c rebuilt and validated — its replacement is the
asserted craze patch, which is *stricter* (identity gate + external matrix
check + fine pins). Nothing else in this line has ever been deleted.

## 1. Engine common to every row — `v18_streak_halt`

* **HTF = 1h bias windows.** 1h swings → 1h `flip` trades + 1h `B2` trades
  (rr 3.0, 16d cap). Each HTF trade becomes a window `[entry_ts, exit_ts, dir]`.
  Only windows whose start candle is CLOSED are usable — causal.
* **C15 knowable-instant rule.** The window is knowable only from the flip
  candle's CLOSE. The engine gates in knowable-instant space:
  `if not (s + 2700 < bar_ts <= e + 2700): continue` (2700 = 3600 − 900, so the
  gate covers 15m bars whose close instant ≥ flip candle close). LTF signals
  inside the flip's own hour are genuinely not takeable live.
* **Regime = 1h chop.** `chop > thresh` → use B2 windows, else use FLIP windows
  (`mode=b2_vs_flip_chop`).
* **LTF = 15m entries.** 15m `decisive mb50` signals, must be: inside the HTF
  window + same dir as window + `ext_stop` gate + `cooldown` + `halt3` + swing
  trail.
* **Costs = fine NET** (see §5): 1m fills + fee + slip + funding.

### 1.1 Knob semantics — lb vs mb, don't mix

* `lb` (`exp31_lb`) = 1h **chop lookback length**. Shipped default 14 (`lb14` =
  twitchy regime detection, lots of B2/FLIP flip-flops). `lb30` = chop over last
  30×1h candles = slow/smooth regime.
* `mb` = swing `min_bars`. `mb20` = shipped 1h swings (`SWING["min_bars_1h"]`).
  `mb10` = twitchier 1h swings → MORE HTF windows (used by A4/OPT lanes).
* `chop_thresh`: shipped 58.0. A4/OPT use 55.0 → more time in B2 regime.
* `exp_persist=2`: regime hysteresis — a regime change must repeat 2 bars before
  the engine switches window sets. Kills chop flicker.
* `exp_mltf=True` (+ `exp_multi_ltf_cd`): multi-LTF port (no busy gate between
  lanes); OPT-cd0 sets `cooldown_bars=0`, OPT-cd10 keeps `cooldown_bars=10`.
* `max_consecutive_losses=3` (halt3) is the LTF throttle in all rows.

### 1.2 Lane definitions (exact knob dicts, from exp40c/exp41 source)

| Lane | 1h swings | knobs (on top of BP) |
|---|---|---|
| `lb30` (production base + `exp31_lb=30`) | mb20 | `exp31_lb=30` |
| `lb14` | mb20 | (none — shipped) |
| `A4` | mb10 | `exp31_lb=30, chop_thresh=55, exp_persist=2` |
| `OPT-cd0` | mb10 | `exp_mltf=True, exp_persist=2, chop_thresh=55, cooldown_bars=0` |
| `OPT-cd10` | mb10 | `exp_mltf=True, exp_persist=2, chop_thresh=55, cooldown_bars=10` |

`BP` (base params) = craze `BASE` with `chop_thresh=58.0`; every lane dict is
spread **over** BP (so A4's `chop_thresh=55` wins). `ext_stop_r` is passed
explicitly per cell (1.5 / 2.0 / 2.5 / 3.0).

## 2. N5 lineage — where the wage experiment came from

The w24 idea predates exp40c and improved DD on **every** base it was tried on:

| Base | w0 → w24 (fine NET, ext1.5) | Δ | DD |
|---|---|---|---|
| lb30 (mb20) | 349t +196.3 → 265t +185.0* | *see §4.3 | 23.6 → 19.4 |
| lb14 | 351t +148.0 → 281t +201.9 (deleted-harness) | +53.9 | 23.4 → 15.8 |
| A4 (mb10) | 359t +203.3 → 261t +223.1 | +19.8 (deleted-harness: 266t +228.6) | 24.8 → 19.8 |

**Theory (window physics, not curve-fit):** w24 = "don't take the first-day ride
in a new HTF leg". At entry the engine knows the parent window's start; age
`wage = (signal-bar ts − window start ts)/3600`. Age < 24h → skip. First-day LTF
signals are discovery cost: the autopsy bucket `wage 0–24h` was 75t −11.9R
(≈ −0.38R/trade). Waiting one day lets the window prove itself before we ride
it. That is why it cut DD on every base and why it isn't tuned to one chop
lookback.

---

## 3. The two knobs and their interaction

### 3.1 `exp_wage_h` — the wage gate (exact implementation)

Lives in `test_experiments_craze.py` inside `build_module()`'s patch list,
inserted at the engine's window-membership gate:

```python
t6f = '        if not (s + 2700 < bar_ts <= e + 2700): continue\n'
assert s.count(t6f) == 1, "window membership"
s = s.replace(t6f, t6f +
    '        if exp_wage_h>0 and (bar_ts-s)/3600.0 < exp_wage_h: continue\n')
```

Properties:
* **Pre-fill filter** — applied while signals are filtered, BEFORE the LTF walk
  simulates. It therefore shifts `busy_until`/cooldown chains downstream (that
  is why fine counts ≠ coarse counts, §4.3).
* **Causal** — `s` is a closed 1h candle ts; age is computable at decision time.
* **Lane-consistent** — age is measured against the SAME window (`intervals[idx]`
  of the same `use`-lane interval set) that admitted the trade.
* Default `exp_wage_h=0` → identity no-op, enforced by the identity gate (§5.1).

### 3.2 `ext_stop_r` — HTF-extension ceiling

At signal time: `ext = (close − pe)*d / |pe − psl|` (how far price already ran
in the window's direction, in R of the HTF window's own risk). If
`ext > ext_stop_r` → skip. `ext_stop 1.5` forbids entries once price ran >1.5R
of the leg; `2.5` admits the 1.5–2.5R band.

### 3.3 The interaction (the central finding)

* **On lb30 (mb20):** ext 1.5→2.5 alone = **+34.8R NET** (196.3 → 231.1). The
  gate was strangling 28 trades entering at 1.5–2.5R extension; on mb20 windows
  those late entries are mature-trend **riders** (+36 gross coarse, fees flat
  73.6, same WR band). ext3.0 adds nothing (+2 gross) — 2.5 is the ceiling.
* **On A4/OPT (mb10 + chop55):** the same band is **trash**. A4-w0-ext2.5
  collapses to +141.3 (−62R vs ext1.5); OPT-cd10-w24 declines monotonically.
  More windows (mb10) + more B2 time (chop55) ⇒ the 1.5–2.5R band fills with
  late entries that are tops, not riders.
* **w24 + wide ext = worst combo everywhere.** Waiting 24h then entering at
  2.0–2.5R extension = buying the top. The knobs are anti-synergistic.
* **Rule of thumb:** w0 → set ext at the w0-sweep ceiling (2.5 on both lb30-w0
  and OPT-cd10-w0). w24 → keep ext1.5 (OPT-cd10) or at most 2.0 (lb30-w24 peaks
  at 2.0 = 197.2). Never mix wide-ext with w24.

## 4. Methodology — how the tests were done

### 4.1 Coarse vs fine — the two scoring modes

* **Coarse** = `run_coarse()` (exp40c, reused by exp41): engine run with
  `fine_ltf=[]` (15m-bar exit resolution), score = **gross R** =
  `sum(t["r_multiple"])`, no costs. Used for fast matrix sweeps and for the
  external validation matrix (which was itself coarse).
* **Fine** = engine run with `fine_ltf` = real 1m candles
  (`_load_fine_1m(ts0, ts1, symbol="BTCUSDT_BYBIT")`), exit path re-timed on 1m
  (which also shifts `busy_until`/cooldown chains — fine counts differ from
  coarse counts). Score = **NET R**:

```
net = Σ r_multiple  −  _trade_costs(trades, fee_pct, 0.0, entry_slip_pct, exit_slip_pct)  −  funding
```

  * fees+slip via `_trade_costs` (`src/btc/btc_routes.py`), rate params from
    `engine.v18_params.get_v18_params("BTCUSDT_BYBIT")` — the 0.055% fee model.
    On lb30 fees were flat ≈73.6R across 349–377 trades (≈0.2R/trade).
  * funding (`fund()` in exp40c, reused by exp41), in R units per trade:
    `bars_held × 0.25h ÷ 8h × 0.0001 × (entry_price ÷ risk_distance)` — i.e.
    0.01% per 8h funding cycle on the notional that 1R of risk controls.
  * DD = `stats(tr)["dd"]` from the craze module.

### 4.2 The two validation gates (both must pass before any result is read)

1. **Identity gate** (exp40c, printed first): the patched craze module with ALL
   experiment flags off must equal the shipped engine exactly — same `n` AND
   same `rs` list. Result: `IDENTITY GATE OK (flags-off == shipped, n=351)`.
   This proves the instrumentation itself didn't perturb the engine.
2. **External matrix gate** (exp40c Phase A): the user's OWN lb30-w24 coarse
   matrix (4 cells, from the pre-deletion run) is hard-coded and asserted
   (`±0.15R` on gross, exact counts):
   `ext1.5 265t +231.6 | ext2.0 294t +248.2 | ext2.5 304t +231.7 | ext3.0 307t +222.4`.
   Result: **4/4 exact**. This pins the rebuilt wage gate to an external
   authority, not to our own harness. If Phase A fails, the run aborts
   (`SystemExit`) — no Phase B/C output is produced.

### 4.3 Validation history — every convention that was tried and rejected

The original Exp40/41 harness was deleted after its run, so the gate had to be
rebuilt and its exact age convention recovered empirically. Full audit trail:

| Attempt | Age convention | Result | Verdict |
|---|---|---|---|
| 1 | age from first CLOSED candle (`s+2700`), pre-fill | counts unchanged vs attempt 2's base | rejected (no effect on counts) |
| 2 | age from raw window start `s`, pre-fill | lb30-w24 ext sweep = user matrix **4/4 exact** | ✅ FINAL |
| 3 | post-hoc ledger partition, trade's own lane | removed 99/97/109 (doc said 74/70/93) | rejected — over-removed ~25/base |
| 4 | post-hoc, 8 variants (raw/±2700/±3600 offsets, canonical flip-first parent, dir-blind) | all clustered 246–254t | rejected |
| 5 | same-direction **leg** anchor (age from start of same-dir window streak), 13 variants incl. pre-fill | did not match; WRONG premise | rejected |
| 6 | **raw pre-fill** (attempt 2) re-checked vs user matrix + user's fine table | **coarse 4/4, fine 4/4 exact** | ✅ FINAL (same as 2) |

Also attempted and abandoned: matching the deleted N5 doc rows (lb30+w24 275t
+224.5, lb14+w24 281t +201.9, A4+w24 266t +228.6). Those rows came from the
deleted harness's own (unrecoverable) convention and are **superseded**: the
user's own quoted fine table (196.3 / 231.1 / 197.2 / 179.1) — which IS the
authoritative record — reproduces **4/4 exactly** under the final gate. The
residual deltas are confined to two w24-ext1.5 cells (lb30 185.0 vs 224.5, A4
223.1 vs 228.6) and are documented, not hidden.

### 4.4 exp41's walk-forward design

* 6 equal segments by entry_ts of the causal full-history sim
  (`step = (ts1−ts0)/6`, trade bucketed by `entry_ts`; ~225 days each).
* **Configs are FIXED** — no per-fold re-fit. Because the engine sim is causal
  end-to-end, each segment bucket is an honest per-segment ledger of a fixed
  rule. What this design tests: *is a fixed config stable across regimes*.
  What it does NOT test: whether the knob-SELECTION process generalizes (the
  OPT knobs were chosen in-sample on the full period — stated caveat, not
  hidden). Segment 1 (oldest data) is the closest thing to true OOS here.
* Per config: total NET, 6 segment NETs, worst segment, per-segment DDs,
  H1/H2 (first/second half of the trade ledger by count).

## 5. Results — exp40c (`_exp40c_results.json`, full matrices)

### 5.0 Identity + validation (printed before anything else)

```
IDENTITY GATE OK (flags-off == shipped, n=351)
PHASE A - prefill wage validation (user matrix, lb30 w24 ext sweep)
  lb30+w24  ext1.5 coarse 265t gross  +231.6   OK (exp 265t +231.6)
  lb30+w24  ext2.0 coarse 294t gross  +248.2   OK (exp 294t +248.2)
  lb30+w24  ext2.5 coarse 304t gross  +231.7   OK (exp 304t +231.7)
  lb30+w24  ext3.0 coarse 307t gross  +222.4   OK (exp 307t +222.4)
```

### 5.1 Phase B — coarse matrix, all 18 cells (gross R, no costs)

| Lane | wage | ext1.5 | ext2.0 | ext2.5 |
|---|---|---|---|---|
| lb30 | w0 | 349t +260.8 | 370t +284.1 | 378t +297.0 |
| lb30 | w24 | **265t +231.6** ✓ | 294t +248.2 ✓ | 304t +231.7 ✓ |
| A4 | w0 | 357t +272.4 | — | 387t +213.6 |
| A4 | w24 | 259t +272.8 | — | 289t +266.6 |
| OPT-cd0 | w0 | 515t +429.8 | — | 583t +396.6 |
| OPT-cd0 | w24 | 363t +372.0 | — | 425t +372.0 |
| OPT-cd10 | w0 | 452t +347.0 | — | 511t +375.6 |
| OPT-cd10 | w24 | 325t +397.6 | — | 382t +371.9 |

(✓ = externally validated cells. lb30 w24 ext3.0 = 307t +222.4 also validated.)

### 5.2 Phase C — fine matrix, all 18 cells (NET, funding-inclusive)

| Lane | wage | ext1.5 | ext2.0 | ext2.5 |
|---|---|---|---|---|
| lb30 | w0 | 349t **+196.3** DD23.6 | 369t +218.2 DD24.6 | 377t +231.1 DD24.6 |
| lb30 | w24 | 265t +185.0 DD19.4 * | 293t +197.2 DD23.6 ✓ | 303t +179.1 DD23.6 ✓ |
| A4 | w0 | 359t +203.3 DD24.8 | — | 390t +141.3 DD28.4 |
| A4 | w24 | 261t **+223.1** DD19.8 * | — | 292t +212.6 DD21.8 |
| OPT-cd0 | w0 | 515t +322.5 DD23.3 | — | 585t +290.0 DD25.0 |
| OPT-cd0 | w24 | 364t +301.6 DD27.7 | — | 426t +302.6 DD25.2 |
| OPT-cd10 | w0 | 453t +259.4 DD32.7 | *(exp41)* +269.2 DD27.1 | 512t +291.4 DD27.1 |
| OPT-cd10 | w24 | 326t **+337.7** DD19.2 | *(exp41)* +329.8 DD23.2 | 383t +315.5 DD22.2 |

✓ = cells reproducing the user's own quoted fine table **exactly**
(196.3 / 231.1 / 197.2 / 179.1 — 4/4, incl. trade counts 349/377/293/303).
\* = the two w24-ext1.5 cells where the DELETED harness's doc rows differ
(185.0 vs its 224.5; 223.1 vs its 228.6) — convention gap in the deleted code,
superseded by the user-matrix-validated gate; every other quoted cell is exact.
Bold = lane winners.

Key cross-lane reads (from these matrices):
* **w0 lanes want wide ext:** lb30-w0 196.3→218.2→231.1 and OPT-cd10-w0
  259.4→269.2→291.4 are both monotonic UP in ext.
* **w24 lanes want tight ext:** lb30-w24 185.0→197.2→179.1 (peak 2.0) and
  OPT-cd10-w24 337.7→329.8→315.5 (peak 1.5) — monotonic DOWN past the peak.
* **A4 ext2.5 is poison on w0** (141.3, −62R) — the mb10/chop55 window family
  fills the 1.5–2.5R band with top-buyers.

## 6. Results — exp41 (missing cells + walk-forward)

### 6.1 Phase 1 — OPT-cd10 ext sweep incl. the missing ext2.0 cells

| Config | coarse | fine (NET) | npt | DD |
|---|---|---|---|---|
| OPT-cd10 w0 ext1.5 | 452t +347.0 | 453t +259.4 | 0.573 | 32.7 |
| OPT-cd10 w0 ext2.0 | 475t +362.4 | 476t +269.2 | 0.565 | 27.1 |
| OPT-cd10 w0 ext2.5 | 511t +375.6 | 512t +291.4 | 0.569 | 27.1 |
| **OPT-cd10 w24 ext1.5** | 325t +397.6 | **326t +337.7** | **1.036** | **19.2** |
| OPT-cd10 w24 ext2.0 | 349t +392.6 | 350t +329.8 | 0.942 | 23.2 |
| OPT-cd10 w24 ext2.5 | 382t +371.9 | 383t +315.5 | 0.824 | 22.2 |

**Missing cell answered: ext1.5 stays king on the w24 lane.** The w24×ext curve
is cleanly monotonic NEGATIVE (337.7 → 329.8 → 315.5; npt 1.04 → 0.94 → 0.82),
while the w0 curve is monotonic POSITIVE (259.4 → 269.2 → 291.4). The two-knob
interaction is structural.

### 6.2 Phase 2 — segmented walk-forward (6 segs ≈ 225d each, fixed configs, fine NET)

| Config | NET | seg 1..6 | worst | max seg DD | H1/H2 |
|---|---|---|---|---|---|
| lb30 w0 e1.5 | +196.3 | −29.6 +76.7 +18.6 +20.8 +50.7 +59.2 | **−29.6** | 19.1 | 69.0/127.4 |
| lb30 w0 e2.5 | +231.1 | −31.1 +100.1 +24.0 +16.0 +70.4 +51.6 | **−31.1** | 22.9 | 95.2/135.9 |
| lb30 w24 e2.5 | +179.1 | −22.5 +86.0 −14.6 +17.5 +56.3 +56.4 | −22.5 | 23.6 | 50.0/129.1 |
| A4 w24 e1.5 | +223.1 | −1.1 +23.7 +22.0 +13.4 +56.0 +109.1 | −1.1 | 19.5 | 46.6/176.5 |
| OPTcd0 w0 e1.5 | +322.5 | +9.6 +109.3 +15.1 +10.5 +68.5 +109.5 | **+9.6** | 20.4 | 174.1/148.4 |
| OPTcd0 w24 e1.5 | +301.6 | −0.3 +83.4 +24.3 +15.1 +62.3 +116.7 | −0.3 | 22.4 | 147.5/154.1 |
| **OPTcd10 w24 e1.5** | **+337.7** | **+13.6 +91.9 +37.5 +21.4 +65.7 +107.6** | **+13.6** | **17.3** | **183.0/154.6** |
| OPTcd10 w24 e2.0 | +329.8 | +9.7 +87.4 +32.7 +16.5 +71.9 +111.6 | +9.7 | 20.6 | 168.6/161.3 |

WF reads:
1. **OPT-cd10 w24 ext1.5 is the champion on every axis**: highest NET (+337.7),
   zero losing segments (worst +13.6), lowest worst-seg DD (17.3), most balanced
   halves (183.0/154.6), best npt (1.04). Beats exp40c's lb30-ext2.5 "winner"
   by +106R AND in every single segment.
2. Only two configs have **no losing segment**: OPTcd10-w24-e1.5 and
   OPTcd0-w0-e1.5. Everything lb30-based bleeds −22…−31 in segment 1.
3. lb30's ext2.5 gain is back-loaded (H1 +95.2 vs H2 +135.9) and its worst
   segment gets WORSE with ext2.5 (−29.6 → −31.1).
4. w24's robustness claim holds on OPT-cd10 (+78R vs w0 twin, DD 32.7→19.2) but
   is neutral-to-negative on OPT-cd0 (w24 costs 21R, worst seg +9.6 → −0.3).
   w24 is base-dependent: it shines with cd10, not cd0.
5. A4 w24 e1.5 confirms as the conservative mid-lane: worst seg −1.1, strong
   back half (+109.1 in seg 6).

---

## 7. Verdicts, caveats, next steps

### 7.1 Verdicts

* **Do NOT kill w24 globally.** Kill it only where its twin beats it (lb30-w0
  ext2.5 lane). On OPT-cd10 it is the biggest single edge in the study.
* **ext rule:** w0 lanes → 2.5; w24 lanes → 1.5 (OPT-cd10) / 2.0 (lb30-w24).
* **New single best: OPT-cd10 + w24 + ext1.5 = 326t / +337.7 / DD 19.2 /
  worst-seg +13.6.** Production base (lb30 w0 ext1.5, +196.3) is beaten by
  ~+141R by it.
* If a simpler/safer change to production is wanted: lb30 + w0 + ext2.5
  (+231.1) is the smallest delta from current production but has the weakest
  WF profile of the leaders.

### 7.2 Honest caveats

* OPT knobs (mb10, chop55, persist2, mltf, cd) were selected IN-SAMPLE on the
  full period. exp41's WF tests fixed-config stability, not the selection
  process. Segment 1 (oldest data) is the closest OOS proxy: +13.6 for the
  champion.
* The two w24-ext1.5 cells (lb30 185.0, A4 223.1) carry the deleted-harness
  convention delta (its rows said 224.5 / 228.6); all other quoted cells are
  externally exact. The final gate is validated against the user's own coarse
  matrix (4/4) — the strongest available authority.
* All numbers are single-instrument (BTCUSDT_BYBIT), single cost model.

### 7.3 Next steps (natural continuations)

1. Nested walk-forward: re-pick OPT knobs per segment (tests the SELECTION
   process, complementing exp41's fixed-config test).
2. ~~cd sweep (0/5/10/15) × wage on the OPT family — is cd10+w24 a ridge or a
   spike?~~ — partially answered by exp42 from the wage side (18–36h band is
   flat-topped on OPT-cd10); the cd dimension itself remains open.
3. ext2.0 is SETTLED (Phase 1) — do not spend more cells there.
4. Cross-instrument sanity on the champion before any production talk.
5. (new, from exp42) — joint wage×ext cell on OPT-cd10 at w36h×ext2.0 (only
   1.5 was run at 36h; the w24 lanes peaked at 1.5–2.0).
6. (new, from exp42) — per-trade autopsy of the 12h cliff on A4 (what exactly
   is admitted at 12h that costs −93R vs 0h).

---

## 8. How to run

```powershell
# from repo root:
python -m py_compile live_stuff/tests/exp40c_wage_gate.py live_stuff/tests/exp41_wf_leaders.py live_stuff/tests/exp42_wage_sweep.py

# full exp40c: identity gate + Phase A validation (aborts on mismatch) + B + C
python live_stuff/tests/exp40c_wage_gate.py 1> live_stuff/tests/_exp40c_out.txt 2> live_stuff/tests/_exp40c_err.txt

# Phase A only (fast gate check):
$env:EXP40C_PHASE="A"; python live_stuff/tests/exp40c_wage_gate.py

# exp41: missing cells + walk-forward (reuses exp40c's BP/fund/run_coarse)
python live_stuff/tests/exp41_wf_leaders.py 1> live_stuff/tests/_exp41_out.txt 2> live_stuff/tests/_exp41_err.txt

# exp42: wage sweep + lb14 recheck + WF on sweep ledgers (triple gate)
python live_stuff/tests/exp42_wage_sweep.py 1> live_stuff/tests/_exp42_out.txt 2> live_stuff/tests/_exp42_err.txt
```

Runtime: exp40c full ≈ 2–3 min, exp41 ≈ 77s, exp42 ≈ 106s. If a gate prints
`MISMATCH` / `FAILED` (Phase A matrix in exp40c, matrix or fine pins in
exp42), the wage gate no longer matches the validated convention — STOP and
fix; do not read any sweep numbers.

---

## 9. One-line summary

`w24` and `ext_stop` are anti-synergistic knobs with opposite ext-optima per
wage lane (w0→wide, w24→tight); lb30's ext2.5 win is lane-specific and
back-loaded; **OPT-cd10 + w24 + ext1.5 (+337.7, DD 19.2, no losing WF segment)
is the new best**, and the rebuilt wage gate in `test_experiments_craze.py` is
externally validated 4/4 against the user's own matrix with an identity gate on
the shipped engine. **Exp 42 (§13):** the 24h point is noisy (±70R between
neighbors) — adopt the 18–36h wage band; DD/npt improve monotonically with
wage everywhere; robustness alternate is OPT-cd10 + w36h (+329.4, worst seg
+17.3, DD 18.4).

---

## 10. Independent verification (2026-09-19, second lane)

An independent verification pass was run by a second lane with its own test
script (`test_verify_wage.py`, since DELETED - see §12 rule 6) importing the
same `build_module()` from `test_experiments_craze.py`. Identity gate passed
(flags-off == shipped, n=351, exact R-list). The script itself is no longer on
disk; every number below was cross-checked against `_exp40c_out.txt` Phase C
and matches to the decimal - which is only possible with the same fine-fill
engine, the same identity-gated base case, and the same wage gate.

### 10.1 ext_stop verification - all 6 cells MATCH (fine NET, funding-inclusive)

| Config | ext | exp40c fine (§5.2) | Independent rerun | Status |
|---|---|---|---|---|
| lb30 w0 | 1.5 | 349t NET +196.3 | 349t NET +196.3 | MATCH |
| lb30 w0 | 2.5 | 377t NET +231.1 | 377t NET +231.1 | MATCH |
| A4 w0 | 1.5 | 359t NET +203.3 | 359t NET +203.3 | MATCH |
| A4 w0 | 2.5 | 390t NET +141.3 | 390t NET +141.3 | MATCH |
| OPT-cd10 w0 | 1.5 | 453t NET +259.4 | 453t NET +259.4 | MATCH |
| OPT-cd10 w0 | 2.5 | 512t NET +291.4 | 512t NET +291.4 | MATCH |

Both sides of every comparison are FINE (1m-fill) numbers - the rerun did use
precise 1m fills and the base case. (A bare-15m rerun cannot reproduce
1m-re-timed counts plus funding-inclusive NET to the decimal.)

### 10.2 Wage gate verification - all 5 cells MATCH (fine vs fine)

Comparison correction: an earlier draft of this table compared COARSE claimed
counts against FINE verified runs and reported "off by 1 trade". That was an
apples-to-oranges label - fine counts differ from coarse counts by design
(1m exit re-timing shifts busy/cooldown chains, §4.1). The correct comparison,
fine claimed vs fine verified:

| Config | exp40c fine (§5.2) | Independent rerun | Status |
|---|---|---|---|
| lb30 w24 ext1.5 | 265t NET +185.0 | 265t NET +185.0 | MATCH |
| lb30 w24 ext2.0 | 293t NET +197.2 | 293t NET +197.2 | MATCH |
| lb30 w24 ext2.5 | 303t NET +179.1 | 303t NET +179.1 | MATCH |
| lb30 w0 ext1.5 | 349t NET +196.3 | 349t NET +196.3 | MATCH |
| lb30 w0 ext2.5 | 377t NET +231.1 | 377t NET +231.1 | MATCH |

The three w24 rows also match the user's own quoted fine table (197.2 / 179.1),
which together with §4.2's coarse matrix makes the external validation
4/4 coarse + 4/4 fine on the final gate.

### 10.3 Deleted-harness N5 rows - non-authoritative (the honest version)

The original Exp40/41 harness was deleted after its run and its exact wage-age
convention is UNRECOVERABLE. Do not guess it and do not describe it - a first
draft here guessed "entry_ts - window_start with no raw-s correction", which is
identical to the current gate's formula and therefore cannot explain a
difference. That guess was wrong and has been removed.

What is known empirically (full audit trail in §4.3):
* 13+ candidate conventions were tested (raw-s, +2700/+3600 shifts,
  closed-candle, canonical flip-first parent, dir-blind, leg anchors, post-hoc
  ledger partitions). NONE reproduces the N5 rows (lb30+w24 275t/+224.5,
  lb14+w24 281t/+201.9, A4+w24 266t/+228.6).
* The current gate reproduces the user's OWN records exactly wherever they
  overlap: coarse matrix 4/4 (§4.2) and fine table 4/4 (§4.3).
* The N5 lb30 delta is large (rebuilt 265t/+185.0 vs claimed 275t/+224.5 =
  -39.5R) while the A4 delta is small (261t/+223.1 vs 266t/+228.6 = -5.5R).
  No tested convention explains the lb30 gap.

Therefore: N5 rows are NON-AUTHORITATIVE - not proven fraudulent, but
unreproducible from any code we can run, and contradicted by the only external
authority available (the user's own numbers). Never cite them as reference
values; the validated rebuild's output is the reference.

**Material consequence (read this):** the N5 message claimed "lb30+w24 =
+224.5, w24 works on all 3 bases (+28.2 on lb30)". Under the validated gate,
lb30-w24-ext1.5 is **+185.0 NET = w24 HURTS by -11.3R on that lane** (base
+196.3). w24 remains positive on A4 (+223.1 vs +203.3) and strongly positive on
OPT-cd10 (+337.7 vs +259.4). The corrected statement is "w24 is
base-dependent", not "w24 works on all bases".

### 10.4 Gate audit - no B3-style inflation

The ext_stop gate evaluates at the signal bar close (pre-fill), using the HTF
window's entry_price and risk - both closed-1h-candle values, knowable at
decision time. No forward-looking data enters the gate. The wage gate uses
`bar_ts - s` where `s` is the window's 1h entry-bar timestamp (closed candle)
- also causal. Both gates are ENTRY-only: they vote dead/alive at the signal
bar; SL/trail/exit logic never changes. No inflation bug found.

---

## 11. Updated verdicts after independent verification

§7.1 stands, now confirmed by a second lane:

1. **ext_stop 1.5→2.5 on lb30-w0 is LEGIT** - independently verified +34.8R
   NET to the decimal. Lane-specific: OPT-cd10-w0 ADOPT (+291.4 vs +259.4);
   OPT-cd0 REJECT (+290.0 vs +322.5); A4 REJECT (+141.3 vs +203.3); w24 lanes
   keep ext1.5 (lb30-w24 peaks at 2.0 = +197.2, still below w0-ext2.5).
2. **Wage gate implementation is correct** on current code - 5/5 fine match
   (§10.2) + 4/4 coarse matrix (§4.2) + 4/4 user fine table (§4.3).
3. **w24 is NOT dead globally.** OPT-cd10 + w24 + ext1.5 = +337.7 / DD 19.2,
   zero losing WF segments - overall champion. But on lb30 it is NEGATIVE at
   ext1.5 (§10.3 correction): base-dependent, not universal.
4. **Anti-synergy holds**: w0 → wide ext; w24 → tight ext. Never mix.

---

## 12. Standing rules for any bot/lane running experiments in this repo

1. **Reference numbers:** only outputs of the current, gate-validated rebuild
   (`exp40c`/`exp41` + `build_module()` from `test_experiments_craze.py`) may
   be cited. The deleted-harness N5 rows are dead - never use them as expected
   values (§10.3).
2. **Gates before results:** identity gate + Phase A external matrix must pass
   AND be printed before reading any experiment output. Abort on mismatch.
3. **Label the scoring mode on every number:** coarse-gross or fine-NET.
   Never compare a coarse claimed value against a fine verified value (this
   produced the bogus "off by 1 trade" rows in the first §10.2 draft).
4. **Fine means 1m fills + fee + slip + funding** via
   `fine_ltf=_load_fine_1m(...)`. Never a bare-15m re-sim with costs bolted
   on. If 1m data is unavailable, report coarse only and say so.
5. **Base case or nothing:** experiments run on the identity-gated base (BP);
   new knobs go through the `build_module()` patch list with an asserted
   anchor string. No engine forks, no silent param edits.
6. **Delete nothing:** harnesses, verify scripts, output logs all stay on
   disk. A verification nobody can rerun is worth nothing (test_verify_wage.py
   was deleted after producing §10 - do not repeat that).
7. **Every number in a doc cites its source file** (script + output log).
8. **Docs are UTF-8 clean.** Double-encoded punctuation is a bug; write
   ASCII-safe if unsure of the toolchain.
9. **Verdicts are lane-specific.** "X works" without naming the base lane is
   not a verdict.
10. **Champion claims need walk-forward** (exp41-style segmented WF, fixed
    configs). Full-sample NET alone is not adoption-grade.

---

## 13. Exp 42 — wage-threshold sweep + lb14 recheck (2026-09-20)

Source: `exp42_wage_sweep.py` → `_exp42_out.txt` / `_exp42_results.json`.
Gates all printed and passed: identity OK (n=351); user lb30-w24 coarse
matrix 4/4; 6 fine pins to exp40c Phase C 6/6. All numbers below: **fine
NET** (1m fills + fee + slip + funding), ext1.5, wage in hours.

### 13.1 Sweep (fine NET)

| wage | lb30 | A4 | OPT-cd10 | lb14 |
|---|---|---|---|---|
| 0h | +196.3 (349t, DD 23.6) | +203.3 (359t, DD 24.8) | +259.4 (453t, DD 32.7) | +148.0 (351t, DD 23.4) |
| 12h | +147.6 (305t, 27.1) | +110.1 (302t, 36.7) | +324.9 (395t, 26.4) | +151.2 (310t, 18.8) |
| 18h | +160.4 (282t, 22.3) | +217.8 (282t, 19.5) | +265.3 (354t, 24.8) | +160.5 (290t, 17.4) |
| 24h | +185.0 (265t, 19.4) | +223.1 (261t, 19.8) | +337.7 (326t, 19.2) | +193.7 (272t, 15.7) |
| 36h | +166.7 (234t, 21.8) | +203.3 (225t, 16.5) | +329.4 (292t, 18.4) | +187.7 (240t, 15.8) |
| 48h | +181.6 (194t, 17.1) | +201.9 (206t, 15.1) | +271.0 (249t, 19.7) | +146.3 (202t, 28.4) |

Argmax: lb30 = **0h**; A4 / OPT-cd10 / lb14 = **24h**.

### 13.2 Findings

1. **"Kill w24" is lb30-only.** On lb30 every wage value nets LESS than w0
   at ext1.5. On the other three lanes 24h is the peak — and lb14-w24 is now
   VALIDATED under the rebuilt gate: 272t +193.7 DD 15.7 (the deleted
   harness claimed 281t +201.9 DD 15.8 — nearly reproduced, unlike lb30's
   N5 row). The DD-king lane is real.
2. **The 24h point is not a smooth peak — the response is noisy.** OPT-cd10
   neighbors swing ±70R (12h +324.9 → 18h +265.3 → 24h +337.7 → 36h +329.4).
   A4 has a −93R cliff at 12h, then an 18–24h plateau. lb30: nothing beats
   w0. So the gate's DIRECTION is lane-dependent and the exact threshold is
   partly luck; read "24h" as "≈1 day, 18–36h band". What IS monotonic:
   npt and DD improve with wage on every lane (fewer, older, better trades —
   A4 DD 24.8→15.1, lb30 23.6→17.1, npt up to ~1.0+).
3. **WF (6 segs, fixed configs) — direction more robust than the point.**
   OPT-cd10: w24h worst seg +13.6, w36h worst +17.3, w12h worst +2.4 (all
   all-positive); 18h has a −25.7 seg; w0 worst −17.1. A4: w36h (+203.3,
   worst +3.3) and w48h (+201.9, worst +9.0) all-positive at much lower DD;
   w24h worst −1.1; w12h catastrophic (segs −37.2/−30.5, H1 −54.9). lb14:
   w36h worst −2.2, w24h −8.4.
4. **Robust picks (worst-seg + DD, not raw NET):**
   - Champion unchanged: OPT-cd10 w24h (+337.7, worst +13.6, DD 19.2).
   - Robustness alternate: OPT-cd10 w36h (+329.4, worst +17.3, DD 18.4).
   - A4 robust: w36h (+203.3 = w0's NET, worst +3.3, DD 16.5 — zero losing
     segments at w0's profit level with 8 points less DD).
   - Sleep-well: lb14 w24h (+193.7, DD 15.7) or w36h (+187.7, DD 15.8).
5. **12h is the one threshold to rule out** (A4 −93R, lb30 −49R; only
   OPT-cd10 likes it). If a partial gate is ever shipped, it must be ≥18h.

### 13.3 Verdict deltas vs §11
* §11.3 refined: w24 is base-dependent AND threshold-noisy — 24h is argmax on
  3/4 lanes but ±70R of noise separates neighbors; adopt the BAND (18–36h),
  not the point.
* lb14 added to the validated lane set (previously it existed only in the
  dead N5 doc rows).
* lb30 verdict stands: no wage gate at ext1.5; ext2.5 is lb30's edge.

---

## 14. Exp 44 — curfew gate: skip only 6–24h, keep 0–6h + ≥24h (2026-09-20)

**Origin:** exp43's age profile (EXP43_LOSS_AUTOPSY.md §2.3): the LTF loss
pocket is the **6–24h** band; w24 is a blunt tool that also cuts lb30's good
0–6h pocket (+3.1R/31t, avgR +0.10). New knob `exp_curfew_a/b` in the craze
patcher — skips only `a ≤ age < b` (no-op when b=0; identity-gated).

**Harness:** `live_stuff/tests/exp44_curfew_gate.py` → `_exp44_out.txt` /
`_exp44_results.json` (≈75s). Gates: identity + user coarse matrix + 8 fine
pins (all passed); curfew canary: **0 in-band violations** on all runs.
Run: `python live_stuff/tests/exp44_curfew_gate.py 1> live_stuff/tests/_exp44_out.txt 2> live_stuff/tests/_exp44_err.txt`

### 14.1 Results (fine NET, ext1.5)

| variant | lb30 | A4 | lb14 | OPT-cd10 |
|---|---|---|---|---|
| w0 | +196.3 (DD 23.6) | +203.3 (DD 24.8) | +148.0 | +259.4 (DD 32.7) |
| w24 | +185.0 (DD 19.4) | **+223.1** (DD 19.8) | **+193.7** (DD 15.7) | **+337.7** (DD 19.2) |
| **curf6-24** | **+217.4** (296t, DD 26.8) | +198.8 (DD 19.0) | +188.7 (DD 17.1) | +302.6 (DD 25.0) |
| curf6-30 | +163.9 (DD 32.8) | +202.4 (DD 16.1) | +160.9 | +273.9 |

### 14.2 Verdicts

1. **Curfew wins exactly where the U-curve predicted — lb30 only:**
   +217.4 = +21.1 over w0 and +32.3 over w24. New best lb30-based single,
   WITHOUT touching ext (and it keeps the first-6h entries). DD caveat:
   26.8 vs w0's 23.6 — it buys NET with slightly deeper DD.
2. **On A4 / lb14 / OPT-cd10 plain w24 stays best** — the overall champion
   (OPT-cd10 + w24 + ext1.5, +337.7) is unchanged. The age structure the
   curfew exploits is lane-shaped, as exp43 said.
3. **Band edge confirmed:** curf6-30 is worse everywhere → the 24–30h band
   earns its keep; 24h is the right lower edge. On A4, curf6-30 (+202.4,
   DD 16.1, worst seg +3.9) ≈ ties A4-w36h as a robust alternative.
4. **WF:** lb30 curf6-24 worst seg −28.1 (still bleeds the oldest data, but
   H1 improves +69.0 → +85.9 vs w0). lb14/OPT curfew variants are dominated
   by w24 in both NET and WF.
5. **Canary:** 0 in-band violations on all 8 curfew runs — knob verified.

**Single-position board update:** lb30+curf6-24 slots in at #3 by NET
(+217.4), still behind A4+w24 (+223.1) on risk-adjustment and A4-w36h on
consistency. Champion (multi) unchanged.

---

## 15. Exp 45 — curfew edge-plateau map + curf×ext combo (2026-09-20)

**Harness:** `live_stuff/tests/exp45_curfew_plateau.py` → `_exp45_out.txt` /
`_exp45_results.json` (≈80s). Gates: identity + user coarse matrix + 6 fine
pins (incl. lb30 w0/w24 at BOTH ext values); canary 0 in-band violations on
all 9 curfew cells.
Run: `python live_stuff/tests/exp45_curfew_plateau.py 1> live_stuff/tests/_exp45_out.txt 2> live_stuff/tests/_exp45_err.txt`

### 15.1 lb30 edge grid (fine NET, 296t-scale cells)

| lower \ upper | skip→24 | skip→30 | skip→36 |
|---|---|---|---|
| skip from 4 | +172.0 (DD 21.8) | — | — |
| skip from 6 | **+217.4** (DD 26.8) | +163.9 | +161.9 |
| skip from 8 | **+219.4** (DD 28.6) | — | — |
| (w0 / w24 refs) | +196.3 / +185.0 | | |

### 15.2 The combo — killed

lb30 c6-24 + ext2.5 = **+215.0** < lb30 w0 + ext2.5 = +231.1 (−16.1).
**The two lb30 edges do not stack** — consistent with exp43's mechanism
finding: both act through entry re-timing, and their chain effects conflict.

### 15.3 Verdicts

1. **Lower edge has a small plateau: 6–8h** (c6-24 +217.4, c8-24 +219.4 —
   statistically indistinguishable). c4-24 collapses (+172.0) — the 4–6h
   trades are real money.
2. **Upper edge is pinned at 24h by mechanism, not tuning:** widening the
   band to 30/36 costs ~−54R because the ≥24h bucket is where the good
   trades live (exp43 age profile: avgR +1.16/+1.23). Same structure as the
   ext ceiling (2.5 optimal, 3.0 adds nothing): the parameter is bounded by
   the measured age profile, not picked off a spike.
3. **A4:** c4-24 is bad (+166.9, seg3 −41.4, H1 −7.1); A4's best remains
   w24 (+223.1). c6-30 (+202.4, DD 16.1, worst seg +3.9) confirmed as the
   A4 robustness alternative alongside w36h.
4. **Combo killed** — do not combine curfew with ext2.5 on lb30.
5. **Single board after exp45:** A4+w24 (+223.1/DD 19.8) balanced king;
   lb30+w0+ext2.5 (+231.1) raw king; lb30+c6-24 (+217.4) third — all three
   remain in-sample-selected (§7.2 caveat stands).

---

## 16. Exp 46 — deferred entry: requeue young signals instead of dropping (2026-09-20)

**Harness:** `live_stuff/tests/exp46_defer_entry.py` → `_exp46_out.txt` /
`_exp46_results.json` (≈86s). Gates: identity + user coarse matrix + 6 fine
pins (all passed); defer canary: 0 age<horizon violations on all 9 defer runs.
Run: `python live_stuff/tests/exp46_defer_entry.py 1> live_stuff/tests/_exp46_out.txt 2> live_stuff/tests/_exp46_err.txt`
(Audit note: first launch crashed on an `exp_stop_r` typo in the emitted
patch — fixed, relaunched clean; both runs are in `_exp46_err.txt` history.)

**Mechanism (new knob `exp_defer_h` in the craze patcher):** a signal with
window-age < horizon is NOT dropped — it is requeued to the first 15m bar at
/after `s + horizon` provided, all known at the defer bar (causal): the SAME
window is still open, the original SL pivot was never touched between signal
and defer bar (setup survived), and ext still passes. Entry at the defer-bar
close; busy/cooldown/halt apply there. `filtered` is re-sorted by final bar
so the ledger stays causal (no-op when off; identity-gated).

### 16.1 Results (fine NET, ext1.5)

| variant | lb30 | A4 | lb14 |
|---|---|---|---|
| w0 | +196.3 (DD 23.6) | +203.3 (DD 24.8) | +148.0 |
| w24 | +185.0 (DD 19.4) | **+223.1** (DD 19.8) | **+193.7** (DD 15.7) |
| defer6 | +183.8 | +209.0 (worst seg **+7.7**) | +151.7 |
| defer12 | +198.6 | +206.5 (worst +7.0) | +145.9 |
| **defer24** | **+203.1** (DD 21.6) | +183.1 (DD 29.4) | +181.6 (DD 17.6) |
| (refs from exp44: curf6-24) | +217.4 | +198.8 | +188.7 |

### 16.2 Verdicts

1. **defer24 beats w24 by +18.1R on lb30 (+203.1 vs +185.0) at the SAME
   24h horizon** — the RQ2 answer: "wait a day, enter if the setup is still
   alive" > "drop everything young". This directly confirms exp43's
   mechanism finding: the gate's value is timing, not removal; deferral
   keeps the trigger AND buys the timing.
2. lb30 timing-config ranking now: **curf6-24 (+217.4) > defer24 (+203.1) >
   w0 (+196.3) > w24 (+185.0)**. lb30-d24's WF worst seg (−20.3) is the best
   of the lb30 timing variants (w0 −29.6, w24 −22.5).
3. **A4: w24 stays king (+223.1)** — deferral is a consistency tool there:
   A4-d6 (+209.0, worst seg **+7.7**) is the best worst-segment of ANY A4
   variant so far (w0 +4.3, w24 −1.1), at lower NET.
4. **lb14: w24 stays king** (+193.7); defer24 (+181.6) below it.
5. **Canary 0 violations everywhere** — the requeue mechanism is internally
   consistent; no trade sits below its horizon.
6. Champion (multi, OPT-cd10+w24+ext1.5, +337.7) unchanged. The two new
   knobs (curfew, defer) are lane-shaped tools, consistent with everything
   since exp43: entry-timing structure is real but lane-specific.

---

## 17. Exp 47 — full stats board: gross/net/avgR/DD/WR + per-year NET + delta vs anchor (2026-09-20)

**Harness:** `live_stuff/tests/exp47_yearly_stats.py` → `_exp47_out.txt` /
`_exp47_results.json` (≈60s). Gates: identity + user coarse matrix + 5 fine
pins (all passed). Run: `python live_stuff/tests/exp47_yearly_stats.py 1> live_stuff/tests/_exp47_out.txt 2> live_stuff/tests/_exp47_err.txt`

| Config | n | gross | cost | NET | npt | DD | WR | 2023 | 2024 | 2025 | 2026 | d(anchor) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ANCHOR lb30 w0 e1.5 | 349 | +287.1 | 90.8 | +196.3 | 0.563 | 23.6 | 29.8% | +22.6 | +121.4 | +52.1 | +91.0 | — |
| lb30 curf6-24 e1.5 | 296 | +295.7 | 78.2 | +217.4 | 0.735 | 26.8 | 32.1% | +26.7 | +130.4 | +57.2 | +81.2 | +21.1 |
| lb30 defer24 e1.5 | 286 | +280.1 | 77.0 | +203.1 | 0.710 | 21.6 | 31.1% | +14.2 | +120.3 | +59.7 | +85.4 | +6.8 |
| lb30 w0 ext2.5 | 377 | +323.3 | 92.1 | +231.1 | 0.613 | 24.6 | 31.0% | +22.7 | +146.3 | +69.3 | +84.9 | +34.8 |
| A4 w24 e1.5 | 261 | +297.7 | 74.6 | +223.1 | 0.855 | 19.8 | 27.6% | +41.3 | +76.4 | +54.0 | +126.2 | +26.8 |
| A4 curf6-30 e1.5 | 277 | +277.5 | 75.1 | +202.4 | 0.731 | 16.1 | 26.4% | +46.6 | +55.8 | +55.9 | +119.1 | +6.0 |
| A4 defer6 e1.5 | 347 | +297.1 | 88.1 | +209.0 | 0.602 | 23.3 | 25.9% | +56.8 | +75.2 | +51.0 | +113.9 | +12.7 |
| lb14 w24 e1.5 | 272 | +268.8 | 75.1 | +193.7 | 0.712 | 15.7 | 31.6% | +40.1 | +85.5 | +59.0 | +84.1 | −2.7 |
| OPTcd10 w24 e1.5 (multi) | 326 | +423.5 | 85.8 | +337.7 | 1.036 | 19.2 | 32.5% | +100.3 | +124.7 | +79.7 | +119.1 | +141.3 |

cost = fee + slip + funding. Year = calendar year of trade ENTRY.

**Per-year reading (the advisor's "classify the environment" test):**
* **lb30 family is 2024-dependent:** anchor gets 43% of its NET from 2024;
  ext2.5 pushes that further (+146.3 in 2024). 2023 is its weak year (+22.6).
* **curf6-24/defer24 keep the lb30 shape** (2024-heavy) — they fix the entry
  pocket, not the regime dependence.
* **A4 family is the balanced one:** A4-w24's biggest year is 2026 (+126.2),
  not 2024; A4-curf6-30 is almost flat 2023–25 (46.6/55.8/55.9); A4-defer6
  has the strongest 2023 of the board (+56.8).
* **lb14-w24 is the most even of all** (min year +40.1, max +85.5).
* **The multi champion is balanced AND big** (+100.3/+124.7/+79.7/+119.1 —
  min year +79.7 beats most configs' max) — that consistency is a large part
  of why it's the overall king.

---

## 18. Exp 48 — price-space autopsy + leg-progress gate (2026-09-20)

**Origin:** user hypothesis — everything so far gates on TIME from window
start (wage/curfew/defer); 2023 (~20k BTC) vs 2024 (~100k) suggests testing
the PRICE-space axis instead. Definitions (all causal): leg anchor = first
window of the current same-direction streak (all past windows); leg progress
R = (signal close − leg anchor)·d ÷ current window risk; pullback = distance
off the leg extreme at entry, in the same units.

**Harness:** `live_stuff/tests/exp48_leg_progress.py` → `_exp48_out.txt` /
`_exp48_results.json` (≈83s; v2 — v1 had a nested-loop bug, documented below).
Gates: identity + user coarse matrix + 4 fine pins (all passed); legskip
canary 0 violations on all 10 cells.
Run: `python live_stuff/tests/exp48_leg_progress.py 1> live_stuff/tests/_exp48_out.txt 2> live_stuff/tests/_exp48_err.txt`

### 18.1 Autopsy (RQ1) — the price-space map is BIMODAL

| leg progress | lb30 n / avgR | A4 n / avgR |
|---|---|---|
| < −1R (leg fighting) | 200t / **+0.75** | 193t / **+1.20** |
| −1R … +20R | **EMPTY** | **EMPTY** |
| ≥ 20R (leg ran) | 148t / **+0.92** | 165t / +0.39 |

Pullback (A4): off leg high 0.5–1.5R → avgR **+2.46** (86t); 1.5–3R →
**−0.54** (24t); <0.5R → +0.34. lb30: 0.5–1.5R → +1.19; 1.5–3R → +0.12.

**Leg progress has NO middle** — legs either collapse against their direction
(and the windows keep re-printing that dir at lower/higher prices → those
entries still average +0.75/+1.20) or they run ≥20 window-risks. There is no
"moderately late leg" population to filter.

### 18.2 Gate cells (RQ2) — legskip is DEAD

All five thresholds (4/6/8/10/12) produce IDENTICAL ledgers (the bimodality
made them so): lb30 209t +93.6 (vs w0 +196.3 = **−102.7R**); A4 198t +78.7
(vs w0 +203.3 = **−124.6R**). Skipping ≥20R-leg entries removes the RIDE —
in a trend-following system, late legs ARE the profit engine. The exact
opposite of the time-space curfew, which worked because the 6–24h band is
decision noise.

### 18.3 Verdicts

1. **legskip: REJECTED on both lanes.** Price-space lateness is the edge,
   not the enemy. (Also empirically: threshold within 4–12 is irrelevant —
   further evidence of bimodality, not of a tuning surface.)
2. **New structural fact:** same-dir window streaks are bimodal in
   price-space (fighting vs running), with zero middle. Any future price-
   relative gate must target the pullback axis, not the progress axis.
3. **Untested follow-up candidate (causal):** an A4 pullback gate — skip
   entries 1.5–3R off the leg extreme (the no-man's land, avgR −0.54, only
   24t). Small n; needs the same pre-fill + WF discipline before any claim.
4. **Process note:** v1 of this harness had a nested-loop bug (autopsy
   re-binned its own output in an infinite loop); caught by watching the
   output grow, process killed, harness rewritten (v2), bug documented here.

### 18.4 How to run

```powershell
python live_stuff/tests/exp48_leg_progress.py 1> live_stuff/tests/_exp48_out.txt 2> live_stuff/tests/_exp48_err.txt
```

---

## 19. Cross-lane audit reconciliation (2026-09-20, second engine lane)

The second lane ran a 12-check deep audit of its own harness (`exp_final_matrix.py`,
its own engine variant WITH partial exits - a knob our engine does not have)
against this lane's craze patcher. Outcome:

* **Their `_build_full()` was missing 4 patches** from `test_experiments_craze.py`:
  `exp_wage_h`, `exp_curfew_a/b`, `exp_legskip_r`, and the post-filter
  `filtered.sort()`. Every w24/curfew config in their matrix was silently wrong
  (wage gate never applied - 127 extra trades on the OPT config).
* **Our numbers CONFIRMED by them:** they ran our exact `build_module()` and
  reproduced 326t / +337.7 for OPT-cd10 + w24 + ext1.5. Our pins hold on their
  environment too.
* Their own champions (atr_high + p7.5 + ext3 + cd8 single +261.5; mltf+persist7
  multi +465.1) do NOT use wage/curfew - unaffected by their bug. NOTE: those
  configs run on their engine variant (partial exits, atr_high mode, ext3) -
  numbers between the two engine variants are NOT directly comparable until the
  engines are unified.
* Their audit of shared mechanics agrees with ours: identity, partial-exit math,
  mltf concurrency, persist causality, ext causality, fine-fill timing - all PASS.

**Decision (coordination):** single source of truth for the shared patcher =
`test_experiments_craze.py::build_module()`. The second lane imports it instead
of maintaining a drifting copy (their copy had silently diverged - exactly the
failure mode SS12 rule 5 exists for). Lane-unique knobs (partial exits etc.) get
ported into the craze patch list as asserted patches so ONE identity gate covers
ALL knobs. Cross-lane rule: before comparing any number, both lanes must match
on the identity baseline (n + R-list) AND the data snapshot.

---

## 20. Exp 49 - partial exits ported + champions reproduced + WF verdict (2026-09-20)

**Harness:** `live_stuff/tests/exp49_partial_champion.py` -> `_exp49_out.txt` /
`_exp49_results.json` (~38s). The second lane's engine variant has partial
exits; ported verbatim into the craze patcher as `exp_partial_r` (default 0.0,
identity-gated): 50% off at exact level fill when best-R reaches the threshold
(coarse AND fine loops - with fine fills the coarse loop is empty, the fine
check is the live one); remainder runs the SAME swing trail half-weighted:
`r = partial_r + (total_move/risk)*0.5` (total move from ENTRY, per their
clarification). Per-trade state init added on our side (their spec omitted it -
without it `_partial_taken` leaks between trades).

Gates all passed: identity n=351 (no-op proof), user coarse matrix 4/4
(incl. two NEWLY measured coarse cells: A4 w24 ext1.5 = 250t/+207.1, ext3.0 =
285t/+218.8), R-formula canary 0 failures on 104 partial trades.

### 20.1 Champions on OUR data - exact reproduction of their claims

| Config | n | NET | npt | DD | partials | worst6 | years (23/24/25/26) |
|---|---|---|---|---|---|---|---|
| champion single sw20 | 371 | +261.5 | 0.705 | 29.3 | 42 | **-23.9** | 32.5/87.5/133.6/98.8 |
| champion single sw10 | 395 | +238.4 | 0.604 | 16.0 | 38 | -3.2 | 40.8/90.8/94.6/109.0 |
| **champion multi sw20** | 487 | +465.1 | 0.955 | 21.9 | 62 | **+1.9** | 127.8/139.5/185.7/127.0 |
| **champion multi sw10** | 501 | **+472.9** | 0.944 | **14.5** | 60 | **+22.7** | 136.2/121.2/191.7/144.4 |
| baseline (no partial) sw20 | 371 | +148.2 | 0.400 | 37.3 | 0 | - | 14.6/78.8/66.6/79.0 |
| baseline (no partial) sw10 | 394 | +163.6 | 0.415 | 29.2 | 0 | - | 33.2/106.0/46.9/73.1 |

Engine unification CONFIRMED: their +261.5/+465.1 claims reproduce to the
decimal on our data + our patcher. The 340t-vs-351t identity difference is
their BASE params (their env), not data drift - the champion configs converge
exactly.

### 20.2 Verdicts

1. **Partial exits are the biggest single edge found in the entire program:**
   +113.3R (single) / +309.3R (multi sw10) over the no-partial baseline of
   the same config - by harvesting 7.5R+ runners at half-size instead of
   trailing them back.
2. **NEW OVERALL KING: champion multi sw10** (+472.9 / DD 14.5 / worst seg
   +22.7 / min year +121.2) - beats the old champion (OPT-cd10+w24+ext1.5,
   +337.7 / DD 19.2 / worst +13.6) on every metric simultaneously.
3. **NEW single king (risk-adjusted): champion single sw10** (+238.4 / DD
   16.0 / worst -3.2 / NET+DD 14.9) - beats A4+w24 (+223.1/DD 19.8, ratio
   11.3) and lb30+ext2.5 (+231.1) on both NET and stability. sw20 variant is
   the raw king (+261.5) but bleeds seg1 (-23.9).
4. **sw answer (their Q2):** sw20 for raw single (+23.1 over sw10), sw10 for
   multi (+7.8) and for stability (worst segs -3.2/+22.7 vs -23.9/+1.9).
5. **Caveats:** (a) partial second-fill fee+slip not yet in `_trade_costs`
   (~0.02R per partial trade, ~1R total - champion NETs slightly generous);
   (b) partial trades book r>0 by construction -> halt3 never fires on them
   (intended behavior of the ported formula, now documented); (c) all
   in-sample, single instrument - the standing caveats.

### 20.3 How to run

```bash
# Via new registry (recommended):
python live_stuff/tests/run_experiment.py champion_multi_sw10
python live_stuff/tests/run_experiment.py --group champions
python live_stuff/tests/run_experiment.py --all

# Direct (legacy):
python live_stuff/tests/exp49_partial_champion.py
```
