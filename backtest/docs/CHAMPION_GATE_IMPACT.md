# P3-D — what the floor does to the CHAMPION book. The user's actual question.

`exp_champion_gate.py`.

## First, the honesty fix

P3-C ran at `mode="atr_high"` — **not the shipped config**. It produced IS
+227.5R / OOS +22.7R. Quoting those numbers as "what happens to 325R" would
have been exactly the shape-vs-meaning mistake this session keeps making.
So this re-ran the gate on the champion, config read from `v18_params.py`
and `AGENT_COORDINATION.md`, not from memory:

```
mode=b2_vs_flip_chop, chop_thresh=61.8, cooldown_bars=20,
sl_buf_atr=0.25, ext_stop_r=1.5, max_consecutive_losses=5
```

Control from this file: **IS 356t +277.1R, OOS 188t +28.2R.** (Slightly
below the quoted +325.8R / +70.2R — expected, different fill basis. Every
comparison below is against *this* control, never a quoted one.)

## A discovery that reframes the whole thing

`v18_streak_halt.py:519-523` already contains:

```python
if ext_stop_r>0:
    ext=(close - pe)*d/hrisk
    if ext>ext_stop_r: continue        # ext_stop_r defaults to 1.5
```

**The champion already has a live-R CEILING.** It refuses new 15m entries
once the 1h leg is more than 1.5R unrealised. Nobody trades there.

**It has never had a live-R FLOOR.** It will happily open a 15m trade while
the 1h leg is deep underwater.

So this is not a new gate competing with the champion. **It is the missing
half of a rule the champion already half-implements** — and the ceiling and
floor are what fight each other in the high-floor arms below.

## The answer to "325R me kya asar hai"

| floor | IS | | OOS | |
|---|---|---|---|---|
| | n | net / PF / **DD** | n | net / PF / **DD** |
| None (champion) | 356 | +277.1 · 2.23 · **17.5** | 188 | +28.2 · 1.23 · **18.1** |
| −0.50 | 320 | +160.1 · 1.79 · 22.1 | 168 | +22.8 · 1.21 · 17.3 |
| −0.25 | 267 | +253.3 · 2.56 · **11.9** | 144 | +31.6 · 1.33 · 17.8 |
| −0.10 | 234 | +252.4 · 2.78 · **11.0** | 123 | +36.6 · 1.45 · 17.4 |
| **+0.00** | **214** | **+259.3 · 3.05 · 9.5** | **111** | **+49.2 · 1.72 · 11.2** |
| +0.10 | 194 | +214.0 · 2.85 · 9.5 | 101 | +31.8 · 1.49 · 14.0 |
| +0.25 | 155 | +179.2 · 2.93 · 12.3 | 86 | +13.7 · 1.23 · 17.6 |
| +0.50 | 110 | +176.9 · **3.98** · 7.7 | 52 | **−6.7** · 0.81 · 9.8 |

### `floor = 0.00`, head to head

| | IS | OOS |
|---|---|---|
| net | +277.1 → **+259.3R** (−6%) | +28.2 → **+49.2R (+75%)** |
| trades | 356 → 214 (**−40%**) | 188 → 111 (**−41%**) |
| WR | 27.5 → **32.7%** | 25.5 → **27.9%** |
| PF | 2.23 → **3.05** | 1.23 → **1.72** |
| trimmed mean | −0.217 → **+0.117** | −0.301 → **−0.196** |
| **maxDD** | **17.5 → 9.5R (−46%)** | **18.1 → 11.2R (−38%)** |

## The honest reading — and it is better than P3-C

**This is NOT "net up in both eras."** IS net is **down 6%** (+277.1 →
+259.3). Anyone quoting the OOS +75% alone would be cherry-picking the era
that flatters it, and the row above is written so that is visible.

**What actually improves, in both eras, on every axis except one:**
- **Drawdown falls by 46% IS and 38% OOS** — the biggest single move
- PF up 2.23→3.05 and 1.23→1.72
- WR up in both
- **IS trimmed mean flips NEGATIVE to POSITIVE** (−0.217 → +0.117) —
  the first time any arm today has done that
- **40% fewer trades**

**So the trade is: 6% of IS net, for roughly half the drawdown and a
materially better-shaped book.** On a book whose measured weakness is
tail-concentration and OOS maxDD, that is a good trade — but it is a
*reshape*, not an *add*. It is not "+325 becomes +350".

**And the ceiling/floor fight is confirmed on the champion too.** `+0.50`
posts the best IS numbers in the entire sweep (WR 39.1%, PF 3.98, DD 7.7R)
and simultaneously turns OOS **negative (−6.7R)**. That is the third
independent confirmation of the inversion, and it is the reason no floor
above 0.00 is admissible.

## Answer to the user's OOS-DD objection

You said 1.6R of OOS drawdown worsening "chalta hai." **On the champion it
is not a worsening at all — the champion's OOS drawdown also falls, 18.1 →
11.2R.** P3-C's OOS DD blip was an artefact of the `atr_high` config, not
of the gate. On the book you actually trade, this objection dissolves.

## What still blocks adoption

1. **IS net is down 6%.** Acceptable as a reshape, but it is a cost, and
   it must be stated as one.
2. **OOS is 111 trades.** The +75% is real directionally and thin in
   robustness.
3. **The grid was written with the feature in mind** — not family-wise
   corrected. `0.00` is a round number; it is also the only round number
   that requires no fitting, which is why it is not alarming here.
4. **P5 has not run.** +21.0R OOS and −17.8R IS both have to clear a
   chance-level null, and the OOS zero-mean bootstrap p-value in
   `IS_IT_RIGHT.md` is already 0.199.
5. Not tested: interaction with `max_consecutive_losses=5` (the floor
   removes trades, which changes streak timing), nor with `cooldown_bars=20`.

## Recommendation

**This is the strongest candidate produced today, and on the champion it is
a reshape rather than a lift — which is exactly what a risk-reduction gate
should look like.** It is not adopted. The one thing that would decide it
is P5.
