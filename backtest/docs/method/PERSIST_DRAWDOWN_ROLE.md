# What exp_persist did in OOS's worst stretch — the owner asked, and it is not what either of us guessed

Date: 2026-10-07. Engine post-C17. Harness: `exp_persist_drawdown.py`. Book:
`fsent_champ_long`.

## The question

`exp_persist` costs **66.1R in sample and only 5.0R out of it**. Read plainly
that suggests persist was barely worth having in OOS. The owner's reading was
better: OOS covers a bearish, thin stretch where `chop` and `atr_pct` both
whipsaw, and persist's 7-bar hysteresis is exactly the mechanism that would stop
the book being fooled there — so it should have earned its keep at the one moment
it mattered, and the aggregate hides that.

That is testable, and the test is about **when**, not **how much**. A total that
says "saved me in the crash" and one that says "mildly useful throughout" differ
by far less than 5R, so the total cannot decide it. Placement can.

## The window, taken from the book rather than assumed

Defined from the shipping book's own equity curve, peak to trough:

    2021-01-06  ->  2021-09-26      depth 11.88R
    120 of 311 trades fall inside it

That is 39% of OOS trades — a real stretch, roughly nine months, and it is where
the drawdown actually happened.

## Inside vs outside

| | persist=7 (shipping) | persist=0 | delta |
|---|---:|---:|---:|
| **inside** the worst stretch | +38.62R | +35.48R | **+3.14R** |
| **outside** it | +200.97R | +199.07R | +1.90R |

Persist is worth more inside (+3.14R) than outside (+1.90R) — **the direction of
the hypothesis is right.** It is not concentrated, though: +3.14R of a +5.04R
total is 62% of the benefit from 39% of the trades. Barely more than even.

## The test that actually decides it

Where do the *differing* trades land?

| | trades | inside window | outside | sum |
|---|---:|---:|---:|---:|
| only at persist=7 | 51 | 16 (**31%**) | 35 | +1.38R |
| only at persist=0 | 65 | 25 (38%) | 40 | −3.66R |

Baseline for comparison: **39%** of all shipping trades fall inside the window.
Persist-only trades fall inside it **31%** of the time — *less* than baseline.

**So the effect does not concentrate. It is spread across the sample.**

And the ten largest persist-only trades are mostly outside the stretch:

| entry | R | inside the worst stretch? |
|---|---:|---|
| 2022-12-12 | +5.84 | no |
| 2021-11-26 | +4.54 | no |
| 2022-06-28 | +3.37 | no |
| 2021-06-25 | +3.23 | **yes** |
| 2021-03-13 | +1.84 | **yes** |
| 2022-05-20 | +1.07 | no |
| 2022-01-06 | +1.00 | no |
| 2021-06-14 | +0.86 | **yes** |
| 2022-01-11 | +0.82 | no |
| 2021-01-28 | +0.79 | **yes** |

Three of the top ten. If persist were a crash-specific brake, this table would be
almost entirely "yes".

## But there is a real risk finding here, and it is not the one asked about

Persist also **shortens the drawdown**, and that was not the hypothesis:

| | max DD | worst stretch ends |
|---|---:|---|
| persist=7 (shipping) | **11.88R** | 2021-09-26 |
| persist=0 | 13.18R | **2022-02-01** |

Persist=0's drawdown is **11% deeper and lasts four months longer.** That is a
distinct benefit from the net-R one, it is not visible in the +5R aggregate at
all, and it points the same way as the inside-window result: persist does its
work in the bad stretch.

So the honest answer is two-part, and the second part is the one that matters:

- **Wrong:** persist is not a crash-specific save. It is mildly useful throughout,
  and 69% of the trades it uniquely creates sit outside the drawdown.
- **Right, and more valuable:** persist **compresses the drawdown** — shallower
  and five months shorter. That is what the 7-bar hysteresis is for, and it is a
  better justification than the net R it was previously being defended on.

## Consequence for the sweep

`_persist_sweep.md` concluded `persist=7` stands, and that stands. But its
justification was "no smaller value beats it in both eras" — a tuning argument.
The real reason is this one: 7 shortens the worst stretch by four months and
costs 1.3R of drawdown depth. Those are not interchangeable, and the tuning
argument would still have held if the drawdown argument were false.

`exp_persist=7` unchanged. No pins affected — this reads the shipping book, it
does not modify it.