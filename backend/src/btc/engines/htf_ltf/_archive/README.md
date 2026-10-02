# Archived engines

The two `_real` modules here are the archived implementations. They are NOT
imported by production: `btc_routes.py` runs `unified.py`.

`../v18_streak_halt.py` and `../v19_champion.py` are shims that re-export
these, because roughly a hundred research scripts across `backtest/`,
`backend/debug/` and `backend/tests/` import those two paths by name and their
numbers are cited in docs. Archiving without shims broke all of them - caught
here when the truncation test failed to import. The shims restore every
attribute, so those scripts work again and production still has exactly one
engine.

## v18_streak_halt.py

The v18 construction. Its pin - max_positions=1, exp_persist=0,
exp_causal_sl=0, v18 params, v18 swing chain - is 352 trades, which is the
centre of v18's COUNT_BAND=(348,358). That pin is now checked through
`unified.py`, which reproduces it with the same three flags.

`backtest/checks/exp_knob_wiring.py` and `run_experiment.py`'s identity gate
both build from `unified.py`. Nothing builds from this file.

## v19_champion.py

The PRE-C16 book, and the origin-pivot research baseline. Superseded, not
wrong: the origin pivot is a real stop placement, it is simply the placement
the shipping strategy does not use.

Verified byte-identical to `unified.py` before archiving, on all three pivot
rules, trade for trade including exits, R and stop price:

    pivot_rule        v19_champion.py     unified.py
    origin            500  +445.22         500  +445.22    IDENTICAL
    leg               499  +355.72         499  +355.72    IDENTICAL
    leg_no_entry      500  +445.19         500  +445.19    IDENTICAL

`unified.py` carries every parameter this file had, plus `max_positions`,
`exp_persist` and `pivot_rule` as explicit arguments rather than hardcoded
values. So there is nothing here that the live engine cannot reproduce.

To restore: move the file back one level and re-point the import in
`btc_routes.py`.
