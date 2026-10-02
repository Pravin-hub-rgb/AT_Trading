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
## 5. The "wired wrong" class — CLOSED by query, 2026-10-01

A knob that **exists in `backend/src`** and is still labelled **untested** in a
doc means nobody ever ran a feature the engine already has. That is the one
existence question worth spending time on, and it has a cheap answer.

```
knobs existing in backend/src: 4
  exp_causal_sl  exp_persist  exp_v19_2x2  exp_v19_causal
engine-native AND labelled untested: 0
  -> CLASS CLOSED
```

Run it as part of `exp_engine_knobs.py` — it is a section there now, not a
separate script.

**What this does NOT close:** a feature that exists and is wired to the wrong
value. That needs reading, not a query, and `exp_engine_knobs` cannot see it by
construction. The three candidates were checked anyway and are all accounted for:
`_r_touch_end` is engine-native and the r_touch arm is rejected (`v18_params`
ships `window_end="exit"`); the trail/breakeven path carries the D3 ordering fix
at three sites with its rebaseline documented; `exp_partial_r` is harness-only
and already closed in `CANDIDATE_BUILD_SHEET.md` Tier D.

**Expected yield was zero and was zero. Do not re-propose this audit** — it was
proposed twice this session and closed twice by query.

## 4. What none of these checks cover

**The generalisation, stated once because it has bitten three separate times.**

`exp_engine_knobs.py` proves a knob **exists**. It does not prove the knob is
**correct** — `exp_max_concurrent` passed it by name while its enforcement was
under active suspicion. `exp_sweep_static.py` matches **net-R shapes**; it cannot
see a dead AUC or trade count, which is how `INSIDE80_P95.md` sat clean for weeks.
And an **overlap audit** that reads the same `exit_ts` / `entry_ts` the engine
reads is not independent verification at all — both would be wrong together. That
argument was used to reject a `+900` clock claim and was itself circular; P120
replaced it with an actual A-vs-B clock comparison.

**Three tools, three different blind spots. None of them covers another. Do not
cite one as if it covered a neighbour.**

| you want to know | use | do NOT use |
|---|---|---|
| is the knob real? | `exp_engine_knobs.py` | reading the name in a doc |
| is the anchor stale? | `exp_sweep_static.py` | for AUC or count claims |
| is the cap on the right clock? | P120's A-vs-B replay | an existence check |

**Verify the artefact, not the tool's exit code.** A green git warning absorbed a
correct change once already: a commit silently did not happen because the command
reported a non-zero status on a stderr warning, and the files were left staged
looking like they had been committed. The tool had done its job and the layer in
between swallowed the result. Every check here should be confirmed by reading what
it produced, not by the fact that it ran.

## 5. Three rules, all earned here

Each one came from a bug in this session, and each is cheaper than the thing it
replaces.

**1. Ask which convention produced the number.** — caught P121

> P91 tabulated shorts at −0.4415 and −0.7471 "absolute". `abs_return()` never
> read `t["dir"]`, so it computed `(exit − entry)/entry` for shorts too, which is
> the *negative* of PnL. Profitable shorts were read as losses. The number was
> arithmetically correct; the reading was not.

**2. Report n beside every rate.** — caught P115

> P119 label (3) read AUC 0.601, which on a naive threshold flags as separating.
> Its positive class is 20 trades out of 252. The pre-registered (1) is what
> stopped a false positive being written up. An AUC without its n is not evidence.

**3. Verify the artefact, not the tool's exit code.** — caught two lost commits

> A commit silently did not happen because the command returned non-zero on a
> stderr warning, leaving files staged and looking committed. The tool did its
> job; the layer between swallowed the result.

**Rule 1 is first because it runs before the experiment.** The other two are
checks you can apply to a finished number. Rule 1 is the only one that costs
nothing and prevents the work rather than auditing it.

**A fifth rule is agent-facing rather than check-facing, so it lives in
`AGENT_COORDINATION.md`: *credit only what you opened*.** A summary is a claim
about work done and needs the same evidence standard as a claim about results.
Three names were carried through several summaries in one session and a
repo-wide search plus `git log --all` found no file and no history for any of
them. A wrong number has a value you can look up; credit has nothing to check
against, so it propagates without meeting resistance. Its companion — *state the
unit of every count* — is there too.

Two of these are the same failure wearing different clothes — a shared variable
between an instrument and its own yardstick. In P115 the feature and the label
both contained `window_end`. In P121 the measure and the convention were the same
expression read twice. **When two numbers disagree, ask what they share before
asking which is right.**

## 6. Standing practice — every check gets a negative control first

**A check that has never been observed failing is indistinguishable from one that
always passes.** Before any check in this directory is trusted, write a deliberate
failure probe: a file that violates exactly what the check claims to catch, run it,
confirm the check fires, then delete the probe.

This is not hypothetical caution. Three times this session a check reported health
instead of the thing it was checking:

- a static sweep counted 28 files while 435 existed
- `if PERP in t: continue` matched nothing and skipped silently
- the `_now_ts` existence check "confirmed" a rule it never tested the clock of

In each case the check returned success. Only the probe distinguishes a detector
from a decoration.

**Worked example.** `RETRACTED_ANCHORS` was added for P91's 0.4415 / 0.7471. The
sweep passed immediately — which proved nothing, since it had never been observed
catching them. A probe file quoting both values with no retraction marker was
written to `backtest/docs/`, the sweep was run, and it flagged
`_PROBE_P91_TEST.md` under both anchors. Probe deleted. Only then was the guard
considered real.

**Cost is a few lines and about a minute. Skip it and a check that silently matches
the wrong shape can sit in the tree indefinitely — which is what
`exp_sweep_static.py`'s own docstring warns about.**

## Running them

Static, safe to run any time:

```
python -u backtest/checks/exp_sweep_static.py
python -u backtest/checks/exp_engine_knobs.py
```

Gates are heavier — run them **serially**. Concurrent runs each load ~1.9M fine
candles and will exhaust memory.