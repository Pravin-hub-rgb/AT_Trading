# START HERE — repo orientation

**A new AI or a new human picking this up: read this file, then
[`pipeline/README.md`](pipeline/README.md). Nothing else.**

~220 measured books, several years of experiments. How the thing *works* lives in
`pipeline/`. What it *measured* lives in the registry, and nowhere else.

## The three things that decide most arguments

**1. One engine.** `backend/src/btc/engines/htf_ltf/unified.py`. Every book is
that engine plus keyword arguments. There is no second engine.
`backtest/tests/test_experiments_craze.py` runs the *shipped source text* with
small asserted patches, so a harness cannot quietly fork the engine.

**2. A pin is not a proof.** `exp_pinverify.py` and `exp_fastcheck.py` answer
"does the engine reproduce this number". They cannot answer "is this number
allowed to exist". Only a causal guard answers that, and it has to be applied by
whoever writes the filter. Three families here shipped large numbers that were
reading the future — see [`CLOSED_DO_NOT_REPEAT.md`](CLOSED_DO_NOT_REPEAT.md).

**3. Never report a number you did not just run.** Re-scoring closed trades is
not a measurement. If the rule changes *which trades exist*, a re-score measures
the old book. Run the engine.

## Where things are

| path | what is in it |
|---|---|
| `backend/src/btc/engines/htf_ltf/unified.py` | the engine |
| `backend/src/btc/btc_engine.py` | signal collection, swing entry helpers |
| `backend/src/firstswing.py` | the swing state machine |
| `backtest/tests/experiment_registry.py` | **every measured book and its pins** |
| `backtest/tests/run_experiment.py` | run one book, or `--all`, `--audit`, `--list` |
| `backtest/tests/exp_pinverify.py` | re-derive every pin (slow, authoritative) |
| `backtest/tests/exp_fastcheck.py` | re-derive a chosen subset, both eras (fast) |
| `backtest/tests/exp_origin_lookahead.py` | the standing hygiene gates |
| `backtest/docs/pipeline/` | how to run an experiment; every knob, by family |
| `backtest/docs/CLOSED_DO_NOT_REPEAT.md` | tried, measured, died |
| `backtest/docs/REGISTRY_BOARD.md` | the shortlist, readable |
| `backtest/experiments/` | per-experiment harnesses and their results |

## Vocabulary, shortest possible

- **HTF** — higher timeframe (1h). Produces *bias windows*: a stretch of time
  where one direction is allowed.
- **LTF** — lower timeframe (15m). Where the actual trades live. Every trade is
  an LTF trade taken inside an HTF window.
- **swing** — a leg of price. Has a start, an extreme, and a **confirmation**.
- **FS** — the print that marks a swing confirmed. Legal to read *at the FS bar*.
  Illegal to read at an earlier bar, because that is the future.
- **B2 / FLIP** — the break marks the book enters on.
- **bias window** — the HTF interval `[start, end, direction, entry_px, sl]`.
- **gray** — holding the slot after an exit so nothing new can enter.
- **knob** — one keyword argument. Families in `pipeline/KNOB_CATALOG.md`.
- **book** — a named set of knobs, pinned in the registry.

## The one rule that settles most arguments

> **A quantity may only be read if it was settled at the moment you read it.**
> Same number, different moment, legal or illegal.

M2 read a swing's leg at the entry bar and was look-ahead.
`exp_fs_small_swing` reads the identical leg at the FS bar and works.

Full write-ups, with dates and measurements, in
[`CLOSED_DO_NOT_REPEAT.md`](CLOSED_DO_NOT_REPEAT.md).