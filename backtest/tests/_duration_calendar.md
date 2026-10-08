<!-- prov: engine=ddd31dc measured=2026-10-08 harness=exp_duration_calendar.py -->
# underwater duration in calendar time

Bucket 2 of `docs/learn/finding optimal book.md`, in units comparable
between books. Trade counts are not comparable across this set.

## IS (era spans 44.3 months)

| book | maxDD | make (wk) | make (mo) | recover (wk) | recover (mo) | underwater (wk) | underwater (mo) | % of era | recovered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BASE | 13.4 | 9.3 | 2.2 | 0.3 | 0.1 | 9.6 | 2.2 | 5.0% | yes |
| atr_low | 28.9 | 24.9 | 5.7 | 3.1 | 0.7 | 28.1 | 6.5 | 14.7% | yes |
| fd | 13.4 | 9.3 | 2.2 | 0.3 | 0.1 | 9.6 | 2.2 | 5.0% | yes |
| flip_quality | 13.4 | 9.3 | 2.2 | 0.3 | 0.1 | 9.6 | 2.2 | 5.0% | yes |
| union | 23.8 | 13.3 | 3.1 | 0.3 | 0.1 | 13.6 | 3.1 | 7.1% | yes |

| book | episodes | longest (mo) | median (mo) | all-episode underwater % of era | deepest (R) | unrecovered |
|---|---:|---:|---:|---:|---:|---:|
| BASE | 104 | 5.1 | 0.1 | 98.6% | 13.4 | 1 |
| atr_low | 132 | 7.0 | 0.0 | 99.8% | 28.9 | 1 |
| fd | 104 | 5.1 | 0.1 | 98.6% | 13.4 | 1 |
| flip_quality | 104 | 5.1 | 0.1 | 98.6% | 13.4 | 1 |
| union | 119 | 7.3 | 0.0 | 99.4% | 23.8 | 1 |

## OOS (era spans 23.9 months)

| book | maxDD | make (wk) | make (mo) | recover (wk) | recover (mo) | underwater (wk) | underwater (mo) | % of era | recovered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BASE | 11.9 | 11.1 | 2.5 | 0.6 | 0.1 | 11.6 | 2.7 | 11.2% | yes |
| atr_low | 14.6 | 7.6 | 1.8 | 0.0 | 0.0 | 7.6 | 1.8 | 7.4% | yes |
| fd | 11.9 | 11.1 | 2.5 | 0.6 | 0.1 | 11.6 | 2.7 | 11.2% | yes |
| flip_quality | 11.9 | 11.1 | 2.5 | 0.6 | 0.1 | 11.6 | 2.7 | 11.2% | yes |
| union | 18.2 | 8.4 | 1.9 | 0.6 | 0.1 | 9.0 | 2.1 | 8.7% | yes |

| book | episodes | longest (mo) | median (mo) | all-episode underwater % of era | deepest (R) | unrecovered |
|---|---:|---:|---:|---:|---:|---:|
| BASE | 65 | 2.7 | 0.1 | 99.7% | 11.9 | 1 |
| atr_low | 72 | 2.3 | 0.1 | 99.5% | 14.6 | 1 |
| fd | 63 | 2.7 | 0.1 | 99.5% | 11.9 | 1 |
| flip_quality | 66 | 2.7 | 0.1 | 99.5% | 11.9 | 1 |
| union | 74 | 3.9 | 0.1 | 95.8% | 18.2 | 1 |

