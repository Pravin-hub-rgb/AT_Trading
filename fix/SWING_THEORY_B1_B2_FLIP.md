# Swing Theory — B1, B2, FLIP (and FS)

**Status:** working theory, owner-ruled. Every rule below is traceable to a dated
chart walkthrough by the owner. Where the code and this document disagree, the
document wins and the code is the bug.

**Scope:** BTCUSDT_BYBIT 15m, 129,715 candles, 2023-01-01 05:30 → 2026-09-13 10:00.
Engine: `backend/src/firstswing.py` (`SwingEngine._step`, `_lock`, `_confirm_direction`,
`_flip`), fed by `backend/src/walker.py`.

> **Note on "tilt":** the owner asked this document to cover B1, B2, FLIP and tilt.
> No symbol, field or rule called *tilt* exists anywhere in `backend/src/`. It is
> recorded here as **undefined** rather than invented. If it is a real concept it
> needs a definition and a dated example before it can be coded.

---

## 1. The marks

| mark | meaning | direction |
|---|---|---|
| **B1** | the leg's first break — the swing begins | sets the leg's direction |
| **B2** | the leg's completion — the direction is now confirmed | same direction as its B1 |
| **FLIP** | the leg is abandoned; the opposite direction begins | opposite to the leg |
| **FS** | first-swing / declaration, separate family (see §7) | — |

A swing (leg) is `B1 → B2`, or `B1 → FLIP → …`, or `B1 → FLIP → B2 → …`.

---

## 2. The shape is `B1 → FLIP → B2`  (owner-confirmed)

The owner confirmed three dates by reading the chart:

```
2023-01-02  B1 01:45 → FLIP 02:30 → B2 09:15
2023-01-06  B1 13:30 → FLIP 14:30 → B2 19:15
2023-01-10  B1 06:00 → FLIP 08:00 → B2 13:45
```

**B2 returns to B1's side *after* the FLIP.** It does not sit between B1 and the FLIP.

Consequence: there is no `B2, FLIP, B2` shape to forbid, because no B2 ever comes
before the first FLIP. `firstswing.py` clearing `ever_b1_dir` on B2 is therefore
**correct behaviour, not a bug**. Measured: 343 swings have `FLIP,B2`; **0** have
`B2,FLIP,B2`.

Owner correction on his own notes: on 2023-01-06 the low is **19:00 L 16675.0**,
not 18:45 (which was 16675.5). Marks unaffected.

---

## 3. What breaks — the running extreme, not a sealed pivot

**OWNER, 2023-01-10** (extreme = the 06:30 high of 17230.0):

> "the highest point is 6:30, so anyone reaching it would be marked as B2. And 12:00
> is irrelevant because these are points inside the extreme."

```
06:30 high 17230.0   <- the running extreme, formed after B1
11:15 high 17228.0   <- did not reach 17230.0  -> no B2
12:00 low  17179.5   <- inside the extreme     -> irrelevant
13:45 high 17258.5   <- crossed 17230.0        -> B2
```

**So: B2 breaks the running extreme formed after B1.** Not a sealed pivot. Not B1's
own level.

This is confirmed in code — `firstswing.py:391-396` is a plain running maximum:

```python
if c.high > self.e_hi.px:
    self.e_hi = Lvl(px=c.high, idx=g_idx, time=self.t)   # running max
if c.low  < self.e_lo.px:
    self.e_lo = Lvl(px=c.low, ...)
self.e_hi_prev = Lvl(px=self.e_hi.px, ...)                # carried to next bar
```

`_tgt = self.e_hi_prev` / `self.e_lo_prev` **is** the running extreme as of the
previous bar.

### The single most important trap: `px` semantics are MIXED

| mark | `px` recorded | is it the level broken? |
|---|---|---|
| B1   | `self.locked_level` (`:540`) | **yes** |
| FLIP | `self.locked_level` (`:599`) | **yes** |
| B2   | `b2_pivot.px` (`:560`) | **NO — it is the candle's own new extreme** |

`_confirm_direction` records `px=b2_pivot.px`, and the B2 branch sets
`b2_pivot = Lvl(px=self.hi/self.lo)` — the candle's own extreme. So a B2's `px` can
never be compared to a cross:

```
2023-01-01 20:45  B2 dir=down px=16550.5   candle H 16560.5  L 16550.5
                              ^ exact equality against itself
```

**Any detector that checks B2 marks by comparing `px` to candle highs/lows fails every
single mark.** This produced a phantom "47% wrong" and then "1722 defects" across four
failed detector attempts. It is a *detector* bug, never an engine bug.

---

## 4. The 50-bar gate applies to FS only — never to B2 or FLIP

Owner-ruled. Do not apply it to B2/FLIP.

---

## 5. A FLIP can never be opposite the previous FLIP  (owner-ruled 2026-10-13)

> "The first check you should do for each swing is that if in a swing there is B1 and
> FLIP, so is FLIP and B2 opposite direction? ... Now the second flip cannot be the
> opposite direction. That's it. ... 02:30 breaking the extreme high, which was 01:30's
> high. So this should be a B2, not a flip."

So the rule is simply: **once a leg has a direction, a break against it is that leg's
B2 — it can never be a FLIP.** A FLIP always goes *with* the new direction, never
against it. No colour test is involved.

Worked example, `2023-01-18` (swing 34), owner-verified:

```
01:00 B1 up | 01:30 B2 up | 02:15 FLIP down | 02:30 B2 | 04:00 FLIP down
02:30 breaks the extreme high set at 01:30 -> B2, not a FLIP
04:00 is on the SAME direction as the 02:15 FLIP -> genuinely a FLIP, correct
```

**This single rule drove FLIP-FLIP alternation from 380 violations to 0.**

### 5.1 Correction to the shape

`2023-03-20 13:30` was originally read as a FLIP (2026-10-12). The owner re-traced it
on 2026-10-13 and **ruled it a B2**:

> "the extreme high, which was at 4:45, it got broken by 13:30, and this will be a B2
> because B1 and B2 are on the same direction. So 13:30 is a B2 here."

Note this was confirmed while `as_b2` was still broken (§6.4), so the original FLIP
reading was made against an engine that could not produce a B2 there at all.

> **⚠ OPEN DEFECT — now CLOSED.** 1 remaining B2-B2 at `2023-01-23 20:15`, where the
> owner confirmed B2 is correct. Effectively resolved; not yet reconciled in the code.

---

## 6. Volatile candles — the sustainability rule  (owner-ruled 2026-10-13)

> "we are waiting for marks after it closes… so we see if it is a green, what means it
> sustained on the B1 direction which was up, so we mark it B2… and same candle later
> will also have a down extreme and later if that low is broken we mark flip on the
> candle which breaks it."

A **volatile** candle breaks BOTH the high and the low extreme. The **colour after
close** decides:

| colour | means | result |
|---|---|---|
| **green** (close > open) | sustained **up** | if the leg is up → **B2**; if the leg is down → **FLIP up** |
| **red** (close < open) | sustained **down** | if the leg is down → **B2**; if the leg is up → **FLIP down** |

Then: **the volatile candle's opposite-side extreme becomes the standing extreme, and
the FLIP is marked on the candle that breaks *that*.** Not on the volatile candle.

### 6.1 The gap rule still applies to a volatile B2

> "if they break an extreme pivot for B2 there is a one candle gap. If there isn't a one
> candle gap, then we think we are neglecting it. But that pivot is already contaminated.
> So we should be waiting for the new extremes."
> "volatile B2 gaps apply… we have to wait for its break after one candle, more than a
> candle."

So a volatile candle **cannot** be B2 when the extreme it broke is contaminated (no
one-candle gap). In that case **no mark at all** — not B2, not FLIP — and we wait for a
fresh extreme to be broken instead.

### 6.2 Sustained the leg but no gap → nothing

> "B1 is up, then the next candle is green while it also has broken the extreme low, but
> we won't mark it flip because the candle sustained in the B1 direction, and we cannot
> mark it B2 also because there is not a gap. So we have to wait for a new candle."

### 6.3 Sustained the leg and a B2 already exists → nothing

Owner on **2025-12-19 20:00** (green, sustained up, but the leg already had its B2):

> "it doesn't even matter if we mark it B2, because we already have a B2… there is no
> point of marking it B2 because we already have a B2 here."

**No mark.** The FLIP then correctly waits for the break of 20:00's own low — which
lands at **23:00** (20:00 low 87443.9; 22:45 low 87505.0 does not reach it; 23:00 low
86713.0 does).

### 6.4 The gap rule explains 955 "broken but unmarked" breaks  (owner-ruled 2026-10-13)

Owner on `2024-06-26`: the 106-point drop at 10:45 correctly got **no** mark, and the
B2 landed on 11:15's 4.4-point extension — *"even a 0.5 point break is a break."*

```
10:45  L 61534.4   broke the extreme  -> NO MARK (no one-candle gap)
11:15  L 61530.0   broke 10:45's low  -> B2 MARK
```

**Structural consequence:** in a clean trend every bar makes a new extreme, so
`p.idx` is always `g_idx-1`, and `p.idx <= g_idx-2` is **never satisfiable**. B2
therefore cannot fire during a monotonic run at all — it always waits for a one-bar
pause, then marks the first bar that extends past the paused extreme, however
marginally. That is the intended behaviour.

Every B2-candidate bar in the chain, classified:

| bars | reason | verdict |
|---|---|---|
| 12,498 | gap contaminated | correct — owner-ruled |
| 4,621 | direction already confirmed → FLIP/as_b2 path | handled |
| 3,135 | B2 already done in this direction | correct — alternation |
| 14 | volatile, colour opposed → FLIP emitted | correct — colour rule |
| **0** | clean gap, unconfirmed, no prior B2, no mark | **no defects** |

Same for FLIP: the last **5** "broken but unmarked" cases are all volatile candles whose
colour sustained the leg (so a B2 was attempted and the gap gate rejected it), or the
owner-ruled `2025-12-19 20:00`. **Zero unexplained breaks in the chain.**

### 6.5 Where the code dropped volatile candles  (fixed 2026-10-13)

Before the fix, `firstswing.py` had a **dead branch**. Once `dir_confirmed` was True:

```python
412  if self.dir == "down" and up_break and not down_break:   # one-sided only
428  if self.dir == "up"   and down_break and not up_break:  # one-sided only
440  self._check_chop()
441  return                       # <-- unconditional: volatile bar produces NO mark
442  if self.dir == "down": ...   # unreachable while dir_confirmed
```

A candle breaking **both** sides satisfied neither 412 nor 428, fell into the bare
`return` at 441, and was **silently discarded**. Verified by line-tracing `_step` on
2023-09-03 13:30: lines executed were `405 → 411 → 412 → 428 → 440 → 441`, no mark emitted.

The `not down_break` / `not up_break` guards came from `7fe645d`, a feature commit —
**they were never an owner ruling.** Note that `fc2a0b4` is titled *"volatile bar B2
precedence now allows opposite flip on same bar"*, i.e. the owner had already ruled the
opposite at some point.

### 6.6 `as_b2` had never once fired  (fixed 2026-10-13)

The same self-comparison bug as V13, still alive in the as_b2 path:

```python
self.e_hi_pivot is not None and self.hi > self.e_hi_pivot.px   # bar vs itself, never true
```

`e_hi_pivot` **includes the current bar** (88ecd00's own note says so), so the condition
was always false and every post-FLIP break became a plain FLIP. Fixed to use
`e_hi_prev` / `e_lo_prev`. This is why the `B1 → FLIP → B2` shape confirmed on
2023-01-02 / 01-06 / 01-10 could not physically occur before the fix.

---

## 7. FS (first swing) — separate family, only partly ruled

- FS anchors on a **sealed pivot**, and the FS bar **breaks that pivot**.
- The pivot must be **fresh** (formed inside the current window).
- The pivot must also survive the **one-candle gap rule**, same as B1/B2
  (`firstswing.py:917-920` for a high, `:950-951` for a low). The bar immediately
  after a candidate pivot must **not** breach it; if it does, the pivot is
  contaminated and is rejected outright rather than marked.
  Owner-verified 2025-08-22 21:45 (swing 2038, up leg): pivot low 21:00 @ 116605.1
  was breached by 21:15 @ 116313.7 on the very next candle → rejected. Next pivot
  21:15 @ 116313.7 survived, because 21:30's low merely *equalled* it, and was
  broken at 21:45 @ 116075.0. So **21:45 is correct and 21:15 would have been
  wrong** — do not "fix" it as late.
- The 50-bar gate applies **here** (see §4), and FS may land **on** the gate bar
  but never before it. Owner ruling 2023-07-02: the 07:00 candle closes at 07:15,
  so at 07:15 it is simultaneously the minBars-50 bar and an FS — legitimate. An
  FS at 06:45 would be inside the window and must not be marked. Gate (timing) and
  gap rule (pivot quality) are independent and both must pass.
  Owner-verified 2023-07-02 07:00 (MB gate and FS on the same bar), 2023-03-19
  17:00→18:30, 2023-03-20 06:15→06:30, 2025-08-22 20:15→21:45.
- `defer_same_bar_arm`: a seal arms the engine on the **next** bar, except the
  V-reversal case (a bar that both seals its own extreme and crosses an older pivot of
  the matching kind is a real break — owner-verified on 2023-01-03 12:45, 2023-02-04
  15:45, 2023-01-14 06:45, 2026-08-14 22:45).
- Chop may only target pivots formed **after** the bar (`dir_established_idx`), else a
  cross of a pre-B2 pivot completes the leg early — owner case 2023-01-02 swing 8:
  B2@13:26 then cross of the pre-B2 13:24 low @13:27 would mark fs_at mid-swing.

---

## 8. Verification state (2026-10-13)

Branch `fix/fs-and-pivot-breaks` at `d71304f`, plus `0818cde` (frontend MB markers
only). BTC 15m, 2840 swings.

| check | result |
|---|---|
| `exp_two_point_missing.py` | **0 missing, 0 late** |
| `exp_fs_breaks_pivot.py` | 2840 ok / **0 fail on all four checks** — the old 40 check-2 failures are **closed**, not artefacts |
| `exp_g3_no_lookahead.py` | PASS, 4476 marks, 0 mismatches |
| `exp_v2_b2_flip.py` | gate 7/7 PASS; placement, target = running extreme, first-cross all **0 fail** |
| **FLIP-FLIP alternation** | **0** (was 380) |
| B2-B2 | 1 (`2023-01-23 20:15`, owner-confirmed correct) |
| unexplained breaks | **0** — every suppressed candidate is accounted for by the gap rule, alternation, or colour rule |

Chain: 2840 swings, **7734 marks** (B1 2840 / B2 2751 / FLIP 2143), after the
volatile-B1 colour fix (`5d6cab2`). Before it: 7740 (B1 2840 / B2 2742 / FLIP
2158). Full-chain fingerprint, sha256 of sorted `time|kind|dir|px|swing` rows +
FS rows, `minBars=50`, `max_swings=len(candles)//2`:
**`393577a28ffd3e02`** (was `c864262630560f83` — that move is expected, the fix
is a deliberate behaviour change, not a display change).

`exp_swing_invariants.py` (added 2026-10-13) is the standing gate: 7 emitted-mark
invariants plus the **suppressed-break** half, which classifies all 20,460 bars
where the engine saw a break and emitted no mark. 0 unexplained. That half
exists because `breaks` only ever contains marks that *were* emitted, so a
suppressed break cannot appear in the payload — the 2023-09-03 volatile FLIP bug
produced no mark at all and was invisible to any emitted-mark-only check.

`exp_v2_gate_deferral.py` (2026-10-13): B2 2742 marks, 968 of them with suppressed
candidates (1769 bars); FLIP 2158 marks, 5 with suppressed candidates (5 bars).
All classified, none unexplained — but this test cannot by itself tell the gate
doing its job from misfiring. It is a review list, not a verdict.

### Owner-confirmed dates — all 34 verified

`d71304f` and the MB review added four, all confirmed on-chart 2026-10-13:

```
2023-03-19 06:00 B1 | 06:30 B2 | 2023-03-20 06:30 FLIP | 13:30 B2   (V13 walkthrough)
2023-01-02 01:45 B1 | 02:30 FLIP | 09:15 B2
2023-01-06 13:30 B1 | 14:30 FLIP | 19:15 B2
2023-01-10 06:00 B1 | 08:00 FLIP | 13:45 B2
2023-09-03 13:30 FLIP | 2024-06-28 18:00 FLIP | 2024-11-14 20:00 FLIP
2025-09-05 18:00 FLIP | 2023-06-14 23:30 B2 | 2023-01-23 20:15 B2
2023-06-10 23:45 B2 | 2025-03-04 21:45 B1, 22:15 FLIP
2024-12-16 04:30 B2 | 2025-03-25 14:45 B2 | 2025-09-24 11:00 B2
2023-06-03 11:30 B2 | 2025-08-21 17:00 FLIP, 19:00 B2 | 2023-01-18 02:30 B2
2024-06-26 11:15 B2 (gap rule)
```

Plus 15/15 spot-checked FLIP<->B2 relabels confirmed correct (3 batches of 5).

### The four MB-review dates, owner-verified 2026-10-13

Each checked as `MB gate -> FS`, in chronological order:

| date | MB gate | FS | why it is correct |
|---|---|---|---|
| 2023-03-19 | 17:00 | 18:30 | 18:00 pivot, broken at 18:30 |
| 2023-03-20 | 06:15 | 06:30 | 05:30 pivot low first broken at 06:30 |
| 2023-07-02 | 07:00 | 07:00 | FS **on** the gate bar — owner-ruled legal |
| 2025-08-22 | 20:15 | 21:45 | 21:00 pivot contaminated by 21:15; gap rule moved FS to 21:45 |

### Measurement trap — the "refused break" claim was wrong

On 2026-10-13 a scan reported "a break happened at 06:15 inside the window and was
refused", and listed 458 swings as "decisive" on that reasoning. **That inference
was invalid.** It tested `breaks[0].idx < min_bars_idx <= fs_at_idx`, which only
establishes that the leg's *first mark* preceded its gate bar — it says nothing
about whether any break was suppressed. `breaks` lists marks that *were* emitted;
a suppressed break appears nowhere in it.

The owner corrected it directly on 2023-03-20: no break occurred at 06:15 at all.
The raw counts (227 FS exactly on the gate bar, 458 within two bars) are real but
mostly ordinary spacing, not evidence that the gate bound. The genuine
gap-rule evidence is the 2025-08-22 walk-through above, which was read off
candles and source, not inferred from indices.

**Do not cite an index comparison as proof that a rule fired.** Check the candle
that was skipped. This repo has a long run of confident, wrong measurements and
that pattern is still live.

### The volatile-B1 colour fix, owner-verified 2026-10-13

`5d6cab2` made a volatile B1 take its direction from the candle colour, matching
what B2 and FLIP had always done. It moved **51 B1 directions** and **78 mark
kinds** (`B2 ↔ FLIP` at the same bar), and moved 212 marks in total. The owner
traced these on the chart and ruled every line correct:

| date | what was checked | ruling |
|---|---|---|
| 2026-05-18 | `B1↑ 21:30` `FLIP↓ 21:45` `B2↑ 22:45` `FLIP↓ 23:45` `B2↑ 00:30` — all five bars appeared only after the fix | correct |
| 2023-01-01 | `B1↓→↑ 05:45`, FLIP `06:00` **added**, `FLIP→B2 07:00`, `B2→FLIP 12:45`, `FLIP→B2 17:30` | correct |
| 2023-02-12 | `B1↑→↓ 05:30` (red volatile), `FLIP→B2 06:00`, `B2→FLIP 15:15` | correct |
| 2023-02-25 | `B1↓→↑ 04:30`, FLIP `04:45` **removed** → `B2↑ 05:15` (mark moved 30 min later), `B2→FLIP 10:45` | correct |
| 2023-05-13 | `B1↑→↓ 12:30` (red volatile), `B2→FLIP 13:00` | correct |
| 2023-06-03 | `B1↑→↓ 12:15`, FLIP `12:30` **added** / B2 `13:00` **removed**, `FLIP→B2 14:00`, `B2→FLIP 20:45` | correct |

Both flip directions are now covered — green volatile → `B1↑` and red volatile →
`B1↓` — and all four kinds of change appear: direction flip, relabel, mark moved
later, and mark added or removed.

**Sampled, not exhaustive.** 6 of 51 direction flips and 11 of 78 kind changes
were put in front of the owner. `exp_swing_invariants.py` covers the rest
structurally; no chart review has, and no chart review can, cover all 7,734
marks.

### The 88% bucket was tested, not assumed

`exp_swing_invariants.py` puts 17,950 of 20,460 suppressed breaks into a single
bucket — *"confirmed + with-the-leg → no B2 by design"* — 88% of everything it
classifies. That rested on one structural claim read straight off `_step`: once
`dir_confirmed` is set there is **no plain-B2 path at all**.

`exp_dir_confirmed_b2_path.py` tests it by forcing `dir_confirmed = False` for
exactly one `_step` call on each such bar and restoring it immediately, so only
that one decision changes.

**Result: 6,668 bars produced a B2 that does not exist in the baseline.**
`dir_confirmed` is what suppresses them. The bucket is correctly attributed and
the harness is not resting on an unexamined assumption.

Note the forced run's chain diverges (7,734 → 12,403 marks) because flipping the
flag mid-run changes later decisions. That is fine for the question asked — *does
the B2 path exist* — but this test does **not** propose a corrected chain, and
the divergence must not be read as one.

### Marks that moved rather than relabelled

The colour fix removed 109 mark-keys and added 103. 78 of those are same-bar
`B2 ↔ FLIP` swaps. The remainder is a distinct shape: **a FLIP disappears and a
B2 appears later the same day** — 67 bars lost a mark, 36 gained one, because
the B1 now locks the other way and the leg re-sequences behind it.

Owner traced and ruled correct:

```
2023-01-01   FLIP 06:00 · FLIP->B2 07:00 · B2->FLIP 12:45 · FLIP->B2 17:30
2023-02-12   FLIP->B2 06:00 · B2->FLIP 15:15
2023-02-25   FLIP 04:45 gone · B2 05:15 appears (+0.5h)
2023-06-03   FLIP 12:30 added · B2 13:00 gone · FLIP->B2 14:00 · B2->FLIP 20:45
2023-09-09   FLIP 22:45 gone -> B2 23:30 (+0.8h)
2023-10-18   FLIP 20:45 gone -> B2 21:30 (+0.8h)
2023-11-28   FLIP 11:45 gone -> B2 13:15 (+1.5h)
```

Correction to an earlier figure: this category was first reported as "71 removed
/ 25 added". The correct counts are 109/103 at mark-key level, of which 78 are
swaps, leaving 67 lost and 36 gained.

### What is verified, and what is not

Chart-verified across this work: both flip directions of the volatile-B1 colour
rule, same-bar relabels, marks that moved later, marks added, and marks removed.

Not chart-verified: the remaining individual instances of each shape. The
harness covers those structurally and
`exp_dir_confirmed_b2_path.py` proved the largest suppression bucket rather than
assuming it, but no amount of testing turns 7,734 marks into 7,734 owner
confirmations.

`exp_v7_freeze.py` is stale by design (fixture predates the V13 and volatile changes) —
drift is expected and is not a failure.

---

## 9. Rules that are settled — do not re-open

1. B1/B2 share a direction; FLIP is opposite. (§2)
2. Shape is `B1 → FLIP → B2`. (§2)
3. `ever_b1_dir = None` on B2 is **not** a bug. (§2)
4. B2/FLIP target the **running extreme**, not a sealed pivot. (§3)
5. A B2's `px` is the candle's own extreme and must never be cross-compared. (§3)
6. The 50-bar gate is FS-only. (§4)
7. **A FLIP can never be opposite the previous FLIP** — a break against the leg's
   direction is that leg's B2. (§5)
8. Volatile candles are decided by **colour after close**, and **only volatile
   candles** — one-sided B2s ignore colour entirely, which is why the red B2s
   `2023-03-19 06:30` and `2023-01-06 19:15` are legitimate. (§6)
9. Volatile B2 still obeys the gap rule; a contaminated pivot means **no mark** and
   we wait for the fresh extreme. (§6.1, §6.4)
10. The gap rule is correct even when it discards a large move and marks a tiny
    extension — *"even a 0.5 point break is a break."* (§6.4)
11. **A volatile B1 takes its direction from the candle colour**, exactly like
    volatile B2 and volatile FLIP. Rule 8 was never applied to B1 — B1 was the
    only kind whose direction came from *which extreme broke*, and the watch
    branch tested `if down_break` first, so a volatile B1 always locked DOWN.
    The same-bar arm guard compounded it by deleting one of the two breaks
    before `_step` ran, hiding the volatility entirely.
    Owner 2026-10-13, 2026-05-18 21:30 (green → `B1↑`) and 2023-02-12 05:30
    (red → `B1↓`). 197 volatile B1s in the chain, all 51 flips of which are
    colour-consistent. One-sided B1s still take direction from the break, not
    the colour — checking colour on every B1 produces ~398 false alarms.
