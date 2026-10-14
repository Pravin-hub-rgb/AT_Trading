# TIER 4 — ENTRY BREAK AND PARAMETER PLATEAU

**Written 2026-10-14 on the corrected chain (2,840 swings / 7,734 marks).**

`exp_optimalbook_study.py` states that tier 4 of
`docs/learn/finding optimal book.md` — parameter plateau, cost sensitivity,
cross-asset — "is a separate harness per axis and is **NOT faked here**". This
document is two of those axes. The third, cross-asset, is still open.

---

# AXIS 1 — WHICH BREAK SHOULD OPEN THE WINDOW?

## Why this needed re-asking

The entry-break presets in `backend/src/btc/btc_routes.py` — `decisive` / `flip` /
`b2`, and the `fs_long` / `fs_short` / `fs_both` family — were last touched on
**2026-09-07** (`7ec23b4`).

That is before the B1 arming fix (2026-10-11, `77711a6`), before V13
(2026-10-12, `88ecd00`), and before the volatile-B1 and same-bar duplicate-pivot
work (2026-10-13). Every number those presets produced was measured while B1, B2
and FLIP were landing on the wrong bars.

**So the ranking between the entry breaks had never been a ranking of anything
real.** The books were re-pinned; this question was never re-asked.

## How the knob works

`unified.py:629-636` already runs all three HTF entry breaks on every call and
picks between them:

```python
_fb_flip = ("fs_both" if "flip"     in move else "flip")
_fb_dec  = ("fs_both" if "decisive" in move else "decisive")
_fb_b2   = ("fs_both" if "b2"       in move else "b2")
```

so `exp_htf_fs_entry="flip" | "decisive" | "b2"` moves **one** entry onto the FS
print and leaves the other two on their break. The LTF plane is held fixed at
normal break entry throughout, so nothing else varies.

Harness `exp_entry_break_study.py`, artifact `_entry_break_study.json`. Risk model
is the shipping champion's, both eras, costs applied.

## Result

| era | entry | n | net | avgR | PF | maxDD | WR |
|---|---|---|---|---|---|---|---|
| **is** | decisive (B2 or FLIP) | 419 | 140.16 | 0.335 | 1.413 | 39.5 | 24.3% |
| **is** | b2 only | 419 | 140.16 | 0.335 | 1.413 | 39.5 | 24.3% |
| **is** | flip only | 716 | 279.31 | 0.390 | 1.503 | 52.6 | 26.1% |
| **is** | htf_fs = all three | 716 | 279.31 | 0.390 | 1.503 | 52.6 | 26.1% |
| **is** | **FS print (long)** | **497** | **428.22** | **0.862** | **2.865** | **23.2** | **38.6%** |
| **is** | FS print (both) | 578 | 358.60 | 0.620 | 2.380 | 22.6 | 36.0% |
| **oos** | decisive (B2 or FLIP) | 249 | **2.04** | 0.008 | 1.011 | 42.1 | 24.9% |
| **oos** | b2 only | 249 | **2.04** | 0.008 | 1.011 | 42.1 | 24.9% |
| **oos** | flip only | 358 | 60.38 | 0.169 | 1.229 | 38.2 | 25.1% |
| **oos** | htf_fs = all three | 372 | 56.84 | 0.153 | 1.209 | 47.3 | 24.7% |
| **oos** | **FS print (long)** | **281** | **194.25** | **0.691** | **2.640** | **10.5** | **40.9%** |
| **oos** | FS print (both) | 347 | 120.80 | 0.348 | 1.810 | 18.3 | 35.4% |

## THE RESULT, AND IT IS NOT A REFINEMENT — IT IS A DIFFERENT BOOK

**Entering on the break is close to dead out of sample.** `decisive` and `b2` both
land at **+2.04R on 249 trades**, which is expectancy of **0.008R** — a book that
does not work. FLIP holds +60.38R and is the only break-based arm with any
out-of-sample edge.

**Entering on the FS print is not a better version of the break entry. It is a
different strategy:**

| | break entry | FS print |
|---|---|---|
| OOS expectancy | 0.008R | **0.691R** — 86× |
| OOS PF | 1.011 | **2.640** |
| OOS maxDD | 42.1R | **10.5R** — a quarter |
| OOS win rate | 24.9% | **40.9%** |

Win rate up 16 points, drawdown down to a quarter, expectancy up 86×, in the
out-of-sample era alone. **On this chain the FS print is the only one of the six
entry modes with an out-of-sample edge worth having.**

This is consistent with what the repo already found independently: the
`FS-EXTreme trail trigger` work (`9afbcb7`) and the `FS-break confirmation` work
(`dc48367`) both closed on the same mechanism — *by the time the FS candle's own
extreme breaks, the move that made the FS worth taking is already behind you.*
Entering **at** the print rather than after its extreme break is the same
mechanism, used in the book's favour.

## `decisive` and `b2` ARE THE SAME BOOK — and that is worth knowing

Every cell is byte-identical between the two. **This is not a copy error.** The
1h chain at min_bars 10 does carry FLIP marks — 985 in sample, 599 out of sample —
but the windows a FLIP-only entry opens are a **superset** of the ones `decisive`
opens. `decisive` never reaches a trade that `b2` does not.

**Practical consequence: `decisive` is not a third option.** Any future experiment
that lists "decisive" as a candidate alongside "b2" is comparing a book to itself.

## Honest limits

- **One risk model.** The FS-entry advantage is measured on the shipping
  champion's knobs. It is not yet shown that the ranking survives a different
  risk model, and the earlier `mode_*` books would be the obvious second sample.
- **Two eras, one split.** OOS here is the Bybit out-of-sample window; a result
  this large is unlikely to be noise but it is still one split.
- **The LTF plane is held at break entry.** Whether FS-entry also wins when applied
  on the 15m plane is not tested here — `exp_fs_entry_side` is a different knob
  and is what the shipping book already uses.
- **`htf_fs = all three` is worse than `flip` alone** in OOS (56.84 vs 60.38) on
  more trades (372 vs 358). Not significant, but it does not argue for "all".

---

# AXIS 2 — PARAMETER PLATEAU (the one the registry itself flagged)

## Why this needed re-asking

`fsent_champ_long_mode_atr_low`'s own registry description records the worry:

> "Its own threshold swept 0.20-0.60 and the OOS gain peaks sharply at 0.35
> (+41.1R) and is NEGATIVE everywhere else — one point, not a region, which is
> exactly the grid-peak failure P69 warns about."

That sweep predates every mark fix. **A threshold that peaks on one point may peak
there only because the marks moved.**

## Result — a plateau, not a spike, in both modes and both eras

Harness `exp_plateau_atr.py`, artifact `_plateau_atr_low.json`, nine points.

### `atr_low` (`fsent_champ_long_mode_atr_low`, `exp_fs_entry_side=long`)

| thr | IS n | IS net | IS PF | IS DD | OOS n | OOS net | OOS PF | OOS DD |
|---|---|---|---|---|---|---|---|---|
| 0.20 | 519 | 501.72 | 3.106 | 23.2 | 263 | 168.38 | 2.462 | 10.5 |
| 0.25 | 521 | 415.15 | 2.612 | 43.3 | 265 | 161.42 | 2.397 | 11.1 |
| 0.30 | 565 | 430.24 | 2.568 | 45.4 | 264 | 179.76 | 2.576 | 13.4 |
| 0.35 | 612 | 478.37 | 2.638 | 44.4 | 269 | 174.79 | 2.474 | 13.2 |
| 0.40 | 642 | 531.77 | 2.771 | 42.4 | 278 | **200.84** | 2.601 | 18.8 |
| 0.45 | 660 | 536.96 | 2.727 | 42.4 | 299 | 132.60 | 1.906 | 18.8 |
| 0.50 | 656 | 509.27 | 2.633 | 42.4 | 314 | 132.04 | 1.857 | 18.8 |
| 0.55 | 658 | 509.01 | 2.629 | 42.4 | 326 | 128.59 | 1.814 | 18.8 |
| 0.60 | 660 | 509.41 | 2.626 | 42.4 | 326 | 130.29 | 1.839 | 18.8 |

**IS: 9 of 9 positive**, range 415.15 .. 536.96.
**OOS: 9 of 9 positive**, range 128.59 .. 200.84.

### `atr_high` (shipping `fsent_champ_long`) — the control

| thr | IS n | IS net | IS PF | IS DD | OOS n | OOS net | OOS PF | OOS DD |
|---|---|---|---|---|---|---|---|---|
| 0.20 | 638 | 437.77 | 2.430 | 44.5 | 351 | 141.92 | 1.850 | 19.2 |
| 0.25 | 638 | 543.64 | 2.898 | 21.9 | 349 | 147.17 | 1.880 | 18.0 |
| 0.30 | 596 | 538.68 | 3.043 | 21.9 | 352 | 131.42 | 1.777 | 21.2 |
| 0.35 | 550 | 462.43 | 2.840 | 21.9 | 347 | 129.63 | 1.789 | 20.1 |
| 0.40 | 517 | 419.45 | 2.731 | 22.0 | 338 | 108.44 | 1.682 | 22.8 |
| 0.45 | 499 | 417.25 | 2.788 | 22.0 | 315 | 187.00 | 2.380 | 14.6 |
| 0.50 | 505 | 433.72 | 2.860 | 22.0 | 298 | 192.95 | 2.537 | 11.3 |
| 0.55 | 502 | 432.20 | 2.863 | 22.0 | 287 | 182.77 | 2.489 | 11.3 |
| 0.60 | 500 | 444.41 | 2.931 | 22.0 | 286 | 195.20 | 2.613 | 9.6 |

**IS: 9 of 9 positive**, range 417.25 .. 543.64.
**OOS: 9 of 9 positive**, range 108.44 .. 195.20.

## What this retires, and what it does not

**It retires the recorded reason** the `mode_atr_low` book was kept open. The
claim was that its only support was a single threshold value — a grid peak. On the
corrected chain it is a plateau: 9 of 9 points positive in both eras, in both
modes.

**It does not promote the book.** `fsent_champ_long_mode_atr_low` is still blocked
on buckets 2 and 9 — drawdown against the owner's 29R budget — at **48.76R worst
start-date drawdown** per `ANY_START_WORST_CASE.md`, which is roughly 65% over
budget. That is a separate question from the shape of its threshold.

**The control matters as much as the result.** `atr_high` is a plateau too, so
"9 of 9 positive" is not an artefact of the grid or of the mode. Both regimes
survive the whole range.

## Honest limits

- **Nine points is a coarse grid.** A plateau on 0.05 spacing could still hide a
  narrow spike between points. The doc's own warning about grid peaks applies
  here too — the grid is finer than the original 0.35-only claim, not infinite.
- **The OOS trough is flat from 0.45 to 0.60** (132.60 / 132.04 / 128.59 /
  130.29) while 0.20-0.40 sits higher (128-201). That is a mild step, not a
  plateau-with-a-shoulder, and is worth knowing before anyone picks 0.35 because
  it is the current pin.
- **Only one threshold was swept.** `chop_thresh` (58.0), `cooldown_bars` (8) and
  `max_consecutive_losses` (3) are all unswept here and are all load-bearing.
- **Cross-asset (tier 4's third axis) is still not measured.**

## What this does and does not authorise

Nothing is adopted by this document. It removes one recorded objection and leaves
the book's drawdown objection standing.