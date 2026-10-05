# HANDOVER - port the 4 missing knobs, then modularize

Written by the previous agent. **Read this fully before touching code.**
There is a correction at the top that will save you a lot of wasted work.

---

## 0. CORRECTION - read this first

An earlier agent reported:

> "4 knobs are missing from the shipped engine, the book is invalid."

**That was wrong.** The knobs are not missing - they are implemented, but they
live in a **source-text patch**, not in `unified.py`.

How the system actually works:

```
unified.py   (1188 lines, production engine)
     |
     |  test_experiments_craze.py::_build_module() reads it as TEXT
     |  and applies ~40 s.replace() steps to inject experiment knobs
     v
patched engine (2282 lines)  -> written to _craze_tmp_<hash>_<n>.py
     |                         -> importlib loads it
     v
THIS is what every sweep, test and fastcheck actually runs
```

So there are two engines:

| | file | lines | role |
|---|---|---:|---|
| production | `backend/src/btc/engines/htf_ltf/unified.py` | 1188 | live trading |
| patched | `_craze_tmp_*.py` (transient) | 2282 | all experiments |

`exp_fastcheck.py` -> `run_experiment.build_module()` -> the patched engine.
`run_experiment.py:244-248` picks `sim(...)` when a `sim` is supplied and only
falls back to `shipped_mod` otherwise - and fastcheck always supplies one.

**Consequence:** every pin in the registry, including `fsent_sig_full`
(234 / +291.02 IS, 153 / +190.93 OOS), came from the patched engine. That is
consistent and the book is legitimate research.

---

## TASK 1 (PRIMARY) - port the 4 knobs into the production engine

The 4 knobs that are only in the patch:

```
exp_bias_momentum_min
exp_partial_r
exp_skip_weekend
exp_trail_skip_n
```

The owner wants these in the shipped engine so the experiment book can be
promoted to production.

### Artifacts already prepared for you

| file | what |
|---|---|
| `backtest/docs/_patched_engine.py` | exact 2282-line patched engine that produced every number |
| `backtest/docs/_engine_port.diff` | `fc /n` diff, shipped vs patched |

Do **not** hand-rewrite the logic from the docs. Port it verbatim from
`_patched_engine.py` so results reproduce exactly.

### Where the patch injects them (in `test_experiments_craze.py`)

| knob | signature line | logic lines |
|---|---:|---|
| `exp_partial_r` | 97 | 1026, 1163-1179 |
| `exp_skip_weekend` | 101 | 959 (+ `_is_weekend` helper ~955) |
| `exp_bias_momentum_min` | 155 | 1341, 1382-1391 |
| `exp_trail_skip_n` | 165 | 1068 |

In the patched engine they sit at signature lines 281 / 285 / 339 / 347.

### The port itself

1. Back up `unified.py` first.
2. Add the 4 params to `simulate_htf_ltf_streak_halt`'s signature with the
   **exact defaults** from the patched engine (`0.0`, `0`, `0.0`, `0`).
   Defaults MUST stay inert - see the identity gate below.
3. Copy each logic block verbatim. `exp_skip_weekend` also needs the
   `_is_weekend()` helper it defines.
4. `exp_trail_skip_n` initialises `_trail_skip_rem` at position open and
   decrements it in two places in the trail logic (patched lines 1954, 1980).

### Then remove the duplicate source of truth

Once the 4 knobs live in `unified.py`, **delete their injection** from
`test_experiments_craze.py`. Otherwise there are two definitions and a
divergence bug waiting to happen.

Keep the other ~36 patches - they are experiment-only by design.

### Acceptance test (do not skip this)

```
python backtest/tests/exp_fastcheck.py fsent_sig_full
```

Must still report **234 / +291.02 IS, 153 / +190.93 OOS**. If the port is
byte-faithful the numbers will not move by a cent.

Second, sharper test - this is the one that proves the port works rather
than merely not crashing:

```
exp_skip_weekend=1  reduced OOS n from 284 -> 239
```

Run the shipped engine with and without `exp_skip_weekend` and confirm the
same 284 -> 239 drop. If the knob is still inert in production, the port
silently failed.

Finally run the identity gate in `test_experiments_craze.py:main()` - it
proves defaults == shipped engine. A correct port keeps it green.
---

## TASK 2 - modularize (owner explicitly asked for this)

Owner's words: *"ek file mai bahut sara code ho jara hai, make it modular.
Debug karna bahut dikkat hoga. Already code ko functions mai baato."*

### Where the pain is

| file | lines | problem |
|---|---:|---|
| `backtest/tests/experiment_registry.py` | **4812** | the worst offender |
| `backtest/tests/test_experiments_craze.py` | 1707 | ~40 sequential `s.replace()` calls |
| `backend/src/btc/engines/htf_ltf/unified.py` | 1188 | one big simulate function |
| `backtest/tests/run_experiment.py` | 581 | ok |

### Suggested split for `experiment_registry.py`

```
backtest/tests/registry/
    __init__.py        re-exports EXPERIMENTS, ALIASES, BP, GROUPS
    base.py            BP, ENGINE_DEFAULTS, shared param blocks
    signal.py          fsent_* / champ_* books
    swings.py          swing family
    cohorts.py         chopband / wage / curfew / atrr families
    closed.py          the graveyard - CLOSED_DO_NOT_REPEAT entries
    helpers.py         shortlisted(), _deref(), resolve()
```

Keep `experiment_registry.py` as a thin re-export so **no import breaks**.
Every harness imports from it; do not move it until all imports are updated.

### Suggested split for `test_experiments_craze.py`

The `_build_module` patch walk is ~40 anonymous inline replacements. Make each
a named function:

```python
def _patch_trailing(s: str) -> str: ...
def _patch_partial_exit(s: str) -> str: ...
```

and have `_build_module` call them in a list. Then a failing `assert s.count(t)
== 1` names itself.

### Refactor rules

- **Port first, refactor second.** Do not mix them; the numbers must stay
  verifiable at every step.
- No behaviour change during the split.
- Commit after each book family moves.

---

## TASK 3 - dead code audit (owner suspects a lot of it)

The owner said: *"junk code aur dead code bahut padha hoga, pata nahi kaise
pata chalega."*

### Known junk already found

- `backtest/tests/_*_tmp.py` - **9 files, 797 KB.** These are stale *copies of
  the engine itself* from older experiment eras. They are almost certainly all
  dead. Confirm nothing imports them, then delete.
- `_craze_tmp_*` leftovers - currently 0, but `_load_module` writes these on
  every `build_module()` call and only cleans up on the happy path. A crashed
  run leaks one. Add a sweep.

### How to find dead code properly

```bash
# 1. knobs in test_experiments_craze.py that no EXPERIMENTS entry sets
grep -o "exp_[a-z0-9_]*" backtest/tests/test_experiments_craze.py | sort -u
#    then cross-check against what the registry actually uses
# 2. functions never called
pip install vulture
vulture backtest/tests/ --min-confidence 80
```

Caution: the patch walk is a **string-manipulation** program. Vulture and
static analysers will produce false "unused" hits on injected code. Verify
every deletion by grepping the string literals, not the Python names.

### Known-closed experiments

`backtest/docs/closed/CLOSED_DO_NOT_REPEAT.md` holds 11 proved lookahead books and
the corrected `exp_swingpause` note. Do not re-open those.
---

## Naming contract (settled, do not relitigate)

| prefix | meaning |
|---|---|
| `sig_*` | **exactly one position** - `max_positions=1` |
| `multi_*` | multiple concurrent positions |

- `"single"` appears in **no** book name. It was renamed to `sig_`.
- 49 `sig_` books, all at `max_positions=1`, all verified.
- Old names still resolve through `ALIASES` in the registry.

### The engine rule you must know

```python
max_positions > 0 and not exp_mltf     # <- this is what actually gates to 1
```

`max_positions=1` alone does **not** mean one position. If `exp_mltf=True`,
the gate is bypassed and the book goes concurrent. This is why "single" books
used to peak at 6 concurrent positions. All 49 `sig_` books were audited to
have `exp_mltf` absent - keep it that way.

---

## Current best book

`fsent_sig_full` - 234 / +291.02 IS, 153 / +190.93 OOS, DD 6.96

```
exp_fs_entry_side     = "short"     <- the one unambiguous edge, d_oos +117.28
exp_bias_momentum_min = 0.8
exp_partial_r         = 0.0
---

## Known broken / needs re-measuring

- **`fsent_sig_fs_mom` is deliberately UNPINNED.** Params were written from
  prose rather than the sweep artifact; fastcheck got 235/+262.29 against a
  recorded 285/+208.16. Do not cite it until params are re-derived from
  `_signal_filter_sweep.json` and it re-pins.
- **43 renamed `sig_` books have `pins: None`.** They got `max_positions=1`
  after being renamed, so their old pins are stale by construction. Refresh
  with `exp_pinverify --all` (slow).
- `exp_prefix_audit.py` is a **failed instrument** - it missed the already
  proved `dirmatch` leak. Never gate on it.
- Gray mode (`exp_fs_gray`) exists but is a no-op. Do not rely on it.
- Uncommitted: the sweep JSONs, the registry rename, the 4 harness fixes for
  `None` pins, `method/KNOB_SWEEP.md`, and the artifacts in this doc.

---

## Docs map

| file | what |
|---|---|
| `backtest/docs/method/KNOB_SWEEP.md` | filter/knob findings **+ this defect** |
| `backtest/docs/method/ONBOARDING.md` | start here |
| `backtest/docs/method/BOOK_CATEGORIES.md` | book taxonomy - has stale "single swing chain" wording to remove |
| `backtest/docs/closed/CLOSED_DO_NOT_REPEAT.md` | 11 proved-lookahead books |
| `backtest/docs/pipeline/{FAMILIES,BASELINE}.md` | pipeline - also has the stale wording |

---

## Suggested order of work

1. Back up `unified.py`. Port the 4 knobs from `_patched_engine.py`.
2. Prove it: `exp_skip_weekend` must reproduce the 284 -> 239 OOS drop.
3. Delete the 4 injections from `test_experiments_craze.py`.
4. Run `exp_fastcheck --all`, then the identity gate.
5. Commit.
6. Then modularize `experiment_registry.py`, family by family.
7. Then the dead-code sweep (delete the 9 `_*_tmp.py` engine copies first -
   biggest easy win, 797 KB).
exp_trail_skip_n      = 2
exp_fs_small_swing    = 6.0
exp_skip_weekend      = 1
max_positions         = 1
```

`sig` = one position. Baseline it beat: IS 396 / +37.80, OOS 231 / **-16.26**.

Full analysis in `backtest/docs/method/KNOB_SWEEP.md`. Key warnings there:
six geometry knobs are dead (zero effect); `exp_kinds=FLIP` and
`exp_entry_swing_age_max` are IS-only mirages; the `b3_k=6` combo collapses
n from 368 to 64 and is filter-overfit.
