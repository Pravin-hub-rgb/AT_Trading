# Equity-curve quality: champion vs trail_half

Date: 2026-10-07. Engine post-C17. Harness: `exp_curve_quality.py`.
Framework: `docs/learn/finding optimal book.md` — this follows its sections 3A,
3B, 4, 5 and 6 rather than inventing a score.

## Why this measurement was needed

`fsent_champ_trailhalf` pins **+42.5R more out of sample** than the book being
traded, and was not adopted because it multiplies in-sample drawdown by 2.37.
Net R and max DD cannot settle that on their own — both move easily when you take
fewer, larger trades, which is precisely what `exp_trail_half` does. So the
question is whether the extra R buys a **more robust curve** or just a steeper
one.

## Section 3A — winner spacing (OOS)

| | champion | trail_half |
|---|---:|---:|
| +3R winners | 33 | 36 |
| max gap between +3R | 39 | 38 |
| +10R winners | 6 | **11** |
| max gap between +10R | 80 | 74 |
| +20R winners | **2** | **6** |
| max gap between +20R | 85 | 75 |
| mean gap between +20R | 85 | **30** |

trail_half produces **three times as many +20R trades** and waits half as long
for them. That is the strongest thing in its favour anywhere in this comparison,
and it is real.

## Section 3B — profit through time (OOS)

Both books earn in every year, both eras. Champion 2021 +78.33R, 2022 +161.26R.
trail_half 2021 **+130.90R**, 2022 +151.19R. **trail_half's advantage is
concentrated in the bad year** — 2021 is where the champion does its weakest
work (+78R of its +240R), and trail_half more than closes that.

In sample: champion +172 / +114 / +138 / +109 across 2023-2026, trail_half +171 /
+89 / +142 / +134. trail_half's one weak year is 2024.

## Section 4 — tail dependence, and this is the finding

Removing the biggest trades, OOS:

| | champion | trail_half | **delta** |
|---|---:|---:|---:|
| full net | +239.59 | +282.08 | **+42.49** |
| minus top 1 | +213.46 | +236.74 | +23.28 |
| minus top 3 | +172.72 | +181.64 | **+8.92** |
| **minus top 5** | **+135.67** | **+136.44** | **+0.77** |
| minus top 10 | +82.85 | +59.04 | **−23.81** |
| minus top 5% | +45.27 | +22.77 | **−22.50** |
| top 5 share of net | 43.4% | **51.6%** | |

**Strip five trades off both books and they are the same book.** +0.77R apart on
135R. Strip six and trail_half is *behind*. Its entire out-of-sample advantage
lives in six trades, and it is more tail-dependent than the champion at every
level past the top five.

The owner put the right question when asking whether removing the top trades is
diagnostic. It is, and here it is decisive: **+42R is six trades deep.**

## Section 5 — gap survivability

Per the framework, a book that still earns *during* the waits between big winners
is healthy; one that bleeds through them is one bad stretch from ending.

| | gaps between +20R | mean gap net | positive gaps | worst intra-gap DD |
|---|---:|---:|---:|---:|
| champion (OOS) | 1 | +80.48R | 100% | 10.12R |
| trail_half (OOS) | 3 | +21.24R | 100% | **12.60R** |
| champion (IS) | 4 | +65.78R | 100% | 13.42R |
| trail_half (IS) | 7 | +34.84R | 100% | **15.69R** |

Both survive their gaps — neither bleeds, which is the section's main question and
both pass it. But trail_half's waits are deeper (12.60R vs 10.12R OOS, 15.69R vs
13.42R IS), and that is the 16.45R drawdown arriving in the same trades where its
+20R winners also arrive. **Its wins and its worst losses are in the same
stretches.**

## Section 6 — the healthy shape

The framework's target is right-skewed without being *dependent* on the tail.

- **champion**: top 5 = 43.4% of net, survives removing the top 10% with +82.85R
- **trail_half**: top 5 = 51.6%, and removing the top 10% leaves **+59.04R**

Both are right-skewed, as a trend-follower should be. trail_half is meaningfully
closer to dependence, and in sample it is worse still: removing the top 5% leaves
champion +105.64R against trail_half **+72.54R**.

## Verdict

**Champion stays. trail_half is not adopted, and now there is a reason that is
not just drawdown.**

The drawdown argument was honest but incomplete: +4.6R of extra drawdown for +42R
looked like a budget question, and budget questions can go either way. The
framework answers it more sharply:

1. **Strip five trades and the advantage is gone** (+0.77R on 135R). The gain is
   six trades deep, not distributed.
2. **It is more tail-dependent at every level** past the top five, and in sample
   it is the weaker book once the tail is removed.
3. **Its drawdown sits in the same stretches as its +20R winners** — deeper gaps
   (12.60R vs 10.12R) and the worst intra-gap DD.

Points 1 and 3 say the +42R is not free R, it is borrowed against a larger drawdown
in the same trades. The right-skew is genuine and the extra +20R frequency is a
real improvement — **but it is bought with concentration, not earned with
robustness.**

If the budget rule in `EQUITY_LENS_EXT_AND_NOHALT.md` is what decides this, trail_half
loses at every budget below 31.68R on the in-sample number and needs 16.45R on the
out-of-sample one. The framework gives the second reason: even at an unlimited
budget it is the more fragile book.

**Nothing changed. No book promoted, no pins touched.**

## Note on the framework's own example

`finding optimal book.md` Sec 5 praises a strategy for earning +29.3R with a 8.1R
drawdown through a 44-trade gap between +20R winners. Measured against that
standard, the champion's OOS gap behaviour (worst intra-gap DD 10.12R, all gaps
positive) is close, and trail_half's (12.60R) is not. The framework's own worked
example is a useful yardstick here and it was not used as one.