# Queue sweep — P7, W1, and a correction on P1

> Run 2026-09-29. Harness `exp_queue_sweep.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## First, the correction: P1 was not run

The queue calls P1 (nested swing containment) "the sharpest falsifier on
the list." **I did not test it.** Letting legs nest changes *which marks
exist* — `btc_swing.py:150` and `walker.py:76 _enforce_alternation` both
have to change, which is an engine edit, not a post-hoc filter. Editing the
engine inside an experiment would move the control that every other harness
here refuses to move.

What this run actually measured for that slot was **window age**, which is
**W1's** question, not P1's. The two are conflated in the output below and
should not be read as one result. **P1 remains open and untested.**

The pool-vs-shipped comparison is also weaker than it looks: I drove
`SwingEngine` continuously instead of with the per-day reset, so the raw
pool came back at 30–31 pivots against 1,634–2,900 shipped swings. That
number is a harness artifact. The ZigZag comparison is unaffected and is
the one worth quoting.

---

## P7 — the 30-minute kill, confirmed

The queue's bet: *"if this is dead we will know in 30 minutes."* It is dead.

| Jaccard vs shipped chain | champ IS | champ OOS | utcsat OOS |
|---|---|---|---|
| ZigZag 3% | **0.0063** | 0.0134 | 0.0134 |
| ZigZag 5% | 0.0017 | 0.0037 | 0.0037 |
| ZigZag 8% | **0.0003** | 0.0010 | 0.0010 |

**Effectively zero overlap at every threshold, in both eras, on both lanes.**
A textbook ZigZag and the shipped chain find essentially disjoint pivots.

**What that means:** the shipped chain is a **segmentation**, and
segmentation is a parameterised choice — never a discovery. Anything found
on it is a property of the tiling, not of the market. This is the same
lesson as log 104's 2h plane test: the plane and the chain carry the edge,
and the parameters underneath them do not.

---

## W1 — late-window fade: a violent era-flip

| arm | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| skip window > 2d | **−301.9R** | +15.4R | **−328.7R** | +5.1R |
| skip window > 3d | **−283.0R** | **+17.1R** | **−303.2R** | +6.0R |
| skip window > 5d | −271.8R | +11.1R | −283.7R | −2.8R |
| skip window > 8d | −153.5R | +2.5R | −173.1R | −7.2R |
| skip window > 12d | −78.1R | +9.2R | −97.1R | +6.1R |
| skip window > 16d | +0.0R | — | +0.0R | +0.0R |

**In IS the old windows carry the entire book** — cut them and −300R goes.
**In OOS the young ones are better.** The sign flips between eras on every
threshold.

**And every cell is inside the null.** The largest `|dNet|` anywhere is
17.1R against **M = 193.4R** — roughly a tenth of it.

### A note on the M flag

The harness flags `|dNet| > M` two-sided, and in IS it fires at −301.9R.
**That is not evidence of anything.** The flag is reporting that the arm
destroyed the book, not that it found something. A threshold that is met by
"delete most of the P&L" carries no information, and the flag should not be
read as a pass on those rows.

### The age gradient, which is the durable part

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| p50 window age (days) | 2.51 | 3.11 | 3.36 | — |
| p75 cohort WR | **33.9%** | **29.0%** | — | **31.7%** |
| whole book WR | 30.0% | 28.0% | 30.8% | 29.6% |

**The oldest quartile of windows has a higher win rate than the book, in
all four cells.** So age is not a decay signal — the queue's own falsifier
for W1 ("a median age shift with no change in realised R means age is a
label, not a driver") is not the right reading either. Age is a *label
that points the opposite way to the intuition*: older windows are not
tired, they are the ones that worked.

This is consistent with P38's stale-decay-leg finding (+68.7R from stale
legs) and with P3-B, where `DEAD` never occurs because the LTF entry can
only fire while the parent is alive. **Three independent results now point
the same way, and none of them is tradable at the required size.**

---

## P4 — not run

`cap_days` is a literal `16` in three call sites of `v18_streak_halt.py`,
so sweeping it is an engine edit and needs its own re-registered run
separately from anything else. It is the one remaining free item that is
also unblocked in principle.

## Verdict

**P7 closed, negative and structural.** **W1 closed, era-flipped and inside
the null.** **P1 still open — it was not tested and this run does not speak
to it.** **P4 outstanding.**

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
