<!-- prov: engine=2c463e9 measured=2026-10-07 harness=exp_cell_tables.py -->
# The experiments - three new books, all FAILED

Your original book is the "before" row. Everything else was built today and none
of it was adopted.

**IN SAMPLE**

| | trades | win % | net R | mean R | PF | max DD | longest loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| **before** - your book | 528 | 40.0 | +533.4 | +1.01 | 3.09 | 13.4 | 11 |
| cell (subset, not a book) | 75 | 45.3 | +132.0 | +1.76 | 4.59 | 7.6 | 6 |
| **exp 1** - GATE (only cell) | 144 | 27.8 | +116.0 | +0.81 | 2.03 | **25.2** | 12 |
| **exp 2** - UNION (book + cell) | 531 | 40.1 | +533.5 | +1.01 | 3.09 | 13.4 | 11 |

**OUT OF SAMPLE**

| | trades | win % | net R | mean R | PF | max DD | longest loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| **before** - your book | 311 | 37.0 | +239.6 | +0.77 | 2.69 | 11.9 | 15 |
| cell (subset, not a book) | 42 | 42.9 | +109.5 | +2.61 | 6.80 | 4.7 | 5 |
| **exp 1** - GATE (only cell) | 58 | 20.7 | +37.6 | +0.65 | 1.89 | 11.0 | 13 |
| **exp 2** - UNION (book + cell) | 307 | 35.5 | +217.3 | +0.71 | 2.46 | **13.8** | 15 |

## Verdict per experiment

**exp 1 - GATE**: only trade the best cell.
FAIL. OOS 58 trades, win rate collapses to 20.7% (your book: 37%). Net +37.6R
against your +239.6R. In-sample drawdown nearly doubles to 25.2R.
The cell looks great as a subset (+2.61 mean OOS) but you cannot build a book
that waits for its tail 42 times in a sample.

**exp 2 - UNION**: keep your book, let the cell add trades.
FAIL. The extra trades lose **−19.0R** out of sample. Final net drops from
+239.6R to +217.3R and drawdown rises to 13.8R.

**cell**: not a book, just the 42 of your 311 OOS trades that happen in that
regime. Kept only because it is what both experiments were trying to use.

## Why both failed

The cell's win rate is only 5.9 points better than yours (42.9% vs 37.0%). That
cannot produce +1.84R more mean. The gain is in the top 10%: cell's best-decile
trade is +9.42R against your +3.23R. And the cell's **median** trade is worse than
yours (−0.262 vs −0.224).

So it does not win more often — it wins bigger, rarely. A book cannot wait for
that on 42 trades, and cutting those trades in half still leaves full-size losses.

Your book is unchanged: 528/+533.37/13.42 IS, 311/+239.59/11.88 OOS.
Source: `_cell_full.json` via `exp_cell_tables.py`.
