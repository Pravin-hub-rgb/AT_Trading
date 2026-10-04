# EXPERIMENTS INDEX — where every harness lives and what it produced

**This file is a map, not a ledger.** It carries no results. Results live in
`experiment_registry.py` for books that won, and in `CLOSED_DO_NOT_REPEAT.md`
for ideas that died. This page answers only: *if I want to look at this
experiment again, where do I go, and can I trust what it printed?*

## The honest state of it

| | count |
|---|---:|
| harnesses in `backtest/tests/exp_*.py` | **409** |
| result files `backtest/tests/_*.json` | **335** |
| harnesses whose results file is findable **by name** | **144** |

That third number is the problem. Roughly two thirds of the harnesses here
print their result to stdout and do not write a JSON beside them, so six years
of experiments are only reachable by re-running them. That is worse than having
no record: the number in the chat that produced the doc may not be
reproducible from what is on disk.

**Nothing here has been mass-renamed or moved.** Doing that across 409 files in
one go would break every import between them and produce a large diff of
unreviewable churn. This page records the state honestly instead. The
convention below applies to everything new.

## The convention, for everything written from now on

A new experiment goes in its own folder with its harness and its results
together:

```
backtest/experiments/<family>_<subject>/
    exp_<name>.py        the harness, runnable on its own
    <name>.md            what it measured and what came out, both eras
    <name>.json          machine-readable results
    README.md            one line: what question this answered
```

And it gets an entry in the table below. If the harness cannot write a JSON, it
does not belong in the table.

## Standing infrastructure (not experiments)

These are tools, not findings. They are the ones that must keep working.

| tool | what it answers | cost |
|---|---|---|
| `run_experiment.py` | run one book, or the whole registry | fast |
| `exp_fastcheck.py` | does the engine reproduce these pins, both eras | ~30s/book |
| `exp_pinverify.py` | does the engine reproduce **every** pin | ~30 min |
| `exp_origin_lookahead.py` | the standing gates: stop source, hygiene, aliases | ~30s |
| `exp_directional_evidence.py` | was the swing read here settled at the decision bar | slow |

**`exp_fastcheck.py` is the one to reach for.** It names the books it checked
*and the ones it did not*, on purpose. `exp_pinverify.py` remains the only thing
that can discharge the registry-wide claim.

## Causality audits

Three separate leaks were found in this repo by asking, for each knob, *which
swing field does it read and when does that field settle*. That method has a
demonstrated true positive; the generic tools that do not name the field do not.

| harness | what it found |
|---|---|
| `exp_dir_causal_evidence.py` | `exp_require_dir_match` reads the swing's final direction — a median 8h after the entry bar |
| same, parameterised by book | `exp_min_swing_ratio` reads `seg.end_px` at the entry bar — settled in 0 of 137 trades |
| `exp_prefix_audit.py` | **does not work.** Kept because it is a documented false negative |

`exp_prefix_audit.py` cleared `dirmatch_multi_sw10`, which is proven
contaminated. It can only see trades within about two days of a corruption
point, and that leak has a median of eight hours. A tool that misses a bug you
already know about has proved nothing by passing, so it is listed here as a
known failure rather than a gate.

## This session's experiments

| harness | question | outcome |
|---|---|---|
| `exp_fs_census.py` | does the FS point the same way as the entry | census, no rule |
| `exp_fs_directional_leg.py` | directional FS entry on causal leg books | became `exp_fs_entry_side` |
| `exp_fs_single.py` | does it work on the 1h-only architecture, and with one position | became `exp_fs_entry_side` + signal books |
| `exp_fs_room_exit.py` | exit when the room from entry is small | failed |
| `exp_fs_untested.py` | breakeven on FS, 4h filter, window closed at FS | all failed |
| `exp_fs_small_swing.py` | exit when the swing's own leg is small | became `exp_fs_small_swing` |
| `exp_dir_causal_evidence.py` | which swings are read unsettled | found two families |
| `exp_dir_causal_rebuild.py` | does direction-match survive being made causal | no |
| `exp_verify_m.py` | recompute the null threshold on the current engine | tool, not a finding |

## Closed line

The full record of what has been tried and died, with the mechanism and the
numbers, is [`../CLOSED_DO_NOT_REPEAT.md`](../CLOSED_DO_NOT_REPEAT.md). When
starting something new, read it first — most ideas here have been tried.