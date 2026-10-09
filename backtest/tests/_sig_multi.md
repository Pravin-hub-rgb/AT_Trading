<!-- prov: engine=439a4f9 measured=2026-10-09 harness=exp_sig_multi.py -->
# sig_full + max_positions=0

One value differs from `fsent_sig_full`. Period control, power gate and
half-year partition all run before any verdict is offered.

## part 1 - the comparison

| era | arm | n | net | DD | WR% | expectancy | net/DD | long R | short R |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| IS | sig_full (serial) | 234 | +295.8 | 10.8 | 41.5 | 1.2642 | 27.44 | +293.3 | +2.5 |
| IS | sig+mp0  <-- THIS | 329 | +484.6 | 13.4 | 45.6 | 1.4729 | 36.19 | +465.9 | +18.7 |
| IS | champ_long (multi) | 528 | +533.4 | 13.4 | 40.0 | 1.0102 | 39.74 | +343.4 | +189.9 |
| OOS | sig_full (serial) | 151 | +194.4 | 7.0 | 46.4 | 1.2877 | 27.94 | +129.8 | +64.6 |
| OOS | sig+mp0  <-- THIS | 194 | +219.8 | 7.6 | 47.4 | 1.1331 | 28.77 | +136.7 | +83.1 |
| OOS | champ_long (multi) | 311 | +239.6 | 11.9 | 37.0 | 0.7704 | 20.17 | +96.6 | +143.0 |

## part 2 - period control

| era | estimable | survivors | new | dropped | raw gap/trade | b | t | MDE | month boot |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| IS | yes | 221 | 108 | 13 | +1.5600 | +2.1619 | +2.240 | 1.8920 | +1.8501 |
| OOS | yes | 144 | 50 | 7 | +0.4452 | +0.3303 | +0.294 | 2.1999 | +0.2847 |

## part 3 - half-year partition

| era | sig+mp0 ahead | cells |
|---|---:|---:|
| IS | 8 | 8 |
| OOS | 4 | 4 |

## part 5 - concurrency shape

| era | arm | max concurrent | depth histogram |
|---|---|---:|---|
| IS | serial | 1 | 1:234 |
| IS | sig+mp0 | 5 | 1:226 2:69 3:21 4:9 5:4 |
| OOS | serial | 1 | 1:151 |
| OOS | sig+mp0 | 4 | 1:146 2:35 3:10 4:3 |
