# RANGE PEAK × NARROW WIDTH — mechanism found, gate FALSIFIED

Two studies, one question, run end to end. **The mechanism was found and it
is real. The gate built from it fails 4/4 and must not be adopted.**

Harnesses: `exp_range_pos_width.py` (2D grid) → `exp_range_verdict.py`
(pre-registered rule, applied in code) → `exp_range_mechanism.py` (MFE/MAE
forensic) → `exp_range_gray.py` (path-true GRAY test, full metrics).

---

## Part 1 — The 2D grid: 7 of 27 pre-registered comparisons survive

Range position quartile × range-width tercile, windows 4h/1d/3d/1w, judged
on **trimmed mean** (not avgR — these books are tail-concentrated, Rule 13).
Survivor rule fixed before the run: same sign in both eras, monotone in ≥3 of
4 cells, extreme cells n≥15. **7/27 survived**, including the user's original
"edges beat the middle" hypothesis in 3 of 4 lanes.

## Part 2 — Mechanism: width sets the SIZE of the payoff, not the hit rate

Peak-position (top-quartile) trades, 3d window, MFE/MAE in R:

| | tight (w0) | normal (w1) | **wide (w2)** |
|---|---|---|---|
| **OOS avg MFE** | 1.45R | 2.30R | **6.04R** |
| **OOS avg MAE** | 1.24R | 1.22R | 1.40R |
| OOS net (champion) | −1.3R | −3.9R | **+57.3R** |
| OOS net (utcsat) | −0.2R | −4.0R | **+65.2R** |

MAE is flat everywhere — **the risk is identical**. Only favourable
excursion moves, and it moves **4×**. So peak entries in a non-expanded
range are not "wrong more often"; they are right and then go nowhere. There
is no room for the trail to work, and this book's entire profit structure
lives in the tail.

**This answers "why did peak entries era-flip":** the peak location never
stopped working — the *expanded-range* peak trades, the ones that actually
build the tail, are the load-bearing subset. When that subset's weight shifts
between eras, the aggregate peak bucket appears to flip.

## Part 3 — The GRAY gate: fails 4/4, decisively

Gate: gray (not skip) peak-position trades with `width <= 1123.2`. Trade runs
to completion, P&L suppressed to r=0, slot held, loss streak advances
(`exp_gray_streak=True`), cooldown untouched → path-true, cascade-free by
construction.

**Controls: all 4 reference ledgers exact** (500/+325.8, 454/+358.9,
279/+70.2, 253/+60.2). `seq_identical=True` and `cascade_term≈0` on every
streakON cell — machinery proven correct before any verdict is read.

### streakON results (the correct arm)

| Cell | trades | grayed | kept | net before → after | Δnet | cohort TRUE netR | cohort WR vs book |
|---|---|---|---|---|---|---|---|
| is/champion | 500 → 500 | 73 | 85.4% | +325.8 → +204.2 | **−121.6** | **+107.4** | **41.1% vs 27.8%** |
| is/utcsat | 454 → 454 | 76 | 83.3% | +358.9 → +217.5 | **−141.4** | **+127.0** | **42.1% vs 29.1%** |
| oos/champion | 279 → 279 | 46 | 83.5% | +70.2 → +66.4 | **−3.8** | −0.7 | 28.3% vs 27.2% |
| oos/utcsat | 253 → 253 | 42 | 83.4% | +60.2 → +53.8 | **−6.4** | **+2.1** | 28.6% vs 28.9% |

Supporting metrics move the same way — PF 1.81→1.55 (IS champ), 2.01→1.66
(IS utcsat), maxDD 21.2→24.9 (IS utcsat, worse), net/yr 97.8→59.3 (IS
utcsat), and ex-best5 collapses from **+113.5 → +18.4** (IS champion).

**Trade count does not change** (500→500 etc.) — that is gray working as
designed: the trade is still taken, only its P&L is suppressed. Queue losses
and replacement-slot cascade are **0.00** by construction, not by luck.

### Verdict: the gate DESTROYS R in 4/4 cells.

The gated cohort is **profitable** — +107.4R and +127.0R in IS — and its win
rate (41–42%) is **far above** the book's own (27.8–29.1%). It is a
better-than-average cohort that the gate would have deleted.

## Part 4 — Why the trimmed-mean verdict misled (the important lesson)

The grid said this cohort was weak (negative trimmed mean). It is not weak —
it is the **highest-hit-rate cohort in the book**. Trimming removes the top
and bottom decile, which is precisely where this cohort's small-but-frequent
winners sit relative to the book's few giant winners. So:

> **Judging a GATE on the trimmed mean is a category error.** The gate
> operates on absolute R. A cohort can have a worse trimmed mean than the
> book and still be the cohort carrying the book's P&L.

The 7/27 survivors were a real structural finding *about orderings*; they
were never evidence that any of those cohorts should be gated.

## Part 5 — The bug class re-confirmed (streakOFF)

| Cell | trades | net after | Δnet | cascade | seqID |
|---|---|---|---|---|---|
| oos/utcsat | 253 → **261** | +70.5 | **+10.3** | **+12.46** | **False** |
| is/utcsat | 454 → 453 | +208.5 | −150.4 | −10.14 | False |
| oos/champion | 279 → **289** | +71.9 | +1.7 | +3.29 | False |

streakOFF manufactures a fake gain (+10.3R in oos/utcsat) purely from the
freed slot admitting replacement trades. `exp_gray_streak=True` is
mandatory, exactly as the wick-gate work established.

## Two harness bugs found and fixed mid-study (both the wrong-cohort class)

1. **`entry_idx`/`exit_idx` are NOT c1h indices.** `entry_idx=204` resolves
   to 2023-01-09 for a trade entered 2023-01-02 (true index 50). The first
   MFE/MAE run measured a completely different cohort — visible as the
   impossible `MAE 0.00` across 32 trades. Fixed to timestamp lookup.
2. **Per-scope feature maps leaked between scopes.** The main loop built the
   maps per scope but left the last scope's in the module, so the IS arms
   looked IS trades up in the OOS table and flagged `gray 0` in IS while
   flagging normally in OOS. Fixed by re-seeding per cell.

Both are the same failure class this repo has been bitten by repeatedly
(wick-gate 15m/1h predicate confusion, Stage B cohort swap). Neither
survived to a reported number.

## Status

**NOT ADOPTED.** No production change, experimental flags remain default-off.
The mechanism finding (width sets payoff size, not hit rate) stands on its
own and is worth keeping. The gate is dead in all four cells.

## Files
- `live_stuff/tests/exp_range_pos_width.py` — 2D grid builder
- `live_stuff/tests/exp_range_verdict.py` — pre-registered rule, applied in code
- `live_stuff/tests/exp_range_mechanism.py` — MFE/MAE forensic
- `live_stuff/tests/exp_range_gray.py` — path-true GRAY + full metrics
- `live_stuff/tests/_range_pos_width.json`, `_range_pos_width_verdict.json`,
  `_range_mechanism.json`, `_range_gray.json`

