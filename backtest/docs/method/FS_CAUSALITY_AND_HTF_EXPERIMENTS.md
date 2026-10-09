# causality audit, and the HTF-side experiments

Date: 2026-10-09. Harnesses: `exp_fs_causality.py`, `exp_register_biasmom.py`.

---

# PART 1 — the causality audit the owner asked for by name

> "there was this base bug of lookahead and i wanna make sure that each trade are
> after fs of the prev swing this is must. i hope this was not violated"

**It was not violated. 0 violations, 6 books, both eras.** And the way that was
established is the interesting part, because the audit first reported **184
violations in the shipping book**.

---

## the audit was wrong before the books were

First pass: **184 C1 violations in `fsent_champ_long` IS**, 104 in OOS, and the
first one was:

```
entry 2023-01-02 15:15:00   fs 2023-01-02 15:15   lead_s = -19800
```

Same wall time, and every violation exactly **−19800 seconds** — which is 5h30m,
the IST offset. `entry_ts` is a real UTC epoch; `fs_at_time` is naive IST wall
time. I parsed both as UTC, so every FS print sat 5½ hours in the future of the
trade that fired on it.

**A causality audit that mis-reads the timezone cries wolf on the one question
that matters most in this repo.** Had that first pass been taken at face value it
would have said the entire fsent family reads the future.

Fixed by applying the loader's own convention, and — this is the part worth
keeping — **proving it before trusting any comparison**: the audit now asserts
that `entry_ts + IST_OFFSET_SEC` reproduces `entry_date` for every trade, and
**aborts rather than reporting a verdict** if it does not.

## what is checked, and why three separate checks

A trade is causal if three different moments are all in the past at entry. They
are separate because each is a different object reading a different field, and
combining them would hide which one broke.

| check | what it asserts |
|---|---|
| **C1** | `entry_ts >= ` the FS print of **its own swing** — the one the owner named |
| **C2** | the swing the **stop** is taken from had already printed FS. The stop sits at `seg.start_px`, the swing's origin; if that swing had not printed, the risk would be computed from a level the market had not reached |
| **C3** | the **HTF window** the trade is attributed to had already opened. C17 was exactly this — `window_end` read as `"exit"` let the gate see the exit before it happened |

**The join is exact, not inferred.** Trades carry `swing_no`, swings carry
`swing_index`, and they are the same enumeration. A nearest-timestamp join is the
only kind that could hide the bug being looked for, so it is not used.

## the result

| book | IS FS trades | C1 | C2 | C3 | OOS C1 |
|---|---:|---:|---:|---:|---:|
| `fsent_champ_long` (shipping) | 352 | **0** | **0** | **0** | **0** |
| `fsent_champ_short` (mirror) | 298 | **0** | **0** | **0** | **0** |
| `fsent_utcsat_long` | 346 | **0** | **0** | **0** | **0** |
| `fsent_sig_full` | 126 | **0** | **0** | **0** | **0** |
| `fsent_sig_multi` | 185 | **0** | **0** | **0** | **0** |
| `fsent_champ_long_htf15` | 352 | **0** | **0** | **0** | **0** |

Every FS trade joins exactly — 352 of 352, 206 of 206, no unjoinable rows.

**C3 also reports the lead from entry to `window_end`, so a book quietly leaning
on the far end of its own window is visible rather than assumed safe.** The largest
lead is 380.5 hours — about 16 days — meaning entries sit well inside their
windows and nothing is trading on the boundary.

**The audit exits non-zero on any violation.** A causality audit that can only
warn is not an audit.

---

# PART 2 — the HTF-side experiments

> "how we are trading on fs same way we do experiment opening htf window on fs
> stuff like that"

## what the HTF plane actually has

The engine is `sim(c1h, HTF_SWINGS, c15, LTF_SWINGS)`. `swings_htf` feeds four
things:

1. the leg ratio (`seg start_px / end_px`)
2. the **bias-momentum breaks** — `exp_bias_momentum_min` is a floor on
   *this HTF leg's magnitude ÷ the previous leg's*
3. the bias-flip series
4. `_sw_ts_dir_mag` — what tags each trade `flip` or `decisive`

**There are two real HTF knobs**, not one:

| knob | what it changes | how |
|---|---|---|
| **HTF leg length** | how many, how coarse the HTF windows are | `min_bars` on the 1h swing series: 10 → 1601 swings, 15 → 1479 |
| **`exp_bias_momentum_min`** | whether a window counts at all | a floor on the 1h leg's magnitude ratio |

The second is the closest thing the engine has to "the HTF window opens only on
strength" — it is literally the 1h leg's own measure deciding whether its window
counts.

**Note what is already on:** `exp_bias_momentum_min` runs at **0.8 on every sig
book** and is **OFF on every champ book**, and it was never swept on the champ
architecture. So this is the first time 0.5 and 1.0 have been measured there.

## the three approaches, each on its own correct swing series

| arm | n | net | dd IS | dd OOS | negative cells |
|---|---:|---:|---:|---:|---:|
| A. baseline (sw10, no biasmom) | 839 | +773.0 | 13.4 | 11.9 | **1 FAIL** |
| **B. htf15 leg only** | 800 | **+822.4** | 17.3 | 16.9 | **0 clean** |
| **C. biasmom 0.5 only** | 775 | +718.6 | **13.4** | 13.5 | **0 clean** |
| D. htf15 **+** biasmom 0.5 | 734 | +776.6 | 21.6 | 13.5 | 0 clean |
| E. htf15 + biasmom 1.0 | 511 | +557.9 | **12.0** | **10.1** | 0 clean |
| F. biasmom 1.0 only | 535 | +516.0 | 12.0 | 10.4 | 0 clean |

### the finding: the two HTF knobs do not combine

**D is worse than B on every axis that matters** — less net (+776.6 vs +822.4),
worse in-sample drawdown (21.6 vs 17.3) — while costing 66 more trades. Both
knobs are fixing the same thing, the weak HTF leg, and stacking them removes more
than it removes.

That is the same shape as every other stacking result in this repo's history, and
it is worth stating as a rule rather than a surprise: **two filters on the same
cause do not add.**

### the finding: the two knobs are two branches of one trade-off

| | net | dd IS | dd OOS | which |
|---|---:|---:|---:|---|
| **B. htf15** | **+822.4** | 17.3 | 16.9 | the **high-return** branch |
| **C. biasmom 0.5** | +718.6 | **13.4** | 13.5 | the **low-drawdown** branch |

**C is the one that matters for the owner's rule.** Its in-sample drawdown is
**13.42R — exactly the parent's** — while removing the negative half-year. Every
other arm that fixes that cell pays for it in drawdown. C pays in return instead:
−31.9R in sample, −22.5R out.

**And E/F show the drawdown branch goes further** — `biasmom 1.0` reaches 12.0R IS /
10.1R OOS, *below* the parent's 11.88R OOS — at a third of the return.

## registered: `fsent_champ_long_biasmom05`

IS 488t / +501.48R / DD **13.42R** / WR 39.5%
OOS 287t / +217.13R / DD 13.47R / WR 37.6%

`exp_fastcheck` reproduces every pinned field on both eras.

**So the owner now has both branches registered and the choice is explicit:**

| book | IS net | OOS net | IS dd | OOS dd | negative cells |
|---|---:|---:|---:|---:|---:|
| `fsent_champ_long` (shipping) | +533.4 | +239.6 | 13.42 | 11.88 | **1** |
| **`..._htf15`** — return branch | **+567.6** | **+254.9** | 17.28 | 16.86 | 0 |
| **`..._biasmom05`** — drawdown branch | +501.5 | +217.1 | **13.42** | 13.47 | 0 |

---

## what is not settled

Neither new book has had a period control run on it. `biasmom05` in particular
has had its negative cell removed but **has not been shown that the removal
survives a half-year fixed effect** — which is exactly the test that killed
`flip_quality` and that `htf15` passed at b = +0.57.

That is the next hour's work and it should be run before either is considered on
its merits rather than on its half-year count.

---

## verification

| check | result |
|---|---|
| `exp_fs_causality.py` | **exit 0** — 0 violations, 6 books, both eras, all three checks |
| TZ convention self-test | asserted on every trade; aborts rather than reporting |
| exact join | every FS trade joined by `swing_no`, 0 unjoinable |
| `exp_fastcheck` (2 new books) | PASS, every pinned field, both eras |
| registry snapshot | re-anchored at 154 rows |
| `exp_origin_lookahead` | PASS |
| shipping book | unchanged — 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS |