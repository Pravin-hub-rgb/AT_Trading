# DOC MAP — what was already measured before logs 109–113

**Written 2026-09-27.** Not a conclusion, not a recommendation. An index of the
work that already existed in `backtest/docs/` and was not read during logs
109–112.

**Why this file exists:** four consecutive logs produced new nulls while a
measured, causality-audited candidate stack sat unopened in the repo. That is a
reading failure, not a research failure. This is the fix — the map first, the
experiment second.

---

## The headline: five things were already done and left default-off

| # | candidate | mechanism | champion IS | champion OOS | status |
|---|---|---|---|---|---|
| 1 | **STACK** = `half+delay1+skipD` | exit-side trail + decisive skip | +429.6 | **+110.5** | reproduces 24/24 (log 113) |
| 2 | **wick gate** | GRAY, short-only, `wick_atr12 < 6.026` on 1h | +28.1 | +19.8 | 4/4 parity, forward gate 5/50 |
| 3 | **win-streak N3** | block entries after 3 global wins | +331.7 | **+90.0** | flat-book PASS, **stack-book FAIL** |
| 4 | **M2 sizing** | 1.5× on `cur_mag_atr >= 3` | +152.7 | +29.1 | **bridge FAILED** (46.5% vs 95% bar) |
| 5 | **Z flags A/B/C** | 1.5× on one regime flag | — | — | sizing-only, 3/4 correlated |

Logs 109–112 produced **0** candidates. These five existed the whole time.

---

## 1. The Stage-B stack book

Exit-side, not entry-side. `exp_trail_half=1` + `exp_trail_delay_r=1.0` +
`exp_skip_decisive=1`. "Prove it first, then trail."

champion IS +325.8 → **+429.6**; OOS +70.2 → **+110.5 (+57%)**; OOS DD
53.2 → **30.6 (−42%)**. Causality-audited (Stage 19 / CHECKLIST 24.24): strict
prev-bar MFE gate gives identical numbers.

**Destroys age10**: OOS +43.2 → −0.3. Multi-only. Reproduced 24/24 in log 113.
Full writeup in `STACK_BOOK.md`.

## 2. The wick gate — this is the "gray trade" mechanism

`WICK_1H_GATE_ADOPTION_RECORD.md`, pinned to source so it cannot drift:

```
predicate : SHORT trades only
feature   : wick_atr12, on the 1-HOUR plane
formula   : (Σ wick over 12 closed 1h bars) / ATR14_1h[j]
cutoff    : j = bisect_right(ts_1h, entry_ts + 900 - 3600) - 1
threshold : wick_atr12 < 6.026   (STRICT '<')
action    : GRAY - trade runs to completion, P&L suppressed, r = 0
```

Evidence: **+28.1 / +25.7 / +19.8 / +23.8R** (champ IS, uts IS, champ OOS,
uts OOS). 4/4 parity asserted. **0.00 cascade.** 6/6 seq-identical. 6/6
ex-best-trade robust. Window 5.0–5.4 | 5.6–6.4 (hole at 5.5). Cliff 6.4→6.5.

**Single blocker: forward gate 5/50.** Nothing else outstanding.

Critical implementation note: the trade must book `r = 0` **while still setting
`busy_until`, cooldown and the streak**. Gating the cooldown is a bug that
shipped in three harnesses and produced a spurious −44R written up as a
structural property of gray mode before being retracted (`CAPITAL_STAGE_PLAN.md`
a11).

Also: costs are deducted on gray trades in-harness but not live — that gap is
`cost_relief` (+17.6R on is/champion). Compare live numbers.

## 3. Win-streak N3 — `WIN_STREAK_STACKING_AUTOPSY.md`

`global_soft_n3` = after 3 completed global wins, block new entries in the
current parent HTF window.

## 4. M2 and the sizing queue

All five queue candidates (M2, sMZX, uMZX, ramp_mag, count_linear) PASS 6/6
backtest; M2 and uMZX also PASS 6/6 cross-venue on Binance. sMZX on the
champion stack book: 429.6 → 802.8 IS / 110.5 → 277.7 OOS.

**All five are blocked.** `cur_mag_atr = |seg.end_px - seg.start_px| / atr15`
uses `end_px`, which `backend_check_wd_days.py:108` shows is **forward-looking**
(FS/SUS confirms at or after the end bar). Order-send-time agreement: **46.5%
against a 95% bar.**

`exp_m2_sendtime_feature.py` then built send-time-computable replacements
(`mag_so_far`, `ramp_so_far`) and re-ran the 6-cell rule. Result: **"NO
send-time replacement clears 6/6. A new feature would be needed, not a
reparameterisation."** Both dead ends documented.

`M1` (`cur_start <= 1`) must never be adopted — flags 71–88% of trades, a
leverage trap, and its flagged avgR is *worse* in key cells.

## 5. Z flags — `REGIME_STRUCTURE_AUTOPSY.md`

Z1 swept 24 regime features; **3 survived**: `er50 <= 0.0767`,
`wick_gt3x_pct12 > 33.3`, `vol7_prev7 <= 0.846`.

Sizing-only. A/B/C are **one correlated family** (all mark the same quiet tape,
overlapping heavily) — deploy at most one.

**The volume gate is RETRACTED for adoption**: post-process said PASS, path-true
rerun **FAILED 3/6** and champion OOS **sign-flipped** (+3.6 → −4.6). Only sizing
flags survive.

## 6. `CAPITAL_STAGE_PLAN.md` a8–a10 — the SL-width family

### a8 — wide-SL sizing: **REFUTED**
"bigger SL ⇒ higher success rate" is **partly real** — OOS wide-SL trades win
35.0%/37.8% vs 20.9%/21.4% narrow. But **avgR runs the other way in 5 of 6
cells**, at the 0.0th percentile against a matched-count random null.
*"Win rate without R is not an edge."*

### a9 — SL-width ladder: the tightest band is the whole edge

| sl_width % | n | avgR | WR | net |
|---|---:|---:|---:|---:|
| **0.00–0.25** | **54** | **+7.871** | 31.5% | **+425.0** |
| 0.25–0.40 | 118 | +2.192 | 27.1% | +258.6 |
| 0.40–0.55 | 129 | +0.903 | 15.5% | +116.5 |
| 0.55–0.70 | 178 | +0.465 | 34.3% | +82.8 |
| 0.70–0.90 | 178 | +1.277 | 33.7% | +227.4 |
| 0.90–1.20 | 293 | +0.091 | 22.5% | +26.6 |
| 1.20–1.60 | 254 | +0.461 | 32.7% | +117.0 |
| 1.60+ | 488 | +0.082 | 35.9% | +40.2 |

**1.7% of trades carry +425R at avgR 7.9.** The runner is a *tight-stop* runner;
width is the enemy. Not monotonic, and the two deepest bands hold only 172
trades, so a gate either removes the losers or throws away the book.

### a10 — the 3%+ gray gate
Fine SL ladder: **3.00–5.00 = −8.4R, 5.00+ = −13.3R**, negative in the aggregate
and 5 of 6 cells. 3%+ is worth ≈ **−21R** — too small to matter and pointing the
wrong way. Damage starts at 3%, not 2%. `exp_sl_width_gate.py` gray run:
**0 of 36 arms pass.**

### a11 — the bug that contaminates both of the above
The first gray pass patched the engine with

```python
if cooldown_bars > 0 and r_multiple < 0 and not _isgray:
```

i.e. it **suppressed the cooldown for gray trades**. That is backwards — a gray
trade still happens, holds its slot, advances the loss streak and should start
its cooldown like a real loss. The suppression shifted the timeline, let worse
trades in, and produced a spurious −44R that was written up as a structural
property of gray mode and then **retracted**.

**"The same suppression is present in `exp_sl_width_gate.py` and
`exp_sl_fine_cascade.py` and their conclusions about gray mode are affected too
— re-run before quoting them."**

The a9 and a10 gray conclusions are therefore **flagged as needing a re-run**.

## 7. Descriptive findings that are not gates

- **`LOSS_AUTOPSY.md`**: zero winners exit in <48 bars. The 12–24h window zone
  is toxic (WR 10.0%, −27.0R); 48h+ carries +225.3R. 10 monster trades (>10R)
  produce **49.1% of gross wins**. MFE giveback of 224.8R is the *cost* of
  letting winners run — trail tightening was tested and rejects, killing 155.3R
  of >10R wins.
- **`WINNER_PATH_AUTOPSY.md`**: retest-at-entry capture is **already 100%**
  (150/150 winners touched ≤entry before +0.5R, 0 missed R). Spent.
- **`MARGINAL_PREENTRY_ATLAS.md`**: champion OOS `first` entries = **−12.5R
  (PF 0.92)**; `green add-on` = **+42.2R (PF 2.08)**. Same on BASE multi and
  utcsat. Red add-ons were also profitable so blocking them fails, but
  **first-vs-add-on is the strongest recurring portfolio split in the repo**,
  and it is on the shipped multi lanes.
- **`FIVE_MINUTE_OPPOSITION_AUTOPSY.md`**: 5m opposition at entry is *not* a
  negative signal (often better). All 30 post-MFE exit counterfactuals lose.
- **`FIVE_MINUTE_MARK_MORPHOLOGY_AUTOPSY.md`**: the `none` cohort (no post-entry
  5m structure) is strongly negative everywhere, −1.19 to −1.32 avgR, both eras.
  Descriptive — post-entry information only.
- **`MB_ARCHITECTURE_AUTOPSY.md`**: MB50 remains stable; every alternative gains
  OOS and loses IS.
- **`SL_RECLAIM_REENTRY.md`**: dead 8/8. *"Reclaim/confirmation triggers on this
  engine have now failed 4/4 times."*

## 8. The rules the docs encode about *how* to test

- **Post-process removal = UPPER BOUND, never adoptable.** Wick gate: +28.1R
  post-process → −50.5R path-true (−78.6R cascade at 280% of the direct
  effect). Z3 vol gate: +3.6R → −4.6R sign flip. GRAY exists to avoid
  refilling the slot.
- **A matched random null passes `curve_better` in essentially every cell**
  (24.87 mechanism, confirmed 3×). dNet+curve alone cannot certify a sizing
  feature.
- **Nested thresholds are one cohort, not N observations.**
- **Windows must be reported as blocks**, with the holes shown.
- **Check the timeframe before believing any wick number** — the 15m-ATR wick
  gate and the 1h-ATR wick gate share a name, differ in formula and cohort, and
  have *opposite sign*. Every "wick gate is dead" verdict in the repo was
  measured on the 15m one.
- **A control failure is an abort, not a footnote.**

## 9. The binding constraint on everything

`FORWARD_TEST_PLAN.md` / CHECKLIST 24.70: **forward n = 5/50**, pre-registered.
Study 2 (deflated statistics) splits by era: **IS passes the deflation test, OOS
fails it.**

Every candidate above is blocked on the same number. No backtest clears it. It
accrues passively.

That is an open, specific, already-diagnosed task.


champion IS +325.8 → **+331.7**, OOS +70.2 → **+90.0**, PF 1.59 → 1.74, DD
53.2 → **43.2**, R/trade 0.251 → 0.343, **OOS 10R+ tail preserved (6)**.

**But `exp_n3_stack.py` (CHECKLIST 24.84): the endorsement does NOT transfer to
the stack book.** `stack+global_soft_n3` IS dNet **−29.7** on champion, and
negative on **all three** stack lanes. IS blocks explode 17 → 56.

So N3 and STACK are **mutually exclusive candidates**, not stackable.
