# CORRECTED-MARK SWEEP — 2026-10-14

Work done after the volatile-B1 colour fix (`5d6cab2`) landed, i.e. on the
corrected chain: **2840 swings / 7734 marks, fingerprint `83a3af3f6ebf0ffa`**
(IS) and `8981622657925d4d` (OOS).

The premise for the whole sweep: **every threshold and every closed mechanism in
this repo was fitted to marks that were ~3% wrong.** 43 B2s had become FLIPs, 35
FLIPs had become B2s and 51 B1 directions had flipped. So the work is not only
"find new ideas" — it is "re-examine what was decided against a surface that has
since moved".

## Rules, applied to every phase

1. Every knob default-off, with an identity gate before any number is quoted.
2. Tune on **IS only**. OOS stays sealed until the item is decided.
3. Record both eras always, losing included.
4. Win → registry pin + doc. Loss → `closed/CLOSED_DO_NOT_REPEAT.md` with both
   eras and the mechanism. Harness kept either way.
5. Anything causal → every book using it becomes `status: "reference"`.

---

## A1 — baseline frozen

`backtest/tests/exp_baseline_freeze.py`, snapshot
`_baseline_2026_10_14.json`, taken at commit `1bb4be1`.

```
             15m mb50 fingerprint   swings  marks
  IS         83a3af3f6ebf0ffa        2840   7734
  OOS        8981622657925d4d        1571   4344
```

Five fsent books, both eras, recorded in the snapshot. `--compare` re-derives and
diffs; it is D2.

**Note on the fingerprint row format.** It includes the price column:
`time|kind|dir|px|swing`. An earlier fingerprint quoted in this session
(`393577a28ffd3e02`) was computed **without** the price column and is therefore
**not comparable** to `c864262630560f83` or to the values above. Treat that one as
void. The tool now states the format in its own output for exactly this reason.

---

## A2 — colour-rule consistency audit

### A2.1 Is colour routed identically on B1, B2 and FLIP? **YES.**

Four volatile sites, all reading `self.cl > self.op`:

| site | line | routes to |
|---|---|---|
| `watch` (B1) | `firstswing.py:466` | `_lock(...)` |
| confirmed-state volatile | `firstswing.py:524-525` | sustained → B2/FLIP |
| unconfirmed-state volatile | `firstswing.py:577` | `_flip` / `_b2_if_gap_allows` |

The B1 site was the one that was missing and was added on 2026-10-13. All four are
now the same predicate. **No inconsistency found.**

### A2.2 Is the B2 alternation rule still right after B1 locks by colour? **YES.**

`_b2_done_in_dir` and `_last_mark_kind` are untouched by the colour change —
`_lock` still resets `_b2_done_in_dir = False` and sets `_last_mark_kind = "B1"`
whatever direction it locked. The alternation keys off `_last_mark_kind`, not off
the direction, so making the direction colour-derived does not perturb it.
Confirmed empirically: FLIP-FLIP 0, B1/B2 same side 0 violations.

### A2.3 Does any volatile path still reach a bare return with no mark? **NO — but the check was blind.**

This is where the sweep found something, and what it found was **in the audit
tool rather than the engine**.

`exp_swing_invariants.py` reported "20460 suppressed breaks examined, 0
unexplained". That was **half the story**. `_step` is only called when
`self.armed` is True (`firstswing.py:428`), so the harness logged armed bars
only. There is a second population it never saw at all:

```
bars with a break, never armed   : 6154   (volatile 2841)
  ...pre-arm warmup (watch, no pending arm)   : 6040
  ...pending-arm deferral (same-bar arm guard) :  114
  ...unexplained                               :    0
TOTAL break-without-a-mark : 26614  (20460 armed + 6154 never armed)
```

Both un-armed buckets are legitimate and named — the engine had not been armed by
a seal and was not doing anything — but they were outside the check and a reader
had no way to know that. **A harness that passes because it excluded its own
subject is the failure mode this repo already warns about**, and it happened
again, in a harness written specifically to prevent it.

The harness now watches `process_bar` as well, recomputes the break flags at its
entry from the same `e_hi_prev`/`e_lo_prev` the engine uses at
`firstswing.py:374`, and reports the un-armed population as its own buckets. The
headline is now **26614 of 26614 classified, 0 unexplained** — and the number a
reader would have quoted is 77% larger than the one they were given before.

### The one real cost A2 exposed

`defer_same_bar_arm` is True for every swing after the first
(`btc_swing.py`), so each such swing defers its first break to the bar after the
seal. Measured: **579 of 2840 instances (20%) lose exactly one volatile bar** to
this before their first mark. One bar each, median 1, max 1 — bounded, but never
tested as a knob. It is the natural next candidate after B1.

---

*(B1, B2, C1, C2, D1, D2 appended below as they complete.)*