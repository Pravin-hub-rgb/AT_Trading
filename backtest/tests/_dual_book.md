<!-- prov: engine=ddd31dc measured=2026-10-08 harness=exp_dual_book.py -->
# two books, one trade each - fsent_champ_long + fsent_sig_full

Zero shared trades. Both make money in both eras.

| era | book | n | net | maxDD | dd_dur | ulcer |
|---|---|---:|---:|---:|---:|---:|
| IS | A | 528 | 533.4 | 13.4 | 22 | 16.8 |
| IS | B | 234 | 295.8 | 10.8 | 13 | 3.8 |
| IS | **monthly corr** | 45 mo | **0.153** | | | |
| OOS | A | 311 | 239.6 | 11.9 | 29 | 14.2 |
| OOS | B | 151 | 194.4 | 7.0 | 8 | 5.6 |
| OOS | **monthly corr** | 24 mo | **0.423** | | | |

| era | w on B | net | maxDD | dd_dur | ulcer | without top1 |
|---|---:|---:|---:|---:|---:|---:|
| IS | 0.00 | 533.4 | 8.0 | 5 | 2.8 | 772.8 |
| IS | 0.25 | 474.0 | 6.6 | 4 | 2.0 | 772.8 |
| IS | 0.50 | 414.6 | 6.4 | 2 | 1.7 | 772.8 |
| IS | 0.75 | 355.2 | 7.5 | 2 | 1.8 | 772.8 |
| IS | 1.00 | 295.8 | 8.6 | 3 | 2.2 | 772.8 |
| OOS | 0.00 | 239.6 | 8.1 | 1 | 2.6 | 401.8 |
| OOS | 0.25 | 228.3 | 5.2 | 1 | 1.3 | 401.8 |
| OOS | 0.50 | 217.0 | 2.3 | 1 | 0.7 | 401.8 |
| OOS | 0.75 | 205.7 | 2.6 | 2 | 0.9 | 401.8 |
| OOS | 1.00 | 194.4 | 3.6 | 2 | 1.5 | 401.8 |
