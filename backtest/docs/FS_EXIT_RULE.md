# DIRECTIONAL FS ENTRY — the FS signal works, but on the ENTRY side

Measured 2026-10-04, engine, both eras, three causal leg-family base books.
Engine knob `exp_fs_entry_side`, default `""` = off. Harness
`exp_fs_directional_leg.py`; results `_fs_directional_leg.json`.

## DO NOT CONFUSE THIS WITH THE CLOSED FS-EXIT WORK

Same FS print. Opposite use. This is the one thing to get right when reading
either document.

| | FS-EXIT (`CLOSED_DO_NOT_REPEAT.md`) | **this** |
|---|---|---|
| Entry | B2/flip, unchanged | B2/flip on one side, **FS on the other** |
| Exit | closes **at** the FS print | unchanged |
| Change | when we LEAVE | **when we ARRIVE** |
| Result | −64R … −275R | **+33R … +332R** |

## The idea

`exp_directional.py` (P80) found the champion's OOS **long** side is not weak,
it is **absent**: 162 trades for +1.8R at PF 1.22, while its 117 shorts carried
+68.4R at PF 2.10. So the champion has no FS problem — it has a **long-side FS
problem**.

Arms, pre-registered, no search:

- **control** — break long, break short (the pinned book)
- **FS LONG** — longs enter at the swing FS print, shorts unchanged
- **FS SHORT** — shorts enter at the FS print, longs unchanged
- **FS BOTH** — both sides at FS

## Why FS as a trigger is legal, and why exit was not

The FS print is the opposite-direction chop cross (`fs_at_idx` =
`last_chop_cross_idx`, `btc_swing.py:106`) and `backend_check_wd_days.py:108`
asserts `fs_at_idx >= seg.end_idx`. That bar has closed before the print is
used, so reading it is causal.

The exit failure was not a causality failure — it was that the swing's
**geometry is retrospective**. By FS time the move it describes is already in
the P&L, so there is nothing left to differentiate. As a trigger the same print
does not need to differentiate anything: it only changes **when the position
opens**.

## Result — every arm, every era, three causal books

| base book | arm | IS n / net / PF | OOS n / net / PF |
|---|---|---|---|
| champion_multi_sw10_leg | control | 499 / +239.1R / 2.10 | 280 / +72.8R / 1.60 |
| | **FS long** | 525 / **+528.9R** / **3.98** | 310 / **+243.9R** / **3.31** |
| | **FS short** | 532 / **+571.4R** / 3.85 | 309 / **+239.3R** / 2.93 |
| | FS both | 648 / +426.4R / 3.09 | 362 / +226.8R / 2.78 |
| utcsat_entry_minus_1 | control | 454 / +358.9R / 2.62 | 253 / +60.2R / 1.58 |
| | **FS long** | 522 / **+510.5R** / 3.37 | 309 / **+243.1R** / 3.34 |
| | **FS short** | 530 / **+563.0R** / 3.75 | 308 / **+229.4R** / 3.19 |
| | FS both | 592 / +280.7R / 2.54 | 325 / +195.2R / 2.76 |
| dirmatch_multi_sw10 | control | 389 / +444.2R / 3.60 | 222 / +172.1R / 2.75 |
| | **FS long** | 426 / +477.4R / 4.48 | 237 / **+260.7R** / **4.84** |
| | **FS short** | 418 / **+658.7R** / **6.00** | 253 / **+235.1R** / 3.78 |
| | FS both | 468 / +416.1R / 4.65 | 264 / +286.5R / **5.50** |

**One directional arm beats its control in all six cells (3 books x 2 eras).
Drawdown falls too**, and on the champion book it falls by more than the net
rises:

| book | arm | IS DD | OOS DD |
|---|---|---|---|
| champion | control | 46.85 | 50.55 |
| | **FS long** | **14.19** | **11.88** |
| | FS short | 25.85 | 23.87 |
| utcsat | control | 21.18 | 29.38 |
| | **FS long** | 22.47 | **11.88** |
| | FS short | 25.92 | 24.76 |
| dirmatch | control | 15.40 | 15.40 |
| | **FS long** | **11.15** | **7.44** |
| | FS short | 11.60 | 12.30 |

## Two findings that replicated

1. **This is not an origin-stop artifact.** P80 measured it on
   `pivot_rule="origin"` — the retired retroactive source. Re-run on
   `leg` and `leg_no_entry` it still works, and the champion dNet is larger
   (+332R) than the origin lane gave (+237R).
2. **Applying FS to BOTH sides is consistently weaker.** 3 books x 2 eras, the
   one-sided arm wins every time. P80's "full FS over-applies" finding holds.
   The champion's healthy side was working; replacing it added churn without
   adding R.

## Pinned books (all re-derived from the engine, both eras)

| book | IS n / net / dd_net | OOS n / net / oos_dd_net |
|---|---|---|
| `fsent_champ_long` | 525 / +528.87 / 14.19 | 310 / +243.92 / 11.88 |
| `fsent_champ_short` | 532 / +571.44 / 25.85 | 309 / +239.32 / 23.87 |
| `fsent_utcsat_long` | 522 / +510.54 / 22.47 | 309 / +243.09 / 11.88 |
| `fsent_utcsat_short` | 530 / +562.98 / 25.92 | 308 / +229.44 / 24.76 |
| `fsent_dirmatch_long` | 426 / +477.38 / 11.15 | 237 / +260.70 / 7.44 |
| `fsent_dirmatch_short` | 418 / +658.65 / 11.60 | 253 / +235.14 / 12.30 |

## What is NOT established here

- **Not live.** No live-path wiring, no forward window, no equity-curve gate.
  These are measured books.
- **The null/M question is untouched.** `exp_verify_m.py` recomputes the
  block-bootstrap threshold on the CURRENT engine; that gate was deliberately
  not applied here, per the owner, and is deferred to the point where a
  candidate becomes a live-engine proposal. Nothing in this doc claims these
  books clear it.
- **`FS both` is measured but not pinned**, on the evidence above.
- **Only three base books.** Directional FS is untested on the single plane,
  on sw20, and on the trail_half family.

## One process note

Two of these six books were first written with the WRONG base params — the
directional arms of `dirmatch_multi_sw10` were built from the champion's block
and therefore measured identical to the champion's arms. The numbers looked
plausible, which is exactly why they have to be re-derived rather than read
off. `exp_fastcheck.py` caught it by printing two identical rows. Registry
entries now copy each book's own base params instead of a hand-written block.

Measured 2026-10-03 on the champion multi book, IS and OOS, through the
harness. Engine knob `exit_fs_max_gap_h`, default -1 = off.

## PLAIN ENGLISH - what the gap actually is

Read this if the tables below mean nothing. Nothing here is new measurement; it
is the same numbers with the jargon taken out.

**The setup, in the words you used.** On the 1h chart we are inside a swing. We
enter on a break mark - B2 or a flip. From that moment the LTF engine does
exactly what it always does: same ratchet trail, same stop, same costs. Nothing
about the entry changes. The only question this doc asks is **when do we let go.**

**FS is the moment the swing signs off.** A swing is not a swing until price
turned around far enough for the structure to agree. FS is that print. So for
every trade, there is a moment - some hours later - where the engine can say
"this is how big this swing turned out to be." It is legal to read it then,
because it has already happened.

**The gap is the distance from your entry to that print, in hours.**

- Entry at B2, FS prints 3 hours later -> gap = 3h
- Entry at B2, FS prints 19 hours later -> gap = 19h

That is the whole idea. **The gap is how much room the move you joined
actually had.** If the extreme was 3 hours away, you bought the top of it. If it
was 19 hours away, you got a real ride. The gap is the one measure of "how far
could this have gone" that is knowable at FS time without cheating.

**Why it works where swing magnitude failed.** Magnitude reads the swing's
height or size. Height is dominated by the first few bars after the entry, which
is why it reads as a prediction of the trade and reads backwards once you are
allowed to look at it legally (`FS_TIME_GEOMETRY.md`). The gap reads *elapsed
time*, and time is not contaminated by the entry itself - every swing in the
table had the same entry and the same first bars. That is the difference, and
it is why one rule was unusable and this one is not.

**What the buckets say.** Same trades, grouped by gap:

| gap | what it means | IS R/trade | OOS R/trade |
|---|---|---|---|
| 0-4h | joined the very end of a move that then died | **-0.72** | **-0.81** |
| 4-12h | ordinary | +0.46 | -0.05 |
| 12-24h | joined the start of a move that really ran | **+1.13** | **+0.90** |
| 24h+ | very slow, had already banked most of it | +0.45 | +0.32 |

Short gap loses money in **both** eras. Long gap makes money in both. Same sign,
same order, opposite ends of the clock. That is the theory.

**Why we cap it at 6h instead of exiting on every FS.** Because "exit on every
FS" is the *worst* arm in the whole table - it also kills the 12-24h runners,
which are where the money is. So the rule is a scalpel, not a scythe: **if the
swing signs off within 6 hours, the move was fake and we leave. If it has not
signed off in 6 hours, we do not touch the trade at all** - the existing
ratchet trail keeps managing it exactly as before.

## A 36% that is NOT about direction - do not conflate these

If you have seen "only 36%" quoted near this work, it is a different fact with
nothing to do with B2 direction versus FS direction.

`FS_ENTRY.md:41` - **~36% of the book disappears if you wait for FS.** Of 500
IS trades, 186 (37.2%) never reach a confirmation at all, so an engine that
entered at FS instead of B2 would hold 314 instead of 500. That is book size.
It says nothing about direction.

The direction fact is separate and it is the opposite of the intuitive guess:

- **100%** of booked trades (499/499 IS, 280/280 OOS) found a **same-direction**
  FS after entry. Zero found an opposite one.
- So "64% of the time FS is opposite to the B2" is **not supported by any
  measurement in this repo.** There is no such population.

**The ~64% you are thinking of is a different set of swings.** The book entered
on 499 of ~1601 IS swings. The other ~1100 never produced a B2 or a flip entry
at all, so the book never traded them and this doc says nothing about them.
That population is already worked in `FS_ONLY_P73` / `FS_ONLY_AUDIT_P74`
(`exp_fs_only.py`): 2900/1634 confirmed swings against 314/179 priced. Read
that before re-running it. It is an **entry** question. This doc is an **exit**
question on entries we already take.

## Why this is different from the closed FS work

`FS_TIME_GEOMETRY.md` tested exiting early when the swing turns out **small**
and it failed - remaining-R by magnitude bucket is flat to inverted. This is
the same event with **no condition on it**. Magnitude was the thing that
failed, not the exit.

It is also causal, which the magnitude version was not allowed to be: the exit
can only fire on a confirmation that has already printed. `fs_at_idx >=
seg.end_idx` is asserted by `backend_check_wd_days`, and the book enters at a
B2/flip break which sits before `seg.end_idx`. So FS is strictly after entry,
always.

## The diagnostic that chose the gap

Trades linked to their confirming swing **by time**, not by index - `swing_no`
and `swing_index` are different counters, and `fs_at_time` only carries HH:MM.
`fs_at_idx` indexes `candles_htf`, so the moment is `candles_htf[fs_at_idx].ts`.

| bucket | IS n | IS net R | IS R/trade | OOS n | OOS net R | OOS R/trade |
|---|---|---|---|---|---|---|
| gap 0-4h | 57 | -41.15 | **-0.722** | 31 | -25.16 | **-0.811** |
| gap 4-12h | 159 | +72.34 | +0.455 | 75 | -3.94 | -0.053 |
| gap 12-24h | 118 | +133.38 | **+1.130** | 80 | +72.20 | **+0.903** |
| gap 24h+ | 165 | +74.53 | +0.452 | 94 | +29.68 | +0.316 |

Every booked entry found a same-direction FS after it, so the "FS opposite
direction" and "no FS" rows are empty by construction - the book only enters
on the swing that FS is about to confirm.

Two facts carried into the experiment:

1. **Short gaps are negative on both eras.** A swing that confirms inside 4h
   gave the position no room.
2. **Long gaps are the best bucket on both eras.** That is where the runners
   live, and it is why the ungated version is a disaster.

The "still open at FS" split was the other strong cut (+1.34R/trade in sample,
+1.05 out, versus about -1.1 for trades that had already closed) but it is
**not** a usable rule - it describes the exit, so using it would be circular.

## The ladder

| gap gate | IS n | IS net R | IS DD | OOS n | OOS net R | OOS DD | exits I/O |
|---|---|---|---|---|---|---|---|
| control (off) | 499 | +239.12 | 46.8 | 280 | +72.79 | 50.6 | 0/0 |
| any FS | 573 | +133.26 | 32.9 | 332 | +57.90 | 28.9 | 346/202 |
| <= 2h | 499 | +245.52 | 43.6 | 283 | +75.37 | 50.4 | 27/12 |
| **<= 4h** | 502 | **+289.98** | 42.34 | 287 | **+79.42** | 43.9 | 53/29 |
| **<= 6h** | 508 | **+303.36** | 45.74 | 297 | **+80.30** | 45.0 | 104/59 |
| <= 8h | 527 | +264.59 | 35.8 | 300 | +69.70 | 45.4 | 155/78 |
| <= 12h | 544 | +257.00 | 34.4 | 312 | +76.90 | 49.6 | 217/105 |
| <= 24h | 566 | +209.38 | 32.9 | 331 | +77.93 | 28.9 | 305/179 |

**The band is a plateau at 2-6h, not a knife edge.** Every arm inside it beats
the control on both eras independently. 8h breaks on OOS, 12h weakens in
sample, 24h is worse than the control in sample.

Exiting on **any** FS costs 106R in sample and 15R out. Same event, no gap
condition - and it is the single worst arm here. That is the whole finding:
the rule is worth something only in the window where the swing failed fast.

## Books

| key | gap | IS net R | OOS net R |
|---|---|---|---|
| `fsexit4_c` | 4h | +289.98 | +79.42 |
| `fsexit6_c` | 6h | +303.36 | +80.30 |

Both clear the requested shortlist (IS >= 130R, OOS >= 50R). 6h is the higher
return in both eras; 4h carries the lower drawdown in both.

## Not tested

- **Cross-TF.** A 1h entry confirmed by a 4h FS is a different experiment and
  would need a second swing chain. Not attempted.
- **15m entries.** The book enters on 1h swings, so the 2900 15m swings never
  generate entries. Getting to 1000+ trades means entering on the 15m chain
  directly, which is a different book, not a knob on this one.
- **FS-only swings.** Not re-opened here, and the diagnostic structurally could
  not see them: it starts from trades, and every booked entry found a
  confirming FS, so swings carrying an FS and no B2/flip were never in the
  sample. That population is already covered by `FS_ONLY_P73` /
  `FS_ONLY_AUDIT_P74` (`exp_fs_only.py`) - 2900/1634 confirmed swings against
  the 314/179 that produced a priced entry. Read those before re-running it.
