# C15 start-side fix — a real 900-second lookahead in the shipping book, found and fixed

Date: 2026-10-10. Harnesses: `exp_leak_proof.py`, `exp_window_floor_causality.py`,
`exp_repin_after_fix.py`, `exp_apply_repin.py`.

**The owner was right to demand proof before believing it. This is the proof, and
it holds up.** Every pin in the fsent family has been re-derived because the fix
moved them.

---

# 1. What the engine's own documentation already said

`C17_WINDOW_END_CAUSALITY.md` lines 17–21, written before this cycle:

> `s` is the **open** of the 1h candle that opened the HTF trade. The window's
> existence is not knowable until that candle **closes**, at `s + 3600`. So the
> start needs the shift: in knowable-instant space, `s + 2700 < bar_ts` is exactly
> `s + 3600 < bar_ts + 900` (2700 = 3600 - 900). **That half is correct and is the
> C15 fix** recorded in `HTF_GATE_AUDIT_P101.md`.

So C15 audited this, derived the correct form, and **the implementation never
matched it**.

| | form | means |
|---|---|---|
| **C15 says is correct** | `s + 2700 < bar_ts` | 2700 absorbs the 900 → HTF closes before LTF bar closes |
| **the code had** | `s + 2700 < bar_ts + 900` | 2700 applied, **and then another 900 added** |

`entry_ts` is `candles_ltf[i]["ts"]` — the 15m bar's **open**, the same value as
`bar_ts`. So the code compared `s + 2700` against the LTF bar's **close** when it
should have compared against its **open**. **The 900 was counted twice**, and the
gate was loose by exactly one 15m bar.

The gate permitted entries up to `s + 1800`; the window is knowable at `s + 3600`.
**A 30-minute band in which the window does not yet exist.**

The engine's own trade-record comment says it outright:

> *"window_start + 3600 is when the governing 1h bias candle closed, i.e. **the
> earliest instant the trade could have been known**."*

That sentence was in the code the whole time. The gate just never enforced it.

---

# 2. The actual trades

`exp_leak_proof.py` prints the whole chain. The worst case:

### 2025-03-10, trade #316, SHORT, −1.06R

| | |
|---|---|
| 1h window candle | opens **13:00**, closes **14:00** · O=83212 H=83280 **L=81366** C=81488 |
| 15m entry candle | opens **13:45**, closes 14:00 · O=**82639** H=82774 **L=81366** C=81484 |
| gate required | entry after **14:00:00** |
| actual entry | **13:45:00** |

**The entry bar is the final quarter of the 1h candle that has not closed.** The
trade is taken at 82639, and that same hour then travels to 81366 — **1273 points,
1.5%** — which a live trader standing on the 13:45 bar has no way of knowing.

The 15m low and the 1h low are the same number, 81366. The 15m bar's close and the
1h candle's close are the same number, 81484. **It is the same moment, and the
gate let it in.**

All six are exactly **900 seconds early** — one 15m bar, cleanly. That precision
is what confirms arithmetic rather than something pathological.

| trade | date | side | R |
|---|---|---|---:|
| #46 | 2023-05-13 | short | −1.22 |
| #316 | 2025-03-10 | short | −1.06 |
| #522 | 2026-08-28 | short | +1.00 |
| — | 2022-03-19 | short | −1.27 |
| — | 2022-08-24 | short | −1.13 |
| — | 2022-09-10 | short | −1.06 |

**Total −4.73R.** On the champion the bug **cost** money — five of six were
losers — so fixing it makes the book better, not worse.

---

# 3. It was in every fsent book

| book | leaked | worth |
|---|---:|---:|
| `champ_long` | 6 | −4.73R |
| `mcloff` | 7 | −5.29R |
| `mcloff_htf15` | 7 | −4.45R |
| `htf15` | 6 | −4.38R |
| `htfesmcl4` | 4 | **+8.80R** |
| `champ_short` | 6 | **+3.87R** |
| `sig_multi` | 2 | −0.20R |
| `sig_full` | 2 | −0.20R |

**On `htfesmcl4` and `champ_short` the bug flattered them.** They were being
compared against a book that was quietly trading 15 minutes early.

---

# 4. The fix

```python
# was:  if not (_floor < bar_ts + 900 < e): continue
if not (_floor < bar_ts < e): continue
```

One token. Two harness anchors moved with it (`test_experiments_craze.py`,
`exp_tf_family.py`) — both are recorded where they live.

**After the fix, the shipped floor is causal:**

| arm | trades | net | lookahead | neg cells |
|---|---:|---:|---:|---:|
| **floor 2700 (shipped default)** | 837 | +777.7 | **0** ✅ | 1 |
| floor 3600 | 834 | +777.8 | **0** ✅ | 1 |
| floor 7200 | 821 | +766.3 | **0** ✅ | **0** |
| floor 0 | 859 | +800.1 | 24 ❌ | 0 |
| mode `fs` | 863 | +792.2 | 28 ❌ | 0 |

**`floor 0` and `mode fs` still leak, and still must not be used.** That is the
correct outcome — they were never real gains.

---

# 5. Every pin moved, so every pin was re-derived

**28 of 28 fsent books changed.** A pin is a claim about a measurement; a stale
one is worse than a missing one because `exp_fastcheck`, `exp_resultsdb` and every
document compare against it and would all agree with each other while all being
wrong.

### the shipping book

| | before | after |
|---|---|---|
| IS | 528 / **+533.37** / 13.42 | **526 / +533.87 / 13.42** |
| OOS | 311 / **+239.59** / 11.88 | 311 / **+243.80** / 11.88 |

Two trades removed, net up 0.50R in sample and 4.21R out of sample. **Small — and
that is the point: a lookahead this quiet would never have been found by looking
at returns.**

---

# 6. A mistake I made while fixing it

The first re-pin script merged `fsent_champ_long`'s params under every book
instead of merging `BP`. That carried `exp_mltf=True` into the serial sig books,
silently switching them to unlimited positions: `sig_full` appeared to gain 93
trades and came out with pins **identical to `sig_multi`**.

Tightening a gate cannot add trades, so a rising count is proof of a harness bug
rather than a measurement. `exp_fastcheck.py` merges `dict(BP)` and that is what
the re-pin had to match. **After the correction every book lost 0–5 trades, which
is the only shape a tightening can produce.**

That is worth stating plainly because it is the second time this cycle a
harness produced a plausible-looking wrong answer and only a structural argument
— ties should not be equal, gains cannot happen from a tightening — caught it.

---

# 7. What this changes about the cycle's conclusions

**None of the rankings move.** `exp_scorecard_report.py` re-run after the fix:

| # | book | score | net | neg |
|---|---|---:|---:|---:|
| 1 | `mcloff_htf15` | 23.0 | +896 | 0 |
| 2 | `htf15` | 32.7 | +830 | 0 |
| 3 | **`sig_multi`** | 37.8 | +698 | 0 |
| 4 | **`sig_full`** | 38.6 | +482 | 0 |
| 5 | `mcloff` | 41.4 | +841 | 0 |
| 6 | `champ_long` (shipping) | 44.9 | +778 | **1** |
| 7 | `htfesmcl4` | 45.4 | +1234 | 0 |
| — | `champ_short` | 66.9 | +813 | 0 |

`mcloff_htf15` first, `sig_multi` third, the shipping book sixth, and
`htfesmcl4` — still the biggest number in the room — seventh.

**And `fsent_champ_long_causalfloor` has been renamed in spirit.** Its
description now says plainly that the name is misleading: with the bug fixed in
the engine, it is no longer the causal book, only a longer wait than causality
requires, carrying the selection pressure of having been chosen from a sweep.

---

# verification

| check | result |
|---|---|
| `exp_leak_proof.py` | 6 trades printed with candles; worst 900s early |
| `exp_window_floor_causality.py` | shipped floor **0 lookaheads** after the fix |
| `exp_repin_after_fix.py` | 28/28 books re-derived; first version had a `BP` merge bug |
| `exp_apply_repin.py` | 29 pin blocks rewritten, every field diff printed |
| `exp_fastcheck.py` | **PASS** — 7 books, every pinned field, both eras |
| `exp_dropdown_parity.py` | **PASS** — dropdown still matches the registry |
| `exp_scorecard_report.py` | re-run; no ranking changes |
| `/results` artifact | regenerated, 25 books, 0.40 MB |

*Shipping book unchanged in configuration: 526 / +533.87 / 13.42 IS, 311 / +243.80
/ 11.88 OOS after the fix, one negative half-year, window floor 2700 untouched.*