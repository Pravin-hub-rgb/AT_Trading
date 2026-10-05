# KNOB & FILTER SWEEP - what actually stood out

Source artifacts (all under `backtest/tests/`):
`_signal_filter_sweep.json`, `_remaining_filters.json`, `_signal_combo.json`,
`_signal_exhaustive.json`.

All numbers below are on `sig_` books (one position, `max_positions=1`).
`d_is` / `d_oos` are the delta vs the pure one-position baseline
(IS 396 / +37.80R, OOS 231 / **-16.26R**).

---

## 1. The one unambiguous winner

| knob | value | d_is | d_oos | OOS result |
|---|---|---:|---:|---|
| `exp_fs_entry_side` | `short` | +136.50 | **+117.28** | 239 / +100.94, dd 11.82 |
| `exp_bias_momentum_min` | 0.9 | +26.89 | +57.21 | 172 / +40.87, dd 24.98 |
| `exp_decay_mode` | 2 | +14.14 | +48.27 | 155 / +31.93, dd 34.16 |
| `b3_k` | 2 | +0.73 | +44.03 | 91 / +27.69, dd 16.40 |
| `exp_legskip_r` | 2.0 | +27.01 | +15.73 | 142 / -0.61, dd 28.55 |
| `exp_skip_decisive` | 1 | +18.88 | +9.92 | 179 / -6.42, dd 37.45 |
| `exp_entry_skip_b2_doji` | 1 | +3.21 | +3.88 | 220 / -12.46, dd 47.50 |

`exp_fs_entry_side="short"` is **2x the runner-up**. It is the only knob that
by itself produces a viable OOS book.

### Direction is the edge

| entry side | OOS net | OOS wr |
|---|---:|---:|
| `short` | +100.94 | 31.0% |
| `long` | +80.45 | 30.0% |
| `both` | +14.83 | 25.1% |

Trading both sides drops the win rate 31% -> 25%. Longs add no edge; they only
dilute. **The edge is one-directional and it is short.**

---

## 2. Dead knobs - zero effect

These produced **identical** numbers to baseline (OOS 231 / -16.34 every time):

```
exp_cohort_swingpause        exp_geom_b1_max
exp_geom_b1_min              exp_geom_mag_min_atr
exp_geom_start_dist_max_atr  exp_ltf_no_entry
```

All six are the geometry/cohort family. They do nothing. Safe to drop.

## 3. IS-only mirages - do not trust

| knob | IS | OOS |
|---|---|---|
| `exp_kinds = FLIP` | +36.95 | **-24.31** (wr 16.7%) |
| `exp_entry_swing_age_max = 50` | +1.77 | -6.83 |
| `exp_skip_utc_sat = 1` | IS gain | OOS **negative** |
| `htf_rr = 4.0 / 5.0` | + | OOS **negative** |
| `exp_trail_half = 1` | + | OOS **negative** |

Looked good on IS, reversed OOS. Classic overfit.

## 4. The combo ladder is filter-overfit - this is the key warning

```
step 1  exp_fs_entry_side=short      368 / +174.30
step 2  + exp_bias_momentum_min=0.8  284 / +208.16
step 3  + exp_skip_decisive=1        272 / +193.45   <- DOWN
step 4  + exp_entry_skip_b2_doji=1   266 / +175.12   <- DOWN
step 5  + exp_decay_mode=3           219 / +200.85
step 6  + exp_legskip_r=2.0          93 / +199.76   <- n collapsed
step 7  + b3_k=6                     64 / +113.56   <- n collapsed
```

`n` falls 368 -> 64. Steps 3, 4, 6, 7 each *reduce* both IS and OOS. The
"best combo" only looks good because it has filtered away ~83% of the sample.

**Rule: a filter that cuts the sample below ~150 OOS trades is no longer evidence.**

## 5. Surviving exhaustive stack

`fsent_sig_full` - 234 / +291.02 IS, 153 / +190.93 OOS (dd 6.96):

```
exp_fs_entry_side      = "short"
exp_bias_momentum_min  = 0.8
exp_partial_r          = 0.0
exp_trail_skip_n       = 2
exp_fs_small_swing     = 6.0
exp_skip_weekend       = 1
```

`exp_fs_small_swing` is insensitive above 4.0 (OOS 147.22 at 4.0, 6.0 and 8.0
- identical), so 6.0 is a safe interior choice, not a tuned edge.

---

## 6. OPEN DEFECT - four "swept" knobs are not in the shipped engine

The shipped engine `backend/src/btc/engines/htf_ltf/unified.py` exposes
**13 `exp_*` knobs** (`simulate_htf_ltf_streak_halt` has a 29-param signature).

Four knobs that the sweeps and `fsent_sig_full` rely on are **absent from it**:

```
exp_bias_momentum_min      NOT IN SHIPPED SIGNATURE
exp_partial_r              NOT IN SHIPPED SIGNATURE
exp_skip_weekend           NOT IN SHIPPED SIGNATURE
exp_trail_skip_n           NOT IN SHIPPED SIGNATURE
```

`grep` for `weekend`, `swingpause`, `trail_skip`, `bias_momentum`, `partial_r`
in `unified.py` returns **0 hits each**. Only `exp_decay_mode` (2 hits) and
`exp_fs_entry_side` / `exp_fs_small_swing` are real.

**Proof (direct call against the shipped engine):**

```
>>> U.simulate_htf_ltf_streak_halt(..., **fsent_sig_full.params)
TypeError: simulate_htf_ltf_streak_halt() got an unexpected keyword
           argument 'exp_bias_momentum_min'
```

The function has **no `**kwargs`** - unknown knobs raise, they are not swallowed.
Yet `exp_fastcheck.py` re-derived `fsent_sig_full` at exactly 234 / +291.02.
That is only possible if the harness is **not** calling this function - it passes
its own `sim` (`measure(sim, data, cfg)`).

Therefore:

- **Every `fsent_sig_*` pin, including the three I fastchecked as OK, was
  produced by a patched engine - not by `unified.py`.**
- The filter-side sweep was run against that same patched engine.
- The swept knobs for the **shipped** engine are only the 13 it actually has.
- `exp_bias_momentum_min` - my "runner-up" recommendation above - **does not
  exist in production.** Its whole contribution (d_oos +57.21) is from the
  patched engine only.

**Until this is resolved, the filter-side sweep is NOT exhaustive, and the
`fsent_sig_*` ladder is smaller than it looks.** Do not promote any book whose
edge depends on the 4 missing knobs.

---

## Verdict

1. Real, defensible edge: **`exp_fs_entry_side="short"`**, then
   `exp_bias_momentum_min`.
2. Six geometry knobs are dead weight.
3. IS-only knobs are traps.
4. Never trust a combo whose sample collapsed.
5. **Four supposedly-swept knobs are missing from the shipped engine - resolve
   before quoting any of the `full`/`wk_pause` results.**