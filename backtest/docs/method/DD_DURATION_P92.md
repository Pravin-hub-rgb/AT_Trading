# P92 — THE DRAWDOWN IS SHORT AND SHARP, NOT LONG. And the bootstrap
# disagrees with the path, which is the finding.

> Run 2026-09-29. Harness `exp_dd_duration.py`.
> **From `method/NEXT_ROUND_BRIEF.md`, Space Bunny's P91.** Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## What P83 promised and did not deliver

`method/CHAMP_ROBUST_P83.md` reported depth — 37.3R over 278 days — and its own
limitations section said: *"Recovery time after the max drawdown is not
reported… and that number matters more than the depth to anyone holding
the bot."* It was left out because the harness computed peak and trough
but never ran the recovery loop. This is that loop.

**Nothing is selected here.** No trade added, removed or re-scored. It
produces no dNet and changes no production code.

## The realised path — the book recovers fast

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| underwater episodes | 33 | 14 | 36 | 15 |
| still open at sample end | 1 | 1 | 1 | 1 |
| episode **depth** median | 265.2R | 15.9R | 282.1R | 11.2R |
| episode **days** median | **23** | **9** | **21** | **9** |
| episode **days** p90 | 89 | 119 | 118 | 119 |
| episode **trades** median | 7 | 5 | 6 | 5 |
| **worst episode** | 445.2R / **21 days** / 6 trades | 105.3R / 53 days / 13 trades | 466.5R / 21 days / 6 trades | 92.6R / 53 days / 10 trades |

**The champion goes underwater 33 times in 3.7 years and the median episode
lasts 23 calendar days and 7 trades.**

**That is a very different picture from the 278-day headline P83 printed.**
A book that drops 37R and is back above its prior high in a median of 23
days is a book whose drawdowns are *sharp*, not slow.

## Two harness bugs on the way, both caught by a number that could not be true

**Bug 1: "33 episodes (33 still open)."** The recovery index was never
written back into the open-episode record, so every episode closed as
never-recovered. It produced a table reading *"worst episode 445.2R deep
over 165 calendar days / 62 trades"* with a median episode of 422 days on a
book whose worst drawdown is 37.3R — **a 422-day median episode is not
possible on a path that recovers, and the depth and duration were
contradicting each other.** That contradiction is what exposed it.

**Bug 2: bootstrap index overrun.** The block bootstrap appended block
*endpoints* rather than per-trade timestamps, so the time series and the
time axis had different lengths.

## The finding, and it is not the one the bootstrap reports

**The block bootstrap says the worst-episode duration has a median of 875
days in IS and 398 in OOS. The realised paths say 21 days and 53.**

**These cannot both be describing the same strategy**, and the discrepancy
is the substantive result:

> **Reshuffling the champion's trades in blocks produces paths that are
> underwater for YEARS. The realised path is underwater for WEEKS.**

**Why that matters for shipping:** a drawdown measured on a resampled path
is a drawdown you would experience **if the trades arrived in a different
order**. The realised order — the one the market actually produced — has a
median underwater spell of 23 days and a worst observed of 53. **The
bootstrap's 875-day figure is a statement about ordering risk, not about the
strategy's history**, and quoting it as "the drawdown could last three
years" would badly misdescribe what the owner would have lived through.

**And the tail sensitivity confirms why.** Remove the top 5% of trades and
the book loses money overall (−138.6R IS, −85.4R OOS) and the worst episode
collapses to 4.9R over 13 days. **The drawdown structure is almost entirely a
property of the top-5% of winners.** Without them there is no book; with
them the drawdowns are short and sharp.

## What this does not say

**It does not say 37.3R is safe.** It says the *shape* is better than the
headline suggested — sharp recoveries, frequent re-entries to new highs —
and that the long-duration figure a naive bootstrap produces is an
ordering artefact rather than a forecast.

**The one episode still open at each sample's end is reported as open**
rather than dropped, which is the honest treatment: a path that ends
underwater is a different fact from one that recovered, and four books
ending underwater out of four is itself worth noting.

## Stated limitations

- **Both lanes are the same data.**
- **The bootstrap's duration distribution should not be read as a forecast**
  — that is the finding, not a caveat on it. It would need an
  order-preserving or regime-blocked resample to say anything about
  duration, and that is untested.
- **Depth is in R-multiples**, and P91 showed the R denominator moves with
  stop distance, so episode depths here inherit the same caveat.
- **Episodes are counted on closed trades only**; a still-open trade at the
  sample end is excluded from the sequence, which understates the final
  episode by one trade.

## Status

**Nothing adopted. Production unchanged.**

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.

**The shippable summary: the champion's drawdowns are short and sharp —
median 23 days underwater, worst observed 53 — and the long-duration
figure comes from reshuffling, not from history.**
