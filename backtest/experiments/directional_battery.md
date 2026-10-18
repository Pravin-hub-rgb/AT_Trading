# The directional target — full profile

Long trades want a further target, short trades a closer one. Direction
is on the order ticket, so it needs no prediction and no lookahead, which
is what separates it from the eight state-variable signals that all flipped
between eras.

## Against the shipped configuration

| book | era | | net | trades | R/trade | win % | PF | max DD | streak |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 107 | IS | shipped 3.0 | +538.4 | 525 | +1.026 | 40.8 | 3.17 | 28.38 | 22 |
|  | IS | directional 5.0/2.5 | +573.0 | 543 | +1.055 | 40.3 | 3.24 | 28.45 | 11 |
| 107 | OOS | shipped 3.0 | +272.9 | 295 | +0.925 | 42.7 | 3.10 | 11.05 | 8 |
|  | OOS | directional 5.0/2.5 | +281.7 | 305 | +0.924 | 43.6 | 3.25 | 11.20 | 8 |
| 110 | IS | shipped 3.0 | +644.0 | 395 | +1.631 | 41.3 | 3.38 | 23.93 | 13 |
|  | IS | directional 5.0/2.5 | +675.5 | 423 | +1.597 | 41.4 | 3.35 | 23.39 | 12 |
| 110 | OOS | shipped 3.0 | +336.2 | 216 | +1.556 | 38.0 | 3.25 | 14.90 | 9 |
|  | OOS | directional 5.0/2.5 | +333.6 | 212 | +1.574 | 37.3 | 3.30 | 22.11 | 14 |

## Long and short separately

| book | era | side | shipped | directional | delta |
|---|---|---|---:|---:|---:|
| 107 | IS | long | +386.7 | +428.4 | +41.6 |
| 107 | IS | short | +151.7 | +144.6 | -7.0 |
| 107 | OOS | long | +104.7 | +123.7 | +19.0 |
| 107 | OOS | short | +168.3 | +158.1 | -10.2 |
| 110 | IS | long | +468.7 | +532.9 | +64.2 |
| 110 | IS | short | +175.3 | +142.6 | -32.7 |
| 110 | OOS | long | +138.7 | +160.5 | +21.8 |
| 110 | OOS | short | +197.5 | +173.2 | -24.3 |
