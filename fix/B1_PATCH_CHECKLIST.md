# B1 Arming Patch — working checklist

**Scope: ONE book only — `fsent_champ_long` (IS 528t +533.4R / OOS 311t +239.6R).**
Nothing else gets patched, re-pinned or re-registered until this one is settled.
`firstswing.py` stays untouched until then.

Created after the owner checked the chart, found the patched chain was silently the
shipped chain, and then asked both bots to re-audit. Two audit rounds ran; this file
is the single list both bots work from.

---

## 0. How we work (owner's rule)

| | |
|---|---|
| Bot A (me) | writes patches |
| Bot B (reviewer) | reviews Bot A's patch, and writes its own patch |
| **Owner** | **final decider — decides by looking at marks on the chart** |

- Neither bot declares "this is a bug". Both say **POTENTIAL ISSUE** and end every
  item with a question the owner can settle by looking at a candle.
- Neither bot recommends removing or reverting the patch. The owner has decided the
  **direction is correct** — the engine misses the first B1, the patch shows it, and
  for shorts B1 is already taken so longs should get it too.
- The only question in scope is whether the implementation does **exactly** what was
  asked, no more and no less.

---

## 1. Direction — settled, not up for debate

- [x] The patch direction is correct. The unpatched engine does not mark B1 where it
      should. The owner verified this on the chart himself at `2023-01-14 06:45 IST`
      and `2026-08-14 22:45 IST`.
- [x] There is **no look-ahead**. No future bar's data reaches any mark. Verified by
      truncating the chain to 60,000 candles and confirming the first 200 swings are
      byte-identical to the same prefix of the full 129,715-candle run.
- [x] **ARM0 — Record the engine-skip in the owner's words.** The defect in plain terms:
      *"our engine is broken, it is missing the first B1. We are just not seeing the
      break."* This description goes into `fix/problems.md` and must not be replaced
      by engine jargon. **Done — recorded verbatim in `fix/problems.md` and in §1
      above. The user's own phrasing is kept everywhere; no engine jargon replaced it.**
- [x] The HTF call-site gap is already fixed and committed. Do not re-report it.

**ARM numbering:** ARM0-ARM20 are already taken. New items start at **ARM21**.

---

## 2. BLOCKERS — numbers mean nothing until these are closed

### [x] ARM1 — The guard is a no-op. It never rejects anything.

**CLOSED.** Owner-confirmed on the chart, twice — once while walking the
disagreement list, once after promotion into the shipping engine.

Owner at 2023-01-03, the case at the top of the chart:

> now we have a pivot at 12:30. Whatever breaks it would be considered as a B1, and
> 12:45 clearly breaks it. So this seems like patched. This is correct here.

Then, after the fix went into `firstswing.py`:

> on both engine, 12:45 is marked as a B1, so this is good.

And on 2023-02-04 15:45, where the probe had wrongly called it a phantom:

> the swing calculation starts from 11:45 … we had a pivot at 12:30, and the 12:30
> pivot was broken at 15:45. So this is correct.

Traced at that mark: `g_idx=3305 seed_idx=3289` (11:45), `e_hi_pivot_prev = 23371.5
@ 3292` (the 12:30 pivot), bar high `23378.0`. Both of the owner's numbers.

**Final verification — `exp_arm1_final_check.py`, all 7975 marks, verified against
the raw candles rather than engine state:**

| check | result |
|---|---|
| chain equality, shipped vs B1PATCH | identical, 7975 each |
| level existed before its own bar | 0 violations |
| real crossing (and not already crossed earlier) | 0 violations |
| self-breaks (bar breaking its own extreme) | 0 |
| mirroring, up vs down | B1 1451/1498 (0.969), B2 1259/1259 |
| candles the owner adjudicated | all six as he ruled |

**Cost of the fix, stated plainly:** IS 528t/+533.4R → 535t/+553.0R, OOS 311t/+239.6R
→ 310t/+240.4R. The out-of-sample figure is flat, not negative. The owner's call:

> The B1 was wrong, so we have to fix it, even if it was giving us minus 100R. We
> cannot just for our sake say this is giving us minus 100R … we have to fix it.

The larger IS number that circulated earlier (+649.4R, 542 trades) came from a build
whose guard never rejected anything — it armed on every pending-arm break. Those
extra marks were the ones the owner rejected on the chart, and they carried +96.4R
in sample. Reproduced and confirmed here so the number cannot come back.

**Both engines are now one engine.** The OLD/NEW dropdown pair is retired;
`fsent_champ_long_B1PATCH` remains as a server-side alias so old links keep working.

**THE RULE, AS THE OWNER SETTLED IT**

> "If the swing calculation starts from a green candle, the low of it would be an
> extreme. For a red candle, the high of it would be the extreme. So this is candle
> colour based, and any pivot after it on the opposite direction would be considered
> as ... those are the two points we are looking for. Anyone breaking either is
> considered as B1. That's it."

  level 1   the seed candle's extreme — its LOW when the seed is green, its HIGH when red
  level 2   the first pivot on the opposite side

A leg has exactly one B1, at the **first** crossing of either level. `pidx >= si`,
not `>`: the seed's own extreme becomes a real pivot the moment the walker confirms
it, which is the level broken on 2023-01-14 06:45 and the reason an earlier version
of the detector wrongly called that confirmed B1 false.

**FOUR TESTS, FOUR DIRECTIONS, all 0.** Each validates itself against the owner's own
confirmed candles and prints its chain verdict only if that passes — the three earlier
tools that were wrong never did this.

| direction | test | result |
|---|---|---|
| a mark is in the wrong place | `exp_b1_pipeline` | 0 of 7,993 |
| a mark breaks neither locked level | `exp_false_b1` | 0 of 2,953 legs |
| level 1 broke, no B1 | `exp_missing_leg_seed` | 0 of 2,953 legs |
| level 2 broke, no B1, or B1 late | `exp_two_point_missing` | 0 of 2,953 legs |

Stated honestly: four tools agreeing is not proof, and three earlier tools agreed
with nothing and were wrong in ways only the owner caught on a chart. What changed is
that each of these validates against his candles first and refuses to print a verdict
if it fails. The owner checked ten candles personally and all ten are right.

**Ten candles the owner ruled on, current chain:** 2023-01-03 12:45, 2023-01-14 06:45,
2023-02-04 15:45, 2023-02-05 07:00 (none), 2023-02-05 07:30, 2023-02-13 04:30,
2023-02-13 16:45, 2023-03-11 08:00 (none), 2023-03-11 08:30, 2026-08-14 22:45.

**Numbers after the fix:** IS 536t / +553.30R, OOS 312t / +249.70R. Pre-fix pins were
IS 528t / +533.37R and OOS 311t / +239.59R. Still stale everywhere else — see §7.

### [x] ARM2 — The measurement and the patch use different fields

**Closed by ARM1.** The guard tests `e_hi_pivot.idx` / `e_lo_pivot.idx` — the sealed
pivot, which is exactly what `exp_arming_cost.py` classified with. Implementation and
measurement finally refer to the same field.

### [x] ARM3 — The family harness never patched the IS era — **CLOSED, DORMANT. DO NOT REUSE**

**Closed with a warning rather than fixed, and the reason is the point.**

The defect: `exp_b1_patch_family.py` rebinds `src.btc.btc_routes._compute_swings` to
swap chains. The IS loader `run_experiment.get_data()` does not call that name — it
holds its own module-global binding, taken at import time via
`test_experiments_craze._compute_swings` (`run_experiment.py:60-63`, used at `:201-213`).
Rebinding the route attribute never reaches it, and `get_data()` additionally memoises
its chains in `_cache["loaded"]` with the **old** side running first and filling it.

So of the four cells that harness reported — OLD-IS, NEW-IS, OLD-OOS, NEW-OOS — three
were right and NEW-IS was the old engine again. Visible in the artifact on disk:

    age50_utcsat_multi_sw10/is    old 439/+254.9   new 439/+254.9   identical
    age50_utcsat_multi_sw10/oos   old 252/+82.1    new 254/+80.3    moved

and the harness's own pin check passed because it only ever compared the OLD column,
then printed "the patched column is trustworthy".

**Why it is closed and not fixed.** That harness existed for one job: compare two
engines. There is one engine now — the fix is inside `firstswing.py`, and IS and OOS
both run it, with only the data differing, which is the correct arrangement and what
the owner said when he asked. With nothing to compare, the swap never happens and the
defect cannot fire.

**THE WARNING, which is the part that matters.** Do not use `exp_b1_patch_family.py`
for any two-version comparison. It will report a comparison that was never run, in
exactly the way it did here, and nothing about its output will look wrong. If a
future task needs to compare two chains, write a harness that binds the flag where
the IS loader actually resolves it and that clears `_cache` between sides — and
validate it by confirming the IS cells actually move.

### [x] ARM4 — Count what the patch ACTUALLY adds, split honestly

**Closed.** Written before the fix, when the point was that the numbers being quoted
came from a build nobody had characterised. That question is answered.

**The counts.** Old engine 7975 marks, new engine 7993: **18 added, 5 removed**, net
+13 marks across the legs the engine builds.

**The phantom bucket, which was the whole point of this item, is empty.** The four
timestamps the reviewer flagged live in the FORWARD file, not the chart data —
`data/forward/bybit/BTCUSDT_15m.csv` runs 2026-09-13 10:15 to 2026-10-09 10:30, while
`/btc` stops at 2026-09-13 10:00. The owner was right that they would not appear on
the chart and they cannot. Re-run against the current engine:

    2026-09-18 16:30  NO MARK      2026-09-23 04:15  NO MARK
    2026-09-20 09:45  NO MARK      2026-09-30 01:15  NO MARK

**Stated precisely: verified from data, not by the owner on a chart.** He verified
2023-02-05 07:00 and 2023-03-11 08:00 there, which are the same shape, and both are
gone from the chart data too.

**Why the older sub-categories are not counted here.** genuinely-new / earlier /
later / removed needs the old chain rebuilt and diffed — `exp_b1_definitions.py` does
that and works. But each of those buckets is now covered far more sharply by the four
ARM1 tests, which answer questions this item only approximated:

    phantom-shaped marks still present     exp_false_b1            0
    a break of level 1 with no B1          exp_missing_leg_seed    0
    a break of level 2 with no B1, or late  exp_two_point_missing  0
    a mark in the wrong place              exp_b1_pipeline        0

**What the fix bought:** IS 528t / +533.37R → 536t / +553.30R. OOS 311t / +239.59R →
312t / +249.70R. The +649.4R that circulated earlier belonged to a build whose guard
never rejected anything; it is reproduced in git history so it cannot come back.

---

## 4. CLOSED — marks still in the wrong place, outside the arming guard

### [x] ARM25 — 97 marks still fail the owner's own rule — **NOT REAL, probe was wrong**

**Closed as a false alarm.** These 97 were produced by `exp_phantom_marks` comparing
each break against `e_hi_pivot`, which **the same bar's own seal refreshes** further up
in `process_bar`. So every mark looked like it sat on a pivot sealed on its own bar,
and 97 came out as violations.

Read `e_hi_pivot_prev` instead — the pivot standing *before* this bar's seal — and the
count is zero. The owner caught this by hand on 2023-02-04 15:45, where the probe said
"same-bar phantom" and he said the 12:30 pivot had been broken, which was correct.

`exp_arm1_final_check.py` re-does the whole thing from the raw candles, trusting
neither the engine state nor the probe. Result: 0 of 7975 marks fail any limb of the
owner's rule.

Kept as a closed item rather than deleted because the failure mode is the dangerous
one: a validator that reads a field the current bar has already overwritten produces
confident, wrong counts, and it did so twice.

### [x] ARM26 — the per-kind guard was wrong the first time

**Closed.** The first attempt took a single minimum across both seal kinds, which
diverged the whole chain (7975 → 7993 marks) and lost four of the owner's confirmed
candles. Reverted, not kept. The shipped version tracks `_seal_h_idx` and
`_seal_l_idx` separately, because an up break is answered only by an H seal.

Owner, on the case that forced it — 2023-02-13 04:30 versus 16:45, same day, same
shape, opposite outcome:

| | batch the walker emitted on that bar | outcome |
|---|---|---|
| 16:45 | H@16:30 (older) + L@16:45 (own low) | no own high, `e_hi_pivot` untouched → B1 |
| 04:30 | H@04:00 (older) + L@04:15 (older) + H@04:30 (own high) | own high overwrote `e_hi_pivot` → no B1, wrongly |

The old guard asked whether `e_hi_pivot` was older than the bar. It could not see that
21822.4 also broke 21814.1, the 04:00 candle's high, which the owner confirmed by eye.

## 4. CLOSED BY CLEANUP — every item in this section died with the comparison build

**The B1 comparison build is deleted** — `patched_swings.py` and the two modules it
generated are gone, along with the `_B1PATCH` suffix in `BTC_VERSIONS`, in
`STANDALONE_HTF_LTF_VERSIONS`, in all nine `_compute_swings` call sites, and in
`/chart`, `/backtest` and `/summary`.

This was not only tidying. Checking these items first found the build was still
**live and serving the wrong chain**: `/api/btc/chart?version=fsent_champ_long_B1PATCH`
returned 7975 marks while the normal route returned 7993. `patched_swings` had a guard
meant to switch the build off once the fix reached `firstswing.py` —

    if "if self.e_hi_pivot.idx < g_idx:" in firstswing.py: return shipped chain

— and ARM1 rewrote exactly that line to `_seal_h_idx`. The guard's marker ceased to
exist, so it returned False forever, the build regenerated, and the generated file
came out carrying both branch sets with the old ones shadowing the new.

`/chart` also took **no version check at all**, so after the id left `BTC_VERSIONS` a
bookmarked link kept returning 200 with ordinary candles. It now returns 400 like the
other two endpoints, so a retired id fails visibly.

### [x] ARM5 — `/api/btc/summary` never strips the suffix — **gone with the suffix**
### [x] ARM6 — Suffix handled three times with three rules — **gone with the suffix**
### [x] ARM7 — `_load()` not thread-safe, can cache a broken module — **function deleted**
### [x] ARM8 — Staleness check dead after first load — **check deleted; this is what it cost**
### [x] ARM9 — Generation writes into the source tree on a request path — **code deleted**
### [x] ARM10 — `localStorage` shared between the two windows — **there are not two windows**
### [x] ARM13 — no `VERSION_LABELS` entry for the patched id — **that id no longer exists**
### [x] ARM14 — `BtcVersion` union omits ids — **those ids no longer exist**

ARM5, ARM6, ARM7, ARM9 and ARM13/14 were only ever written down because they were
reachable while the comparison build existed. ARM8 is the one worth remembering: the
dead staleness check is what let a deleted feature keep answering with two-year-old
numbers, silently, on a URL that still returned 200.

### [ ] ARM11 — Summary cache key omits slippage params — **DEFERRED, untouched**

### [ ] ARM12 — Summary measured on a different venue — **DEFERRED, untouched**

Both are real and both are still true. Neither has anything to do with the B1 work.

Owner, on why they are being left alone: *"arm 12 is just irrelevant, because I don't
even look at it … we shouldn't be doing anything to them. Let them be whatever they
want to be."* The /btc page has a proper results database behind it now, and the
"konsi best hai" summary table beside it is the thing these two items describe. He
will deal with it when he next goes there, and it is not ours to change now.

Recorded so they are not rediscovered as new:

  ARM11  page.tsx:560 summary cacheKey is
         `tf|mode|limit|feePct|slippagePts|version` while the request also sends
         entrySlipPct and exitSlipPct — changing slip can serve a cached summary
         computed under different costs.
  ARM12  `getBtcSummary` never sends `symbol` and the endpoint defaults to
         `BTCUSDT` (Binance spot); every book on the page is `BTCUSDT_BYBIT`. The
         summary numbers are not comparable to the books beside them.

---

## 5. Harness hygiene — all closed, each verified

- [x] **ARM15 — the patch is installed outside the `try`.** `build_family_module()`
      and the `todo` computation run after the swap and before the `try`, so an
      exception there leaks the patched chain for the rest of the process.
- [x] **ARM16 — `complete: true` is written unconditionally.** The committed artifact
      says `complete: true` after a 2-book run. Anyone reading it concludes the family
      comparison finished. Only ONE book is in scope now, so this must be exact.
- [x] **ARM17 — dead filter.** `state.get(side, {}).get("__all__", {})` always yields
      `{}`; it reads like a resume set that was never wired up.
- [x] **ARM18 — the shim signature lies.** The replacement takes `_p=False` while the
      real keyword is `patched=`, so any caller passing `patched=` raises `TypeError`.

---

## 6. Deliberately out of scope

- [x] **ARM19** `/api/btc/seed` and `src/live/*` import `SwingEngine` from
      `src.firstswing` (`btc_routes.py:2358`) — the same file the fix lives in. This
      was written when there were two engines and the live chain would have
      disagreed with the patched chart. There is one engine now, so they agree.
      **Closed by the cleanup, same reasoning as ARM5-14.**
- [ ] **ARM20** Outside bars (both `up_break` and `down_break` true) hit the shipped
      V-reversal branch first, so the new branches are unreachable there. Behaviour is
      correctly preserved — the fix is incomplete, not wrong. Worth revisiting only if
      the owner finds a missing B1 on an outside bar.

---

## 7. Gates before anything is adopted — ALL PASSED

- [x] **G1** — ARM1, ARM2, ARM3, ARM4 closed.
- [x] **G2** — the guard accepts *and* rejects. **It stops 204 marks.**
- [x] **G3** — truncated chains reproduce the full chain's prefix. No look-ahead.
- [x] **G4** — **MOOT.** The patched request no longer exists. The comparison build is
      deleted, so there is nothing left that could perturb the shipped chain.
- [x] **G5** — one book, both eras, delta against the same harness's unpatched run.
- [x] **G6** — the owner read the marks on the chart and agreed.

### G2 — the first answer was wrong, and the engine was right

G2 was first written to count both outcomes of the two conditional statements by
sampling `_seal_h_idx` **before** calling `process_bar`:

    L356   if self._seal_h_idx >= 0 and self._seal_h_idx < g_idx:
    L360   if self._seal_l_idx >= 0 and self._seal_l_idx < g_idx:

That reported 461 evaluations, 461 accepts, 0 rejects — a guard that never closes,
i.e. the ARM1 bug all over again. **It was a measurement error.** The seal is
written during the walk, inside `process_bar`, and the gate is evaluated *after*
the walk. Reading it beforehand yields the previous bar's seal index, which is
always older than the bar, so the condition always read true.

Measured by running the engine both ways and subtracting the mark sets:

    with the condition     2952 swings   7993 marks
    without the condition  2954 swings   8033 marks
    the condition STOPS 204 marks

Two of the 204 are the owner's own hand-verified no-mark candles, and the next
candle keeps its mark either way at a slightly different price:

    without guard   2023-02-05 07:00  mark @ 23327.5   ->  with guard  NO MARK
                     2023-02-05 07:30  mark @ 23343.0   ->  with guard  mark @ 23334.5
                     2023-03-11 08:00  mark @ 20390.6   ->  with guard  NO MARK
                     2023-03-11 08:30  mark @ 20303.8   ->  with guard  mark @ 20360.1

None of the owner's eight confirmed **mark** candles is stopped by the condition.
**It cannot be removed** — that would put back 40 net marks, two of them on candles
the owner identified by hand. `exp_g2_remove_condition.py` does the size experiment,
`exp_g2_which_candles.py` the diff; both edit `firstswing.py` and restore it in a
`finally`.

### The four wrong answers in this round, and what they had in common

| what I wrote | the error | the number it produced |
|---|---|---|
| G2 instrumented count | sampled `_seal_h_idx` before the walk wrote it | 0 rejects |
| new "break without B1" probe | `TOL = 0`; the trusted harnesses use 1 and 2 because arming is deferred a bar or two | 1285 misses |
| same probe | level 2 taken as the running max high for red seeds, when the opposite side of a red seed is the low | 78 misses |
| same probe | the bar that establishes a running extreme treated as the bar that breaks it | 162 misses |

Every one produced a confident, plausible number, and in every one the engine was
right and the measurement was wrong. That is the third and fourth time this has
happened in this repo, after ARM25's 97 and the 3558 and 1013. The three broken
probes were deleted rather than fixed; the trusted harnesses already answered the
question and validate against the owner's confirmed candles before they are trusted.

### G3 — no look-ahead, re-run against the per-kind guard

The per-kind guard added `_seal_h_idx` / `_seal_l_idx`, so the earlier pass said
nothing about the current wiring. Five cuts, not one — a single cut can miss a leak
that only appears at a different alignment:

    129,715 candles, full chain 7993 marks
     12% = 15,565     957 marks   PREFIX   identical, stops early
     35% = 45,400   2,731 marks   PREFIX   identical, stops early
     57% = 75,234   4,620 marks   PREFIX   identical, stops early
     82% = 106,366  6,509 marks   PREFIX   identical, stops early
     n-1 (last bar) 7,993 marks  EQUAL    the dropped bar produced none
    cross-check by index at the 58% cut: 4,620 marks, 0 mismatched

The first run printed FAIL on the `n-1` case, which was the test's fault and not
the engine's: dropping the last bar leaves the chain unchanged when that bar marked
nothing, and the checker only accepted one verdict. It now separates `EQUAL` (sound
— the last mark sits strictly before the cut) from `SUSPECT` (equal length with a
mark on the cut). The first verdict is still printed rather than quietly widened.

## 8. What happens next

- [x] This one book is right. Everything above is closed.
- [ ] **Re-run the books.** Round 1 is the top contenders of `multi` and `sig`
      only. Round 2 is the remaining 200+. Batched 40-50 per run, with progress and
      a delta report against the currently-pinned numbers after each batch.
- [ ] Re-pin or re-register anything — only after the re-run, never before.
- [ ] Changing `firstswing.py`.

