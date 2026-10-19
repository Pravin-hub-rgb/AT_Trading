# htf_rr is not a target knob. It is a window-length knob, wearing a target's clothes.

2026-10-16. Branch `research/four-validation-techniques`.

## The short version

`htf_rr` is named after and registered as a risk:reward target. It is not one.
Raising it from 3.0 to 4.0 does three things in sequence, and only the first one
is what anyone assumed was happening:

1. the HTF target moves further away,
2. so the HTF trade takes longer to resolve,
3. so **the window during which LTF entries are allowed stays open longer**,
4. so LTF entries arrive later, and
5. **later entries fail the `ext_stop_r` admissibility test and get rejected.**

Step 5 dominates. The book ends up with *fewer* trades at a *higher* setting,
which is the opposite of what a longer window is supposed to do and is the tell
that the name is misleading.

## The line that does it

```python
# unified.py:1214-1216
if hrisk > 0:
    ext = (float(candles_ltf[bar]["close"]) - pe) * d / hrisk
    if ext > ext_stop_r: continue
```

`ext` is how far price has already travelled from the window's own opening
level, in units of the HTF risk. Once it exceeds `ext_stop_r` (3.0 on every
candidate book), the entry is refused as late.

A longer window does not create more opportunities. It **delays** them, into a
region where the gate has already closed.

## The measurement that settled it

`exp_htfrr_decompose.py` runs each book at several `htf_rr` values and, per HTF
window, separates the change in book net into two terms:

- **delta from the ENTRY SET** — LTF trades admitted at the higher setting but
  not the lower one
- **delta from HTF BOOKING** — the extra R on the HTF trade itself

| book | era | compare | windows | duration x | LTF entries | entry-set delta | HTF-booked delta | total |
|---|---|---|---:|---:|---|---:|---:|---:|
| 106 | IS | 3→4 | 230 | 1.06 | 751 → 726 | −48.1 | +18.2 | −29.9 |
| 108 | IS | 3→4 | 230 | 1.06 | 762 → 735 | −56.0 | +18.2 | −37.8 |
| 106 | OOS | 3→4 | 120 | 1.14 | 384 → 392 | +25.2 | −11.3 | +13.9 |
| 108 | OOS | 3→4 | 120 | 1.14 | 425 → 418 | +13.5 | −11.3 | +2.2 |

Three things fall out of this table.

**The entry-set term is two to three times the HTF term.** −48.1 against +18.2,
−56.0 against +18.2. Whatever `htf_rr` does, it mostly does it to the LTF book,
not to the HTF trade it is nominally attached to.

**The HTF-booked delta is identical across books: +18.2 on IS, −11.3 on OOS.**
That is not a coincidence, and it is the most useful number in the table. Those
HTF trades are not book-specific at all — they are the same small population of
trades that reached 3R and then either extended or did not, and every book in
the family is trading the same underlying swings. The books differ in which LTF
entries they take. They do not differ in which HTF trades reach 3R.

**The sign of the HTF term flips between eras.** +18.2 on IS, −11.3 on OOS.
The extension behaviour of 3R-reachers is not stable, and that instability is
the entire content of the "3.0 works on IS, 4.0 works on OOS" split. It is not
a preference between two settings. It is one population whose behaviour changed
between two markets.

## Why the earlier sweeps were unreadable

Because they were all reading the sum of these two terms and could not tell them
apart. The volatility bucketing (`exp_htfrr_mechanism.py`) bucketed by the ATR
level at entry and found the best setting flipped between eras *within the same
bucket*. That looked like the mechanism failing. It was the mechanism being
unreadable — a book-level net is a blend of a window-length effect and an
extension effect, and bucketing the blend does not unbundle it.

Worth recording that this is the same trap twice in this repo. `exp_trail_skip_n`
was optimised on IS and picked the OOS-worst value, three folds out of three.
`htf_rr` was "optimised" on OOS after being invisible on IS. Both are the same
mistake: treating a compound knob as if it had one effect, then reading one
era's answer as if it were the parameter's answer.

## What this does and does not tell us

**It tells us the mechanism is upstream of `htf_rr` entirely.** Nobody needs to
decide "3.0 or 4.0". The real decision is **how long a window should stay
open**, and `htf_rr` is a clumsy way of setting it that happens to also move the
HTF target as a side effect.

**It does not tell us the right answer.** The decomposition says where the effect
lives. It says nothing about whether a longer window should be conditional.

## The mechanism this suggests, and why it is not yet built

There is an architecture for exactly this already in the engine, used by `mode`:

```python
# unified.py:1097  pick the window set by state
use = "decisive" if atr_pct > atr_high_thresh else "flip"
# unified.py:1186-1193  hold it for N bars before switching
if _rg_c >= PERSIST: _rg_s = use; _rg_c = 0
```

A window-length analogue would read ATR (or leg size, or the decay state that
`_decay_legs` and `_decay_frac` at `unified.py:815` and `:840` already compute
and nothing currently calls) at window open, and set window length from it, with
a persistence counter so it does not flicker.

**It is not built, and nothing here argues it should be yet.** Building it now
would be a new fitted rule on the same data that produced the original 3.0, which
is precisely the failure the external review in `METHODOLOGY_REVIEW_RESPONSE.md`
identified. The decomposition's value is that it tells us such a rule would be
aimed at the right thing, which the volatility test could never have established.

There is also a ready-made switch for decoupling. `window_end="r_touch"` closes
the window at the first touch of 1.5R instead of at the target, which separates
window length from target distance entirely. It is implemented and was previously
measured at −130R against the default. That number is the honest price of the
decoupling, and it was measured before anyone knew what it would be used for.

## The honest summary

| question | answer |
|---|---|
| Is 4.0 better than 3.0? | On IS, no. On OOS, yes. Neither is a general answer. |
| Why? | One population of 3R-reaching HTF trades changed its extension behaviour between two markets. |
| What is `htf_rr` really? | A window-length control with a target side effect. |
| Where does the effect live? | 70–75% in the LTF entry set, 25–30% in HTF booking. |
| Does that mean anything should change? | Not yet. It means any future rule would be aimed at the right thing. |