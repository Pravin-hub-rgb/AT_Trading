# PORTFOLIO PART 2 — 5/6 assets are kills-clean, and the "best" weighting is
# a degenerate collapse, not a result.

Date: 2026-09-28. `exp_portfolio_kill_weight.py` → `_portfolio_kill_weight.json`
276.9s. K1-K7 definitions verbatim from `exp_stat_arb.py:75-83`.

## 1. Kill table — this is the real result

| asset | IS | kills | OOS | kills |
|---|---|---|---|---|
| AVAX | 145t +173.9R | **NONE** | 82t +189.8R | **NONE** |
| BNB | 126t +200.9R | **NONE** | 92t +95.9R | **NONE** |
| LTC | 138t +147.9R | **NONE** | 95t +89.0R | **NONE** |
| LINK | 133t +122.5R | **NONE** | 87t +116.5R | **NONE** |
| DOT | 115t +84.8R | **NONE** | 88t +32.3R | **NONE** |
| NEAR | 98t +108.7R | K5 (98 < 100) | 85t +50.9R | NONE |

**5/6 pass the counted bars in BOTH eras** — AVAX, BNB, LTC, LINK, DOT.
NEAR fails only on trade count in IS (98 vs 100); it is the one that was
marginal.

This is materially better than 24.95's 2/8 kills-clean, and it is a
different population: 24.95 tested four lanes on two assets, this tests
one frozen lane on six. **The lane, not the asset, was the variable that
mattered** — 24.95 already showed that.

**Caveat on K6:** three assets have WR below 40% (LTC 36.2/38.9, DOT
39.1/38.6). They pass here because 24.95 granted a differential exemption —
v18 books are low-WR by construction, so K6 would fire on every book
including the champion. Raw WR is printed above so the exemption is
visible rather than buried.

## 2. Weighting — the winner is NOT a result

| scheme | IS | OOS (weights fit on IS) | vs equal |
|---|---|---|---|
| equal | +139.8R (+38.1/yr) | +95.7R (**+47.9/yr**) | — |
| inv_vol | +133.4R (+36.3/yr) | +77.6R (+38.8/yr) | **−9.1R/yr** |
| inv_corr | +146.7R (+40.0/yr) | +116.5R (+58.3/yr) | +10.4R/yr |

**`inv_corr` "wins" by +10.4R/yr, and that number must not be used.** Its
OOS weights are:

    AVAX 0.00   BNB 0.00   LTC 0.00   LINK 1.00   NEAR 0.00   DOT 0.00

**It collapsed to 100% LINK.** The inverse-variance formula divides by a
portfolio variance that went near-zero on this correlation matrix, so the
"weighting scheme" degenerated into a single-asset book and is being
compared against a six-asset portfolio. The +10.4R/yr is LINK's OOS return
minus an equal-weight blend — an artefact of the collapse, not evidence
that correlation weighting works.

Had that been reported as "correlation-aware weighting beats equal weight
out of sample," it would have been a false headline of exactly the kind
this repo has retracted before.

**`inv_vol` is a genuine negative**: it loses 9.1R/yr to equal weight out
of sample, on weights fit on IS only.

## Verdict

1. **Five kills-clean assets exist** (AVAX, BNB, LTC, LINK, DOT) on a
   frozen lane, both eras. That is the finding.
2. **Equal weight is not obviously wrong.** The one honest weighting test
   lost to it out of sample. There is no evidence here that any weighting
   scheme beats equal, and the scheme that appeared to win is degenerate.
3. **A proper correlation weighting needs a different estimator** — an
   inverse of a regularised covariance (e.g. Ledoit-Wolf), or a simple
   pairwise cap, not naive inverse-variance on six near-uncorrelated
   series. That is a new experiment, not a retune.

## Still true from part 1

Mean pairwise correlation +0.072 IS / −0.053 OOS, and the equal-weight
portfolio draws down 1.25–1.79× a single book rather than 6×. The
diversification finding is unaffected by the weighting result.

**The Binance-fapi caveat is unchanged** — none of this answers a Bybit
question.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
