# ENTER AT FS — M2 becomes legal, and turns out to be exactly backwards

The user's idea, and the cleanest result of this whole line of work.

## The idea

The engine enters on the first break mark (B2 or flip) — early, which is
precisely why M2 had to be forward-looking. The proposal: **stop entering on
B2/flip, enter on FS instead** (when the swing confirms). At that moment the
swing's final geometry is known by definition, so **M2 stops being
look-ahead and becomes an ordinary legal entry-time feature.**

This is the right way to attack the problem: not repairing the feature, but
changing when we enter so the feature becomes legal. So it was worth one
honest measurement.

## Two bugs I found and fixed mid-run

1. **Drawdown computed on sorted R.** The first pass sorted the R list before
   walking peak/drawdown, which is meaningless — every cell reported
   `max_dd 1.0`, i.e. just the largest single loss. Fixed to walk the curve
   in time order. (base is/champion max_dd is really 56.7, not 1.0.)
2. **Overlapping bucket bands.** The mid band was written `mag <= t2`, which
   re-included the small bucket — mid came out n210 instead of n105. Fixed to
   mutually exclusive bands.

Both were caught before any number was reported.

## Result 1 — FS-entry is a viable but much smaller book

*(gross `r_multiple`, not `net_r` — costs are not subtracted in this run, so
these are not comparable to the +325.8R net figures quoted elsewhere)*

| Cell | BASE (B2/flip) | missed if we wait | FS-ENTRY | FS-ENTRY avg R |
|---|---|---|---|---|
| is/champion | 500t, +445.2R, DD 56.7 | 186t (37.2%) | 314t, +151.1R, DD 47.8 | +0.481 |
| is/utcsat | 454t, +466.5R, DD 56.7 | 163t (35.9%) | 291t, +158.4R, DD 47.8 | +0.544 |
| oos/champion | 279t, +105.7R, DD 34.1 | 100t (35.8%) | 179t, +94.0R, DD 33.8 | +0.525 |
| oos/utcsat | 253t, +92.6R, DD 34.1 | 95t (37.5%) | 158t, +86.8R, DD 33.8 | +0.549 |

**~36–37% of the book disappears** if we wait for FS. What remains is smaller
but not obviously worse per trade — and in OOS the drawdown is unchanged
(33.8 vs 34.1) on a book 36% smaller.

This is a real trade-off, not a free win. Note also that 2900 swings exist in
IS and 1634 in OOS, all with an FS — so a *true* FS-only engine could in
principle take swings that never produced a B2/flip entry, which would be a
much larger book. That is not simulated here.

## Result 2 — the important one: M2 is exactly BACKWARDS

Entering at FS makes the bucket legal. Then, across all four cells, the
big-swing bucket is the **worst** one:

| Cell | small swing | mid swing | **BIG swing (M2's bucket)** |
|---|---|---|---|
| is/champion | n105, avg **+0.571** | n105, +0.654 | n104, avg **+0.216** |
| is/utcsat | n98, avg **+0.616** | n97, +0.845 | n96, avg **+0.168** |
| oos/champion | n60, avg **+0.923** | n60, +0.527 | n59, avg **+0.118** |
| oos/utcsat | n53, avg **+0.937** | n53, +0.629 | n52, avg **+0.073** |

Big swings give the **lowest** average R in 4/4. Small swings give the
**highest** in 3/4.

> M2's premise was "big swings are good". When you actually buy a swing
> *after* it has been confirmed big, it is the worst thing you can buy —
> because the move that made it big has already happened. M2's entire
> apparent power was the look-ahead.

This is the definitive answer, and it is stronger than "M2 is unmeasurable":
**M2's sign is inverted when it becomes legal.** Every earlier result — the
retraction, the FS-time geometry being flat, the null on both directions —
follows from this one fact.

## What the whole line of work established

| Step | Finding |
|---|---|
| entry + 1.5× | illegal — M2 reads the future |
| shuffle null | showed selection, but could not see look-ahead |
| retraction | the null is necessary, not sufficient |
| FS exit | dead 4/4 — everything open at FS is worth holding |
| FS add | +R, but `add_any` beat `add_M2` and `add_BAD` was also +R → drift, not selection |
| **FS entry** | **M2's sign inverts 4/4 — the look-ahead was the whole edge** |

## Status

**NOT ADOPTED.** No engine change, no new entry logic. This measures an
alternative entry timing on the existing book; it does not implement it.

If someone wants to pursue FS-entry, the open questions are: the 36% of
trades lost, whether a true FS-only engine can reach the 2900/1634 confirmed
swings rather than only the 314/179 that produced a B2/flip entry, and a
trail designed for a late entry. None of that is answered here.

## Files
- `live_stuff/tests/exp_fs_entry.py` → `_fs_entry.json`
- `live_stuff/docs/SMZX_LOOKAHEAD_RETRACTION.md` — the retraction this confirms
