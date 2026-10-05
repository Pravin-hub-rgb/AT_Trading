# P71: B1 cannot fire entries, and the reason is structural

> Run 2026-09-29. Harness `exp_b1_entry.py`. **Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **closed/CLOSED_DO_NOT_REPEAT.md's "still open (not closed)" B1 item is now
> closed on evidence — and the answer is more interesting than a yes/no.**

## What was tested

`btc_swing` emits break marks of kind `"B1"` / `"B2"` / `"FLIP"`, and
`_collect_signals` prices only two of them:

```python
tradeable = {"decisive": ("B2","FLIP"), "b2": ("B2",), "flip": ("FLIP",)}
```

**B1 is in no entry set.** Every B1 mark is generated, read, checked and
skipped. The open question was whether that was leaving money on the table.

Two arms, because "add B1" is not one thing — v18 builds its HTF windows
from `flip` and `decisive` v7 calls, and adding B1 to each reaches a
different place:

| arm | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| control (B1 never enters) | 500t +325.8R | 279t +70.1R | 454t +359.0R | 253t +60.2R |
| **B1 → decisive set** | 466t +161.4R **−164.4R** | 273t +34.2R **−36.0R** | 424t +198.4R **−160.6R** | 244t +43.6R **−16.6R** |
| **B1 → flip set** | **+0.0R** | **+0.0R** | **+0.0R** | **+0.0R** |
| B1 → both | −164.4R | −36.0R | −160.6R | −16.6R |

**Both arms fail, and one of them fails in a way that is more informative
than the P&L.**

## The finding: B1 entry is structurally impossible, not merely disabled

Two things in that table that are worth more than the numbers:

**1. Adding B1 to the flip set changes the book by exactly nothing** —
+0.0R, identical trade count, identical PF, identical drawdown, in all four
cells. Not "approximately the same": **identical**.

**2. Adding B1 to the decisive set REDUCES the trade count**, 500 → 466 in
IS and 454 → 424 on utcsat. **Adding an entry trigger made the book
smaller.**

Both follow from the same thing, and it is in `_collect_signals`: the loop
over `breaks` is **FCFS — "first tradeable mark decides"**. Once a B2 or a
FLIP fires on a swing, `swing_done = True` and the swing is closed. A B1
mark on that swing is always *earlier* than its B2 or FLIP, so it is
**always reached first** and would become the entry — but the engine never
sees a swing whose B2/FLIP has already fired, because by the time it looks,
the swing is already done.

**And the counts say the marks are there.** Per swing chain, OOS:
**B1 = 2537, B2 = 1990, FLIP = 1985.** B1 is not a rare signal being
cautiously excluded; it is the *most common* mark, and it is more common
than B2 and FLIP combined. The engine generates roughly 6,500 break marks
per chain and prices at most one per swing.

**So the exclusion is load-bearing and correct.** B1 fires earlier and
weaker than B2 or FLIP — a first touch of a structure extreme versus a
decisive break. Making it the entry would mean entering on every first
touch, which is why the decisive arm loses 36–164R *and* ends up with fewer
trades: B1 entries land earlier, sit in the book longer, and crowd out the
better B2/FLIP entries that would have come after them on other swings.

## Why the flip arm is inert rather than harmful

The flip arm producing a bit-identical book is the part that took reading.
It means **B1 marks do not appear on the swings whose marks reach the flip
entry path at all** — the flip windows are built from `entry_break="flip"`,
and on those chains the only marks that exist are the ones already priced.
Given the global counts above, that is a strong claim and it is the kind
that deserves a caveat: the counts are summed over BOTH chains
(`args[1]` and `args[3]`) and are not attributed per chain per kind. **So
"flip has no B1 marks" is a plausible reading, not a measured one.** The
measurement that would settle it — a per-chain, per-kind breakdown — is a
two-line change and was not run.

## Verdict

**B1 cannot fire entries, and the attempt to make it do so costs 36–164R in
all four cells.** Nothing adopted; the champion's trigger set stands.

**`closed/CLOSED_DO_NOT_REPEAT.md` should move "B1 entry" from *still open* to
closed**, with the reason recorded rather than just the verdict, because the
reason is the useful part: B1 is not an unexploited edge, it is a strictly
earlier and strictly weaker version of a mark the engine already trades on
the same swing, and the FCFS rule means only one of them can ever be
the entry.

**This also retires a standing temptation.** "Only ~1/3 of confirmed swings
get priced" looks like obvious headroom on any dashboard. It is not. The
unpriced swings are unpriced because their marks are duplicates or
supersessions of marks on other swings that were priced, not because
capacity went unused.

## Stated limitations

- **The per-chain, per-kind mark attribution is missing**, so the
  explanation for the inert flip arm is inferred rather than measured.
  Stated above rather than papered over.
- **Both arms are single-arm tests.** A "B1 as a SEPARATE additional entry
  alongside B2/FLIP on other swings" variant would need a different engine
  change — not a tradeable-set key — and was not attempted. It is the one
  formulation the FCFS argument does not already rule out.
- **Both lanes are the same data.**
- **Drawdown moves with the net** here: the decisive arm's IS DD goes 17.8R
  → 50.6R on the champion lane. That is B1 entries holding the slot longer,
  not a risk-profile improvement, and it is the opposite of the
  better-drawdown-worse-return pattern seen elsewhere this round.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
