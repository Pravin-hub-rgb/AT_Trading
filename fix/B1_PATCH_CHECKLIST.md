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
- [ ] **ARM0 — Record the engine-skip in the owner's words.** The defect in plain terms:
      *"our engine is broken, it is missing the first B1. We are just not seeing the
      break."* This description goes into `fix/problems.md` and must not be replaced
      by engine jargon.
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

### [ ] ARM4 — Count what the patch ACTUALLY adds, split honestly

Needed before any number is quoted again. Categories, counted not argued:

- [ ] genuinely-new position (no B1 nearby before)
- [ ] same break, arrived earlier by N bars
- [ ] same break, arrived later by N bars
- [ ] removed
- [ ] **phantom shape** — the bar that sealed the pivot printed that pivot as its own
      high/low, so the "break" is against the bar's own extreme

The phantom bucket is the one that decides whether ARM1's fix should suppress or keep.

- **Owner check:** `2026-09-18 16:30`, `2026-09-20 09:45`, `2026-09-23 04:15` and
  `2026-09-30 01:15` were flagged as phantom-shape by the reviewer on the forward
  file. Owner to confirm on the chart whether a B1 belongs on those bars.

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

## 4. Wiring — the patch must apply everywhere, or nowhere
### [ ] ARM5 — `/api/btc/summary` never strips the suffix

`btc_routes.py` computes `_patched` and threads it into both chain builds, but never
does `version = version[:-len("_B1PATCH")]`. The suffixed id reaches `_run_preset`
(which branches on exact string equality) and is echoed in the response.

Harmless today only by coincidence: both ids miss every `_run_preset` branch and land
on the generic `else`. The day someone adds an `fsent_champ_long` branch there, the
patched window silently runs a different engine.

- **Bot A fix:** strip it. **Bot B:** verify no other consumer wanted the full id.

### [ ] ARM6 — Suffix handled three times, three different rules

| endpoint | validates | strips | order |
|---|---|---|---|
| `/chart` | **no validation at all** | yes | n/a |
| `/backtest` | yes | yes | **validate before strip** |
| `/summary` | yes | **never** | **validate before strip** |

`"fsent_champ_long_B1PATCH"` is hand-appended to `BTC_VERSIONS` purely so the
unstripped string passes validation. Nothing enforces that sync.

- **Bot A fix:** one helper, one rule, used by all three.
- **Owner check:** none — objective defect.

### [ ] ARM7 — `_load()` is not thread-safe and can cache a broken module forever

FastAPI runs sync endpoints in a threadpool. On a cold process two concurrent
requests both see `_swing_fn is None`, both see a stale stamp, both call `_generate()`.
`Path.write_text` truncates before writing, so a third thread can import a
half-written file. The broken module object then stays in `sys.modules`, and every
later request re-imports **that same broken object** — no restart fixes it.

- **Bot A fix:** `threading.Lock`, write to `.tmp` + `os.replace`, pop `sys.modules`
  on import failure.
- **Owner check:** none — objective defect. Bot B to attempt a concurrent hammer test.

### [ ] ARM8 — The staleness check is dead after the first load

`_load()` returns the cached function before `_sha()` is ever re-evaluated. And even
if it ran, `importlib.import_module` returns the already-cached `sys.modules` entry,
not the rewritten file. Edit `firstswing.py` on a live server and the patched chain
keeps the old engine with no warning.

- **Owner check:** none — objective defect.

### [ ] ARM9 — Generation writes into the source tree on a request path

A read-only checkout, container or non-writable install raises `OSError` → HTTP 500 on
every `_B1PATCH` request, forever. The UI shows "Internal Server Error" with no hint
that the patch generator is the cause.

- **Bot A fix:** generate outside the package tree, or fail with a readable message.

### [ ] ARM10 — `localStorage` is shared between the two windows

`BOOK_KEY` is `localStorage`, so with OLD in window A and NEW in window B, changing
the dropdown in B and then reloading A silently shows A the patched chain. The two
windows then agree on everything — which is exactly the "the patch did nothing"
symptom. `sessionStorage` (the chart cache) is per-tab and is fine.

- **Bot A fix:** per-tab book selection, or URL-driven.
- **Owner check:** the two-window workflow must survive a reload.

### [ ] ARM11 — Summary cache key omits slippage params

Key is `tf|mode|limit|feePct|slippagePts|version`; the request also sends
`entrySlipPct` and `exitSlipPct`, and the effect deps omit both. Changing entry/exit
slip serves a cached summary computed under different cost assumptions.

### [ ] ARM12 — The summary is measured on a different venue

`getBtcSummary` never sends `symbol`, and the endpoint defaults to `BTCUSDT`
(Binance spot). Every book on the page is `BTCUSDT_BYBIT`. The summary table beside
the comparison is therefore not comparable to either window.

- **Owner check:** is the "konsi best hai" table meant to be Bybit at all?

### [ ] ARM13 / ARM14 — Cosmetic
- [ ] no `VERSION_LABELS` entry for the patched id → footer prints the raw id
- [ ] `BtcVersion` union omits the patched id and several others; `books.ts` types
      `version` as bare `string`, so a typo is caught nowhere

---

## 4. Harness hygiene

- [ ] **ARM15 — the patch is installed outside the `try`.** `build_family_module()`
      and the `todo` computation run after the swap and before the `try`, so an
      exception there leaks the patched chain for the rest of the process.
- [ ] **ARM16 — `complete: true` is written unconditionally.** The committed artifact
      says `complete: true` after a 2-book run. Anyone reading it concludes the family
      comparison finished. Only ONE book is in scope now, so this must be exact.
- [ ] **ARM17 — dead filter.** `state.get(side, {}).get("__all__", {})` always yields
      `{}`; it reads like a resume set that was never wired up.
- [ ] **ARM18 — the shim signature lies.** The replacement takes `_p=False` while the
      real keyword is `patched=`, so any caller passing `patched=` raises `TypeError`.

---

## 5. Deliberately out of scope

- [ ] **ARM19** `/api/btc/seed` and `src/live/*` build chains from the shipped
      `SwingEngine` directly. Not reachable from a `_B1PATCH` request, but the live
      marks will not agree with the patched chart once this is adopted.
- [ ] **ARM20** Outside bars (both `up_break` and `down_break` true) hit the shipped
      V-reversal branch first, so the new branches are unreachable there. Behaviour is
      correctly preserved — the fix is incomplete, not wrong. Worth revisiting only if
      the owner finds a missing B1 on an outside bar.

---

## 6. Gates before anything is adopted

- [ ] G1 — ARM1, ARM2, ARM3, ARM4 closed.
- [ ] G2 — the guard rejects **something** and accepts something. A guard that never
      fires is not a guard; there must be a positive control proving both outcomes.
- [ ] G3 — chain built from 60,000 candles still matches the full run's prefix
      (no look-ahead regression).
- [ ] G4 — shipped chain unchanged after any patched request, over HTTP, repeatedly.
- [ ] G5 — one book only: `fsent_champ_long`, both eras, reported as a delta against
      the unpatched run of the **same** harness.
- [ ] G6 — the owner has looked at the marks and agreed.

## 7. Not being done yet

- [ ] Re-running the other 160 books. ARM3 means the earlier family run is void for the
      in-sample half. Deferred until this one book is right — it is 4 runs, not 648,
      and the same defects would repeat.
- [ ] Re-pinning or re-registering anything.
- [ ] Changing `firstswing.py`.
