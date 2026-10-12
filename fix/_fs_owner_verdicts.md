# FS — validation record and honest evidence

FS work closed 2026-10-12 on branch `fix/fs-and-pivot-breaks`.
Chain: **2844 → 2753 swings, 7712 → 7505 break marks.**

## What was actually reviewed by the owner, on the chart

| # | date | what was checked | verdict |
|---|---|---|---|
| 1 | **2023-01-23 10:30 → 09:45** | engine held the retired 08:30 pivot and marked 45 bars late; 09:45 crosses the 09:15 high 22698.5 | correct |
| 2 | **2023-07-11 16:45 → 17:15** | tightest case, +2 bars | correct |
| 3 | **2025-03-15 01:15 → 2025-03-16 18:30** | widest, +165 bars | correct |
| 4 | **2024-12-30 22:30 → 2024-12-31 00:45** | first four marks identical, only the ending moved onto a B2 at 23:30 | correct |

On 2025-03-15 the owner applied the rule himself: *"direction is down and we
are just looking for an up direction chop, which happened at 18:30."*

## Full evidence table — read this before quoting confidence

| check | result |
|---|---|
| **30 of 516** FS mark moves | reviewed on chart, all correct |
| **1 of 241** gone swings (2023-01-23) | reviewed, correct |
| **3 of 241** gone swings | reviewed, all correct |
| **6 of 6** owner-confirmed FS anchors | pass |
| **2754** B1 legs | 0 missing, 0 late |
| no-look-ahead | PASS |

**NOT 516.** That figure was over-claimed earlier in the session. The number
actually reviewed is 30 of 516. The remaining 486 were not looked at. Their
shape is inferred from the three that were, which is a sample, not a proof.

`_fs_mark_moves.csv` has all 516 rows sorted ascending, with a `bars` column,
so the unreviewed ones are easy to find if anyone wants to widen the sample.

## What the chain change is

A retired pivot means the next pivot is never crossed, so the leg completes on
B2 or FLIP instead. The swing survives with a different ending and the FS
stamp goes. That is **absorption, not deletion** — owner-confirmed on
2024-12-30, where the first four marks were identical and only the completion
moved.

## Known limitations, deliberately not fixed

**38 stale citations.** The engine aims at a pivot the chart no longer draws.
Marks are correct in every case; only `last_confirm_hit` is stale, and that
field is read by nothing on BTC — `btc_swing.py` ignores it and it is never
sent to the client. `exp_fs_breaks_pivot.py` check 2 reports them.

**2023-01-08 cites 07:30, not 07:45.** Its MARK is correct at 08:00 and
owner-confirmed. Fixing the citation needs the swallow-splice inside the
engine, which measured at 2551 swings / 2453 marks moved / anchors broken. Not
worth it for an invisible field.

**The freshness scan in `_check_chop` cannot fire.** See below.

## The tripwire is weaker than it looks

`exp_v7_freeze.py` was re-pinned to the approved chain. Re-proving it after
the re-pin, it caught nothing across three separate edits:

1. removed the duplicate-seal guard in the walker fix
2. shortened the freshness scan to one bar
3. disabled the freshness scan entirely, both branches

All three left the chain at 2753 / 7505 / identical sha.

**Disabling freshness outright changes nothing.** So the loop in `_check_chop`
is dead — the marks that this session fixed moved because of the *snapshot
removal* in the same commit, not the freshness change. That commit message
overstates its freshness half; it is correct but was not what did the work.

This is also why the original ARM1 bug slipped past the same fixture. The
fixture detects changes in mark count and position. It is not evidence the
engine is correct — `exp_fs_breaks_pivot.py` and the owner's chart are.

**Open question:** why cannot the freshness scan fire? The level it guards
appears to be spent by an earlier gate before `_check_chop` reaches it. Not
diagnosed. It does not affect any mark today, but it is a real loose end and
belongs in the next session's list.

## Branches

| branch | what |
|---|---|
| `fix/fs-and-pivot-breaks` | engine — the walker fix, the freshness/snapshot work, the MB metadata, the tripwire |
| `fix/insider-zigzag-display` | the chart line only. The engine fix is deliberately NOT on this branch |

## Files

- `fix/_fs_mark_moves.csv` — 516 moved marks, ascending, with bars moved
- `fix/_walker_stack_far.patch` — copy of the walker fix
- `fix/V_CHECKLIST.md` — V1 and V12 are now closed by this work; V2 (B2) and
  V13 are next
