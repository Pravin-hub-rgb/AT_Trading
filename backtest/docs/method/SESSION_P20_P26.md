# P20–P26 — a session of corrections. Five of my own errors, caught by the user.

`method/AGE_GATE.md` covers P20 alone. This covers P20–P26 and is worth more for
the process record than for the results.

Every headline number here came from code in this repo with pins
reproduced first. Where a result is negative it is reported as negative.
Five of the errors below were mine, found by the user pushing back on
something I had asserted.

---

## The spine: the user corrected the METHOD, not the answers

*"kitne lookback swings, ye sab main hi kar raha hun"* and *"koi bhi M
clear nahi hua, ye karna zaroori hai? research karo"* were both right and
both changed how every arm is now scored.

| # | What the user caught | What it was |
|---|---|---|
| 1 | "gray-with-held kabhi run nahi hua" | **I corrected myself**: every post-hoc filter is gray-with-held. True purge had never been run. P21 ran it. |
| 2 | "kon rule bana raha hai −27R bura hai? equity curve toh theek hai" | I made a per-year delta the killer. **My framing, not the user's ask.** |
| 3 | "lookback swings kitne" | `N_SWINGS=4` was an **arbitrary constant**, never justified. P23 swept it. |
| 4 | "decay price-action edge hai, time wala kamzor" | Correct — decay is structural; `age`/`nest1h` are clock-based. |
| 5 | "M karna zaroori hai? research karo" | **M is the wrong test for a filter** (below). Replaced with a permutation null. |

---

## P20 — the age CEILING (`method/AGE_GATE.md`)

`exp_max_swing_age` is a **ceiling** (refuse old windows); `age>0.5d` is a
**floor** (refuse new). Opposite shapes, and they do not compose.
Removing the ceiling **gains +100.7R IS on one lane and loses −144.8R on
another** — it is fitting the era. On 2 of 3 lanes it is better *removed*
out of sample. The champion has no ceiling, so its numbers are unchanged.

A reporting bug was caught mid-run: arms C/D printed `net_r(tr)`, the
unfiltered book, beside the filtered count. Caught because B and C showed
identical nets at different n — impossible. Fixed and rerun.

---

## P21 — TRUE PURGE vs SLOT-HELD (the never-run arm)

Every P14–P20 filter was **gray-with-slot-held**: the engine set
`busy_until` before the trade was inspected, so the next signal was
already blocked. A true purge rejects *before* the slot is taken.

| lane | era | B HELD | C PURGE | slot effect |
|---|---|---|---|---|
| champion | IS | +382.4R (353) | +353.8R (361) | **−28.7R** |
| champion | OOS | +74.6R (199) | +74.6R (203) | 0.0R |
| age25_dirmatch | IS | +378.2R (172) | +420.7R (178) | +42.5R |
| age25_dirmatch | OOS | +135.9R (117) | +125.8R (114) | −10.2R |

**Purging is not free money.** On the champion it is −28.7R: the signal
behind a filtered trade is not better than the filtered one. Held-slot was
the right methodology all along.

Engine note: with the champion's `exp_mltf=True` the `busy_until` check
is disabled outright (`if (not exp_mltf) and busy_until ...`).

---

## P22 — anatomy of the 500 (`exp_book_anatomy.py`)

Nobody had ever printed the book.

```
500 trades, +325.8R NET.  long 273 (+339.5R) / short 227 (+105.7R)
FLIP 251 (+362.8R)  B2 249 (+82.4R)
100% inside a 1h "flip" window; the signal must match window direction
trail 313 (+632.2R)  sl 187 (−187.0R)  -> no fixed target is ever hit
```

Exit is the **ratchet** (a new 15m swing raises the stop), not a 3R
target. `target` is computed at `v18_streak_halt.py:592` and **never read
as an exit condition**.


---

## P23 — how many swings? (`exp_decay_lookback.py`)

`N_SWINGS=4` swept across 2,3,4,5,6,8,10,12 x thresholds. **No lookback
wins decisively; the family is flat and 4 is not special.** In OOS,
`thr=0.75` beats `thr=0.90` (dNet +4.4 vs −10.5, DD 17.3 vs 34.3) — the
looser threshold looked better in-sample and **loses out of sample**,
which is exactly the trap of selecting on IS alone.

A second bug: `per` was computed as `net/n` instead of `(gross−net)/n`,
double-subtracting cost. Fixed before the numbers above.

---

## P24 — directional decay + the 1h chain (`exp_directional_decay.py`)

Two user ideas, both tested, both rejected.

| arm | IS dNet | OOS dNet |
|---|---|---|
| B 15m both sides (incumbent) | **+39.0** | **+9.7** |
| C 15m direction-specific | −31.6 | −0.8 |
| D 1h both | −64.5 | −12.1 |
| E 1h direction-specific | −40.4 | +8.4 |
| F 15m AND 1h | −78.9 | +10.3 |

**Blocking only the broken side is worse than blocking both** — a short
taken while buying structure fails is also a bad trade. Decay has only
ever been built on 15m legs; the 1h chain is worse, not better.

---

## P25/P26 — `M` was the wrong bar, and the replacement is weaker

**`M` (P5) is a move-block bootstrap of the book's own net** — the right
question for a *book*, the wrong one for a *filter*. A filter is a subset
of the same trades on the same days; comparing its net to a reshuffle
band throws the pairing away. The effect is that M is so wide that
**nothing can ever clear it**, which is a way of saying "never adopt
anything" while looking rigorous.

Replaced with a **permutation null**: mark as many trades at random as the
real filter did — same book, same outcomes, same size — destroying only
the link between rule and trade. `p = P(random dNet >= real dNet)`.

| arm | IS p | OOS p | both eras |
|---|---|---|---|
| **decay<0.75** | 0.000 | 0.021 | yes |
| **age>0.5d** | 0.002 | 0.020 | yes |
| **age>1.0d** | 0.030 | 0.012 | yes |
| **nest1h>0.25+age>0.5d** | 0.000 | 0.037 | yes |
| decay<0.90 | 0.000 | 0.402 | no |

**The honest caveat, stated because 8 of 8 arms pass in-sample:** the
book is profitable, so *any* filter removing losers scores well against a
random-removal baseline. Random is a strawman — nobody proposes removing
random trades. "REAL" here means only **"better than a same-size random
pick,"** a low bar that does **not** show the specific signal is
predictive rather than a generic shrinkage effect.

**Third bug, the worst of the session:** the first version computed
`p = P(null <= dNet)`, a lower tail. A good filter has positive dNet, so
that inverts the test and every verdict flips. Caught only because 8/8
arms reading p≈1.000 is not a plausible result. P25 additionally built
its 15m legs from synthesized 1m bars instead of the real `sw15`, so its
"15m" arm was a different filter whose dNet was **negative** (it removed
winners). Fixed and rerun; the table above is the corrected run.

---

## Where this leaves the champion

**Nothing adopted. No production change.** The champion is 500 trades /
+325.8R IS, 279 / +70.1R OOS, exactly as pinned.

`decay<0.75` is the most defensible candidate — structural, predicted by
P11 before the search, and the only idea of mine that survived the user
pushing back on it. It is still **not adopted**: it is post-hoc rather
than run through the engine as a pre-slot gate, it loses 22.3R in 2025,
and the null it now clears is a low bar.

**The forward window is at 5 trades and the pre-registered rule is no
verdict below n=50.** Until then the only unselected arbiter is data that
does not exist yet, and every further filter is another draw from the same
grid.
