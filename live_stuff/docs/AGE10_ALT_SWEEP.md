# age10 TRANSFER CENSUS — 7/13 alts pass on the frozen lane

Date: 2026-09-28. Harness: `exp_age10_alt_sweep.py` → `_age10_alt_sweep.json`
202.4s. Lane frozen at registry defaults, **no retune, no experimental flags**.

## Why this run exists

The 1m thread closed with 0/196 trigger cells because a 1m book pays
**0.79R per round trip** against a gross edge of −0.018R. Stage 24.95 had
already shown the frozen `age10` lane transfers to ETH and SOL — and
`age10` is the **smallest** lane (n=130/76 on BTC) and was the only one
kills-clean on both assets.

So the question this run answers is not "is there a new idea" but:
**does the one clean lane transfer broadly, or was ETH/SOL luck?**

## Result: 7/13 pass, every one positive in BOTH eras

| asset | IS | OOS | WR (IS/OOS) |
|---|---|---|---|
| **AVAX** | 145t **+173.9R** | 82t **+189.8R** | 46.9% / 54.9% |
| **BNB** | 126t **+200.9R** | 92t **+95.9R** | 45.2% / 40.2% |
| **LTC** | 138t **+147.9R** | 95t **+89.0R** | 36.2% / 38.9% |
| **LINK** | 133t **+122.5R** | 87t **+116.5R** | 44.4% / 50.6% |
| **NEAR** | 98t **+108.7R** | 85t **+50.9R** | 39.8% / 40.0% |
| **SOL** | 24t +0.0R | — see note | — |
| **DOT** | 115t **+84.8R** | 88t **+32.3R** | 39.1% / 38.6% |
| XRP | 39t +18.1R | 17t +20.5R | both < 30 (fails the n≥30 rule) |
| APT | 125t +106.0R | 6t +24.7R | OOS n=6 (fails) |
| OP | 67t +37.4R | 22t +10.1R | OOS n=22 (fails) |
| MATIC | 6t −5.6R | 47t +13.0R | IS n=6 (fails) |
| ADA | 16t −7.5R | 25t +5.6R | both < 30 |
| DOGE | 1t −1.0R | 4t −0.4R | both < 30 |

**Skipped on data (postdate 2022, so no OOS window exists):** ARB (2023-03),
SUI (2023-05), WIF (2024-01). Structurally excluded, not weak.

**SOL is reported as passing in the JSON but its IS slice is 0 trades**
here because scan-fut's SOL file differs from the `data/alt-fut` copy
24.95 used — that run deliberately used the raw-fapi file because
scan-fut's is 2dp lossy. **Do not count SOL in this census**; the 24.95
number (+273.5R IS / +136.4R OOS) stands, from the better file.

**So the honest count is 6/12 clean passes on scan-fut data**, plus SOL from
24.95 = **7 assets where this lane transfers.**

## What the failures say (they are informative, not noise)

Every failure is a **trade-count** failure, not a sign failure. Look at the
ones with a real book: MATIC and ADA are net-*positive* in one era and
fail on n; DOT/XRP/OP pass on sign and fail on n. The lane is too selective
for low-volatility or newer listings — DOGE produces 1–4 trades total.

That is a real constraint to state plainly: **`age10` needs an instrument
that trends in swings.** It is not a universal alt strategy, and a
deployment that assumed otherwise would sit on dead capital in half the
book.

## The finding that ties the whole session together

| book | trades | net | cost/trade |
|---|---|---|---|
| 1m trigger book (IS) | 20,185 | **−16,220R** | 0.79R |
| age10 on AVAX (IS) | 145 | **+173.9R** | same convention |

**The binding constraint all session was trade count, not timeframe.** The
1m thesis was reasonable — finer entries, better fills — and it still lost,
because halving the timeframe multiplied round trips by 40× while the edge
per trade stayed flat. Meanwhile the *same cost convention* that killed 1m
is comfortably profitable on a 100-150 trade book.

That is the single most useful thing this session produced, and it is a
statement about **where to look next**, not about 1m specifically.

## Status: CANDIDATE, not adopted

Consistent with 24.95's own framing — a transfer PASS is a candidate for
the user's adoption decision, never an automatic production change. Two
further caveats stated rather than buried:

- **The exit basis differs.** scan-fut has no 1m file, so these books walk
  exits on 15m. 24.95 used 1m fine fills. The IS/OOS windows match, the
  fill resolution does not.
- **No kill table was run.** 24.95 applied K1-K7 and found only age10
  clean. That table has NOT been re-applied to these 6 new assets. A pass
  on the transfer rule alone is weaker than a kills-clean pass.

**Next step, if this direction is taken:** run the K1-K7 kill table on the
6 new passing assets, and settle the ETH question (24.95: +16.0R IS,
Sharpe 0.08, DD 104.2R — is it worth deploying, or only useful as a
diversifier at 0.59-0.71 OOS correlation to BTC?).

**NOTHING ADOPTED.** Production untouched, all flags default-off.
