# HANDOVER — the `_dts` collision in the engine patcher, and what is still open

**Date:** 2026-09-29 · **Branch:** `experiments/v19-plus`
· **Written because the next agent needs the root cause, not the symptoms.**

---

## 1. The bug that cost this session ~15 runs

`backend/src/btc/engines/htf_ltf/v18_streak_halt.py:314`

```python
import datetime as _dts          # <-- the ENGINE already owns this name
```

**Any experimental kwarg named `_dts` silently overwrites that local with
whatever the caller passes.** If the caller passes a list, the engine's
later `bs.bisect_right(_dts, _t)` calls `len()` on it and works by luck. If
the caller passes something else — or nothing, while a stale value lingers —
the engine dies with:

```
TypeError: object of type 'module' has no len()
```

**That exact error is what I chased for most of the session.** It appeared as
"0 trades" on the control arm, which is what made it look like a data
problem rather than a name collision. It was neither a data problem nor a
data-scope problem: the control was fine until the gate kwargs were added.

**Rule for the next agent: do not use short underscore names for patcher
kwargs in this engine.** `_sr`, `_t`, `_U`, `_g`, `_v`, `_j`, `_L`, `_p` are
all taken inside the LTF loop. `exp_slot_vs_purge.py` got away with
`_nst`/`_agd` only by luck of naming; a fresh harness must use a distinctive
prefix (e.g. `_pd*` as `exp_decay_gray_skip.py` now does) **and** grep the
engine for the name before using it.

---

## 2. Where P33 stands

`live_stuff/tests/exp_decay_gray_skip.py`. Written from scratch for this
question. Status:

- **Control PASSES** — 500t / +325.8R IS, 279t / +70.1R OOS, pin matched.
- **The `_dts` collision is found and renamed** (`_pdts`, `_pdlo`, `_pdup`,
  `_pdlog`, `_pdthr`).
- **One remaining failure:** with the gate kwargs live, the control arm
  returns **0 trades** instead of 500. The gate is default-off
  (`_pdthr=0.0`) so the `continue` cannot fire, which means the block is
  still mutating engine state. Suspect the `_t` local: the engine uses
  `_t` at `:1084` inside the shadow-book branch, and the injected block
  assigns `_t = int(candles_ltf[i]["ts"])` at the same loop level.
  **Rename `_t` first.**

**Do not report any P33 number until the control prints 500t / +325.8R.**
The harness already stops on a control mismatch; keep that.

---

## 3. The question P33 is trying to answer

`decay < 0.75` is the user's own idea (P11), and it is the only candidate
that has survived scrutiny. Two live-implementable ways to act on it:

| | n | slot | cost |
|---|---|---|---|
| **GRAY** — no order, hold the slot busy | stays 500, grayed at r=0 | held | none |
| **SKIP** — no order, leave the slot free | falls, next signal is taken | free | none |

A post-hoc "remove from the list" is **not a mechanism** — the order has
already gone. I used that label wrongly in P21's table and the user caught
it ("skip toh purge hai, current definition sahi karo").

**What is already known, and is not the open question:**

- P21 ran GRAY vs SKIP on `nest1h+age`: freeing the slot cost **−28.7R IS**
  and **0.0R OOS** on the champion.
- P15 ran `decay<0.75` post-hoc: **307 trades, +383.9R, WR 33.6%, PF 3.34**,
  with a hand-auditable causality proof. Re-run and reproduced twice today.
- **`decay` specifically has never been run as a pre-slot SKIP.** That is
  the open cell, and it is the only reason P33 exists.

The prior from P21 is that SKIP will be worse on this book too, but decay
blocks 193 of 500 trades versus `nest1h+age`'s 148, so it frees far more
slots and the answer genuinely is not given by the `nest1h+age` number.

---

## 4. The user's standing corrections (do not relitigate)

1. **"decay sirf ek side measure karta hai"** — correct. `decay_pair()`
   returns `(broken_up_frac, broken_dn_frac)` and every caller discards the
   second (`v, _ = decay_pair(...)`). Confirmed measurable on both sides:
   1482 up legs vs 1418 down legs, 500/500 trades have a usable value on
   each. The directional mirror was run (P24, −31.6R) and lost.
2. **"−27R in 2025 is why it is bad?"** — the user's framing, not mine. A
   per-year delta is not a smoothness test. Equity curve is.
3. **"M is the wrong bar"** — correct, and the most important correction of
   the session. `M` bootstraps the book's own level; a filter is a paired
   before/after. Replaced with a permutation null (P25/P26), then a paired
   block bootstrap on the differences for exit-side changes (P27).

---

## 5. Reproducibility rule adopted

Every result is now printed with its control line. **If the control does
not match the pin, the run is invalid and nothing after it is reported.**

This exists because of a second error: P15's doc reports the champion at
+356.9R while `net_r()` gives +325.8R. P15 uses `sum(rs) - per*n` with a
fixed per-trade cost; `net_r()` uses actual per-trade costs. They are not
the same basis, and the 31R gap silently changed every dNet quoted in the
decay docs. **Numbers quoted against +356.9R are understated against
+325.8R** — `decay<0.75` is +27.0R on the P15 basis and about +56R on the
NET basis. Until someone re-runs the decay family end-to-end on one basis,
treat every published dNet as provisional.
