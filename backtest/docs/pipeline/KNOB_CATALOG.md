# KNOB CATALOG

Every non-base knob in the registry, with the family it belongs to
([`FAMILIES.md`](FAMILIES.md)), the number of books
that set it, and - where a knob reads a swing - whether it is settled at the
moment it reads it. **No results here.** A number lives in
`experiment_registry.py` and nowhere else.

`books` is how many registry books carry the knob, not how many distinct values
it takes. Generated from the registry; regenerate rather than hand-edit.

| knob | family | books | what it does |
|---|---|---:|---|

### Plane

| knob | books | what it does |
|---|---:|---|
| `exp_mltf` | 160 | enable the LTF cascade *(values: True)* |
| `max_positions` | 4 | 1 = signal plane (one position), 0 = multi (unlimited) *(values: 0, 1)* |

### Trigger

| knob | books | what it does |
|---|---:|---|
| `exp_fs_entry_side` | 10 | enter one side at the swing FS print, other side unchanged *(values: long, short)* |
| `b3_k` | 5 | deferred fill - wait up to k bars for a better price, enter at that bar's close *(values: 10, 2, 4, 6)* |
| `exp_entry_swing_age_max` | 3 | skip if the swing containing the entry is too old *(values: 50)* |
| `exp_ltf_no_entry` | 3 |  *(values: 0, 1)* |
| `exp_kinds` | 2 |  *(values: FLIP)* |
| `exp_legskip_r` | 1 |  *(values: 2.0)* |
| `exp_skip_decisive` | 1 |  *(values: 1)* |

### PriceAction

| knob | books | what it does |
|---|---:|---|
| `exp_decay_mode` | 14 | decay gate on the strength of recent confirmed legs *(values: 1, 2, 3, 4)* |
| `exp_bias_momentum_min` | 11 |  *(values: 0.5, 0.6, 0.7, 0.8)* |
| `exp_entry_skip_b2_doji` | 3 |  *(values: 1)* |
| `exp_cohort_swingpause` | 2 |  *(values: 1)* |
| `exp_min_swing_ratio` | 2 | CLOSED look-ahead - reads the swing's final leg at entry *(values: 3.0)* |
| `exp_geom_b1_max` | 1 |  *(values: 1)* |
| `exp_geom_b1_min` | 1 |  *(values: 96)* |
| `exp_geom_mag_min_atr` | 1 |  *(values: 4.0)* |
| `exp_geom_start_dist_max_atr` | 1 |  *(values: 1.0)* |

### Regime

| knob | books | what it does |
|---|---:|---|
| `exp_persist` | 164 |  *(values: 1, 2, 3, 4)* |
| `exp_chop15_hi` | 9 |  *(values: 61.0)* |
| `exp_chop15_lo` | 9 |  *(values: 55.0)* |
| `exp_atr_ratio_max` | 8 |  *(values: 1.4)* |

### Time

| knob | books | what it does |
|---|---:|---|
| `exp_swingpause` | 35 | after a loss, wait for a NEW confirmed swing before the next entry *(values: 1)* |
| `exp_skip_utc_sat` | 29 |  *(values: 1)* |
| `exp_wage_h` | 22 | hours a direction is held before a swing counts *(values: 10, 12, 16, 20)* |
| `exp_skip_weekend` | 14 |  *(values: 1)* |
| `exp_curfew_a` | 5 |  *(values: 16.0, 4.0, 6)* |
| `exp_curfew_b` | 5 |  *(values: 20.0, 24, 4.0, 8.0)* |
| `exp_skipwin` | 3 |  *(values: 1, 2)* |
| `exp_window_entry_cap` | 3 |  *(values: 1, 2, 3)* |
| `exp_window_win_kill_action` | 3 |  *(values: close)* |
| `exp_window_win_kill_n` | 3 |  *(values: 1, 2, 3)* |
| `exp_window_win_kill_scope` | 3 |  *(values: window)* |
| `exp_skipwin_halt` | 2 |  *(values: 1)* |
| `exp_event_mode` | 1 |  *(values: shift)* |
| `exp_event_shift_min` | 1 |  *(values: 1440)* |
| `exp_loss_streak_action` | 1 |  *(values: halt)* |
| `exp_loss_streak_mode` | 1 |  *(values: halt)* |
| `exp_loss_streak_n` | 1 |  *(values: 3)* |
| `exp_skip_utc_sun` | 1 |  *(values: 1)* |
| `exp_window_loss_kill_action` | 1 |  *(values: close)* |
| `exp_window_loss_kill_n` | 1 |  *(values: 1)* |
| `exp_window_loss_kill_scope` | 1 |  *(values: window)* |

### Exit

| knob | books | what it does |
|---|---:|---|
| `exp_trail_half` | 8 | ratchet halfway to the extreme instead of all the way *(values: 1)* |
| `exp_trail_delay_r` | 7 | do not trail until +N R unrealised *(values: 1.0, 3.0)* |
| `exp_trail_skip_n` | 6 | no trail for the first n bars *(values: 3, 4, 6, 8)* |
| `exp_fs_small_swing` | 3 | exit at the swing FS if that swing's own leg is under N x ATR *(values: 6.0)* |
| `exp_trail_max_dist` | 3 |  *(values: 0.6, 1.0)* |
| `exit_fs_max_gap_h` | 2 | exit at the swing FS if it confirms within N hours of entry *(values: 4.0, 6.0)* |
| `exp_ma_trail_period` | 1 |  *(values: 20)* |
| `exp_pivot_trail` | 1 | trail to the intervening extreme, armed after that extreme prints *(values: 1)* |
| `exp_profit_stage_distance_r` | 1 |  *(values: 0.25)* |
| `exp_profit_stage_r` | 1 |  *(values: 5.0)* |
| `exp_trail_delay_prevbar` | 1 |  *(values: 1)* |

### Risk

| knob | books | what it does |
|---|---:|---|
| `exp_partial_r` | 205 | partial close at N R *(values: 0.0, 1.0, 2.0, 3.0)* |
| `exp_cap_days` | 12 | cap a trade's duration in days *(values: 1, 12, 16, 20)* |
| `exp_risk_max_pct` | 3 |  *(values: 1.0, 1.5)* |
| `exp_window_r_cap` | 3 |  *(values: 1.0, 2.0, 3.0)* |

### Sizing

| knob | books | what it does |
|---|---:|---|
| `exp31_lb` | 13 |  *(values: 30, 50, 60)* |
| `exp_campaign_max_addons` | 6 |  *(values: 1, 2, 3, 4)* |
| `exp_campaign_max_total` | 6 |  *(values: 1, 2, 3, 4)* |
| `exp_campaign_block_mixed` | 4 |  *(values: 1)* |
| `exp_campaign_require_marked_r` | 2 |  *(values: -0.5, 0.5)* |
| `exp_cohort_loss_n` | 2 |  *(values: 1, 2)* |
| `exp_cohort_rearm` | 2 |  *(values: 1)* |

### StopSource

| knob | books | what it does |
|---|---:|---|
| `pivot_rule` | 105 | where the initial stop goes: leg / leg_no_entry / origin(look-ahead) *(values: leg, leg_no_entry, origin)* |

### LOOKAHEAD

| knob | books | what it does |
|---|---:|---|
| `exp_require_dir_match` | 8 | CLOSED look-ahead - reads the swing's final direction *(values: 1)* |
| `exp_max_swing_age` | 4 | CLOSED look-ahead - reads the forming swing's start *(values: 10, 25)* |
| `exp_union_dual_only` | 1 | CLOSED look-ahead - same code block as min_swing_ratio *(values: 1)* |

### ?

| knob | books | what it does |
|---|---:|---|
| `exp_causal_sl` | 4 | stop = running extreme since the last CONFIRMED swing *(values: 1)* |

## The causality column, stated once

Every knob above that reads a swing field is either **settled** at the moment it
reads it or not. The check is not "is this number sensible", it is "was this
value final at this bar".

| reads | settled? | knobs |
|---|---|---|
| `seg.end_px` at the FS bar | yes - the extreme printed | `exp_fs_small_swing`, `exp_pivot_trail` |
| `seg.end_px` at the entry bar | **no** - a later bar | `exp_min_swing_ratio`, M2 |
| swing `dir` via `start_idx <= i` | **no** - still forming | `exp_require_dir_match`, `exp_max_swing_age`, `exp_max_running_mag` |
| swing via `confirmed_at <= i` | yes | `exp_swingpause`, `exp_causal_sl` |

See `CLOSED_DO_NOT_REPEAT.md` for the measurements behind the two closed rows.
