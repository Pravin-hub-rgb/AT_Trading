# How to run one experiment, end to end

Read this before adding a book. It describes enforced reality, not aspiration:
each step names the check that catches you if you skip it. Rules written as
prose did not survive a single session here. The checks did.

## 0. You are changing PARAMS, not the engine

`engines/htf_ltf/` is closed. One implementation, `unified.py`. If your idea
needs new engine code, that is an architecture change - stop and say so.

check: `backtest/checks/exp_single_engine.py`

## 1. Add one entry to EXPERIMENTS

In `backtest/tests/experiment_registry.py`. Copy the shape of a book you
already trust. Only the keys that differ from your base belong in `params` -
do not restate the core. A second copy of the core is how copies drift apart.

The base is applied for you: `BASE = {**BP, **cfg["params"]}`.

## 2. Confirm the knob is LIVE before believing the number

A knob that is accepted, configured and never read returns a plausible result
and changes nothing. That happened here: 62 registry entries set `exp_persist`
and the patched body had no hysteresis code at all.

check: `backtest/checks/exp_knob_wiring.py`

## 3. Run it

    cd backtest/tests && python run_experiment.py <your_key>

It prints n / gross / net / WR / DD and marks each pinned field OK or FAIL.
Read the FAILs. They are the point of running it.

## 4. Confirm the knob actually MOVED something

If the result is identical to your base, the knob is inert. Find that out
before spending an hour interpreting a number that did not change.

## 5. Record provenance, not just the number

Venue, basis (fine 1m fills or coarse 15m), and date go in the entry.

Every figure in this repo is Bybit PERP, `BTCUSDT_BYBIT`. `BTCUSDT` is
Binance spot and is not this market; measuring with it silently moves the data
window and the trade set.

If a number has no independent justification, say so in the pin. "Observed on
2026-10-02" is a weaker claim than "v18 spec says 352".

## 6. Verify the trade set, not just the count

n matching while gross and dd differ is not a match. Compare trade lists:

    "|".join("%s,%s,%s" % (t["entry_ts"], t["exit_ts"], t["r_multiple"]) for t in trades)

## 7. If the idea is a causality claim, test it

An audit here claimed the stop pivot was lookahead. Measured, it is causal -
40 of 40, `start_px` identical with and without the future.

check: `backtest/tests/exp_origin_lookahead.py`

The 1h bias to 15m execution containment rule:

check: `backtest/checks/exp_htf_bias_containment.py`

## 8. Before you commit

    cd backtest/checks
    python exp_single_engine.py
    python exp_knob_wiring.py
    python exp_htf_bias_containment.py

Plus the identity gate, which runs inside `run_experiment.py` and prints
IDENTICAL or DIVERGED. It must say IDENTICAL.

## Worked example: CHAMPION ENTRY-1

**Idea.** The causal stop reads the leg extreme up to and *including* the entry
bar, so the entry's own high or low can set the stop. Exclude it.

1. `unified.py` already had `pivot_rule`. Added one value, `leg_no_entry`:
   the slice ends at `_br_idx` instead of `_br_idx + 1`.
2. The knob wiring check reported it LIVE.
3. Measured: 500 trades / +445.19R. It MOVED - against leg's 499 / +355.72R.
4. Trade lists hashed and compared. 497 of 500 stops identical to the origin
   book, 0.03R apart. That is the finding, and it contradicted the existing
   C16 audit, so the doc was corrected.
5. All checks green.

A new book, no new engine, and a claim in the audit corrected on the way past.

## What not to do

- Copy an engine file to try a variation. That produced three divergences this
  session and the halved-PERSIST artefact.
- Pin a number you saw rather than one you can justify. Two such pins were
  deleted this session for exactly that.
- Re-anchor a stale pin to whatever the code prints today. That converts a
  check into one that cannot fail.
- Trust n alone. It matched while dd differed by 16R.
- Read one source file and conclude. The line that mattered was three lines
  from the line being read.
