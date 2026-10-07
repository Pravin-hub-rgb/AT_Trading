# Knob audit: which of fsent_champ_long's knobs actually shape it

Date: 2026-10-07. Harnesses: `exp_knob_binds.py`, plus the two follow-ups
recorded below. Engine post-C17.

METHOD
======
Drive each knob to a value that cannot mean what the book has - not a
neighbour, a different world - and compare the resulting trade list to base
field by field. A knob that leaves the list byte-identical is INERT at this
operating point. The size of the change on the knobs that do move is their
weight in the book.

INERT (4)
=========

| knob | book value | probe | verdict |
|---|---|---|---|
| `atr_low_thresh` | 0.35 | 0.99 | INERT |
| `chop_thresh` | 58.0 | 0.0 | INERT |
| `exp_mltf` | True | False | INERT **at max_positions=0 only** |
| `window_end` | "exit" | "r_touch" | INERT - see the coupling below |

BINDS (10), with the cost of breaking each
==========================================

| knob | probe | d trades IS/OOS | d net R IS/OOS |
|---|---|---|---|
| `atr_high_thresh` | 0.0 | +136 / +48 | +124.3 / -49.0 |
| `cooldown_bars` | 0 | +153 / +95 | **-172.1 / -99.2** |
| `exp_fs_entry_side` | "" | -25 / -23 | **-244.9 / -173.6** |
| `exp_partial_r` | 1.0 | +83 / +40 | -261.0 / -100.9 |
| `exp_persist` | 0 | -3 / +14 | **-66.1 / -5.0** |
| `ext_stop_r` | 1.5 | -51 / -36 | -31.2 / -61.0 |
| `htf_rr` | 2.0 | -30 / -22 | +8.6 / -55.9 |
| `max_consecutive_losses` | 0 | +47 / +26 | +33.2 / +31.3 |
| `pivot_rule` | "origin" | -3 / -1 | -68.4 / -0.8 |
| `sl_buf_atr` | 0.0 | -3 / -3 | **-94.0 / -85.5** |

The three that carry the book are `exp_fs_entry_side` (the whole thesis -245R
without it), `cooldown_bars` (-172R IS) and `sl_buf_atr` (-94R IS). `ext_stop_r`
at 1.5 costs 31-61R, which is the trap described in the registry entry.

NOT IN THE EFFECTIVE CONFIG: `exp_cap_days`, `sl_mode`. They are engine function
defaults, absent from `BP`, so they are not carried by the book and cannot drift.

## WHY "INERT" IS NOT "DEAD" - three different reasons, three different answers

This is the part worth keeping. A knob that does not move the number today may be
live code that this book has switched off through some *other* setting, and
describing that as dead would be a lie that costs someone a strategy later.

**1. `atr_low_thresh` and `chop_thresh` are mode-gated.** Measured across modes:

    mode=atr_high    atr_low_thresh IDENTICAL   chop_thresh IDENTICAL
    mode=atr_low     atr_low_thresh DIFFERENT   chop_thresh IDENTICAL
    mode=chop        atr_low_thresh IDENTICAL   chop_thresh DIFFERENT
    mode=atr_both    atr_low_thresh IDENTICAL   chop_thresh IDENTICAL

The engine reads each only under the mode that uses it. This book runs
`mode="atr_high"`, which routes on `atr_high_thresh` alone, so both are inert by
construction. They come alive if `mode` changes, not if the threshold does.

**2. `exp_mltf` is knob-gated, and is LIVE.** This is the one that would have
been got wrong by trusting the audit table:

    max_positions=0 : exp_mltf True vs False -> IDENTICAL   n 528 vs 528
    max_positions=1 : exp_mltf True vs False -> DIFFERENT   n 528 vs 355

`exp_mltf` is inert only because `max_positions=0` already disables the position
gate the knob wraps. At `max_positions=1` it removes 173 trades. **It must stay in
the config**, and it must not be described as removable.

**3. `window_end` is value-collapsed against `ext_stop_r`.** `_r_touch_end()`
short-circuits to `trade["exit_ts"]` when `ext_r <= 0`, and `window_end="exit"`
also uses `exit_ts`, so at `ext_stop_r=0.0` the two settings are the same code
path:

    ext_r  window_end=r_touch          vs "exit" same era
    0.0    IS 528 / +533.4              IDENTICAL
    1.5    IS 341 / +290.2              different (-187 trades)
    3.0    IS 528 / +533.4              IDENTICAL
    8.0    IS 528 / +533.4              IDENTICAL

At `ext_stop_r=3.0` it collapses too, for a different reason: `htf_rr=3.0`, so
`r_touch` looks for 3R and the trade exits at its own 3R target first. **So
`ext_stop_r` and `window_end` are the same threshold twice whenever
`ext_stop_r <= htf_rr`.** Harmless on this book, which uses `"exit"`, but a
future `window_end="r_touch"` on this config would silently get `"exit"`
behaviour. Recorded so it is a known coupling and not a surprise.

## WHAT WAS CHANGED, AND WHAT DELIBERATELY WAS NOT

**Changed:** `ext_stop_r` 3.0 -> 0.0 on `fsent_champ_long`, with the reasoning and
the re-test evidence written into the entry. Verified: pins unchanged, 0
mismatches.

**Not changed, on purpose:** `atr_low_thresh`, `chop_thresh` and `exp_mltf` are
left written out at their current values.

An inert knob written explicitly is pinned. The same knob omitted inherits
`BP`, and `BP` is shared by every book in the repo and does move - its
`chop_thresh` is already overridden once, to 58.0, precisely because that is a
production tuning. Deleting these fields would buy tidiness and pay with a silent
dependency on a global that other work is known to change. The one knob that
genuinely had to move is `ext_stop_r`, and it moved to an explicit `0.0` - never
to nothing, because `BP` carries `1.5` and that value binds for 51 trades IS and
36 OOS.

The audit's value is that nobody has to re-derive this. `chop_thresh` in
particular has been re-measured at least four times across this repo's history;
it is inert for a reason that is now written down in one place.
