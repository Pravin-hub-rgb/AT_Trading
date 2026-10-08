<!-- prov: engine=ddd31dc measured=2026-10-08 harness=exp_mode_confirm2.py -->
# check 2 on the right lanes, shipping book included

Family sharing fsent_champ_long's architecture. Base is each book's own
as-booked config; arms change only `mode`.

| family | arm | era | n | net | mean | PF | maxDD | ulcer | streak | -top5 | d net |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fsent_champ_long | **BASE** | IS | 528 | 533.4 | 1.010 | 3.09 | 13.4 | 16.8 | 11 | 342.5 | |
| fsent_champ_long | atr_low | IS | 641 | 721.3 | 1.125 | 3.22 | 28.9 | 20.5 | 16 | 514.7 | +187.9 |
| fsent_champ_long | fd | IS | 529 | 534.8 | 1.011 | 3.07 | 13.4 | 54.8 | 11 | 343.9 | +1.4 |
| fsent_champ_long | flip_quality | IS | 527 | 534.8 | 1.015 | 3.10 | 13.4 | 16.4 | 11 | 343.9 | +1.4 |
| fsent_champ_long | union | IS | 813 | 580.0 | 0.713 | 2.40 | 23.8 | 16.6 | 16 | 389.2 | +46.6 |
| fsent_champ_long | **BASE** | OOS | 311 | 239.6 | 0.770 | 2.69 | 11.9 | 14.2 | 15 | 135.7 | |
| fsent_champ_long | atr_low | OOS | 315 | 280.7 | 0.891 | 2.96 | 14.6 | 64.3 | 15 | 176.8 | +41.1 |
| fsent_champ_long | fd | OOS | 295 | 276.8 | 0.938 | 3.05 | 12.2 | 65.7 | 15 | 172.9 | +37.2 |
| fsent_champ_long | flip_quality | OOS | 294 | 244.4 | 0.831 | 2.87 | 11.9 | 77.6 | 15 | 140.5 | +4.8 |
| fsent_champ_long | union | OOS | 442 | 303.8 | 0.687 | 2.45 | 18.2 | 10.8 | 15 | 199.9 | +64.2 |
| fsent_utcsat_long | **BASE** | IS | 525 | 465.0 | 0.886 | 2.81 | 20.7 | 21.6 | 14 | 299.9 | |
| fsent_utcsat_long | atr_low | IS | 642 | 720.6 | 1.122 | 3.21 | 28.9 | 21.4 | 16 | 513.9 | +255.6 |
| fsent_utcsat_long | fd | IS | 527 | 472.5 | 0.897 | 2.81 | 13.9 | 55.0 | 11 | 307.4 | +7.5 |
| fsent_utcsat_long | flip_quality | IS | 525 | 465.0 | 0.886 | 2.81 | 20.7 | 21.6 | 14 | 299.9 | +0.0 |
| fsent_utcsat_long | union | IS | 813 | 564.6 | 0.694 | 2.36 | 36.6 | 27.2 | 16 | 373.7 | +99.6 |
| fsent_utcsat_long | **BASE** | OOS | 310 | 238.8 | 0.770 | 2.68 | 11.9 | 14.3 | 15 | 134.8 | |
| fsent_utcsat_long | atr_low | OOS | 314 | 279.9 | 0.891 | 2.95 | 14.6 | 64.4 | 15 | 176.0 | +41.1 |
| fsent_utcsat_long | fd | OOS | 294 | 276.0 | 0.939 | 3.04 | 12.2 | 65.8 | 15 | 172.1 | +37.2 |
| fsent_utcsat_long | flip_quality | OOS | 293 | 243.6 | 0.831 | 2.87 | 11.9 | 77.7 | 15 | 139.7 | +4.8 |
| fsent_utcsat_long | union | OOS | 440 | 300.6 | 0.683 | 2.44 | 18.2 | 11.0 | 15 | 196.7 | +61.8 |
| fsent_champ_short | **BASE** | IS | 532 | 600.6 | 1.129 | 3.07 | 17.6 | 4.3 | 12 | 399.5 | |
| fsent_champ_short | atr_low | IS | 621 | 825.0 | 1.329 | 3.43 | 32.3 | 8.1 | 14 | 595.1 | +224.4 |
| fsent_champ_short | fd | IS | 540 | 552.9 | 1.024 | 2.88 | 17.6 | 4.3 | 8 | 357.2 | -47.7 |
| fsent_champ_short | flip_quality | IS | 532 | 600.6 | 1.129 | 3.07 | 17.6 | 4.3 | 12 | 399.5 | +0.0 |
| fsent_champ_short | union | IS | 821 | 604.4 | 0.736 | 2.34 | 24.2 | 12.0 | 19 | 431.5 | +3.8 |
| fsent_champ_short | **BASE** | OOS | 312 | 239.5 | 0.768 | 2.46 | 23.9 | 46.1 | 14 | 109.5 | |
| fsent_champ_short | atr_low | OOS | 301 | 283.8 | 0.943 | 2.78 | 20.1 | 11.4 | 12 | 153.8 | +44.3 |
| fsent_champ_short | fd | OOS | 302 | 291.2 | 0.964 | 2.82 | 17.9 | 10.7 | 14 | 161.1 | +51.7 |
| fsent_champ_short | flip_quality | OOS | 294 | 293.5 | 0.998 | 2.92 | 19.3 | 10.9 | 12 | 163.5 | +54.0 |
| fsent_champ_short | union | OOS | 441 | 267.5 | 0.607 | 2.17 | 27.4 | 21.1 | 16 | 137.4 | +28.0 |
