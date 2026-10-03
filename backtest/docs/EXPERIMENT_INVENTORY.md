# Experiment inventory - what lives where, and what is NOT in the registry

Written 2026-10-02. The question this answers: after re-measuring every book,
is any experiment still lurking unmeasured?

## The two audits behind it

1. **Knob audit.** Every exp_* knob the engine understands (harness-patched or a
   real `unified.py` signature parameter), intersected with the knobs any
   `exp_*.py` sets, minus the knobs any book sets. That was 41 knobs.

2. **Knob/value audit.** The same, but per VALUE rather than per knob - a knob
   can have one book and still have had three values tested by hand. That was
   39 pairs across 14 knobs.

A third pass then swept the tail, and the residual is now down to the four
pairs in the next section that are not books at all.

Both are now measured and recorded as books. This is the layer that was

previously invisible: the trail family was in it, and so was a
bias-momentum sweep four scripts had run and no book had captured.

## What the registry does NOT cover, and why

| category | scripts | why not a book |
|---|---|---|
| other venue/instrument | 44 | A book is a config on this venue's data. BTCUSDT is Binance spot and is not traded on this project, so a cross-venue number cannot be pinned against these books at all. |
| own grid, now covered | 51 | Ran a private grid over engine knobs. Every (knob, value) it used is now a book. |
| post-hoc / analysis only | 37 | These never call the engine. They read trades that were already booked and re-slice them - autopsy, decomposition, decile walk. They are analysis, not an unmeasured experiment. |
| runs registry books | 273 | Consumes books. Measured by definition. |
| sizing / capital model | 65 | Position sizing sits above the trade list, not inside the engine. Scaling a book by kelly or a fixed fraction is a capital question and would need its own pins. |

## The honest answer

**Nothing is lurking in the knob layer.** Every value of every live engine knob
that any script tested is now a measured, pinned book, including the ones that
turn out to be inert. The only residue is four pairs that are not experiments
(see below), so the audit is closed, not merely unfinished.

**What is not covered is above the engine, not inside it:** sizing and capital
models, other venues and instruments, and post-hoc analyses of trades already
booked. Those are research notes rather than unmeasured books, and turning them
into books would need a different kind of pin - the ones here assume a config
produces a trade list.

## Knobs that cannot be books, and why

Four (knob, value) pairs a script sets are not books, deliberately:

- `exp_regime_persist` at 3 and 5, and `exp_window_quality` at 0.1 and 0.2
  (`test_combos.py`). These are not parameters of the engine at all - passing
  them raises `TypeError: got an unexpected keyword argument`. Either that
  script measures something other than what the knob name suggests, or it
  measured these on a pre-unification engine and they were lost. A book whose
  knob the engine rejects would be a fiction, so they are recorded as a comment
  in the registry instead.

- `exp_5m_data` and friends are **stats sinks**, not knobs. The default is
  `None` and they exist to receive output, so "setting" them is not an
  experiment. `exp_5m_confirm=1` with `exp_5m_wait_min=240` raises TypeError
  because `exp_5m_data` has to be a dict, not the string `"five"`.

## Still inert, measured and recorded so nobody re-runs them

| book | why inert |
|---|---|
| `gap_inert_geom` | exp_geom_* gates wired but not binding at these values |
| `gap_inert_kill` | exp_window_win_kill_* wired but not binding |
| `gap_inert_chop65` | chop_thresh does not bind under mode=atr_high |
| `gap_inert_winkill2` | exp_window_win_kill_n=2 never fires on this book |
| `gap_inert_winkill3` | exp_window_win_kill_n=3 never fires on this book |
| `gap_inert_lossstreak` | exp_loss_streak_* never fires at n=3 |
| `gap_inert_cohort2` | exp_cohort_* never fires on this book |
| `gap_inert_curfew44` | curfew a=4.0 b=4.0 is a degenerate band, closes instantly |
| `gap_inert_event_shift` | scheduled-event shift +/-24h changes nothing on this book |
| `gap_inert_cohort1` | cohort gate at loss_n=1 never fires |

A knob that is wired but does nothing is worse than one that is missing,

because it looks like it was tested. These are recorded so the next person

does not spend an afternoon rediscovering that.

## Regenerating

```
cd backtest/tests
python run_experiment.py <book_key>
```
