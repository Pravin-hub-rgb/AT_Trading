# CHECKS — the verification layer, kept separate from research

**These are checks, not experiments.** They exist to answer "is the repo telling
the truth right now", and they are deliberately segregated so a failing check is
never confused with a finding. Research harnesses live in `backtest/tests/`.

Rule: **a new check goes here. A new experiment does not.** If you cannot state
what a check would have caught, it is an experiment.

## 1. Static — read-only, seconds, no engine run

| check | what it catches | what it does NOT catch |
|---|---|---|
| `exp_sweep_static.py` | syntax errors, pre-C16 net-R pins, Binance-spot venue loads, registry `pivot_rule` coverage, documented-red harnesses | **net-R anchors only.** It cannot see a stale AUC or trade count, which is how `INSIDE80_P95.md` sat clean while its headline was dead |
| `exp_engine_knobs.py` | `exp_*` names referenced by `test_experiments_craze.py` that **no engine implements** — harness patches that read as real knobs | **existence, not correctness.** `exp_max_concurrent` passed this check by name while its enforcement used the wrong reference. Existence is necessary, not sufficient |

Both are under `exp_` because that is the repo's existing convention, not because
they are experiments. Their docstrings state their own limits; that is the point.

## 2. Gates — actually run, minutes, pass/fail

| check | proves | cost |
|---|---|---|
| `exp_verify_route.py` | the FastAPI route end to end | ~3 min |
| `exp_live_swing_parity.py` | live and backtest produce identical swings (15m 2900/2900, 1h 1316/1316, zero structural field differences) | ~3 min |
| `backend/tests/test_v18_causal_integrity.py` | v18's five integrity assertions including `COUNT_BAND=(348,358)` | ~4 min |

`test_v18_causal_integrity.py` lives in `backend/tests/` because it is pytest-style
with asserts. That is its correct home; do not move it here.

**What has never been tested: slot parity.** Swing parity — entry logic — is
proven. Whether live and backtest agree on how many positions are open at once is
unmeasured. Do not read swing parity as parity.

## 3. Research — `backtest/tests/`

One-off experiments: `exp_p115_bars_to_wend.py`, `exp_p117_slot_grid.py`,
`exp_p119_cap1_tail.py`. These produce findings and are expected to be slow and
to sometimes falsify themselves.

**The other ~530 files in `backtest/tests/` are historical experiments, not
checks.** Most predate the current venue convention and the C16 re-anchor. Their
presence in the tree is not endorsement. Do not bulk-run the directory as a
health check — that is precisely the move `exp_sweep_static.py` was rewritten to
warn against.

## Running them

Static, safe to run any time:

```
python -u backtest/checks/exp_sweep_static.py
python -u backtest/checks/exp_engine_knobs.py
```

Gates are heavier — run them **serially**. Concurrent runs each load ~1.9M fine
candles and will exhaust memory.