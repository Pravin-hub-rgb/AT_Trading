# HTF plane 1h vs 2h — parent timeframe test

**Date:** 2026-09-27 · **Harness:** `backtest/tests/exp_htf_2h.py` → `_htf_2h.json` (149s) · **Status: NOT ADOPTED. 1h stands. Direction closed.**

## What was asked

Everything in this programme so far changed *what* is traded (a flag) or *how
much* is risked (position size). Nothing had changed the *plane* the strategy
reasons on. This tests the one structural assumption never questioned: **is 1h
the right parent timeframe at all?**

## Pre-registered, before the run

- **Control:** 1h arm must reproduce the published books exactly (500t/+325.8 IS).
  If the patch leaked or broke, abort.
- **Arms:** 1h (control) vs 2h. LTF 15m and fine 1m **unchanged** — only the
  parent plane moves.
- **Lanes:** champion / utcsat / age10, IS + OOS.
- **No gate.** This is measured, not passed. The question is "better or worse".
- Nothing adopted.

## Data — no downloads needed

There is no 2h CSV anywhere in `data/` (Bybit ships 15m/1h/1m/4h/5m). But 2h
is exactly 2×1h, so it resamples losslessly:

| Scope | 1h rows | 2h buckets | complete 2h bars | dropped |
|---|---|---|---|---|
| IS | 32,434 | 16,218 | **16,216** | 2 |
| OOS | 17,520 | 8,761 | **8,759** | 2 |

A bucket is kept only if it has **both** 1h legs — a half-formed 2h candle
must never reach the engine. Exactly 2 buckets are dropped per scope, and both
are the **ragged series edges**, not gaps: verified as bucket index 0 and the
final index (`2022-12-31 18:00` / `2026-09-13 04:00` IS; `2020-12-31 18:00` /
`2022-12-31 18:00` OOS). **Zero interior gaps in either era**, so the OOS
result is not a data-quality artifact.

*(Note on timestamps: the raw CSVs stamp 1h bars at `:30`; the loader
hour-aligns them to the opening boundary. Bucketing is done on the engine's
hour-aligned convention, which is what the engine sees.)*

## The finding that made this non-trivial

The shipped engine hard-codes 1h arithmetic, and one of the seven sites is
load-bearing for causality:

```python
# backend/src/btc/engines/htf_ltf/v18_streak_halt.py:269
candle_ts_htf_close=[t+3600 for t in candle_ts_htf]
```

This list is the **causality gate** — it decides which parent bar has CLOSED and
may therefore be read. Feeding 2h candles while it still says `t+3600` lets the
engine read a 2h bar's high/low/close **one hour before it actually closed**.
That is a lookahead leak, not a subtle bias.

So the plane shift is *only* valid because the harness patches that constant to
7200. The other six sites are LTF-side (`ts+900` = 15m close, `2700` = window
bounds) or derived, and correctly stay.

> **Do-not-repeat rule:** any future work that changes the HTF plane must move
> `candle_ts_htf_close` in the same commit, or it is not a plane test — it is a
> leak with a plausible-looking number attached.

## Result — 2h loses 6/6, and the way it loses is the informative part

| Cell | 1h n | 1h net | 1h DD | 1h PF | 2h n | 2h net | 2h DD | 2h PF | Δnet |
|---|---|---|---|---|---|---|---|---|---|
| is/champion | 500 | **+325.8** | 27.7 | 1.81 | 484 | +49.4 | 60.6 | 1.13 | −276.4 |
| is/utcsat | 454 | **+358.9** | 21.2 | 2.01 | 436 | +59.7 | 46.1 | 1.18 | −299.2 |
| is/age10 | 130 | **+435.7** | 8.7 | 7.57 | 125 | +184.4 | 7.8 | 3.70 | −251.3 |
| oos/champion | 279 | **+70.2** | 53.2 | 1.34 | 254 | **−55.8** | 95.2 | 0.74 | −126.0 |
| oos/utcsat | 253 | **+60.2** | 29.4 | 1.33 | 228 | **−56.1** | 80.5 | 0.71 | −116.3 |
| oos/age10 | 76 | **+43.2** | 8.6 | 1.91 | 79 | +13.6 | 8.2 | 1.28 | −29.6 |

All six 1h controls reproduced their published numbers exactly.

## Why this is not just "2h is coarser"

The obvious objection: 2h is a slower, blurrier version of 1h, so of course it
does less. The data refutes that reading:

1. **Trade count barely moves** — −3% to −9% in five of six cells (age10 OOS
   actually *gained* 3 trades). If 2h were merely a quieter view, the book
   would be smaller but comparably *good*. It isn't.
2. **Drawdown roughly doubles** (27.7→60.6, 21.2→46.1, 53.2→95.2, 29.4→80.5)
   while trade count holds. Same number of trades, twice the pain. The path got
   worse, not thinner.
3. **PF collapses toward 1.0**, and in OOS both live lanes go **negative**
   (0.74 and 0.71) — the 2h book loses money out of sample.

So 2h is not a lower-information filter; it selects a *different and worse*
set of trades. The parent plane is load-bearing, not a knob.

## Reading

The strategy's edge lives in the **1h** plane specifically. Halving the
resolution of the regime/chop/swing chain destroys it rather than degrading it
gracefully. Combined with the earlier work this says the 1h choice is
load-bearing and should be treated as a **fixed structural assumption**, not a
tunable.

There is a plausible mechanism worth recording (not a tested claim): at 2h a
"swing" spans twice the clock hours, so a 20-bar swing is 40h. The gate opens
on structure that is already 40h old, by which time the 15m entry is reacting to
news the parent never saw. The degradation pattern — not fewer trades, worse
ones — is consistent with acting on stale context.

## Scope and honesty notes

- **age10 reported separately** throughout, per house convention. It is default-off
  (structurally different single-book strategy) and is not evidence about the
  live lanes. Its IS-only survival here mirrors its behaviour elsewhere.
- Swings were computed on the **same `min_bars`** as 1h (20 and 10) over 2h bars.
  That is the honest plane test. Re-tuning `min_bars` to 10/5 to hold swing
  *duration* constant would be a second, different experiment — it was not run,
  and this result does not speak to it. Recorded as an open question, not a
  hidden caveat.
- OOS 1h was gap-free and resampled cleanly to 8,759 complete 2h buckets, so the
  OOS result is not a data-quality artifact.

## Verdict

**1h confirmed. 2h rejected, 0/6.** No production file was modified — runtime
patch only, `backend/` verified clean. No adoption, nothing to adopt.



---

# ADDENDUM — the confound is now resolved (2026-09-27)

The section above ended with an open question: *the 2h run held bar-counts in
bar units, so all six lookbacks doubled; did the 0/6 come from resolution or
from duration?* That is answered below, by experiment.

## Step 0 first — is our 2h real? (venue cross-check)

Rather than assert the 2h was fine, it was checked against Bybit's own
`interval=120` klines (`htf2h_fetch_verify.py`).

| Scope | common bars | open/high/low identical | OHLC mismatches |
|---|---|---|---|
| IS | 16,214 | 16,213 | 2 (1 bar) |
| OOS | 8,757 | **8,757 (100%)** | 59 (`close` only) |

**`open`, `high` and `low` are byte-identical on 24,970 of 24,971 common bars
(99.996%).** Bucket alignment is confirmed against the venue, not assumed. The
residue is data *vintage*, and the field breakdown proves it: misaligned
buckets would corrupt high/low too, but every OOS discrepancy is `close`-only
(median 3.0 points, all in 2021) — the venue revised historical closes after the
repo's 1h snapshot was taken.

**Substitution was declined, deliberately.** The fresh download extends 10 bars
past the repo's 1h snapshot and revises historical closes. Swapping it in would
have mixed a data-vintage change into a timeframe comparison and produced a
number that looked like a "2h effect". Both planes stay on the one snapshot.

## The 5 arms (pre-registered, 324s, both identity gates EXACT)

| Arm | Plane | sw20/sw10/chop/garch/ent/detect | HTF swing | HTF:LTF ratio |
|---|---|---|---|---|
| C0 | 1h | 20/10/14/96/96/48 | 20h | 1.6× |
| A1 | 1h | 10/5/7/48/48/24 | 10h | 0.8× |
| B0 | 2h | 20/10/14/96/96/48 | 40h | 3.2× |
| A2 | 2h | 10/5/7/48/48/24 | 20h | 1.6× |
| A3 | 2h | 10/5/**14/96/96/48** | 20h | 1.6× |

A2 restores C0's 1.6× ratio exactly, which is what isolates resolution.

| Arm | IS champ | IS utcsat | OOS champ | OOS utcsat |
|---|---|---|---|---|
| C0 1h full | **+325.8** | **+358.9** | **+70.2** | **+60.2** |
| A1 1h half | +328.2 | +346.9 | +71.1 | +62.3 |
| B0 2h full | +49.4 | +59.7 | −55.8 | −56.1 |
| A2 2h half | +53.9 | +51.6 | −46.4 | −50.3 |
| A3 2h sw-half, feat-full | +53.9 | +51.6 | −46.4 | −50.3 |

## What this actually shows

**1. Duration is inert. A1 ≈ C0 in both eras.** Halving all six lookbacks on
the 1h plane moved champion by +2.4R IS and +0.9R OOS — inside noise, and
slightly *positive* both times. A1 even inverts the ratio (0.8×: the parent
swing becomes shorter than the LTF swing) and nothing breaks. Whatever the
strategy is doing, it is not sensitive to how much history the parent looks
back over.

**2. Resolution is the whole story. A2 ≈ B0.** Restoring the duration *and* the
1.6× ratio on the 2h plane recovered essentially nothing: +49.4 → +53.9 IS,
−55.8 → −46.4 OOS. Both 2h arms still collapse. Since duration was varied and
shown inert, and 2h still fails at matched duration, the damage is the 2h bar
itself.

**3. The feature lookbacks do not touch the book at all.** A2 and A3 are
bit-identical in both eras. That could have been a plumbing bug, so it was
falsified directly (`_probe_inert.py`): driving chop/garch/ent/detect to absurd
values (`lb` 2 → 400) leaves the book at `n=490, net=+53.8630` **every time**,
while the patched engine's own `_chop_series_1h` at `lb=14` vs `lb=2` returns
**different series**. So the parameters genuinely reach the code and are
genuinely non-binding on trade selection. The book is decided by the swing
chain.

## The corrected conclusion

The first write-up said "the 1h plane is load-bearing" on 0/6 evidence alone.
That was directionally right but the *reason* was unproven. It is now pinned
down much more precisely:

> The strategy's edge depends on the parent plane being sampled at **1h**, and
> is **indifferent to lookback duration** and **indifferent to the chop/garch
> feature windows**. Per-bar structure in the parent — swing turns, chop
> transitions — is what carries the signal, and that structure is averaged away
> when the same window is sampled at 2h.

This also *closes* the open question flagged in the first write-up, which said
the 0/6 "does not speak to" a duration-matched 2h. It now speaks to it, and the
answer is that duration matching does not rescue 2h.

`age10` is reported separately throughout and shows the same pattern
(+435.7 / +431.7 / +184.4 / +185.6 IS). It remains default-off and is not
evidence about the live lanes.

## Still not claimed

- No adoption in any arm. The shipped engine stays **1h / min_bars 20**.
- Only 1h and 2h were tested. 30m/4h were not, and this result does not
  license proposing them (see Rule 2 in `AGENT_COORDINATION.md`).
- The mechanism in the box above is an *interpretation* consistent with the


---

# ADDENDUM 2 — the ladder, not the plane (2026-09-27)

Addendum 1 concluded "1h is load-bearing because the parent must be sampled at
1h". **That conclusion is wrong, and this addendum supersedes it.** It came from
a design flaw: every earlier run moved the HTF while **holding the LTF at 15m**,
so "2h is bad" and "an 8:1 ladder is bad" were never separated.

The user spotted the flaw directly: shipped is 15m × 4 = 1h, so 30m × 4 = 2h
should be an equally coherent family. That is the right question, and it turns
out the ladder is half the story.

## Also fixed here: a causality leak in every prior 2h run

v18:537-539, in the engine's own comment:

> *the window is knowable from the flip candle CLOSE (entry_ts + 3600); the LTF
> entry instant is bar_ts + 900. Gate in knowable-instant space.*
> `if not (s + 2700 < bar_ts <= e + 2700): continue`

`s` is an HTF `entry_ts` (v18:239), so the gate compares HTF space to LTF space,
and `2700 = 3600 − 900 = htf_bar_secs − ltf_bar_secs`. The earlier runs patched
the bisect close list to 7200 but **left this 2700 alone** — they gated on 1h
math while reading 2h bars, admitting entries up to an hour before the 2h flip
candle closed. Every prior 2h number is recomputed here. The leak *flattered*
2h, and 2h still lost, so the direction of those verdicts survives; the numbers
did not.

The gate is now derived (`_knowwin = htf_bar_secs - ltf_bar_secs`) at all **7**
sites. Two lessons from doing this safely, both worth keeping:

- **A grep of the raw v18 file is not enough.** `build_module()` layers extra
  patches, and two more gate sites exist *only* in the patched text. Sweep the
  literal and hard-assert none survive.
- **Check your patch variable name for collisions.** `_win` already exists in
  v18 as a local list slice (`_win=_vol15[_lo:_vi]`). Naming the gate `_win`
  reassigned it and produced `int + list` far from the cause.

## The grid (446s, both era identity gates EXACT)

min_bars 15m = 50 (shipped) — champion / utcsat:

| Cell | LTF/HTF | Ladder | Gate | IS champ | IS utcsat | OOS champ | OOS utcsat |
|---|---|---|---|---|---|---|---|
| F0 control | 15m/1h | 4:1 | 2700 | **+325.8** | **+358.9** | **+70.2** | **+60.2** |
| F1 LTF only | 30m/1h | 2:1 | 1800 | +241.6 | +200.1 | +15.5 | −9.9 |
| F2 HTF only | 15m/2h | 8:1 | 6300 | +40.2 | +59.7 | −47.3 | −50.0 |
| F3 family | 30m/2h | 4:1 | 5400 | +222.4 | +159.3 | −19.9 | −10.4 |

## The three paired contrasts — this is the actual result

Pairing cells that differ in exactly one factor separates the three effects that
earlier work had fused.

| Contrast | Held fixed | IS champ | OOS champ | Read |
|---|---|---|---|---|
| **A — ladder** | HTF = 2h | +222.4 vs +40.2 | −19.9 vs −47.3 | **matching the ladder recovers most of the 2h loss, both eras** |
| **B — LTF** | HTF = 1h | +241.6 vs +325.8 | +15.5 vs +70.2 | **30m LTF costs 84R IS and 55R OOS on its own** |
| **C — HTF** | LTF = 15m | +40.2 vs +325.8 | −47.3 vs +70.2 | 2h under a 15m LTF is very costly |

**Contrast A confirms the user's hypothesis.** Held at 2h, moving the LTF to 30m
so the ladder returns to 4:1 recovers +182R IS and +27R OOS, and PF goes
1.11 → 2.28. The 8:1 mismatch was a genuine, separable drag. This part of the
insight is right, and it invalidated my earlier conclusion.

**Contrast B is where the hypothesis stops.** Held at 1h, the 30m LTF *by itself*
costs 84R IS and 55R OOS. So 30m is not a free substitute for 15m. The ladder is
**necessary but not sufficient**: matching 4:1 does not rescue a coarser LTF,
because the LTF is what actually generates entries and 15m captures structure
that 30m averages away.

## Verdict

- **The shipped 15m/1h remains the best cell in all 12 measured cells.** Nothing
  beats it, in either era, on any lane.
- **15m LTF is load-bearing** (Contrast B, both eras) — it is the entry
  generator, and coarsening it is not compensated by anything upstream.
- **The 4:1 ladder is load-bearing** (Contrast A, both eras) — Addendum 1 was
  wrong to call this a "resolution" effect; a large part of it was ladder skew.
- **2h is no longer disqualified.** It was never fairly tested until this run,
  and at a matched 4:1 ladder it is roughly half as bad as it looked. It is
  still not *better* than 1h, and it is not adopted.
- Nothing adopted. Engine stays 15m / 1h / min_bars 20.

## One loose end worth naming, not acting on

`min_bars_15m=25` on the **shipped 15m/1h** control gave +272.8R IS but
**+128.6R OOS** — better out of sample than the shipped +70.2R, while being
worse in sample. That is a single un-pre-registered observation on a lever I had
not proposed, so it is a **lead, not a finding**, and it is not adopted. It is
recorded because it is the one place the LTF swing length (6.25h vs 12.5h)
moved OOS in the right direction, and because Contrast B just proved the LTF side
is where the binding sensitivity lives — the opposite of the HTF chop/garch
windows, which log 105 proved inert. Worth a properly pre-registered sweep; not
worth a decision now.

  evidence, not a separately tested claim.
