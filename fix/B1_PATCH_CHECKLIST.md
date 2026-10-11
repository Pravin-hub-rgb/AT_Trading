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

**DONE, and owner-confirmed on the chart.** The same-direction break is accepted
whenever the pivot it broke was sealed on an EARLIER bar; the phantom (pivot sealed
on this very bar) stays suppressed. Promoted into `backend/src/firstswing.py` itself.

Owner at the top of the chart, 2023-01-03:

> now we have a pivot at 12:30. Whatever breaks it would be considered as a B1, and
> 12:45 clearly breaks it ... So this seems like patched. This is correct here.

Then re-confirmed after promotion: *"on both engine, 12:45 is marked as a B1."*

Verified on the promoted chain: `2023-01-03 12:45` B1 down 16713.0, `13:00` none,
`2023-02-05 07:00` none, `2023-03-11 08:00` none, `2023-01-14 06:45` B1 down,
`2026-08-14 22:45` B1 up. `test_1h_parity_deep` still passes.

Unpatched and patched are now the same chain (7975 marks). `patched_swings.py` returns
the shipped chain instead of generating a redundant second copy.

**Scope note — ARM1 was the arming guard only.** Marks firing on the normal
(non-pending) arming path were never in scope. 97 of them still fail the owner's own
rule. That is ARM25, not a reopening of ARM1.

### [x] ARM2 — The measurement and the patch use different fields

**Closed by ARM1.** The guard tests `e_hi_pivot.idx` / `e_lo_pivot.idx` — the sealed
pivot, which is exactly what `exp_arming_cost.py` classified with. Implementation and
measurement finally refer to the same field.

### [ ] ARM3 — The family harness never patched the IS era

`exp_b1_patch_family.py` rebinds `src.btc.btc_routes._compute_swings`. The IS loader
`run_experiment.get_data()` holds its own module-global binding, imported at import
time — rebinding the route attribute does not reach it. `get_data()` additionally
memoises its chains, and the **old** side runs first and fills that cache.

Visible in the artifact already on disk: IS cells are identical across sides, only
OOS moves.

- **Bot A fix:** clear the loader cache between sides and bind the flag where the
  IS loader actually resolves it.
- **Owner check:** none — this one is objectively a harness defect, no chart needed.

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

## 3. OPEN — marks still in the wrong place, outside the arming guard

### [ ] ARM25 — 97 marks still fail the owner's own rule

ARM1 fixed the **arming guard** path. Marks that fire on the **normal** (non-pending)
arming path were never in its scope, and a pass of the owner's own rule over the whole
promoted chain still leaves these behind.

The rule, as the owner states it: a mark is legitimate if it broke **either** a pivot
sealed on an earlier bar **or** the extreme of the leg's first candle (the white flow
line has not been drawn yet, so the first candle's extreme substitutes).

```
pivot-break        7728
first-candle-ext     152
WRONG                 97      <- B1: 34   FLIP: 63
```

Every one of the 97 has `piv_idx == g_idx`: the mark sits on a pivot that was sealed on
its own bar, and the bar did not cross the sealed pivot level either. Both rules
reject it.

- **Earliest remaining wrong B1:** `2023-02-04 15:45 IST`, B1 up, pivot 23378.0 sealed
  on that same bar. The candle's own high *is* 23378.0, so the "break" is against its
  own extreme.
- **Earliest remaining wrong mark of any kind:** `2023-01-02 17:00 IST`, FLIP down.
- Full list: `backtest/tests/_arm1_remaining_wrong.json`.

- **Owner check:** is `2023-02-04 15:45` a correct B1 up or not? The answer decides
  whether the normal arming path needs the same `piv.idx < g_idx` guard the pending
  path now has, and whether FLIP is in or out of scope.
- **Owner check:** is `2023-01-02 17:00` a correct FLIP down?

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
