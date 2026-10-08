<!-- prov: engine=ddd31dc measured=2026-10-08 harness=exp_owner_scorecard.py -->
# owner scorecard - 4 mode candidates vs base

Framework: `docs/learn/finding optimal book.md`. Budget 20R.
The 11.88R veto I invented on 2026-10-08 is not used here.

## bucket 1 - raw profitability

| book | era | n | net | expectancy | PF | WR% | payoff |
|---|---|---:|---:|---:|---:|---:|---:|
| BASE | IS | 528 | +533.4 | +1.010 | 3.09 | 40.0 | 4.64 |
| atr_low | IS | 641 | +721.3 | +1.125 | 3.22 | 39.2 | 5.00 |
| fd | IS | 531 | +528.6 | +0.996 | 3.06 | 39.7 | 4.64 |
| flip_quality | IS | 526 | +533.3 | +1.014 | 3.10 | 39.9 | 4.66 |
| union | IS | 813 | +580.0 | +0.714 | 2.40 | 37.4 | 4.03 |
| BASE | OOS | 311 | +239.6 | +0.770 | 2.69 | 37.0 | 4.58 |
| atr_low | OOS | 315 | +280.7 | +0.891 | 2.96 | 38.1 | 4.80 |
| fd | OOS | 291 | +238.3 | +0.819 | 2.82 | 36.8 | 4.85 |
| flip_quality | OOS | 294 | +244.2 | +0.831 | 2.87 | 37.4 | 4.80 |
| union | OOS | 442 | +303.8 | +0.687 | 2.45 | 34.4 | 4.68 |

## bucket 2 - drawdown and duration

| book | era | maxDD | dd%ret | make | recover | underwater | worst20 | worst50 | streak | budget |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BASE | IS | 13.4 | 2.5 | 22 | None | 286 | -12.7 | -8.3 | 11 | PASS |
| atr_low | IS | 28.9 | 4.0 | 82 | None | 460 | -16.3 | -26.4 | 16 | OVER |
| fd | IS | 13.4 | 2.5 | 22 | None | 289 | -12.7 | -8.3 | 11 | PASS |
| flip_quality | IS | 13.4 | 2.5 | 22 | None | 286 | -12.7 | -8.3 | 11 | PASS |
| union | IS | 23.8 | 4.1 | 46 | None | 771 | -14.5 | -18.9 | 16 | OVER |
| BASE | OOS | 11.9 | 5.0 | 29 | None | 220 | -10.8 | 1.4 | 15 | PASS |
| atr_low | OOS | 14.6 | 5.2 | 22 | 0 | 22 | -14.2 | 6.7 | 15 | PASS |
| fd | OOS | 11.9 | 5.0 | 29 | None | 213 | -10.8 | 1.5 | 15 | PASS |
| flip_quality | OOS | 11.9 | 4.9 | 29 | None | 216 | -10.8 | 3.4 | 15 | PASS |
| union | OOS | 18.2 | 6.0 | 34 | None | 237 | -13.9 | -10.7 | 15 | PASS |

## bucket 3 - return per unit of pain, and winner spacing

| book | era | net/DD | ulcer | posMon% | gap+3R | gap+5R | gap+10R |
|---|---|---:|---:|---:|---|---|---|
| BASE | IS | 39.80 | 16.8 | 71.1 | 5/19/42 | 8/25/58 | 22/58/121 |
| atr_low | IS | 24.96 | 20.5 | 66.7 | 3/17/57 | 6/29/67 | 8/56/123 |
| fd | IS | 39.45 | 18.3 | 68.9 | 6/19/42 | 8/25/58 | 23/58/121 |
| flip_quality | IS | 39.80 | 16.6 | 71.1 | 5/19/42 | 8/24/58 | 22/58/121 |
| union | IS | 24.37 | 16.6 | 75.6 | 3/24/60 | 9/43/80 | 43/85/195 |
| BASE | OOS | 20.13 | 14.2 | 70.8 | 2/24/40 | 4/30/70 | 27/58/81 |
| atr_low | OOS | 19.23 | 64.3 | 70.8 | 2/20/37 | 4/28/45 | 18/58/81 |
| fd | OOS | 20.03 | 67.0 | 70.8 | 2/26/41 | 4/30/72 | 28/57/78 |
| flip_quality | OOS | 20.52 | 66.6 | 70.8 | 2/26/41 | 4/30/72 | 28/57/81 |
| union | OOS | 16.69 | 10.8 | 70.8 | 3/23/63 | 6/36/63 | 22/87/92 |

## bucket 4 - tail dependence

| book | era | drop top1 | drop top3 | drop top5 | drop top10 | drop top1% | drop top5% | drop top10% | top5% contribution |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | IS | 90.9 | 75.7 | 64.2 | 46.9 | 64.2 | 19.8 | -8.8 | 80.2 |
| atr_low | IS | 93.3 | 80.1 | 71.4 | 55.4 | 67.1 | 18.0 | -8.8 | 82.0 |
| fd | IS | 90.8 | 75.5 | 63.9 | 46.5 | 63.9 | 17.7 | -9.6 | 80.9 |
| flip_quality | IS | 90.9 | 75.7 | 64.2 | 46.9 | 64.2 | 19.8 | -8.8 | 80.2 |
| union | IS | 91.6 | 77.7 | 67.1 | 50.2 | 56.4 | 3.9 | -28.6 | 95.0 |
| BASE | OOS | 89.1 | 72.1 | 56.6 | 34.6 | 72.1 | 16.3 | -11.7 | 81.1 |
| atr_low | OOS | 90.7 | 76.2 | 63.0 | 43.1 | 76.2 | 26.3 | -4.6 | 71.2 |
| fd | OOS | 89.0 | 71.9 | 56.4 | 34.2 | 71.9 | 18.0 | -10.1 | 79.1 |
| flip_quality | OOS | 89.3 | 72.6 | 57.4 | 35.8 | 72.6 | 20.0 | -7.5 | 77.2 |
| union | OOS | 91.4 | 78.0 | 65.8 | 44.5 | 71.8 | 13.5 | -21.8 | 86.5 |

## bucket 5 - retention, bucket 6 - complexity

| book | expectancy ret% | PF ret% | net ret% | DD expansion | knobs |
|---|---:|---:|---:|---:|---:|
| BASE | 76.3 | 87.0 | 44.9 | 0.89 | 11 |
| atr_low | 79.2 | 91.8 | 38.9 | 0.51 | 11 |
| fd | 82.3 | 92.1 | 45.1 | 0.89 | 11 |
| flip_quality | 81.9 | 92.6 | 45.8 | 0.89 | 11 |
| union | 96.3 | 102.1 | 52.4 | 0.76 | 11 |
