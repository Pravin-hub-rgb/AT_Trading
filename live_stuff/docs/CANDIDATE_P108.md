# P108 - CHAMPION AS A FINAL CANDIDATE. Backtesting only.

Branch: agents/champion-reality-audit
Date: 2026-09-30. Net accounting, IS, v19 champion.

Scope note: this note is backtesting only. No live-bot work, no porting,
no capital model, no parameter merge. Those are deferred until a final
candidate is chosen.

## SUBPERIOD ROBUSTNESS

    year     n       net      PF
    2023   107    +86.9R    2.71
    2024   161    +88.8R    2.07
    2025   130    +68.8R    2.26
    2026   102    +81.3R    2.79
    ALL    500   +325.8R

Four consecutive calendar years, all positive, none carrying the result.
The worst year is +68.8R across 130 trades, so no single period is doing
the work.

    H1 (first 250 trades)   +146.0R
    H2 (last 250 trades)    +179.8R

Both halves positive, and the second half is the stronger one. This is the
check that matters for a strategy found late in a research programme: the
book is not front-loaded.

## MULTIPLE-COMPARISON THRESHOLD

    M = 193.4R   (from the number of experiments run)
    champion IS net = +325.8R
    1.68x M - EXCEEDS

## VERIFIED ELSEWHERE

- Pin reproduced from a real import of the committed v19_champion.py:
  IS 500t/+325.78R, OOS 279t/+70.15R.
- HTF gate lookahead clean: C12, C14, C15 fixed in source. C14-narrow
  residual measured at +1.4R.
- Fillability: all 500 entries have close[i] == open[i+1], 0R of edge in
  the close-fill assumption.
- Correlated-cluster risk measured: worst single overlap cluster -0.97R,
  losing clusters total -10.4R.
- bars_to_window_end rejected as arithmetic, not signal. The causal
  substitute scores AUC 0.472.

## WHAT THIS DOES NOT SETTLE

Forward data holds 2 champion trades over 12.5 days. A live ruling needs
40-70 trades, roughly March 2027. Nothing here is a statement about live
merit.

The champion is a legitimate final candidate on backtest evidence. It has
not been selected by the user and no live work has been done.