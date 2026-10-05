# B1 / B2 / FLIP decomposition — free, and it kills the whole idea

**Date:** 2026-09-27
**Harness:** `backtest/tests/exp_break_kind.py` → `_break_kind.json`
**Cost: zero new sims, zero new data, zero new code. It answered the question
in ~90 seconds and the answer is NO.**

---

## Why this framing

Every experiment in this programme treated a signal as a **point in time with a
direction** and asked whether to take it, skip it, or delay it. That framing is
exhausted — Rule 17 closed it, and log 111's 5m gate lost 222R in 36/36 cells.

`B1 / B2 / FLIP / FS` are a different object. They are **states of a state
machine**:

* **B1** = first A/B break → **locks** the direction, `dir_confirmed = False`
* **B2** = fresh-extreme extension → **confirms** that lock
* **FLIP** = the opposite extreme breaks → the engine **reverses its own lock**
* **FS** = first-swing declaration, confirmed either by chop-break (▲FS) or
  sustain (◆SUS)

A FLIP is the engine *admitting it was wrong*. That is a self-declared error,
not a market-derived label — exactly the kind of information a filter cannot
manufacture, because it is already sitting in the book.

## It was free

The engine tags every trade at build time:

```
ltf_trades.append({... "break_kind": sig["kind"] ...})      # L1811
```

and the live LTF path already branches on `kind` four separate times
(`exp_b1_b2_mode`, `exp_vol_b2_rvol`, `exp_kinds`, `exp_entry_skip_b2_doji`).
So the engine *itself* already treats these as different kinds of thing. The
decomposition only had to bucket the books we had already simulated.

## The result — and it is a reversal, not an edge

### bybit IS (3.67y)

| lane | kind | n | % trades | net | % net | median | trimmed | PF | top5 |
|---|---|---|---|---|---|---|---|---|---|
| champion | B2 | 249 | 49.8% | +32.0 | **9.8%** | −1.08 | −0.31 | **1.17** | **384.2%** |
| champion | FLIP | 251 | 50.2% | +293.8 | **90.2%** | −1.11 | −0.09 | **2.43** | 114.4% |
| utcsat | B2 | 238 | 52.4% | +66.0 | 18.4% | −1.07 | −0.20 | 1.37 | 190.6% |
| utcsat | FLIP | 216 | 47.6% | +292.9 | **81.6%** | −1.11 | +0.00 | 2.66 | 107.1% |
| age10 | B2 | 45 | 34.6% | +75.8 | 17.4% | −0.08 | +1.08 | 4.46 | 45.2% |
| age10 | FLIP | 85 | 65.4% | +360.0 | **82.6%** | +0.07 | +2.42 | 9.10 | 50.4% |

### bybit OOS (2.0y) — the reversal

| lane | kind | n | % trades | net | % net | median | trimmed | PF | top5 |
|---|---|---|---|---|---|---|---|---|---|
| champion | B2 | 148 | 53.0% | +68.9 | **98.1%** | −1.02 | −0.01 | 1.73 | 114.6% |
| champion | FLIP | 131 | 47.0% | +1.3 | **1.9%** | −1.08 | −0.56 | **1.01** | **6084.7%** |
| utcsat | B2 | 144 | 56.9% | +39.0 | **64.8%** | −1.04 | −0.13 | 1.42 | 166.3% |
| utcsat | FLIP | 109 | 43.1% | +21.2 | 35.2% | −1.07 | −0.42 | 1.24 | 329.5% |
| age10 | B2 | 41 | 53.9% | +23.9 | 55.3% | −0.58 | +0.20 | 2.06 | 79.6% |
| age10 | FLIP | 35 | 46.1% | +19.4 | 44.9% | −1.06 | +0.41 | 1.77 | 39.2% |

**All three lanes reverse.** FLIP goes from 90.2% → 1.9% of net on champion.
Note the FLIP top-5% concentration of **6084.7%** on OOS champion: that bucket's
entire +1.3R is one or two trades wearing a costume.

This is **the S3 pattern from log 109, reproduced exactly** — a
consistent-looking IS effect that reverses OOS, from the same root cause.

## The conclusion, which is the actual value of this run

> **`B1` / `B2` / `FLIP` carry no stable economic distinction on this strategy.**

Not "the effect is small." *The sign of the effect flips between eras, in every
lane.* Any proposal of the form "trade FLIP, not B2" — or its inverse — is
mining noise, and the `exp_kinds` knob sitting in the engine at L1293 is a
loaded gun for exactly that mistake.

The broader law this re-confirms, in its starkest form: **sub-bucket statistics
on these books are governed by one or two trades.** 384% and 6084% top-5%
concentrations are not edge cases; they are the normal state. Rule 13/14 exist
because of this, and this run is the cleanest demonstration yet.

## What this kills, cheaply

Before anyone spent a day on it:

* "trade FLIP not B2" (and the reverse) — **dead**, era-dependent.
* "FLIP entries are the engine's own mistakes, so they're more honest" —
  **dead**, it reversed.
* Any `exp_kinds` tuning — **dead**, it is a free parameter to overfit with.

## What survives at this level, and why

The labels are unstable, but the *process* around them is not. These ideas do
not depend on a label's historical avgR:

1. **The B1→B2 unconfirmed window as an uncertainty object.** B1 locks with
   `dir_confirmed=False` and the engine then does nothing until B2/FLIP. That
   window is a genuine, engine-acknowledged "I don't know yet" period. Sizing
   by state (half size while unconfirmed) changes *exposure during uncertainty*
   rather than filtering — no trade removed, so Rule 18's slot-cascade does not
   apply.
2. **B1 as an early-warning read, using a higher TF to move the frontier.** At
   B1 time, does the 2h/4h swing state indicate which way this lock resolves?
   That is not a direction *comparison* on a trade, so Rule 17 does not reach it.
3. **Latency (B1→B2 duration), volatility-normalized by a higher TF.** A slow
   confirm in a quiet 2h is a different object from a slow confirm in a violent
   2h. Orthogonal to direction — Rule 17 closed direction, not timing.
4. **The `chop` category.** `_compute_swings` supports a `b2_vs_flip_chop` mode
   that emits `chop` as distinct from B2 and FLIP. The live path uses
   `continuous`, which does not separate it. Untested.
5. **FS source: chop-break (▲FS) vs sustain (◆SUS).** Two structurally
   different confirmation paths. The chart plan notes `fsMarkers` carries only
   `{idx, invalid}` with no source field. If the Python engine also drops it,
   that is a free decomposition — but given the reversal above, it must be
   judged on **both eras simultaneously** or it is already dead.

## The honest meta-lesson

This is the second time this programme has walked into the S3 trap (log 109's
2h-opposing, now the break-kind reversal). Both times the IS looked decisive and
the OOS inverted it. The cheap defence that worked both times is exactly what
worked here: **decompose first, in both eras, before writing anything down** —
and notice that the cheapest possible decomposition is one the engine already
stores in every trade record.

The one intervention that has ever survived here — the wick gate, +28.1R IS,
4/4, replicated — did so because it was causally motivated, pre-registered, and
implemented in-engine with gray. Not because a bucket once looked good.


Read only this and you have a beautiful, publishable, wrong story: **the
engine's textbook continuation signal is nearly worthless (PF 1.17, carrying
9.8% of net from half the trades, with 384% of its net in the top 5%), while
the money comes from FLIP — the engine reversing its own mistake.**
