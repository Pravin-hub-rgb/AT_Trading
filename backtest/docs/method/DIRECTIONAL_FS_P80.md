# P80: directional FS — **CLOSED AT P82, NOT SIGNIFICANT IN ANY CELL**

> **PERMUTATION TESTED AT P82 (`method/PERMUTATION_P82.md`).** Every cell fails:
> champion IS p = 0.6895 and 0.8590, champion OOS p = 0.9197 and 0.7712,
> utcsat IS p = 0.3022. **The four-of-four positive result and the clean
> period partition were a difference of two large, similar numbers — a swap
> of ~400 trades for ~400 trades. Closed.** P80's numbers below are correct
> and reproduce; the interpretation did not survive.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **This is the first architecture in the round that is positive in all four
> cells AND survives the period partition in every one of them.**

## The idea, and where it came from

P78 found the champion's OOS **long** side is not weak, it is absent —
162 trades for **+1.8R at PF 1.22** — while the FS hybrid's long side is
199 trades for **+93.3R at PF 2.44**. The owner's proposal was to take the
FS trigger on that one side and leave the champion's break entries on the
other:

```
champion      long = break,  short = break
FS hybrid     long = FS,     short = FS      (P73 — dead, 3-5 in IS)
THIS          long = FS,     short = break   (the owner's idea)
              long = break,  short = FS      (the mirror)
```

P75 established the two books are 99.8% disjoint, so this is not a blend of
two views of the same trades — it is one trigger on one side and a different
trigger on the other.

## Result — 4 of 4 cells positive, and the partition holds everywhere

| arm | champ IS | utcsat IS | champ OOS | utcsat OOS |
|---|---|---|---|---|
| **FS long, break short** | **+184.8R** 6-2 ✅ | **+42.5R** 5-3 ✅ | **+172.9R** 4-0 ✅ | **+154.8R** 4-0 ✅ |
| break long, FS short | **+237.2R** 6-2 ✅ | **+137.7R** 5-3 ✅ | +160.3R 4-0 ✅ | +176.1R 4-0 ✅ |
| FS long, FS short (P73) | +79.4R **3-5** ❌ | **−78.2R** 2-6 ❌ | +163.4R 4-0 | +138.7R 4-0 |

The champion lane in full:

| arm | era | n | net | R/trade | PF | WR | dNet | partition |
|---|---|---|---|---|---|---|---|---|
| break long, break short | IS | 500 | +325.8R | +0.652 | 2.38 | 30.0% | — | — |
| **FS LONG, break short** | IS | **522** | **+510.5R** | **+0.978** | **3.89** | **41.6%** | **+184.8R** | **6-2** |
| break long, break short | OOS | 279 | +70.1R | +0.251 | 1.59 | 28.0% | — | — |
| **FS LONG, break short** | OOS | **309** | **+243.1R** | **+0.787** | **3.30** | **37.5%** | **+172.9R** | **4-0** |

## The thing that matters most

**The directional version is BETTER than the full-FS version it came from.**

| | full FS (P73) | FS long only (P80) |
|---|---|---|
| champ IS partition | **3-5** ❌ | **6-2** ✅ |
| champ IS dNet | +79.4R | **+184.8R** |
| champ OOS PF | 2.81 | **3.30** |

**Changing the trigger on ONE side turned a candidate that failed the
partition 3-5 into one that passes it 6-2, and raised the OOS profit factor
from 2.81 to 3.30.** Full FS over-applies: it replaces the short side too,
and the champion's short entries were working — they carry +68.4R in OOS at
PF 2.10 with no help.

**So the owner's instinct was not merely right, it was more precise than the
thing it was derived from.** The champion does not have an FS problem; it has
a long-side FS problem.

## Both directions work, which is the strongest signal here

`FS long` and `FS short` both clear the criterion, in both lanes, in both
eras, with 6-2 and 5-3 in IS and 4-0 in OOS. The mirror is not a sanity
check that failed — it is a second architecture with the same shape.

**`break long, FS short` clears M** at +237.2R on the champion lane
(123% of the null). `FS long, break short` reaches 95% of M at +184.8R.

**Why a result that fails the null can still be the more interesting one:**
M = 193.4R is a two-year whole-book null. The directional arms move ~40–50
trades relative to the champion, so a net built from a small change is not
measured against the right null. That is not a licence to ignore M — it is a
reason the correct bar for this arm is the **paired bootstrap over the trade
differences**, not the whole-book null. That measurement has not been run.

## What is still missing

**One test, and it is the one that decides this:**

> **The paired bootstrap.** Both books share most of their infrastructure and
> differ in a few dozen trades. Resampling the *difference* is the correct
> significance test for a change of this size, and it is cheap. Until it
> runs, "+184.8R" and "+237.2R" are large numbers without a distribution.

Also outstanding, in order:

1. **Both lanes are the same data.** Their agreement is encouraging and is
   not independence.
2. **`FS SHORT` was pre-registered as the mirror so the result would not be
   attributed to "FS" in general — and it passed.** That is the strongest
   internal check available and it held.
3. **No threshold was searched.** Four arms, fixed in advance, family-wise.
   Nothing is selected on the numbers.
4. **The trigger change is Causal.** P79's prefix invariance test passed at
   100% across 13,201 swing comparisons on the same chain these entries are
   drawn from, and `fs_at_idx` is the bar on which `process_bar` first
   declared the structure.

## Status

**NOT ADOPTED.** Everything else in the round that reached this far failed at
least one gate; this passes both of the gates it has been given, and has one
left.

**Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS. Nothing in production
touched.** But this is the first arm in the round where the honest
recommendation is "run the significance test, not the next idea" — and that
is a different place to be than anywhere else in P55–P80.
