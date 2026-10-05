# EXPERIMENTS

Per-experiment folders for everything new. The layout is required by
[`../docs/pipeline/README.md`](../docs/pipeline/README.md) §6:

```
<family>_<subject>/
    exp_<name>.py        the harness, runnable on its own
    <name>.md            what it measured, both eras
    <name>.json          machine-readable results
    README.md            one line: what question this answered
```

A harness that cannot write its JSON does not belong here.

**Do not move the existing 409 harnesses out of `backtest/tests/`.** They import
each other by module path and a bulk rename would break all of them in one
unreviewable diff. The state is documented in
[`../docs/pipeline/signal/EXPERIMENTS.md`](../docs/pipeline/signal/EXPERIMENTS.md) instead,
including the fact that most old harnesses print to stdout and write no JSON.

Results are not recorded here. Winning books are pinned in
`experiment_registry.py`; ideas that died are in
`../docs/closed/CLOSED_DO_NOT_REPEAT.md`.