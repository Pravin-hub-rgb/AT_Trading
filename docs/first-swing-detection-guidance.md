# First Swing Detection — Rebuild Spec

This replaces the current confirmation logic in `FsV2Engine` (in `flowline.ts`).
The pivot/walker infrastructure underneath it (`WalkerEngine`, session
extreme tracking, A/B sealing from bar one) is **not changing** — it already
does its job correctly. Everything below is about the layer on top of it:
how we decide a swing is real, and what happens if nothing resolves.

Read this top to bottom before touching code. Section 5 is the actual
implementation checklist; everything before it is the reasoning, so you
know *why*, not just *what*.

---

## 1. The core idea

Every day, from 9:15, the market prints a session high and a session low.
Call them **A** (high) and **B** (low) — whichever comes first doesn't
matter, they're just the two starting reference points.

From there, exactly one of three things happens:

1. Price keeps extending the same extreme, twice in a row → **Continuation**
2. Price extends one extreme, then reverses and breaks the other → **Reversal**
3. Neither happens cleanly by 10:00 → **Fallback**, or **no swing at all**

Only one of these fires per day. First swing only — nothing about
previous days matters.

---

## 2. Real detection

"Real" means: at least one genuine break has happened. Both paths below
end the same way — direction gets confirmed, then we wait for
**chop-back** or **7-bar sustain** to actually declare it.

### 2a. Continuation

Worked example, selling side:

- **A** = session high, **B** = session low (set from bar 1)
- Price breaks **B** → prints a new, lower low. Call this new low **C**.
  That's break #1.
- Price breaks **C** → prints an even lower low, **D**. That's break #2.
- Two extensions in a row, same direction → **direction confirmed**.

Mirror logic for buying (extending the high twice).

This is exactly what `sameSideBreaks >= 2` already does in the live code
(`FsV2Engine`, lines ~1000–1013 and ~1035–1054) — **no change needed
here.** It only counts a "break" when price clears the *current* extreme
pivot level and prints a fresh one — not a re-test of the same level.
Keep that behavior.

### 2b. Reversal

- Price breaks one extreme (say, breaks **B**, the low) — that's the
  first move.
- Price turns around and breaks the *other original* extreme (**A**, the
  high) — **one break is enough here**, not two.
- Direction confirmed = the reversal side (up, in this example).

This is what `oppositeSideBreaks = 1 → dirConfirmed = true` already does
(lines ~1006–1013, ~1038–1041, ~1055–1058) — **also no change needed.**
The logic is already correct; it just wasn't clearly documented, which is
part of why this spec exists.

**Important:** a reversal break is not an "invalidation." The old code
has a comment claiming an opposite break before "natural stage-2" should
invalidate the day (see Section 4). It doesn't actually do that anywhere
in the executable code (`preInvalidated` is declared but never set to
`true`) — and that's correct per this spec. An opposite break is not a
failure state, it's the *other real detection path*. Nothing about this
system should have a dedicated "invalidated" state. See Section 4.

### 2c. Confirmation (applies to both paths)

Once direction is confirmed, freeze the broken level as the reference,
and wait for either:

- **Chop-back**: price breaks back through any earlier pivot in the
  opposite direction. Counts as confirmation — the swing still stands,
  the market's just chopping before/around it. (`normalHighs`/
  `normalLows` check, lines ~1063–1089 — unchanged.)
- **Sustain**: price closes beyond the frozen level for 7 bars straight.
  Counter reset any time a fresh extreme prints in the trend direction
  (the streak has to be measured *after* the extreme is final, not
  during it). (Lines ~1092–1119 — unchanged.)

Whichever fires first wins. This part of the code is already correct and
matches this spec exactly — do not modify Section 2's confirm logic.

---

## 3. Fallback

This is new. It exists to guarantee the day never gets stuck with no
answer, and to keep Real detection honest — Real detection is allowed to
just... not fire, and that's fine, because Fallback covers it.

**Trigger:** only evaluated once, at **10:00**, and only if neither Real
path (2a or 2b) has already declared by then. Real detection keeps
running the entire 9:15–10:00 window with no early cutoff — Fallback
never preempts it.

**Rule, at 10:00:**
- Take the session range formed from 9:15 to 10:00 (`eHi.px` to `eLo.px`
  at that point).
- If price is currently in the **top 25%** of that range → declare an
  up-swing.
- If price is currently in the **bottom 25%** of that range → declare a
  down-swing.
- If price is sitting in the **middle 50%** → **declare nothing.**
  Explicit no-call — "no swing detected today, stand aside." Do not
  guess with a midpoint split, do not keep watching past 10:00. A
  genuinely unclear market is a real, valid outcome, not a bug to patch
  around.

**No confirmation step for Fallback.** No break required, no chop/sustain
wait. Position at 10:00 *is* the answer, for better or worse — that's
what makes it "fallback" rather than "real."

---

## 4. Cleanup: dead code in `FsV2Engine`

These fields are declared, written to, and **never read by anything that
affects `declared`/`confirmSource`/`dir`.** They're leftovers from an
earlier design (a "ZONE/STAGE" shortcut) that got superseded by the
break-based logic in Section 2, but nobody deleted the scaffolding.
Confirmed by grep — zero conditional reads on any of these:

- `stage`, `convertedByZone`
- `zoneSide`, `touchedUp`, `touchedDown`, `armedSeen`
- the local `armed` const (~line 951) and its inputs `armBars`,
  `armRangePts`
- `zonePct` getter (~line 889) and the `FsV2Opts.zonePct` field
- `preInvalidated` (declared, reset, checked at flush — but never set
  `true` anywhere, so the invalidation branch at the time-cap flush,
  lines ~1123–1125, is unreachable dead code too)

**Action: delete all of the above**, including the header comment block
at the top of the file (lines ~783–798) that describes the old
`E-PIVOTS → STAGES → ZONE → FINAL` design — replace it with a short
comment pointing at this doc instead. Fallback (Section 3) covers the
*intent* the old ZONE code was reaching for (a range-position shortcut),
but it's a cleanly separate tier now, not a shortcut buried inside Real
detection — so there's nothing to "revive," it's fully superseded.

### `FirstSwingEngine` (separate, older class — lines 640–768)

This is a different, simpler engine with a hardcoded `mPoints = 20`
point-distance trigger (T-A) plus a two-close rule (T-B). It predates
`FsV2Engine` and does not reflect this spec at all.

**Action: confirm whether this class (or `computeFirstSwingDeclared`,
line 755) is still referenced anywhere in the live app** — outside this
file, in whatever renders the UI. If nothing imports it, delete the
whole class (lines 640–768) along with the `T-A`/`T-B` comment block. If
something still does import it, that call site needs to be repointed at
the new `FsV2Engine` logic before this spec is considered fully live —
two engines producing two different answers for the same thing is worse
than either one alone.

---

## 5. Implementation checklist

- [ ] Confirm `FirstSwingEngine` usage across the app; delete the class
      if unused (Section 4)
- [ ] Delete dead ZONE/STAGE fields and the outdated header comment in
      `FsV2Engine` (Section 4)
- [ ] Leave Section 2 (continuation + reversal + chop/sustain confirm)
      as-is — it already matches this spec
- [ ] Add the Fallback tier (Section 3): a check that runs once, exactly
      at 10:00, only if `declared` is still `false`
      - top/bottom 25% of the 9:15–10:00 range → declare, no confirm
        step, tag the result so downstream consumers know it came from
        Fallback rather than Real detection (e.g. keep `confirmSource`
        but add a `"fallback"` value, or a separate `tier` field)
      - middle 50% → leave `declared = false` permanently, with a clear
        `noSwingToday = true` flag rather than silence — downstream code
        should never have to infer "nothing happened" from absence of a
        result
- [ ] Remove the now-fully-dead `invalidated`/`preInvalidated` state
      entirely — nothing in this spec produces an "invalidated" day.
      Outcomes are: Real (continuation), Real (reversal), Fallback
      (up/down), or explicit no-swing.
- [ ] No minimum swing size for now — this was discussed at length and
      deliberately parked. Do not add a size floor. (Revisit once
      there's a real history of declared swings to calibrate against —
      until then any number is a guess.)

---

## 6. Open items (not blocking, revisit later)

- **Size floor.** The idea on the table: build a rolling average of the
  9:15–9:45 move size over the past N days, require today's candidate
  to reach ~90% of that before Real detection is trusted. Parked
  because there's no historical data yet to calibrate against — wire it
  up once a few weeks of declared swings exist to check it against.
