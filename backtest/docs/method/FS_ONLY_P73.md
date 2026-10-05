# P73: a true FS-only engine — **SUPERSEDED BY P74, LABEL WAS WRONG**

> **AUDITED 2026-09-29 → `method/FS_ONLY_AUDIT_P74.md`.** The arm below is a
> **HYBRID**, not FS-only: only the `decisive` entry path was routed to FS;
> the `flip` and `b2` paths were untouched. `method/FS_ONLY_ENGINE.md` (2026-09-28)
> already answered the pure FS-only question — **263t +31.7R IS, 108t +1.3R
> OOS** — and P73 did not read it. **The "strongest live candidate"
> registration is WITHDRAWN.** Numbers below reproduce from the stated
> patch; the interpretation did not survive the audit. Champion unchanged,
> nothing adopted.

> Run 2026-09-29. Harness `exp_fs_only.py`. **NOT ADOPTED. Two tests outstanding.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **The strongest result of the P55–P73 round, and the one that most needs
> the period partition before anyone believes it.**

## The open item, and why it was worth running

`closed/CLOSED_DO_NOT_REPEAT.md` listed it as still open:

> *"True FS-only engine. 2900/1634 confirmed swings exist; only the 314/179
> that produced a B2/flip entry have been priced. An FS-only entry could be
> a larger book. Not simulated."*

Nemotron rated it rank 3 of 10: *"Never simulated; 2,900 swings vs 314
priced; different trigger set."*

**Every entry the champion takes is a break** — a B2 or a FLIP, price
crossing a structure extreme. The swing engine also stamps an **FS moment**
on every swing: the bar at which structure was *first declared*, before any
break. So this is not the same book with a looser filter. It asks a
different question: **does the book have an edge when structure is
recognised, or only when it is broken?**

The patch gives `_collect_signals` an early-return branch for
`entry_break == "fs_only"`, emitting one signal per swing at `fs_at_idx`,
in the swing's own direction, stopped at the swing's start pivot — the level
the engine already uses for a same-direction mark. Nothing else changes, so
the B2/FLIP control is byte-identical and is re-verified inside the run.

**Causality:** `fs_at_idx` is the bar the structure was declared on —
information available at that bar and not before. It is not the pivot's
timestamp, so it carries no P52 lookahead.

## Result

| arm | lane / era | n | net | R/trade | PF | DD | dNet |
|---|---|---|---|---|---|---|---|
| control (break entry) | champ IS | 500 | +325.8R | +0.652 | 2.38 | 17.8 | — |
| **FS-only** | champ **IS** | **646** | **+405.2R** | +0.627 | **2.99** | **14.3** | **+79.4R** |
| control (break entry) | champ **OOS** | 279 | +70.1R | +0.251 | 1.59 | 37.3 | — |
| **FS-only** | champ **OOS** | **364** | **+233.6R** | **+0.642** | **2.81** | **17.3** | **+163.4R** |
| control (break entry) | utcsat IS | 454 | +359.0R | +0.791 | 2.62 | 14.8 | — |
| FS-only | utcsat **IS** | 592 | +280.7R | +0.474 | 2.54 | 14.9 | **−78.2R** |
| control (break entry) | utcsat OOS | 253 | +60.2R | +0.238 | 1.58 | 22.1 | — |
| FS-only | utcsat **OOS** | 326 | **+198.9R** | +0.610 | 2.78 | 21.1 | **+138.7R** |

**Three of four cells positive. In the champion lane, both eras: more
trades, better profit factor and better drawdown simultaneously.**

| | champion IS | champion OOS |
|---|---|---|
| trades | 500 → **646** | 279 → **364** |
| PF | 2.38 → **2.99** | 1.59 → **2.81** |
| drawdown | 17.8R → **14.3R** | 37.3R → **17.3R** |
| net | +325.8R → **+405.2R** | +70.1R → **+233.6R** |

**That combination has not appeared once in this programme.** Every previous
candidate that improved the risk profile did it by destroying the return —
the 1D architecture (P57), the union (P60), `cand_4h1h` (P58→P61), the
relative-price filter (P69). Here the return goes up too, and the champion's
OOS profit factor rises 77% while its drawdown falls 54%.

## Why it is still not adopted — three outstanding tests

**1. Nothing clears M = 193.4R.** Best cell +163.4R, **84.5% of the null**;
champion IS is 41%. Close, but the criterion is the criterion.

**2. The utcsat IS cell is −78.2R, and that is the alarming part.** The two
lanes are the same market with different parameters, so a disagreement
*between lanes in the same era* is a different animal from every era-split
this programme has catalogued. **It is parameter sensitivity, not
overfitting to a period** — arguably worse, because it means the result
depends on a setting nobody has identified yet.

**3. The period partition has not been run.** This is the test that killed
`cand_4h1h`, and P61's lesson was that an aggregate "better in both eras"
means nothing until it survives a calendar half-year split. **Given that
`cand_4h1h` looked like this and then went 4-4 in IS, that test is not
optional and its absence is the single most important caveat here.**

**Also not run:** a hybrid — B2/FLIP entries plus FS entries on swings that
never broke. That is the formulation which would actually ADD to the book
rather than replace it, and the one that would take the 2900-vs-314 gap
seriously instead of trading one trigger for the other.


## What the trigger change actually did

- **Entries move earlier.** An FS entry is taken when structure is declared,
  before price has broken anything. More information used, less confirmation
  used.
- **Stop levels get tighter by construction.** Stopping at the swing's own
  start pivot rather than at a broken extreme means a structurally meaningful
  invalidation rather than a confirmed one. **The drawdown improvement and
  the profit-factor improvement are plausibly the same fact, not two.**
- **The book grows by ~30%, not by 9x.** 500 → 646 rather than 500 → 2900,
  because the one-slot rule suppresses most FS signals that overlap an open
  position. **The "2900 swings vs 314 priced" headroom is therefore not
  reachable as stated** — the binding constraint is the slot, not the
  trigger set.

That last point corrects part of the item's framing: the gap between 2900
swings and 314 priced trades is mostly **time overlap**, not unexploited
signal supply.

## A harness bug worth recording

The first run returned **zero trades in every cell** while reporting a
perfectly healthy signal count — 1600 HTF and 2899 LTF signals in IS. The
diagnostic printed `bar='00:30'`: `fs_at_time` on these records is a **time
of day, not a datetime**, so `store.pos()` never matched anything.

**Resolving the bar by `fs_at_idx` into `store.candles` fixed it**, and is
format-independent. Same lesson as P64: *the signal count looked perfect
while every trade was zero*, and only an explicit diagnostic separated those
two states. Sixth instance this round.

**The diagnostic is also unreliable as written** — it calls
`_collect_signals` without `candles`, so `store` is None and the OOS line
prints 0 signals even though the book produces 364 trades. **It is measuring
the wrong thing and should be fixed before it is trusted again.**

## Stated limitations

- **The period partition is not run.** Stated three times because it matters
  more than anything else here.
- **Both lanes are the same data**, so the lane disagreement is a parameter
  effect, not independent evidence either way.
- **The hybrid arm is not run**, and it is the formulation most likely to
  help.
- **Only the champion's parameter set was varied by lane.** Nothing sweeps
  `cap_days`, `htf_rr` or the entry-break mix alongside the new trigger, and
  sweeping them now would be a search on a result already seen.
- **FS and break entries are not disjoint.** How many of the 646 IS FS
  entries coincide with champion trades is not measured, so "more trades"
  must not be read as "disjoint additional trades" until it is.

## Where this leaves it

**The strongest live candidate in the programme.** Registered as such, with
two named tests outstanding — the period partition and the hybrid arm — and
it must clear both, plus M, before it is considered. **If the period split
comes back 4-4 the way `cand_4h1h` did, this closes like that did.** That
is the correct prior, not a formality.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
