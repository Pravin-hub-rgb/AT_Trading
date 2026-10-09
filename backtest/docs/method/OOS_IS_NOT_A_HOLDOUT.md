# CORRECTION — I judged `sig_multi` on data that is not a holdout

Date: 2026-10-08. This file withdraws a claim I made earlier today.

## what I said

I wrote, in `SIG_MULTI_REGISTERED.md` and in the commit for that book:

> "the out-of-sample magnitude is not established (b +0.3303 against an MDE of
> 2.1999 — roughly a seventh of what the test can detect)"
>
> "the arm does not stop working out of sample, it works about 6× less per trade on
> 50 new trades"
>
> "in sample the magnitude is powered (b +2.1619 …)"

and framed the whole thing as though "OOS" were forward evidence about whether the
arm would work going forward.

## why that framing was wrong

`docs/method/FORWARD_TEST_PLAN.md` — written **2026-09-25**, thirteen days before
today — says this in its own second paragraph:

> "Every result so far comes from data that has already been inspected:
>
> - IS 2023-01-01 -> 2026-09-13
> - **"OOS" 2021-2022 (reused many times, not a holdout)**"

I read the plan's results log while checking this and had the chronology in front
of me without noticing what it meant. The dates confirm it:

| era | actual span | length |
|---|---|---|
| IS | 2023-01-01 → **2026-09-13** | 3.7 years |
| "OOS" | 2021-01-01 → 2022-12-31 | 2.0 years |

**"OOS" is two years OLDER than IS, not newer.** So `b = +0.33` on that window is
not evidence about the future. It is evidence about **2021–2022**, a period that
predates the in-sample data and has been re-scored many times.

**The owner's objection was exactly right:**

> "in which period you were testing? … at least we have to wait six months. How
> can we judge on the basis of this that this is wrong if you are doing it on this
> few days data. This is seriously wrong. We have to wait for at least four
> months"

## what actually exists for forward testing, and its state

The contract is **ACTIVE** and complete. It has:

- a hard data boundary at **2026-09-13 10:03 IST**
- five pre-registered gates: R1 execution parity, R2 edge survival, R3 no
  degradation vs anchor, R4 drawdown containment, R5 sample-size honesty
- an append-only results log
- a scoring harness: `backtest/tests/exp_forward_eval.py`, which concatenates
  `data/bybit/` with `data/forward/bybit/`, asserts pre-cutoff parity, and scores
  **only** trades entered after the cutoff

**And it has been scored once already, on 2026-09-25:**

| date | window | n | candidate | net R | verdict |
|---|---|---:|---|---:|---|
| 2026-09-25 | 2026-09-13 → | **5** | all four pre-registered candidates | **−3.83** | **NO VERDICT (n<50)** |

12.5 days produced **5 trades**, all shorts into a rising market. The contract's
own reading is that this establishes the *pipeline* is sound, not anything about
the edge. It estimates **~4 more months to n≥50** and **~12 more months to
n≥150**.

**`data/forward/bybit/` does not exist on this machine right now.** The 2026-09-25
window it was scored on is no longer present locally, and `scripts/download_bybit_forward.py`
is what fetched it. So there is nothing to re-score and no forward window I could
have used instead.

## the correction, stated properly

**Wrong:** "`sig_multi`'s out-of-sample magnitude is underpowered, therefore do not
adopt."

**Right:** `sig_multi` has **no forward evidence at all**, because no forward window
exists on this machine. The 2021–2022 window is not a holdout and never was. The
power-gate number is a real measurement of a real limitation *of that old window*,
and it should not be read as a forward verdict in either direction. It does not
say the arm is bad; it says we have no forward data on it.

## what this does to the adoption question

It removes the main stated reason for caution and replaces it with the correct one.

| my earlier reason | status |
|---|---|
| "OOS magnitude underpowered (b +0.33 vs MDE 2.20)" | **withdrawn as a forward argument.** It describes 2021–2022, not the future |
| "6× smaller out of sample" | **withdrawn as a forward argument.** Same reason. The 2.16 vs 0.33 gap is a 2023–26 vs 2021–22 difference and I should have said so when I reported it |
| "first out-of-sample half-year worth almost nothing (+39.6 vs +39.9)" | **stands**, but is likewise a 2021–22 observation, not a forward result |
| 99% of the raw gap survives period control, both eras | stands — it is a statement about regime-dependence, which is a different question from forward validity |
| 12 of 12 half-year cells | stands, same caveat |
| tail improves in every cell, both eras | stands, same caveat |

**The honest position now:** `sig_multi` is the best candidate this repo has and
its adoption decision is **blocked on forward data, not on the in-sample
statistics.** The contract already anticipated this — its pre-registered candidate
list is `CHAMPION_BASE`, `CHAMPION_N3`, `KING_BASE`, `KING_WN3`, and **`sig_multi`
is not on it.**

## the one piece of good news in this

**Because no forward window exists on disk, nothing is burned.**

The contract's own rule 3 says a window is burned if a change is proposed *because
of forward results*. No forward results have been produced on this machine, so
**`sig_multi` can be added to the pre-registered list now, at zero cost**, before
the window restarts. That is the cheapest high-value action available in this
whole research program and it closes today. Adding it after the next window is
scored would cost a fresh four months.

Two things are needed for it: the candidate added to the contract's table, and
`data/forward/bybit/` re-fetched via `scripts/download_bybit_forward.py` so a new
window can start.

## the HTF request

Separately, the owner asked for a full HTF×LTF sweep across every LTF-side
experiment. That is a large, mechanical piece of work and it is **not** something
to start inside a correction — it needs its own plan, because a full cross-product
over 152 books is a selection-risk problem before it is a research problem. The
contract's own reasoning applies: "the search space is already large. Adding
marginal candidates raises selection risk faster than it adds evidence."

My recommendation is that it be scoped to the fsent family only rather than all
152 books, and that whatever comes out of it lands on the pre-registered forward
list rather than being adopted on sweep results. I have not started it and nothing
in this file claims otherwise.