# C16 four-arm trade diff (measured)

Harness: `backtest/tests/exp_v19_arm.py` -- **one arm per process**.
Data: `%TEMP%/at_datacache.pkl` (c1h/sw10 + c15/sw15 + fine), exp_causal_sl=0,
window_end=exit, cooldown_bars=8, max_consecutive_losses=3, ext_stop_r=3.0,
chop_thresh=58.0, htf_rr=3.0. Costs: fee 0.055%/side, entry slip 0.005%,
exit slip 0.01%, funding 0.01%/8h bar-scaled (the route's own model).

## HARNESS TRAP -- read this before trusting any multi-arm run

Running two arms inside one process produces **wrong numbers** and the results
look plausible. Measured on the same commit, same cache, same params:

    same process, origin then leg : 500t / 445.22R then 500t / 433.47R
    one process per arm         : 500t / 445.22R then 499t / 355.72R

An earlier four-arm harness reported "0 trades added, 0 removed, -3.26R". All of
that was contamination from the second run. Reloading the cache per arm does not
help either: input list lengths do not change, so a mutation check on length
reports "not mutated" while the arm is still contaminated. Always one arm per
process.

## Arms (clean, one process each)

| arm | trades | gross R | cost R | net R |
|---|---|---|---|---|
| origin = PRE-C16, v19_champion | 500 | 445.22 | 119.44 | **+325.78** |
| leg + exp_causal_sl=1 = v19_causal | 499 | 355.72 | 116.60 | **+239.12** |
| leg = POST-C16, v19_c16 | 499 | 355.72 | 116.60 | **+239.12** |

The origin arm reproduces the registry pin `champion_multi_sw10`
`{n: 500, net: 325.78}` exactly.

`v19_causal` and `v19_c16` are byte-identical in outcome. exp_causal_sl=1 and
the C16 leg rule compute the same stop.

## Membership: 7 removed, 6 added, 493 shared

Removed (pre-C16 only), entry_ts in UTC; IST is +5:30:

    1687275000  2023-06-20 15:30
    1688497200  2023-07-04 19:00
    1705564800  2024-01-18 08:00   = 13:30 IST
    1729951200  2024-10-26 14:00
    1730024100  2024-10-27 10:15
    1745017200  2025-04-18 23:00
    1745262900  2025-04-21 19:15

Added (post-C16 only):

    1687034700  2023-06-17 20:45
    1688570100  2023-07-05 15:15
    1688989500  2023-07-10 11:45
    1704942000  2024-01-11 03:00
    1729462500  2024-10-20 22:15
    1729987200  2024-10-27 00:00

500 -> 499 net. A tighter stop changes which signals clear the entry gates, so a
different trade count is expected here and is not by itself an SL-rule bug. The
stateful gates (cooldown_bars, max_consecutive_losses) shift too, which is why
removals and additions are not one-for-one on the same signals.

## Verdict

C16 costs **-1 trade and -86.66R net** against the lookahead origin rule. It stays:
the origin is the swing's declared origin, knowable only once the leg has completed,
so it is not placeable live. The 2024-01-18 08:00 UTC (= 13:30 IST) trade is one of
the seven that C16 removes.
