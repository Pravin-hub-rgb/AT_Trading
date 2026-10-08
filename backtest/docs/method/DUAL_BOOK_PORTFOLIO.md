# The two books are genuinely different — and that makes the blend a sizing trade, not a free one

Date: 2026-10-08. Engine post-C17. Harness: `exp_dual_book.py`.
Books: `fsent_champ_long` (A) and `fsent_sig_full` (B). Nothing adopted.

## The observation

The permutation test in `SHIPPING_BOOK_NULL.md` found the two books share **zero
trades** — 100% disjoint in both eras. They are also mirror images of each other:

| | A `fsent_champ_long` | B `fsent_sig_full` |
|---|---|---|
| FS entry side | **long** | **short** |
| positions | **multi** | **max_positions=1** |
| IS | 528t / +533.4R / DD 13.40 | 234t / +295.8R / DD 10.80 |
| OOS | 311t / +239.6R / DD 11.90 | 152t / +194.4R / **DD 7.00** |

Two different strategies, both profitable in both eras, and B has **less than
two-thirds of A's out-of-sample drawdown**. That combination has never been tested
as a portfolio.

## The correlation — the number that decides whether this is worth anything

| era | monthly return correlation | months |
|---|---:|---:|
| IS | **0.153** | 45 |
| OOS | **0.423** | 24 |

**Low in both eras.** In sample the two books barely move together — 0.153 is
close to independent. Out of sample it is 0.423, meaningfully positive but still
far from "one strategy twice".

So B is a **real diversifier**, not a copy. That is the good news and it is not
in doubt.

## And yet no blend weight wins, and that is the finding

| era | w on B | net | max DD | DD duration | ulcer |
|---|---:|---:|---:|---:|---:|
| **IS** | 0.00 (A alone) | **533.4** | 8.0 | 5 | 2.77 |
| | 0.25 | 474.0 | 6.6 | 4 | 2.04 |
| | 0.50 | 414.6 | **6.4** | **2** | **1.73** |
| | 0.75 | 355.2 | 7.5 | 2 | 1.79 |
| | 1.00 (B alone) | 295.8 | 8.6 | 3 | 2.18 |
| **OOS** | 0.00 (A alone) | **239.6** | 8.1 | 1 | 2.58 |
| | 0.25 | 228.3 | 5.2 | 1 | 1.34 |
| | 0.50 | 217.0 | **2.3** | 1 | **0.70** |
| | 0.75 | 205.7 | 2.6 | 2 | 0.87 |
| | 1.00 (B alone) | 194.4 | 3.6 | 2 | 1.51 |

**The blend at w=0.50 cuts out-of-sample max drawdown from 8.1R to 2.3R — a 71%
reduction — while giving up only 22.6R of net.** Out of sample, that is an
extraordinary trade by any normal standard.

And yet the harness says **no blend weight beats champion on both net and
drawdown**, and it is right, because **the net always falls**. There is no weight
at which the drawdown improves while the return is kept. Every point on both
curves is a straight trade between the two.

## Why the naive reading of this table is a trap

It is very easy to read "OOS drawdown 8.1R → 2.3R, that's a 71% cut for 9% of
the return, ship it" and that reading is **arithmetically true and completely
misleading**.

The blend at w=0.5 is A at **half size** plus B at **half size**. Halving A's size
alone would cut A's drawdown to roughly 4R while giving up half its net. B
contributes some diversification on top, which is why 2.3R beats that. **Most of
the drawdown reduction is position sizing, not diversification.**

This is the same trap as `CELL_THREE_WAYS.md`, where a cell correlated at +0.65
with its parent book bought no diversification. Here the correlation is much
better — 0.153 in sample — and it still does not show up as free money, because
the correlation is being applied to a book that was never counted twice in the
first place.

## What this actually tells us

1. **The two books are genuinely different strategies.** Zero shared trades,
   opposite FS sides, and a monthly correlation of 0.153 in sample. Whatever else
   is unresolved about either book, this is not the same book measured twice.
2. **The diversification is real but small, and it is already inside A's drawdown
   number.** A is multi-position with a peak of 11 concurrent trades; overlapping
   its own trades already diversifies it internally. Adding a second uncorrelated
   book cannot diversify a book that is already diversified against itself by
   holding eleven positions at once.
3. **There is a real trade available to an owner who wants less drawdown.** w=0.50
   costs 22.6R out of sample and buys a 5.8R reduction in max drawdown and a
   4x reduction in ulcer. Whether that is worth it is a risk-budget decision, and
   the rule for those already exists in `EQUITY_LENS_EXT_AND_NOHALT.md`.

## Stated limitations

- **The blend is a weighted sum of two equity curves, not a re-simulated book.**
  Running both for real would contend for capital and for the position slots, and
  neither book has a size channel, so the interaction cannot be modelled here.
  This is arithmetic on measured curves, and it says so.
- The monthly correlation is estimated on 45 and 24 months. The in-sample figure
  of 0.153 has a wide confidence interval and should not be read to three digits.
- The DD figures in the blend table are computed on the monthly aggregate, which
  is coarser than the trade-level max DD the books report (A's trade-level OOS
  max DD is 11.88R; its monthly-curve figure here is 8.1R). The two are different
  measures and are not interchangeable.
- Both books are pre-C17-pin-era registries whose pins reproduce, but the blend
  has never been a registered book, so it has no pin and no identity gate.

**Nothing adopted. No book added, re-weighted or re-pinned.**