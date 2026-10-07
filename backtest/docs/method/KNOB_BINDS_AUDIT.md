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

All four verdicts are scoped to **this book's configuration**, and for
`chop_thresh` that scope is load-bearing - see the correction below.

| knob | book value | probe | verdict |
|---|---|---|---|
| `atr_low_thresh` | 0.35 | 0.99 | INERT (mode-gated) |
| `chop_thresh` | 58.0 | 0.0 | INERT **on mode="atr_high" only** |
| `exp_mltf` | True | False | INERT **at max_positions=0 only** |
| `window_end` | "exit" | "r_touch" | INERT - value-collapsed, see below |

BINDS (10), with the cost of breaking each
==========================================

| knob | probe | d trades IS/OOS | d net R IS/OOS |
|---|---|---|---|
| `atr_high_thresh` | 0.0 | +136 / +48 | +124.3 / -49.0 |
| `cooldown_bars` | 0 | +153 / +95 | **-172.1 / -99.2** |
| `exp_fs_entry_side` | "" | -25 / -23 | **-244.9 / -173.6** |
| `exp_partial_r` | 1.0 | +83 / +40 | -261.0 / -100.9 |
| `exp_persist` | 0 | -3 / +14 | **-66.1 / -5.0** (see the sweep note below) |
| `ext_stop_r` | 1.5 | -51 / -36 | -31.2 / -61.0 |
| `htf_rr` | 2.0 | -30 / -22 | +8.6 / -55.9 |
| `max_consecutive_losses` | 0 | +47 / +26 | +33.2 / +31.3 |
| `pivot_rule` | "origin" | -3 / -1 | -68.4 / -0.8 |
| `sl_buf_atr` | 0.0 | -3 / -3 | **-94.0 / -85.5** |

The three that carry the book are `exp_fs_entry_side` (the whole thesis -245R
without it), `cooldown_bars` (-172R IS) and `sl_buf_atr` (-94R IS). `ext_stop_r`
at 1.5 costs 31-61R, which is the trap described in the registry entry.

**Every delta above is measured against the SHIPPING configuration** -
`max_consecutive_losses=3`, `exp_persist=7`, `ext_stop_r=0.0` - each knob probed
alone from that base. That base matters and it is not a detail. The same probe
against a different base gives a different number: dropping `exp_persist` from
the shipping book costs 66.1R IS, but from the halt-off book it costs 61.7R IS,
because the halt re-sequences which trades the persist filter is even asked
about. Reading a delta off the wrong row of a grid is how a correct table gets
argued into a wrong number - the `exp_persist` row here and the halt row below
it are both true, and they are both true only against the base stated above.

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

### CORRECTION - `chop_thresh` is NOT dead in this registry

The first version of this file wrote the finding as a property of the repository
and that was wrong. It is a property of `mode="atr_high"`, and the difference is
worth +105R to +163R. Caught by the owner asking whether chop_thresh was really
being used here, which turned out to be the right question.

`chop_thresh` is read by eighteen `mode` branches in the router, among them
`mode="b2_vs_flip_chop"`. The registry census:

    mode=atr_high                215 book(s)   inert for chop_thresh
    mode=union                     2 book(s)   inert for chop_thresh
    mode OMITTED                   13 book(s)   inherit BP's mode=b2_vs_flip_chop
                                                        <- READS chop_thresh

`BP` carries `mode="b2_vs_flip_chop"`, and 13 books do not name `mode` at all, so
they inherit it and reach the branch at `unified.py:788`:

    elif mode=="b2_vs_flip_chop":
        use="b2" if ch > chop_thresh else "flip"

Measured on four of the 13, `chop_thresh` against 0.0, IS era:

    book                    mode inherited    as booked      chop=0.0     delta
    lb30_chop55_persist2    b2_vs_flip_chop   432 / +247.1   504 / +141.5  +105.6R
    lb30_w24_ext3.0         b2_vs_flip_chop   414 / +313.3   461 / +149.8  +163.5R
    lb30_halt0              b2_vs_flip_chop   485 / +280.5   551 / +154.2  +126.3R
    a4_w24_ext3.0           b2_vs_flip_chop   367 / +132.5   461 / +149.8   +17.3R

`lb30_chop55_persist2` is the clearest: the "chop55" in its name is
`chop_thresh=55`, and it carries +105R. So **13 registry books reach a live
`chop_thresh` by silent inheritance, and one of them is named after the knob.**
`exp_knob_binds.py` now prints this census before its verdict table so that an
INERT row can never again be read as a registry-wide claim.

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

**Also changed, 2026-10-07: the four INERT keys were removed.** `chop_thresh`,
`atr_low_thresh`, `exp_mltf` and `window_end` are gone from the entry. The
earlier version of this file argued for keeping them written out, on the grounds
that an inert knob written explicitly is pinned. That argument was right about
the principle and wrong about these four, because **omitting them inherits an
identical value in every case**:

    chop_thresh      book 58.0  ->  BP 58.0    identical
    atr_low_thresh   book 0.35  ->  BP 0.35    identical
    window_end       book exit  ->  BP exit    identical
    exp_mltf         book True  ->  BP absent  -> engine default, which is what
                                                this book already did

Verified by removing all four and re-running: trade lists **byte-identical on both
eras**, 528 / +533.37 IS and 311 / +239.59 OOS. The counter-book
`fsent_champ_long_nohalt` also re-derives exactly (575 / +566.58 / 15.13 IS,
337 / +270.91 / 14.16 OOS). The entry is now 10 keys instead of 14.

**The principle is unchanged, and it is why `ext_stop_r` was NOT removed.**
Omitting a key is not the same as turning it off. `BP` carries `ext_stop_r=1.5`,
which is a live filter blocking 51 IS / 36 OOS trades, so that one must be
written as an explicit `0.0`. Three of the four removed keys happened to be safe
only because nobody had moved their BP default yet — that is a fact about
today's `BP`, not a fact about the key, and it is the reason the comparison
above is worth running before deleting rather than after.

**When any of the four comes back:**
- `chop_thresh` / `atr_low_thresh` — if `mode` on this book ever changes to a
  chop- or atr_low-reading mode. 13 registry books already reach chop_thresh this
  way, carrying +105R to +163R.
- `exp_mltf` — if this book ever runs at `max_positions=1`, where it removes 173
  of 528 trades.
- `window_end` — if `ext_stop_r` ever rises above `htf_rr`, where "exit" and
  "r_touch" stop resolving to the same path.

`exp_knob_binds.py` prints the mode census above the verdict table and flags any
book that omits `mode`, so a future audit cannot produce an INERT row whose scope
has been dropped.
