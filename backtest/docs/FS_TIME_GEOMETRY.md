# FS-TIME GEOMETRY — the legal version of M2 works, and it is USELESS

The user's idea, and the result. This closes the loop on M2.

## The idea (correct, and worth testing)

M2 is the strongest sizing flag in the repo and it is forward-looking: it
reads the swing's `end_px`, which does not exist at the B2/flip entry
(`backend_check_wd_days.py:108` asserts `fs_at_idx >= seg.end_idx`).

The user's fix: **don't try to know the swing at entry — wait for it.** At
the moment the swing confirms (`fs_at_idx`), that same `end_px` is legally
known. So: entry → swing confirms → read the swing's true geometry → bucket
it → if the bucket is bad, **exit there and gray onward.**

This is a late-management action, not an entry filter. Nothing in it needs
information that doesn't exist at the moment it's used. Structurally it is
the right answer to a look-ahead problem.

## Feasibility: excellent

Measured on is/champion before designing anything:

- **500/500** trades have an FS
- FS **always** lands after the entry (median 9.2h, p25 5.5h, p75 11.2h)
- **62.8%** of trades are **still open at FS time** (64.1% / 64.2% / 62.5% on
  the other three cells)

So a large, genuinely actionable population exists, and it is actionable
precisely because the information is available exactly then.

## Result: the remaining R is FLAT — there is nothing to exit into

Remaining R = what is still at risk from FS to exit. That is exactly the
quantity an "exit at FS" rule would capture or give up.

| Cell | bucket | n | **R@FS (already banked)** | **REMAINING R** | final R |
|---|---|---|---|---|---|
| is/champion | low mag | 105 | +0.511 | **net +60.8** | +114.4 |
| | mid mag | 105 | +0.831 | **net +142.8** | +230.1 |
| | high mag | 104 | +2.179 | **net +60.1** | +286.7 |
| is/utcsat | low / mid / high | 98/97/96 | +0.580 / +0.770 / +2.497 | **+58.0 / +155.9 / +44.3** | — |
| oos/champion | low / mid / high | 60/60/59 | +0.122 / +0.791 / +0.848 | **+43.4 / +46.4 / +11.1** | — |
| oos/utcsat | low / mid / high | 53/53/52 | +0.108 / +0.864 / +1.017 | **+31.6 / +46.2 / +5.4** | — |

**high-mag minus low-mag, in REMAINING R:**

| is/champion | is/utcsat | oos/champion | oos/utcsat |
|---|---|---|---|
| **−0.000R** | **−0.131R** | **−0.535R** | **−0.491R** |

Zero in one cell, **negative** in three. The ordering is flat-to-inverted,
not a gradient you could trade on.

And the low-mag bucket's remaining R is **positive in all four cells**
(+60.8 / +58.0 / +43.4 / +31.6). So exiting all low-mag trades at FS would
**give up** 60.8R / 58.0R / 43.4R / 31.6R, not save it.

## Why — and this is the real finding

Look at the **R@FS** column. In is/champion the swing-magnitude buckets are
+0.511 / +0.831 / +2.179 at FS. Nearly the whole difference between the
buckets is **already banked by the time the swing confirms**. The remaining R
is flat because there is nothing left to differentiate.

> **M2's information is entirely retrospective.** By the time the swing is
> confirmed and its geometry is legal to read, the move it measures has
> already happened and is sitting in the P&L. Read at the entry, that same
> number "predicts" the trade — and that reading is exactly the look-ahead
> that makes M2 unusable.

This is the cleanest statement of the M2 problem found so far, and it is
consistent with everything else already on record: `mag_so_far` 0/6
("the threshold is unreachable mid-swing"), `ramp_so_far` 0/6 ("pure
leverage, the M1 trap"), send-time agreement 77.5% against a 95% bar.

## Verdict

**The FS-time exit rule is dead.** Not because the idea is unsound — it is
legally sound and highly feasible — but because the quantity it would act on
does not exist. A bucket that is bad *in hindsight* was not bad *going
forward*; it was simply a move that had already happened.

The corollary is the useful part: **there is no timing-based rescue for M2.**
Any rule that waits for the information waits too long, because by then the
information is about the past. That is a stronger and more useful negative
than "M2 has look-ahead" — it says the family is closed, not merely
currently unmeasurable.

## Status

**NOT ADOPTED.** No production change. This run is descriptive: it measures
R@FS and remaining R from the existing book and proposes no gate.

## Files
- `backtest/tests/exp_fs_time_geometry.py` → `_fs_time_geometry.json`
- `backtest/docs/SMZX_LOOKAHEAD_RETRACTION.md` — the M2 problem this closes
