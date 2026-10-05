# P10 — a runner is half-identifiable live, and not enough to act on

`exp_runner_live.py`. Pins reproduced first (IS 500t/+325.8R, OOS
279t/+70.1R).

## First: the user is right, and the repo already proved it

`_trail3.out.txt` (STUDY 3) is a perfect monotonic separator, and the
separating variable is exactly what the user named — the ratchet:

| IS champion, n=500 | n | R | avgR | **ratchets** | bars |
|---|---|---|---|---|---|
| never ratcheted | 187 (37.4%) | −187.0 | −1.00 | **0.0** | 193 |
| trail exit <1R | 212 (42.4%) | −111.3 | −0.52 | **1.8** | 1691 |
| 1–3R | 38 (7.6%) | +69.1 | +1.82 | **3.4** | 3001 |
| 3–10R | 46 (9.2%) | +253.2 | +5.51 | **4.8** | 5140 |
| 10R+ | 17 (3.4%) | +421.1 | +24.77 | **6.6** | 7519 |

**6.8% of trades carry +151% of gross P&L. 37.4% carry −42%.** The user's
read — "the ratchet was never crossed, so it kept riding, that's what
caught it" — is exactly right and is not a new observation.

**The problem is that `ratchets` is measured at exit.** It is hindsight.
The repo's whole trail family (half / delay1 / tighten) is saturated and
REJECTED precisely because exit modulation cannot fix an entry problem.

## The live test: what the state at +1R buys you

+1R is the only moment you could actually act. 243 of 500 IS trades and
142 of 279 OOS trades ever get there — **roughly half die before +1R at
all.**

**By time to +1R (15m bars):**

| bucket | IS n | IS P(3R+) | IS P(10R+) | OOS n | OOS P(3R+) | OOS P(10R+) |
|---|---|---|---|---|---|---|
| ≤8 | 95 | 28.4% | **10.5%** | 46 | 15.2% | **2.2%** |
| 8–24 | 69 | 30.4% | 5.8% | 34 | 29.4% | 5.9% |
| 24–72 | 60 | 21.7% | 3.3% | 44 | 22.7% | 4.5% |
| 72–200 | 14 | 7.1% | 0.0% | 17 | 17.6% | 5.9% |
| >200 | 5 | 0.0% | 0.0% | 1 | 0.0% | 0.0% |

**IS is cleanly monotone — the faster a trade reaches +1R, the higher
P(10R+), 10.5% down to 0.0%. OOS is not monotone at all** — the fastest
bucket is the *worst* at 2.2%. **Falsifier (b) fires: the ordering exists
in IS and inverts in OOS. That is the signature of hindsight.**

**By MAE before +1R (how deep the drawdown went on the way):**

| bucket | IS n | IS P(10R+) | OOS n | OOS P(10R+) |
|---|---|---|---|---|
| ≤−0.9R | **9** | 22.2% | **4** | 25.0% |
| −0.9..−0.6 | 46 | 6.5% | 34 | 8.8% |
| −0.6..−0.3 | 108 | 4.6% | 55 | 1.8% |
| −0.3..−0.1 | 57 | 7.0% | 34 | 2.9% |
| >−0.1 | 23 | 8.7% | 15 | 0.0% |

**This one is directionally consistent in both eras and it is the
interesting result: the deeper the drawdown on the way to +1R, the higher
the chance of a 10R+ runner.** OOS goes 8.8% → 1.8% → 2.9% → 0.0% as the
drawdown shallows. **A trade that gets shaken out hard and comes back is
more likely to be a runner than one that walked straight to +1R.**

But the top bucket is **n=9 in IS and n=4 in OOS.** That is four trades.
The 22.2%/25.0% figures are one trade each.

## The verdict, and it is the pre-registered negative

**No reliable bucket reaches a P(10R+) worth acting on.** Excluding the
n≤9 buckets, the best IS bucket is 10.5% and the best OOS bucket is 8.8% —
and they are not the same bucket. **Falsifier (c) fires: nothing here is
actionable.** Act on "10% chance of 10R" and you are trading a coin flip
on four observed trades.

**So the answer to "how does the market tell us" is: mostly it does not,
and the part where it seems to is the part where it lies to you in OOS.**

## A bug, reported because it would have been a fake finding

**The ratchet-at-+1R column is degenerate.** All 243 IS and 142 OOS
trades land in a single `>0.5` bucket, zero variance. The reason is
tautological: the engine applies the ratchet *before* the SL check on the
same bar (D3 ordering, `method/TRAIL_MECHANICS.md:6`), so at the instant price
first touches +1R the ratchet is *always* at +1R. **The feature is
guaranteed to carry no information, and I should have known that before
spending a table on it.** It is reported here rather than deleted because
it is a useful negative: the thing that separates the book at exit is
provably unavailable at the moment you would need it.

## What this closes, and what it opens

**Closed:** any proposal to detect runners at +1R and act on it. The
state is measured, the probabilities are known, and the best reliable
bucket is 10.5% IS / 8.8% OOS on different buckets. This is why the exit
family is dead and should stay dead.

**Open, and genuinely novel:** the user's second idea — **"busy rakhe but
trade nahi"**. Grep for `busy_but_no_trade`, `hypothesis suppression`,
`block_next`, `mark_busy`, `signal_block` returns **zero hits repo-wide**.

That is hypothesis suppression: when a signal fires and the rules say do
not take it, the engine is currently left *free* and will take the next
signal instead. If the next signal is worse — which the P1-P nesting probe
found for late-in-leg entries, and which the `1_sl_never_ratcheted` class
at −1.00R flat suggests — then occupying the slot without trading is
strictly better than doing nothing. It needs no size channel, no equity,
and no concurrency state, all of which the other ideas are blocked on.
**This is the best remaining idea and it has never been run.**
