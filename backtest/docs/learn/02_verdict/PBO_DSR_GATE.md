# PBO and DSR — the multiple-testing gate

2026-10-19. Branch `research/htfrr-structural`. Commit alongside `SELECTION_RULES.md`.

**This is the step that was missing.** Thirteen books were explored, the
best-looking one was carried forward, and nothing ever asked what that
selection costs in statistical terms. PBO and DSR are the standard prices for
that question, from the same literature that produced the walk-forward and
Monte Carlo work already in this repo.

Both fail. Not marginally.

---

## PBO — Probability of Backtest Overfitting

CSCV: 13 books, S even blocks of equal trade-count, every way of choosing S/2 as
in-sample, complement as out-of-sample. For each split, rank all 13 on IS, then
see where the IS-winner lands in the OOS ranking. PBO is the fraction of splits
where it lands in the bottom half.

| era | S=8 (70 splits) | S=10 (252) | S=12 (924) |
|---|---|---|---|
| OOS 2021-22 | **0.571** | 0.627 | 0.607 |
| IS 2023-26 | **1.000** | 0.798 | 0.891 |

**Bar is 0.15.** Every value is 4x to 7x over it, and stable across block
counts — so it is not an artifact of the partition.

Interpretation: on the IS era the in-sample winner landed in the bottom half of
the out-of-sample ranking in **100% of splits**. Not "sometimes". Every time.
Whatever produced the historical ranking does not survive being re-partitioned
in time.

This is a statement about the **selection procedure**, not about any individual
book. It says the exercise of "test 13, keep the best" was mostly noise.

---

## DSR — Deflated Sharpe Ratio

Sharpe per trade, then deflated against what the best of N=13 lucky strategies
would produce under the null of no skill.

| era | best SR | best DSR | books with p < 0.05 |
|---|---|---|---|
| OOS | 0.2851 (107) | **−38.3** | **0 of 13** |
| IS | 0.2890 (110) | **−46.8** | **0 of 13** |

`SR* = 1.7033` for N=13. Every book's Sharpe is a fraction of that. DSR is
negative for all 26 book-era cells, p = 1.0000 for every one.

**Not one book clears the multiple-testing bar.**

---

## Why these numbers are an optimistic floor, not a ceiling

Two reasons, both inflating the true problem:

1. **N = 13 undercounts the trials.** Each book also had its parameters swept
   inside it — `exp_trail_skip_n`, `exp_persist`, `cooldown_bars` and others
   across dozens of cells. The real trial count is far higher, and `SR*` rises
   with N. A larger honest N makes every DSR worse, not better.

2. **The OOS era is contaminated.** 2021-22 was used for filtering throughout
   this work, repeatedly. Books that survived using it have been selected on it.
   The 0.571 there is measured on data that already knows about the winner.

So the honest reading is not "PBO is 0.57". It is **"PBO is at least 0.57, and
probably materially higher."**

---

## What this does NOT say

It does not say the strategies have no edge. A genuinely positive expectancy
strategy can still fail DSR when it is one of many and the sample is short.

It does not say the work was wasted. The engine, the cost model, the verified
slippage, the deterministic pipeline — all of that stands.

It says **the historical evidence does not identify which book to deploy.** That
was already the honest position from the gate sequence, which produced no
survivor. PBO and DSR confirm it statistically rather than leaving it as a
judgement call.

---

## The one correction this makes to earlier work

`SELECTION_RULES.md` Gate 5 ranked survivors by patience, then R per trade, then
net, and noted that net was the last tie-break. Consulting the standard practice
on this, **net profit is the single metric most correlated with overfitting**,
because it rewards whatever fit the sample hardest. It should not appear as a
selection input at all, even last.

That does not change today's outcome — no book reached Gate 5 — but the rule
file carries the error and the rule file is what a future reader will follow.

---

## What is left

Everything that remains is forward work:

- collect live/paper fills on a frozen candidate
- score it once at the end of a defined window
- do not look at the window to choose

The expert's operational gate was 20-50 round trips or one quarter, whichever
comes first, with a slippage audit against actual fills. The forward window here
holds roughly one month and a handful of trades. That is short of the bar, and
the bar exists precisely because short of it means the backtest is the only
evidence, and the backtest has now been shown not to separate these books.