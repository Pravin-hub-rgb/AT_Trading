
# C16 four-arm trade diff (measured)

Harness: `backtest/tests/exp_v19_c16_diff.py`
Data: `at_datacache.pkl` (c1h/sw10 + c15/sw15 + fine), exp_causal_sl=0, window_end=exit,
cooldown_bars=8, max_consecutive_losses=3, ext_stop_r=3.0, chop_thresh=58.0, htf_rr=3.0.
Costs: fee 0.055%/side, entry slip 0.005%, exit slip 0.01%, funding 0.01%/8h bar-scaled.

## Arms

| arm | trades | gross R | cost R | net R | avg risk |
|---|---|---|---|---|---|
| leg (POST-C16, live-placeable) | 499 | 355.72 | 116.60 | 239.12 | 741.4 |
| origin (PRE-C16, lookahead)    | 499 | 358.98 | 116.70 | 242.28 | 741.1 |

Cost model reproduces the UI exactly (239.12 net, 21.76 funding), so the harness is
consistent with what the dropdown shows.

## Membership

0 added, 0 removed, 499 shared. **C16 does not add or drop any trade.**
The 2024-01-18 13:30 trade is present in BOTH arms.

## Changed trades (6 of 499)

| entry_ts | dir | sl origin -> leg | risk origin -> leg | R origin -> leg |
|---|---|---|---|---|
| 1673019000 | long  | 16675.1 -> 16674.6 | 142.4 -> 142.9 | +2.48 -> +2.47 |
| 1681690500 | short | 30524.3 -> 30544.6 | 481.0 -> 501.3 | +0.96 -> +0.92 |
| 1722219300 | long  | 66757.2 -> 66731.5 | 2480.6 -> 2506.3 | -1.00 -> -0.99 |
| 1754314200 | long  | 114111.9 -> 114059.6 | 638.2 -> 690.5 | -1.00 -> -0.92 |
| 1769088600 | short | 90243.8 -> 90298.5 | 660.5 -> 715.2 | -1.00 -> -0.92 |
| 1786986900 | long  | 63951.8 -> 63937.3 | 224.7 -> 239.2 | +55.73 -> +52.35 |

gross delta +3.26R, cost delta -0.10R, **net delta +3.16R** (origin is better).

## Verdict

C16 costs **-3.16R net** and buys live-placeability. Keep it. The origin rule is the
swing's declared origin, knowable only after the leg completes, so it is lookahead.

## The -86.66R that is NOT C16

Registry pin `champion_multi_sw10` = `{n: 500, net: 325.78}`. That entry is
`engine: "patched"` with `exp_mltf: True` and `exp_persist: 7`.

`simulate_htf_ltf_streak_halt` in v19_champion.py has **no** `exp_mltf` and **no**
`exp_persist` parameter. The pin was measured on a different engine than the one the
dropdown runs, so 500t/+325.78R was never reproducible from this book.

The earlier "500 -> 499 trades, -86.66R under C16" claim was wrong on both counts:
membership is unchanged, and the 86.66R gap is a cross-engine pin mismatch, not C16.
