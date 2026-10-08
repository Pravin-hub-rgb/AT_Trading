# flip_quality beats the shipping book on all three books in its own family

Date: 2026-10-08. Engine post-C17. Harness: `exp_mode_confirm2.py`.
Nothing promoted by this file. **The four candidate books stay registered and
pinned, and this file changes one line of their status — see the correction
section.**

## The gap the owner found

`exp_mode_confirm.py` reported that all four mode candidates "fail check 2, the
second lane, out of sample". The owner asked the right question: **was the
shipping book itself in that comparison?**

It was not. Two problems, both mine:

1. **The lanes were the wrong family.** Check 2 used `champion_multi_sw10` and
   `utcsat_multi_sw10`. Those are `pivot_rule=origin`, no `exp_fs_entry_side`, no
   `exp_mltf` — a **different architecture**. The candidates were rejected on a
   book that does not resemble the one they modify.
2. **The shipping book was never tested anywhere.** It has no second lane in
   that run, so "the candidates failed and the champion passed" was not something
   the data said. It was something I implied.

## The right family

Three books share `fsent_champ_long`'s architecture — `pivot_rule`, FS entry
side, `exp_mltf`, swing, every risk knob:

| book | FS side | IS | OOS | OOS DD |
|---|---|---|---|---|
| **`fsent_champ_long`** (shipping) | long | 528 / +533.4R | 311 / **+239.6R** | 11.9 |
| `fsent_utcsat_long` | long | 525 / +465.0R | 310 / **+238.8R** | 11.9 |
| `fsent_champ_short` | short | 532 / +600.6R | 312 / **+239.5R** | 23.9 |

**All three net about 239R out of sample.** That is either a coincidence of the
era or the architecture carries the result.

## Result — each mode against its OWN family's base, out of sample

| mode | champ_long | utcsat_long | champ_short | wins |
|---|---|---|---|---:|
| `atr_low` | +41.1 dd 14.6 | +41.1 dd 14.6 | +44.3 dd 20.1 | 1/3 |
| `fd` | +37.2 dd 12.2 | +37.2 dd 12.2 | +51.7 dd 17.9 | 1/3 |
| **`flip_quality`** | **+4.8 dd 11.9** ✅ | **+4.8 dd 11.9** ✅ | **+54.0 dd 19.3** ✅ | **3/3** |
| `union` | +64.2 dd 18.2 | +61.8 dd 18.2 | +28.0 dd 27.4 | 0/3 |

### `flip_quality` is the only mode that holds, and it holds on all three

| | champ_long | utcsat_long | champ_short |
|---|---:|---:|---:|
| base net / DD (OOS) | +239.6 / 11.9 | +238.8 / 11.9 | +239.5 / 23.9 |
| **`flip_quality` net / DD** | **+244.4 / 11.9** | **+243.6 / 11.9** | **+293.5 / 19.3** |
| delta net | **+4.8** | **+4.8** | **+54.0** |
| delta DD | **0.0** | **0.0** | **−4.6 (better)** |

**Drawdown does not rise on any of the three, and falls on the short book.** That
is the property `atr_low`, `fd` and `union` all lack — every one of them buys its
gain with drawdown, which the halt governance rule disqualifies on its own.

`union` has the biggest numbers and wins 0 of 3 on the criterion, because its
drawdown is 18.2R against the base's 11.9R. `atr_low` wins only where its base is
already 23.9R. **`fd` is positive in all three but its drawdown rises on all
three** (12.2 against 11.9, twice).

## The answer to the owner's question

> is my book better than these in the same checks?

**On net, no** — `flip_quality` is ahead on all three books. **On drawdown, yes,
and that is what decides it.** Your book sits at 11.88R OOS; `flip_quality` sits
at the same 11.88R on both long books and 19.3R against the short book's 23.9R.

## And the result I was wrong about

`exp_mode_confirm.py` said all four were disqualified on the second lane. **That
was measured on the wrong family.** On the family that actually shares this
book's architecture:

- `flip_quality` is **not** disqualified — it wins 3 of 3
- `atr_low` and `fd` are partially disqualified (1 of 3 each, both on drawdown)
- `union` is disqualified on all three (drawdown)

The gate in `exp_mode_confirm.py` was correct and its inputs were wrong. The
`sibling` bug I fixed there was real, but fixing it was not enough, because the
lanes it checked were never the right ones.

## What would still have to be settled before adopting

Even for `flip_quality`, three things are open, and they are not small:

1. **The gain is small where it is clean.** +4.8R on both long books out of
   +239.6R is **2%**. The +54.0R on the short book is the only large number, and
   that book is a *different* architecture (FS short) with a 23.9R drawdown.
2. **The three books are the same data.** Three books agreeing is three readings
   of one series. That is not independence, and it is why the framework's
   instrument exists — no half-year period control has been run on this.
3. **`flip_quality` reads `chop_thresh`.** It is one of the branches
   `exp_repo_map.py` found had never been run, and `KNOB_BINDS_AUDIT.md`
   documents that `chop_thresh` is live in 13 registry books. This book sets
   `chop_thresh` implicitly — it was **removed** from this book's config on
   2026-10-07 as one of the four inert keys. **`flip_quality` needs that key
   back**, because the branch reads it and BP's default (58.0) is what would be
   inherited. That is a live decision, not a formality: it means the candidate
   is not the same configuration as the shipping book plus a mode string.

## Correction to make regardless of the adoption decision

`fsent_champ_long_mode_flip_quality`'s registry description currently says it
"fails out of sample on both second lanes (-7.0R champion, -4.1R utcsat)". **That
sentence is wrong** — those numbers are real but they were measured on a
different architecture, and on the correct family the arm is ahead on all three
books. The description should be corrected so the next reader is not sent to a
verdict that came from the wrong comparison.

**Nothing promoted.** `fsent_champ_long` unchanged at 528 / +533.37 / 13.42 IS
and 311 / +239.59 / 11.88 OOS.