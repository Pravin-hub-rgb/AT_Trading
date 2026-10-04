# KNOB FAMILIES — the taxonomy

A knob belongs to exactly one family, and the family tells you what kind of
object it is and therefore how it interacts with other knobs. Nothing here
carries a result. Results live in `experiment_registry.py` and nowhere else,
because they change when the engine changes.

## Why this matters

Two knobs from different families almost never interfere. Two from the **same**
family are usually measuring the same thing twice, and the second one is usually
adding nothing but looking like a result. Before adding a knob to a book, check
its family against what is already in the book — if the family is already
represented, the marginal knob is a fit, not a filter.

## The eight families

### 1. PLANE — single vs multi

Not a knob. The first decision, and the one that changes what "a trade" means.

| plane | positions | who can trade |
|---|---|---|
| **signal** (`max_positions=1`) | exactly one | an account that cannot carry concurrent losers |
| **multi** (`max_positions=0`) | unlimited | an account that can |

`max_positions` is the only knob in this family. Everything else is downstream of
it: serialising throws trades away, so a knob that stacks well in multi can be
useless in signal.

### 2. PRICE ACTION — what the structure looks like

Reads the *shape* of the swing or the move: is this leg big, is momentum with
us, has the swing been running long, is this candle a doji.

`exp_decay_mode`, `exp_bias_momentum_min`, `exp_min_swing_ratio`, `exp_geom_*`,
`exp_entry_skip_b2_doji`, `exp_momentum`, `exp_cohort_swingpause`.

**This is the family that produced every look-ahead leak in this repo.** All of
them read a swing field that is not settled at the entry bar. See
`CLOSED_DO_NOT_REPEAT.md`. Before adding anything here, state which field is
read and when that field settles.

### 3. TIME — remove trades by the clock or by recency

Does not look at price at all. Either "not right now" (session, weekday,
scheduled event) or "not yet, we just had a loss" (cooldown, streak, pause).

`cooldown_bars`, `max_consecutive_losses`, `exp_swingpause`, `exp_loss_streak_*`,
`exp_skip_utc_sat`, `exp_skip_utc_sun`, `exp_skip_weekend`, `exp_wage_h`,
`exp_curfew_a` / `exp_curfew_b`, `exp_event_shift_min`, `exp_event_mode`,
`exp_window_entry_cap`.

**These are the weakest filters in the repo and the easiest to overfit.** Each
one throws trades away on a schedule, which is a free parameter with no
mechanism. `exp_swingpause` is the only one with a reason: it waits for a *new
confirmed swing* after a loss, so it is "structure updated" rather than "waited
N minutes".

### 4. TRIGGER — which trades, not whether

Changes *what kind of entry* counts, rather than gating an entry that was
otherwise going to happen. A trigger can take trades a gate would never allow.

`exp_fs_entry_side`, `exp_kinds`, `exp_flip_break`, `b3_k`, `exp_ltf_no_entry`,
`exp_entry_swing_age_max`.

`exp_fs_entry_side` is the one that works in this repo. `b3_k` is a deferred
fill — it waits up to k bars for a better price and re-prices the entry at the
bar it lands on.

### 5. REGIME — is the environment right now

Reads volatility or chop to decide whether the current conditions suit the
strategy at all.

`exp_chop15_lo` / `exp_chop15_hi`, `exp_atr_ratio_max`, `exp_persist`,
`exp_regime_skip`, `atr_high_thresh`, `atr_low_thresh`, `chop_thresh`, `mode`.

`mode` is the important one and is not really a knob — it decides how the chop
and ATR bands combine to pick between the flip and b2 HTF interval sets.

### 6. EXIT — when to let go

Trail shape, stop shape, and everything that decides the exit rather than the
entry.

`exp_trail_half`, `exp_trail_delay_r`, `exp_trail_skip_n`, `exp_trail_max_dist`,
`exp_pivot_trail`, `exp_ma_trail_period`, `exp_profit_stage_r`,
`exp_profit_stage_distance_r`, `exp_fs_small_swing`, `exp_fs_gray`,
`exit_fs_max_gap_h`, `exp_trail_delay_prevbar`.

Trail knobs are a sub-family that mostly fight each other — a half-step trail and
a delayed trail are two statements about the same event. `exp_trail_half` with a
`skip_n` is the combination that carries the top books; `exp_trail_half` with a
`delay_r` is measured and weaker.

### 7. RISK — how much, and how many at once

Position size, stop width, partial closes, concurrency caps.

`exp_partial_r`, `exp_risk_max_pct`, `exp_max_concurrent`, `ext_stop_r`,
`sl_buf_atr`, `htf_rr`, `exp_cap_days`, `exp_max_running_mag`,
`exp_window_r_cap`.

`exp_cap_days` is the time-based one and belongs here rather than in TIME,
because it bounds a trade's duration rather than gating when it opens.

### 8. SIZING — dynamic position size

Adds or removes into a position as the campaign develops.

`exp_campaign_max_total`, `exp_campaign_max_addons`, `exp_campaign_block_mixed`,
`exp_campaign_require_marked_r`, `exp_cohort_loss_n`, `exp_cohort_rearm`,
`exp31_lb`.

## The base knobs

`experiment_registry.BP` is what every book inherits before its own `params`.
These are ten values and they are not cosmetic: `mode`, `cooldown_bars`,
`max_consecutive_losses`, `ext_stop_r`, `sl_buf_atr`, `htf_rr`, `window_end`,
and the chop/ATR thresholds. A book that overrides all ten is not "the same book
with a filter", it is a different book. See [`BASELINE.md`](BASELINE.md).

## Rules that fall out of the taxonomy

- **Never add a second knob from a family the book already has.** That is how
  this repo got books with four overlapping filters and no idea which one was
  doing the work.
- **A knob from family 2 must name the swing field it reads and when that field
  settles.** This is the look-ahead gate.
- **Family 3 knobs are the ones to delete first when a book looks too good.**