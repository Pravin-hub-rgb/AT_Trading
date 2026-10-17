# Forward Testing Contract — the finish line

**Written 2026-10-16. Replaces `FORWARD_TEST_PLAN.md` (2026-09-25), which is
kept for its history but whose candidate list is retired.**

Every number this repository has ever produced came from data that has already
been looked at:

| era | span | what it really is |
|---|---|---|
| IS | 2023-01-01 → 2026-09-13 | **where every book was found.** Its numbers are search results, not measurements. |
| "OOS" | 2021-01-01 → 2022-12-31 | a separate file, read many times. **Not a holdout.** One regime, and the crash-heavy one. |
| **forward** | **after 2026-09-13 10:02 IST** | **never searched. The only clean data in this repo.** |

## 1. The boundary is hard and it already exists on disk

`data/bybit/` ends at **2026-09-13 10:02 IST**. `data/forward/bybit/` holds what
came after, is never merged back, and was downloaded before any of it was read.
It currently runs to **2026-10-09 10:30** — 26 days, 3 to 15 trades per book.

Three rules, unchanged:

1. **Forward data is scored, never tuned on.**
2. **No parameter, threshold, filter, candidate or config may be chosen using it.**
3. If a change is proposed *because* of a forward result, the window is **burned**
   and a new one starts from scratch.

## 2. Candidates — fixed before any more forward data is scored

The 2026-09-25 list named `champion_multi_sw10` and `utcsat_multi_sw10`. Both
have been retired, so that list could not be scored at all. Replaced now.

All five are multi books (`max_positions=0`). Serial books were closed on
2026-10-16: not rejected, demoted — not held to a live standard.

| id | book | IS net | OOS net | both | max DD | R/trade | roll10% | ulcer |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **110** | `fsent_champ_long_htf15_tskip6` | +639.8 | +328.5 | **+968.4** | 22.81 | **1.5226** | **72.2%** | **2.194** |
| **107** | `fsent_champ_long_mcloff_htf15` | +539.8 | +270.2 | +809.9 | 28.38 | 0.9677 | 66.8% | 4.388 |
| 109 | `fsent_champ_long_htf15_htffs` | +765.9 | +346.1 | +1111.9 | 29.76 | 0.9652 | 62.0% | 4.770 |
| 108 | `fsent_champ_long_htfesmcl4` | +770.5 | +339.1 | +1109.6 | **20.02** | 0.9348 | 62.6% | **7.347** |
| 106 | `fsent_champ_long_htffs` | +758.0 | +313.4 | +1071.3 | 22.45 | 0.9381 | 63.0% | 4.790 |

**110 and 107 are the two carried forward.** They are not near-duplicates of
each other — 68% trade overlap, which is the most independent pair in the set.
The other three overlap each other by 85–93% and are one bet wearing three
names; they stay listed so the history is intact, not because they are being
considered separately.

Why these two, in the owner's terms — *smoothness, wins spread out and rolling*:

- **110** is the smoothest book on every measure that exists: ulcer 2.194 against
  4.39–7.35, 72.2% of rolling 10-trade windows positive against 62–67%, worst
  rolling 50-trade window −5.85R against −20R, and no negative half-year in
  either era.
- **107** is the only book whose out-of-sample result is statistically
  distinguishable from luck (p = 0.011), it has no negative half-year in either
  era, and its **worst** half-year is +7.4R.

They fail differently, which is why both are carried:

- **110 has a median trade of −1.05R.** More than half its trades lose, carried
  by a small number of large winners. Expect long dry spells.
- **107 draws down deeper** — 28.38R, and 140 days to recover, and it was still
  underwater when last measured. Its roll10 is 66.8% against 110's 72.2%.

## 3. Decision rules — fixed now, cannot be relaxed later

**R1 — execution parity, checked first.** Live marks must reproduce backtest
marks before any result is believed.

**R2 — edge survival.** Positive cumulative R over the window.

**R3 — no degradation.** The window must not do worse than the same book did on
IS.

**R4 — drawdown containment.** Drawdown must stay inside the pre-registered
kill-line.

**R5 — sample size honesty.** Below 50 trades the window is **provisional, not a
verdict**, whatever it shows. At roughly 0.37 trades per day, six months is about
67 trades per book — thin, but it is the only route to a number nobody searched.

## 4. The stop rule

The window closes when **either** book reaches 50 forward trades, or six months
pass, whichever comes first. Then one book is chosen on the record above plus
whatever the window added. **If both are positive, 110 is chosen for the live
experience it produces; if 107 is the only one significant, 107 is chosen even
though it feels worse.**

## 5. The one thing that has not been measured, and it is the one that matters

Backtest fills a stop at the stop price, or at the bar open if the bar gapped
through it. Live attaches a **Market** stop to Bybit. On a wick, those differ,
and the backtest does not know by how much.

**The measurement: how often does the 15m bar's low go past the stop price?** That
count is the live slippage exposure and it is currently unknown. It should be
measured before the window is closed, not after.

## 6. What is forbidden during the window

Tuning on it. Adding a candidate because it looked good forward. Reading the
window and then changing the book's knobs. Quoting a forward number without
saying the window length behind it.

## 7. Results log

### 2026-09-13 → 2026-10-09, first scoring (26 days)

| book | trades | net R | win rate | PF | DD | months + |
|---|---:|---:|---:|---:|---:|---|
| 110 | 3 | **−3.61** | 0.0% | 0.00 | 3.6R | 0/1 |
| 107 | 8 | +1.72 | 37.5% | 1.78 | 3.8R | 1/1 |
| 109 | 13 | +2.04 | 38.5% | 2.19 | 3.0R | 2/2 |
| 108 | 15 | +3.27 | 33.3% | 2.12 | 4.1R | 2/2 |
| 106 | 13 | +2.04 | 38.5% | 2.19 | 3.0R | 2/2 |

**Reading it honestly: nothing.** Three to fifteen trades cannot separate an edge
from a lucky month. It is recorded because it is the only data nobody has
searched, and because **110 has already lost three straight at exactly −1R**,
which is worth watching and proves nothing.

**It does contradict the factor ranking** — 110 ranked first of 26 and has the
worst forward number; 108 ranked fourth and has the best. Where they disagree,
the forward window is the better evidence, because the ranking was built on
searched data. One window of 26 days is not enough to settle it, but it is not
nothing either.

## One thing that is already settled

exp_no_opposite, the opposite-direction lock, is **ON by default for every
book** as of 2026-10-16, and both candidates' pins were re-derived under it.
It refuses a new trade when a trade in the opposite direction is already open.

It is worth stating what this means for the forward test: it applies to **both
arms equally**, so it does not favour either candidate and it is not a variable
here. It is simply the engine's behaviour from this point forward. The forward
numbers for 107 and 110 below are already post-lock.
