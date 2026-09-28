# PORTFOLIO LAYER — a genuinely new bucket. The six alt books are
# near-uncorrelated, and that is a real finding.

Date: 2026-09-28. `exp_portfolio_layer.py` → `_portfolio_layer.json`
136.6s. All 12 per-asset controls exact against the transfer sweep.

## Why this bucket is new

Every transfer result in the repo is a **per-instrument** yes/no: "does this
lane work on asset X?" Six positive answers do **not** imply a good
portfolio — six books can all lose in the same month. Nobody has ever
measured what happens when they run together, and that is precisely the
question a live multi-asset book has to answer.

The obvious next move for someone holding a 7/13 transfer rate is "run them
all." If that is wrong, the discovery arrives after capital is at risk.

## The books (all controls exact)

| asset | IS | DD | OOS | DD |
|---|---|---|---|---|
| AVAX | 145t +173.9R | 11.0 | 82t +189.8R | 5.4 |
| BNB | 126t +200.9R | 6.0 | 92t +95.9R | 11.6 |
| LTC | 138t +147.9R | 10.9 | 95t +89.0R | 6.9 |
| LINK | 133t +122.5R | 7.9 | 87t +116.5R | 5.3 |
| NEAR | 98t +108.7R | 13.2 | 85t +50.9R | 6.9 |
| DOT | 115t +84.8R | 10.9 | 88t +32.3R | 11.1 |

## Result: they genuinely diversify

**Mean pairwise monthly-R correlation: IS +0.072, OOS −0.053.** Near zero
in both eras, and **stable across them** (drift −0.125, below the 0.15
threshold for calling it era-dependent). Range IS −0.26..+0.56, OOS
−0.32..+0.61.

**The equal-weight portfolio is the point:**

| | portfolio net | per year | portfolio DD | single-book DD (avg) | ratio |
|---|---|---|---|---|---|
| IS | +139.8R | +38.1R | **17.9R** | 10.0R | **1.79×** |
| OOS | +95.7R | +47.9R | **9.9R** | 7.9R | **1.25×** |

**Holding six books costs 1.25–1.79× the drawdown, not 6×.** That is the
arithmetic signature of real diversification rather than six copies of one
bet. If these were one position wearing six hats, the ratio would be
near 6.

## What this does and does not say

**Does say:** a six-asset equal-weight sleeve is a materially different risk
object from any single book, and its drawdown is small in absolute terms
(9.9–17.9R) while running ~750 trades per era across both eras.

**Does NOT say:**
- **No subset is selected.** The per-asset nets are printed so the user can
  choose; picking the best subset on the same data that scored it is the
  multiplicity this repo forbids. Any subset built later must be
  re-validated on data that did not choose it.
- **The data is Binance fapi, not Bybit perp.** This inherits the same
  caveat as the transfer census — it does not answer a Bybit question.
- **The exit basis is 15m**, not the 1m fine fills that 24.95 used.
- **No kill table was run.** The transfer rule is weaker than kills-clean.
- **Equal weight is a choice, not an optimum.** Nothing here optimises
  weights; a correlation matrix near zero would *justify* something other
  than equal, but that is a separate experiment and it is the one worth
  doing next.

## The interesting loose end

The correlation is near zero, but **not uniformly**. Three pairs are
consistently the exceptions in both eras: AVAX-BNB (+0.05 / +0.60),
NEAR-DOT (+0.56 / +0.24), and LINK is the most consistently diversifying
name (−0.32 with AVAX, −0.32 with LTC, −0.30 with DOT in OOS).

That is a hypothesis, not a finding: **the six are not six independent
assets, and a portfolio built without looking at the matrix could quietly
concentrate.** AVAX and BNB are the two largest books AND each other's
nearest neighbour in OOS — which is exactly the pair a naive equal-weight
sleeve would double up on.

## Next experiment, if this direction is taken

1. Kill table (K1-K7) on the six — required before any candidate claim.
2. Correlation-aware weighting vs equal weight, on the same pre-registered
   rule, validated on the era that did not choose the weights.
3. Confirm on **Bybit** data before any of it informs a Bybit book.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
