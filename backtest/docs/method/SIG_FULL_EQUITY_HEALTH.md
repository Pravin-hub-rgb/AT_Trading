# Is fsent_sig_full's equity curve actually healthy? Yes, with one known soft spot

Date: 2026-10-07. Engine post-C17. Harness: `exp_sig_full_quality.py`.
Framework: `docs/learn/finding optimal book.md`, sections 3A, 3B, 4, 5, 6.

## The question

`fsent_sig_full` tops the single-position sig ladder at **+194.4R OOS on 6.96R
drawdown**, and it is the only book in that ladder still positive after its top
10% of trades is removed. That last property is what makes it interesting, because
that test is the one that closed `trail_half` on the multi book, ch=50, ch=55 and
`persist=5` in this repo.

But surviving top-10% removal is one test, not a judgement about a curve. It says
nothing about whether the book earns *during* the waits between big winners, which
is the framework's Section 5 and the section that most often gets skipped. Pins
verified first: `exp_fastcheck.py` reproduces 234 / +295.83 / 10.78 IS and 152 /
+194.44 / 6.96 OOS.

## Section 3A — winner spacing (OOS)

| | count | mean gap | median gap | max gap |
|---|---:|---:|---:|---:|
| +3R | 26 | 4.9 | 4.0 | 23 |
| +5R | 18 | 7.2 | 4.0 | 23 |
| +10R | 5 | 34.0 | 28.5 | 75 |
| +20R | **3** | 28.5 | 28.5 | **37** |

Short waits for ordinary winners, and the +20R wait maxes at 37 trades.

## Section 3B — profit is earned throughout

| | 2021 | 2022 |
|---|---:|---:|
| OOS | +75.35 | +119.09 |

| | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|
| IS | +91.58 | +114.29 | +55.40 | +34.56 |

Every year positive in both eras. No single stretch carries it.

## Section 4 — tail dependence (OOS)

| removed | net left |
|---|---:|
| top 1 | +162.21R |
| top 3 | +113.03R |
| top 5 | +87.41R |
| top 10 | +43.50R |
| **top 10%** | **+10.61R** |
| top 5 share of net | 55.0% |

Still positive at the tenth percentile. Compare the sig ladder's other books:
`fsent_both_trail_half` goes to **−5.5R** at top 5 and its top five are 105.7% of
its net. This book is not that.

## Section 5 — the deciding section: does it earn during the waits?

The framework's own worked example praises a strategy that made **+29.3R through a
44-trade gap at 8.1R drawdown**, and calls that much healthier than 44 trades of
−30R rescued by one +40R. That is the standard to hold this book against, and no
book in the repo had been measured against it.

| | gaps between +20R | positive | worst intra-gap drawdown |
|---|---:|---:|---:|
| **IS** | 3 | **2 of 3 (67%)** | 10.78R |
| **OOS** | 2 | **2 of 2 (100%)** | 5.77R |

OOS: a 37-trade gap returned **+11.38R** at **5.77R** drawdown. That is the
framework's healthy shape — it keeps earning while it waits, and the wait is
shallower than the example's 8.1R.

## The soft spot, stated plainly

One in-sample gap is **negative**: 14 trades, **−4.04R**, 4W/10L, drawdown 5.69R.
So in sample the book does not *always* earn during the wait — two of three gaps
do, one does not.

It is a short gap and the loss is small relative to the +38.70R and +19.29R the
other two returned, which is why the year table still shows every year positive.
But it is the honest answer to "is the curve clean": **it is not perfectly clean,
it is robust.** A book that never bleeds through a gap would be suspicious rather
than healthy — some negative gaps are what a real curve looks like.

## Verdict

**Yes — `fsent_sig_full` is the healthiest book on the sig ladder, on the
framework's own terms.**

1. It passes the outlier bar that closed every other candidate in this repo.
2. It earns in every year, both eras — not one stretch.
3. It earns *during* the waits between its big winners, 2 of 2 gaps out of sample
   and 2 of 3 in sample, at a drawdown shallower than the framework's example.
4. Its drawdown is the ladder's lowest, 6.96R OOS, on 152 trades.

The one soft spot — a −4.04R gap in sample — is small, short, and offset. Worth
knowing rather than pretending it is not there.

**Not promoted.** It is already registered and pinned; this harness changes no
config. And note it is **not** the book being traded — `fsent_champ_long` is,
which is multi and holds 11 simultaneous positions at peak. `fsent_sig_full` is
the single-position option, and on this evidence it is the better-shaped one of
the two.