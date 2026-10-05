# Engine & Book Architecture — core/lego split

Audit date: 2026-10-02. Produced from AST analysis of the REAL generated
engine module (built via `_build_module()`), not from reading source by eye.

## 1. What the numbers actually are

| Thing | Count |
|---|---|
| Registry books | 116 |
| Distinct knobs used across books | 39 |
| Engine signature knobs (built module) | 127 |
| LIVE — read somewhere in the body | 121 |
| DEAD — accepted, never read | 6 |
| Hardcoded numeric constants in body | ~30 |

The engine is 3.3x wider than anything any book has ever used. That is the
central problem: **the engine has grown to hold hypotheses that were tested,
recorded, and left in.** Nothing prunes them.

## 2. The core/lego split

A book should be able to say only what is different about it. Right now every
book re-declares the whole core by hand:

```
book A:  mode=atr_high, chop_thresh=55.0, ext_stop_r=3.0, ...
book C:  mode=atr_high, chop_thresh=55.0, ext_stop_r=3.0, ...   <- identical to A
```

Common-core count across all 116 books is **zero**, because no book inherits
anything. So the split has to be:

- **CORE** — `unified.py`'s own signature. The 15 knobs it already declares
  (`chop_thresh`, `mode`, `atr_*`, `ext_stop_r`, `sl_buf_atr`,
  `cooldown_bars`, `max_consecutive_losses`, `htf_rr`, `window_end`,
  `exp_persist`, `exp_causal_sl`, `max_positions`, `pivot_rule`,
  `soft_width`). These are the only knobs with a documented default that
  equals a measured book.
- **LEGO** — injected research knobs (`exp_mltf`, `exp_partial_r`,
  `exp_swingpause`, `exp_wage_h`, ...). Each one is a hypothesis. Each one
  should be attributed to the book that introduced it.

Target shape:

```python
CORE = dict(mode="atr_high", chop_thresh=55.0, ext_stop_r=3.0, ...)

"nowknd_multi_sw10": {
    "desc": "king + skip weekend entries",
    "base": "king_multi_sw10",          # inherits, does not re-declare
    "params": {**CORE, "exp_skip_weekend": 1},
}
```

## 3. Why adding a knob today is dangerous

The harness injects knobs by string replacement into the generated source
(158 `s.replace(...)` sites). A new knob must be added in **three** places:

1. the `s.replace(t1, ...)` signature injection list,
2. the patch body that makes it do something,
3. the registry entry that sets it.

Miss (2) and you get a knob that accepts a value, returns a plausible number,
and changes nothing. That already happened:

- **`exp_persist`** — set by 62 books; the patched v18 body had no hysteresis
  code at all. Every one of those books ran with the knob inert.
- **`exp_wick_reject`** — injected into the signature, has no patch body.
  Currently unused by any book, so nothing is corrupted yet, but the next
  experiment to try it would get a fabricated result.

`backtest/checks/exp_knob_wiring.py` now fails the build on exactly this
class: it builds the real module, AST-parses it, and compares registry knobs
against knobs that are actually referenced in the body.

```
RESULT: PASS - every registry knob is wired to live engine code
```

Known write-only debug flags are allow-listed explicitly: `exp_5m_stats`,
`exp_campaign_stats`, `exp_event_stats`, `exp_window_loss_kill_stats`,
`exp_window_win_kill_stats`.

## 4. Hardcoded constants — mostly fine, one category to keep an eye on

The dominant literal is `50.0`, appearing ~23 times. It is the neutral
fallback for every per-bar regime score (chop, entropy, FD, HMM, GARCH, and
the `_ramp(x, 50.0, hw)` band). It is a sentinel, not a tuned value —
**do not** promote it to a knob. Genuinely tunable-looking candidates:
`0.95`, `0.5`, `0.3`, `0.0005`, `4.0`, `16`. None is currently reachable by a
book, so any experiment that wanted to move them has silently not been run.

## 5. Rerun plan after C16

`pivot_rule` defaults to `"leg"` in `unified.py`, and 19 engine call sites
read that default. Every book that did not explicitly pass `pivot_rule` was
therefore switched from the origin pivot to the causal leg pivot **without
any caller asking**. Measured on the origin/origin vs leg/leg pair: 500 trades
+325.78R net becomes 499 trades +239.12R net.

Consequences for the 116 books:

- Books that never set `pivot_rule` (114 of 116) were all re-baselined by the
  C16 default alone. Their historical pins are stale.
- Only the 2 books that set `pivot_rule` explicitly are trustworthy.
- Order of work: unify the engine first (so there is one construction), then
  rerun the suite once, then re-anchor pins to the single new book.

## 6. Open decision

`exp_persist` default in `unified.py` is `7`. The historical books were all
measured with hysteresis effectively off. Unifying therefore either keeps the
280-trade historical book (default `0`) or re-anchors everything to the
260-trade configured book (default `7`). This is a strategy decision, not an
engineering one, and it should be made once, explicitly, before any rerun.
