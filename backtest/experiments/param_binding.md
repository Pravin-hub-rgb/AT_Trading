# Which parameters are load-bearing

Every parameter of 107 and 110, perturbed to two neighbouring values
on each side, on both eras. A knob whose trade list does not move is
not a parameter. Counting how many trades change separates three
things worth separating: inert (no change at all), cosmetic (list
moves, net does not), and structural (the list moves materially).

This is the prior question to a sensitivity test, not a replacement
for one - a parameter can be strongly structural and perfectly
smooth. 107's cooldown heat map was beautifully flat, and this is
why that flatness was partly meaningless.

## Verdict

| book | parameter | value | worst net move | trades still shared | reading |
|---|---|---|---:|---:|---|
| 107 | `atr_high_thresh` | 0.65 | 15.6R | 94.2% | **structural** |
| 107 | `atr_low_thresh` | 0.35 | 0.0R | 100.0% | **INERT** - no test can find a cliff here |
| 107 | `chop_thresh` | 58.0 | 0.0R | 100.0% | **INERT** - no test can find a cliff here |
| 107 | `cooldown_bars` | 8 | 5.8R | 98.3% | cosmetic |
| 107 | `exp_fs_entry_side` | long | 143.3R | 0.0% | **structural** |
| 107 | `exp_partial_r` | 0.0 | 306.9R | 21.4% | **structural** |
| 107 | `exp_persist` | 7 | 12.9R | 96.6% | cosmetic |
| 107 | `ext_stop_r` | 3.0 | 15.6R | 93.7% | **structural** |
| 107 | `htf_rr` | (unset -> default) | 161.4R | 77.0% | **structural** |
| 107 | `max_consecutive_losses` | 0 | 178.0R | 63.8% | **structural** |
| 107 | `max_positions` | 0 | 358.5R | 65.0% | **structural** |
| 107 | `mode` | atr_high | 65.8R | 66.9% | **structural** |
| 107 | `pivot_rule` | leg | 0.3R | 99.4% | cosmetic |
| 107 | `sl_buf_atr` | 0.01 | 2.0R | 5.5% | cosmetic |
| 107 | `window_end` | (unset -> default) | 0.0R | 100.0% | **INERT** - no test can find a cliff here |
| 110 | `atr_high_thresh` | 0.65 | 19.9R | 91.2% | **structural** |
| 110 | `atr_low_thresh` | 0.35 | 0.0R | 100.0% | **INERT** - no test can find a cliff here |
| 110 | `chop_thresh` | 58.0 | 0.0R | 100.0% | **INERT** - no test can find a cliff here |
| 110 | `cooldown_bars` | 8 | 12.3R | 96.3% | cosmetic |
| 110 | `exp_fs_entry_side` | long | 116.4R | 0.0% | **structural** |
| 110 | `exp_partial_r` | 0.0 | 383.5R | 17.2% | **structural** |
| 110 | `exp_persist` | 7 | 33.0R | 91.7% | **structural** |
| 110 | `exp_trail_skip_n` | 6 | 81.5R | 44.0% | **structural** |
| 110 | `ext_stop_r` | 3.0 | 20.9R | 87.5% | **structural** |
| 110 | `htf_rr` | (unset -> default) | 264.9R | 67.1% | **structural** |
| 110 | `max_consecutive_losses` | 3 | 151.8R | 65.7% | **structural** |
| 110 | `max_positions` | 0 | 491.0R | 43.0% | **structural** |
| 110 | `mode` | atr_high | 229.1R | 59.2% | **structural** |
| 110 | `pivot_rule` | leg | 8.7R | 98.5% | cosmetic |
| 110 | `sl_buf_atr` | 0.01 | 3.1R | 4.1% | cosmetic |
| 110 | `window_end` | (unset -> default) | 0.0R | 100.0% | **INERT** - no test can find a cliff here |

An INERT row is not a wasted parameter, it is a parameter that
cannot be overfitted on. The risk being bought down here is
specific: a flat heat map over a knob that changes nothing proves
nothing about the strategy.
