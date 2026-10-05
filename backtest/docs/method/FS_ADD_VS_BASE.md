# FS ADD vs BASE — the book numbers, and what they actually mean

The user asked the right question: *base vs result, what is the delta?* The
earlier runs reported "earns +X R" for a subset, which is not the book. This
run reports the book.

Design as the user specified it: **1x everywhere, no exits.** At FS, if the
swing bucket is good, add 0.5. What happens to the book?

## BASE vs ARMED

### is/champion — base 500t, +325.8R, WR 27.8%, PF 1.81, DD 27.7

| Arm | adds | gross | cost | **DELTA** | armed book | DD | PF |
|---|---|---|---|---|---|---|---|
| CTRL add_BAD (bottom bucket) | 105 | +30.4 | 9.4 | **+20.9** | +346.7 | 27.7→29.6 | 1.79 |
| **CTRL add_any (all open)** | 314 | +131.8 | 24.5 | **+107.3** | **+433.1** | 27.7→41.7 | 1.87 |
| add_M2 (top third) | 210 | +101.6 | 15.1 | **+86.5** | +412.3 | 27.7→40.9 | 1.90 |
| add_wide (top half) | 157 | +88.5 | 11.7 | +76.8 | +402.6 | 27.7→40.0 | 1.90 |
| add_slow (bars_fs) | 105 | +97.4 | 11.5 | +85.9 | +411.7 | 27.7→39.1 | 1.93 |

### is/utcsat — base 454t, +358.9R, PF 2.01, DD 21.2

| Arm | adds | gross | cost | **DELTA** | DD |
|---|---|---|---|---|---|
| CTRL add_BAD | 98 | +29.0 | 7.9 | **+21.1** | 21.2→24.6 |
| **CTRL add_any** | 291 | +129.1 | 22.2 | **+106.9** | 21.2→38.3 |
| add_M2 | 194 | +100.8 | 14.4 | **+86.4** | 21.2→35.8 |
| add_wide | 146 | +80.0 | 11.4 | +68.5 | 21.2→34.9 |
| add_slow | 106 | +92.8 | 12.0 | +80.8 | 21.2→34.0 |

### oos/champion — base 279t, +70.2R, PF 1.34, DD 53.2

| Arm | adds | gross | cost | **DELTA** | DD |
|---|---|---|---|---|---|
| CTRL add_BAD | 60 | +21.7 | 2.8 | **+18.9** | 53.2→57.3 |
| **CTRL add_any** | 179 | +50.4 | 7.5 | **+42.9** | 53.2→66.4 |
| add_M2 | 120 | +29.9 | 4.8 | **+25.1** | 53.2→62.3 |
| add_wide | 90 | +32.4 | 3.2 | +29.2 | 53.2→58.0 |
| add_slow | 64 | +17.9 | 3.0 | +14.9 | 53.2→64.3 |

### oos/utcsat — base 253t, +60.2R, PF 1.33, DD 29.4

| Arm | adds | gross | cost | **DELTA** | DD |
|---|---|---|---|---|---|
| CTRL add_BAD | 53 | +15.8 | 2.4 | **+13.4** | 29.4→34.1 |
| **CTRL add_any** | 158 | +41.6 | 6.7 | **+34.9** | 29.4→37.3 |
| add_M2 | 106 | +25.3 | 4.3 | **+21.0** | 29.4→32.7 |
| add_wide | 79 | +31.8 | 2.8 | +29.0 | 29.4→32.0 |
| add_slow | 59 | +10.3 | 2.9 | **+7.4** | 29.4→36.1 |

## What this means — and it is not good news for the idea

**The delta is positive in every arm, every cell. That is exactly why I ran
the controls.**

- **CTRL add_any beats add_M2 in all four cells** (+107.3 vs +86.5, +106.9
  vs +86.4, +42.9 vs +25.1, +34.9 vs +21.0). Adding 0.5 to *every* trade
  open at FS earns more total R than adding it only to M2's "good" bucket.
- **CTRL add_BAD is also positive everywhere** (+20.9 / +21.1 / +18.9 /
  +13.4). Adding to the *worst* bucket — the swing that looked bad — also
  makes money.

So the +R is real, but it does not come from the bucket. It comes from the
fact that a trade open at FS usually keeps going, whoever it is. The bucket
is not selecting anything; it is just deciding **where to stop adding**, and
it stops early enough to leave money on the table.

The permutation null agrees: in `exp_fs_time_decision.py`, `mag_atr` ADD sat
at the 27th / 12th / 21st / 17th percentile of a 200-draw shuffle — i.e.
M2's top bucket is **no better than a random third**. The per-trade figures
here are consistent with that: the top bucket is more efficient *per add*
(+0.41R vs +0.34R), but that only reflects the bottom bucket dragging
`add_any` down, not the top bucket being special.

**This is `monster_sizing` M1's trap in new clothes.** The repo already
condemned M1 for exactly this: "its gain is 1.5x leverage, not selection."
The FS add is the same shape — size up during a move, gain R, but the gain
does not come from knowing which moves are good.

## The cost, stated plainly

The add is not free. Every cell pays:

| Cell | base DD | add_M2 DD | add_any DD |
|---|---|---|---|
| is/champion | 27.7 | 40.9 | 41.7 |
| is/utcsat | 21.2 | 35.8 | 38.3 |
| oos/champion | 53.2 | 62.3 | 66.4 |
| oos/utcsat | 29.4 | 32.7 | 37.3 |

Max drawdown rises **1.3× to 1.7×** in every cell. So the honest summary of
"add 0.5 at FS" is: **more R, materially more drawdown, and none of it
attributable to the bucket condition.**

## Verdicts

- **EXIT at FS: dead** (4/4, from `method/FS_TIME_DECISION.md`) — every subset's
  remaining R is positive, so exiting always gives up money.
- **ADD at FS: positive R, but NOT selection.** `add_any` beats `add_M2`
  4/4, and `add_BAD` is positive 4/4. The bucket condition adds nothing; it
  is drift plus leverage plus drawdown.
- **M2 at FS: null 4/4** in both directions.

## Status

**NOT ADOPTED.** Nothing was added or exited; this is measured on the
existing book. If someone wants the +R anyway, the honest version of the
trade is "scale up 0.5 on every trade open at FS" — and that should be
judged as a leverage decision with a 1.3-1.7x drawdown cost and a live
size-state implementation, not as a smarter entry.

## Files
- `backtest/tests/exp_fs_add_book.py` → `_fs_add_book.json`
- `backtest/docs/method/FS_TIME_DECISION.md` — per-trade + null, both branches
