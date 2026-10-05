# FS-TIME DECISION, BOTH DIRECTIONS — exit is dead, add is era-flipped

The user's design, both branches, tested per-trade against a permutation null.

**The design:** at FS (swing confirmation) the swing's geometry is legally
known. So — *swing is bad → exit right away; swing is good → add 0.5 here.*
A late-management action, not an entry filter. Structurally the right answer
to M2's look-ahead.

**Why this run exists:** the previous FS run measured only *aggregate*
remaining R per tercile. That is the same aggregation error M2 itself made —
an aggregate can be positive while individual trades are not, so it cannot
decide trade-by-trade. This run decides per trade, prices both directions, and
runs a 200-draw permutation null on the feature itself.

## A sign bug I introduced and fixed before reporting

My first pass flagged "BEATS NULL" on a **high** exit value. That was
backwards: **exiting GIVES UP the remaining R**, so a good exit is a *low*
one. The harness now labels correctly (`exit_giveup_R`, `exit_GOOD`,
`add_GOOD`) and the run was redone. The numbers below are from the corrected
run. Flagging this because it is the same class of error as the M2 problem
itself, and it would have flipped the conclusion.

## EXIT branch: dead, 4/4

Value = R given up by closing at FS. **Positive giveup = exit destroys money.**

| Cell | best exit feature | gives up | null mean | pctile |
|---|---|---|---|---|
| is/champion | `r_fs` low-third | **+3.6R** | +85.1 | 0.5% |
| is/utcsat | `r_fs` low-third | **+6.4R** | +84.5 | 1.5% |
| oos/champion | `r_fs` low-third | **+14.6R** | +34.9 | 21.5% |
| oos/utcsat | `r_fs` low-third | **+14.7R** | +29.6 | 28.0% |

Every exit value is **positive in all four cells**. There is no subset — on
any feature, in either tercile — whose remaining R is negative. The best
possible exit still gives up +3.6R.

The reason is in the header line of each cell: the total remaining R of the
population open at FS is **+263.7 / +258.2 / +100.9 / +83.2R**. Holding from
FS to exit is worth a great deal. There is nothing to escape from.

## ADD branch: one feature pays, and only in IS

Value = 0.5 × remaining earned on the selected trades.

| Cell | `bars_fs` add (top third) | null mean | pctile | verdict |
|---|---|---|---|---|
| is/champion | **+100.2R** | +45.1 | **100.0%** | ADD PAYS |
| is/utcsat | **+96.6R** | +42.2 | **99.5%** | ADD PAYS |
| oos/champion | +20.1R | +16.1 | 66.0% | null |
| oos/utcsat | +12.0R | +13.7 | 49.0% | null |

`bars_fs` = how many 15m bars elapsed between entry and FS, i.e. **how long
the swing took to confirm**. Adding half-size when confirmation was SLOW beats
a random null at the 100th and 99.5th percentile in IS.

It does **not** hold OOS (66th and 49th percentile). **2/4, IS-only** — it
fails the both-eras bar that every other candidate in this repo has been held
to, and the 4th time in this session that the IS-only result has not survived
OOS. Note the pyramid family is separately CLOSED (`V4 −111.3/−87.3`, no arm
passed both gates); this is a different trigger and was tested fresh, but it
would have to clear that bar on its own merits, and it does not.

## M2 itself, read legally: null in both directions, 4/4

| Cell | `mag_atr` EXIT | `mag_atr` ADD |
|---|---|---|
| is/champion | +60.8 (27.5%) | +30.1 (27.0%) |
| is/utcsat | +58.0 (24.0%) | +21.8 (12.0%) |
| oos/champion | +43.4 (66.0%) | +5.5 (21.0%) |
| oos/utcsat | +31.6 (55.5%) | +2.7 (16.5%) |

Swing magnitude, read at FS when it is legal, beats no null in either
direction in any cell. Combined with the retraction, the picture is now
complete: M2 is not merely unusable at entry, it carries **no information
once it becomes legal**.

## Verdicts

- **EXIT at FS: dead, 4/4.** Confirmed per-trade with a null, not just in
  aggregate. The population open at FS is worth holding.
- **ADD on slow confirmation: 2/4, IS-only, fails OOS.** Reported, not
  recommended.
- **M2 at FS: null, 4/4.** The family is closed on merit now, not just on
  causality.

## Status

**NOT ADOPTED.** Descriptive only — this run measures remaining R from the
existing book and prices hypothetical actions. No engine change, no gate, no
position was actually added or exited.

## Files
- `backtest/tests/exp_fs_time_decision.py` → `_fs_time_decision.json`
- `backtest/docs/method/FS_TIME_GEOMETRY.md` — the aggregate version of this test
- `backtest/docs/method/SMZX_LOOKAHEAD_RETRACTION.md` — the M2 problem
