# BOOK CATEGORIES — position first, then family


<!-- C17-NOTICE -->
> **C17 NOTICE (2026-10-07).** The figures in this document were measured before
> the C17 gate fix, which removed a lookahead from the HTF window gate and
> invalidated 214 of 215 registry pins. They are kept as the dated record they
> were, and they are **not** what the engine produces today - do not quote them
> as current. Current numbers: `python exp_pinverify.py` (re-derives every pin),
> `docs/method/C17_WINDOW_END_CAUSALITY.md` (what changed and why),
> `docs/multi/MULTI_RANKINGS.md` and `docs/signal/SIGNAL_RANKINGS.md`
> (regenerated from a post-C17 measurement).
------------------------------------------------------------------------------

**Where this belongs.** Not in `pipeline/`. `pipeline/` is the procedure for
running a *new* experiment. This page is a map of the books that already exist,
so that "which one do we ship" can be asked against a structure rather than
against 220 registry rows.

**The first question about any book is not "which knobs does it have", it is
"which plane is it on".** Everything else nests inside that.

## The primary axis is POSITION

The owner's word for this was "single": **one position at a time**. That is the
axis that decides what a book is for.

| book type | positions | `max_positions` | books |
|---|---|---:|---:|
| **SIGNAL** | exactly one | 1 | **4** |
| **MULTI** | several at once | 0 | 216 |

> **These are two different books, not two settings of one book.** A multi book
> stays multi forever and is never converted into a signal book. A signal book
> is built for one position and carries its own filters, its own research and its
> own theory.

**The deployment plan follows that split.** Ship a signal book first, because an
account without capital for concurrent losers cannot run a multi book. Raise
capital from it, and only then deploy the multi books, which were always going to
be multi.

### The second axis is architecture, not position

`exp_mltf` selects whether the 15m cascade runs inside each HTF bias window or
only the 1h book trades. That is a separate question from how many positions a
book holds.

| architecture | `exp_mltf` | books |
|---|---|---:|
| cascade | True | 160 |
| 1h only | absent | 60 |

The two axes are independent, and the cross-tab is:

| | SIGNAL (1 position) | MULTI (unlimited) |
|---|---:|---:|
| **cascade** | **0** | 160 |
| **1h only** | 3 | 57 |

All four signal books are 1h-only, which is what makes them buildable today: the
position gate bites on the 1h-only architecture and is inert on a cascade book
(measured: 0/1/2/3 give byte-identical books at peak concurrency 6). That is a
property of the engine, not a finding about cascade books — and it does not
need fixing, because cascade books are going to stay multi anyway.

### The signal books already exist and work

They are not a plan, they are measured and pinned:

| book | IS | OOS |
|---|---|---|
| `fsent_sig_sw10_short` | 369 / +174.30 / DD 16.62 | 239 / +100.94 / DD 11.82 |
| `fsent_sig_sw10_long` | 355 / +116.40 / DD 21.07 | 230 / +80.50 / DD 13.53 |
| `fsent_sig_sw20_short` | 343 / +146.90 / DD 32.46 | 203 / +95.00 / DD 10.23 |
| `fsent_sig_sw20_short_wr` | 343 / +146.94 / DD 32.46 | 203 / +95.00 / DD 10.23 |

All of them hold exactly one position at a time. What is still open is *which*
one to ship, and what filters to build on top of it — that is the next question,
not the existence of the book type.

> **Corrected 2026-10-05.** This table previously carried a fourth row reading
> `fsent_single_sw20_short_wr` at `515 / +492.60 / DD 14.15`. That row was wrong
> twice over. The +492.60 appears nowhere in the repository - not in the
> registry, not in any results JSON - and 515 trades is a multi-book trade count
> wearing a signal book's name; the four real signal books run 343-369 in sample.
> The book itself is also a duplicate: `fsent_sig_sw20_short_wr` and
> `fsent_sig_sw20_short` carry identical `params`, identical `swing`, and pins
> that differ only in rounding (146.94 vs 146.90). It is the same experiment
> entered twice, not a fourth result, and the `_wr` suffix does not select
> anything - there is no win-rate parameter differing between them.
>
> The number has been replaced with what the registry actually pins rather than
> deleted, so the row still shows that a `_wr` twin exists and is not a result.
> It is also a textbook instance of the fault this repo already has two of: a
> measured number copied onto a book that did not produce it. See
> `closed/CLOSED_DO_NOT_REPEAT.md` for the twelve-book inheritance fault and
> `fsent_sig_fs_mom`, where a pin was copied from a two-knob ladder onto a
> four-knob book. A pin is a claim about a measurement, and copying one is
> indistinguishable from making it until something re-derives it.

**Three is the honest count, not four.**

## Inside a plane, the filter families

From [`FAMILIES.md`](FAMILIES.md). Counts are books carrying at least one knob
from that family.

| family | SINGLE | MULTI |
|---|---:|---:|
| Risk | 48 | 157 |
| Time | 45 | 49 |
| Regime | 13 | 160 |
| StopSource | — | 105 |
| PriceAction | 4 | 27 |
| Trigger | 6 | 19 |
| Exit | 4 | 18 |
| Sizing | 10 | 11 |
| **LOOKAHEAD (closed)** | 4 | 6 |

### What that table says

**Risk and Time carry the SINGLE plane.** Nearly every single book has a risk
knob and nearly every single book has a time knob. That is what a book looks
like when it has been filtered until it is a different machine — and it is why
"which single do we ship" is currently unanswerable. See
[`BASELINE.md`](BASELINE.md) for what a pure baseline is.

**MULTI carries Regime on all 160.** `exp_persist` and the chop/ATR thresholds
are not filters on a multi book, they are how the cascade picks between the
flip and b2 interval sets. Uniformity there is structural, not fitted.

**StopSource appears only in MULTI (105).** `pivot_rule` is a stop source, not
a knob, and it is what separates the research-only `origin` books from
everything causal. See `closed/CLOSED_DO_NOT_REPEAT.md`.

**PriceAction is small and now closed.** Four single books and 27 multi books
carry it, and the family produced every look-ahead leak in this repo. It is the
first family to check and the first to delete.

## How to ask the question properly

| question | answer with |
|---|---|
| which books can I actually deploy? | plane × gate — and today that is 3 single signal books |
| is this book over-filtered? | count its families; more than three is a smell |
| is this knob a filter or structural? | its family — Regime and StopSource are structural |
| did I re-add a knob a book already has? | the family, not the knob name |

`experiment_registry.py` can be queried with `shortlisted()`; a plane/family
view is not wired in yet and should be, so that "which of my books are
deployable" is one call rather than an argument with the registry file.

---

## KNOB CATALOG — every knob, by family

Every non-base knob in the registry, grouped by the family it belongs to
([`pipeline/FAMILIES.md`](pipeline/FAMILIES.md)), how many books set it, and what it
does. `books` is books, not distinct values. **No results here** - a number lives
in `experiment_registry.py` and nowhere else. Generated from the registry.

> `exp_causal_sl` sits under "?" in the generated order and belongs in Time or
> StopSource: it gates the stop on the last CONFIRMED swing. Reclassification is
> cosmetic; the causality verdict in the table below is what matters.

---

### Plane

| knob | books | what it does |
|---|---:|---|
| `exp_mltf` | 160 | enable the LTF cascade *(values: True)* |
| `max_positions` | 4 | how a SIGNAL book is built: 1 = one position, 0 = unlimited. Multi books stay multi; this is not a converter *(values: 0, 1)* |

### Trigger

| knob | books | what it does |
|---|---:|---|
| `exp_fs_entry_side` | 10 | enter one side at the swing FS print, other side unchanged *(values: long, short)* |
| `b3_k` | 5 | deferred fill - wait up to k bars for a better price, enter at that bar's close *(values: 10, 2, 4, 6)* |
| `exp_entry_swing_age_max` | 3 | skip if the swing containing the entry is too old *(values: 50)* |
| `exp_ltf_no_entry` | 3 | block LTF entries inside the window |(values: 0, 1)* |
| `exp_kinds` | 2 | restrict entries to these break kinds |(values: FLIP)* |
| `exp_legskip_r` | 1 | skip a leg that has already run N R |(values: 2.0)* |
| `exp_skip_decisive` | 1 | drop the decisive HTF interval set, keep b2 gaps filling |(values: 1)* |

### PriceAction

| knob | books | what it does |
|---|---:|---|
| `exp_decay_mode` | 14 | decay gate on the strength of recent confirmed legs *(values: 1, 2, 3, 4)* |
| `exp_bias_momentum_min` | 11 | skip unless HTF close and 3-bar MA agree (momentum) |(values: 0.5, 0.6, 0.7, 0.8)* |
| `exp_entry_skip_b2_doji` | 3 | skip a B2 entry whose signal candle is a doji |(values: 1)* |
| `exp_cohort_swingpause` | 2 | cohort variant of the fresh-structure pause |(values: 1)* |
| `exp_min_swing_ratio` | 2 | CLOSED look-ahead - reads the swing's final leg at entry *(values: 3.0)* |
| `exp_geom_b1_max` | 1 | skip if the swing printed more than N B1 marks |(values: 1)* |
| `exp_geom_b1_min` | 1 | require at least N B1 marks on the swing |(values: 96)* |
| `exp_geom_mag_min_atr` | 1 | skip if the swing leg is under N x ATR |(values: 4.0)* |
| `exp_geom_start_dist_max_atr` | 1 | skip if the entry is far from the swing start |(values: 1.0)* |

### Regime

| knob | books | what it does |
|---|---:|---|
| `exp_persist` | 164 | bars the regime state must persist before it switches |(values: 1, 2, 3, 4)* |
| `exp_chop15_hi` | 9 | upper edge of the 15m chop band (skip above) |(values: 61.0)* |
| `exp_chop15_lo` | 9 | lower edge of the 15m chop band (skip below) |(values: 55.0)* |
| `exp_atr_ratio_max` | 8 | skip if current ATR is over N x its own floor |(values: 1.4)* |

### Time

| knob | books | what it does |
|---|---:|---|
| `exp_swingpause` | 35 | after a loss, wait for a NEW confirmed swing before the next entry *(values: 1)* |
| `exp_skip_utc_sat` | 29 | no entries on UTC Saturdays |(values: 1)* |
| `exp_wage_h` | 22 | hours a direction is held before a swing counts *(values: 10, 12, 16, 20)* |
| `exp_skip_weekend` | 14 | no entries on Sat or Sun |(values: 1)* |
| `exp_curfew_a` | 5 | no entries before hour A (UTC) |(values: 16.0, 4.0, 6)* |
| `exp_curfew_b` | 5 | no entries after hour B (UTC) |(values: 20.0, 24, 4.0, 8.0)* |
| `exp_skipwin` | 3 | skip the Nth trade in a row |(values: 1, 2)* |
| `exp_window_entry_cap` | 3 | max entries per bias window |(values: 1, 2, 3)* |
| `exp_window_win_kill_action` | 3 | what win-kill does: close |(values: close)* |
| `exp_window_win_kill_n` | 3 | kill the window after N wins |(values: 1, 2, 3)* |
| `exp_window_win_kill_scope` | 3 | scope the win-kill to the window |(values: window)* |
| `exp_skipwin_halt` | 2 | halt trading after a skipped win |(values: 1)* |
| `exp_event_mode` | 1 | scheduled-event handling: shift the event |(values: shift)* |
| `exp_event_shift_min` | 1 | minutes to shift a scheduled event by |(values: 1440)* |
| `exp_loss_streak_action` | 1 | what the streak rule does: halt |(values: halt)* |
| `exp_loss_streak_mode` | 1 | how the streak is counted |(values: halt)* |
| `exp_loss_streak_n` | 1 | losses in a row that trigger the streak rule |(values: 3)* |
| `exp_skip_utc_sun` | 1 | no entries on UTC Sundays |(values: 1)* |
| `exp_window_loss_kill_action` | 1 | what loss-kill does: close |(values: close)* |
| `exp_window_loss_kill_n` | 1 | kill the window after N losses |(values: 1)* |
| `exp_window_loss_kill_scope` | 1 | scope the loss-kill to the window |(values: window)* |

### Exit

| knob | books | what it does |
|---|---:|---|
| `exp_trail_half` | 8 | ratchet halfway to the extreme instead of all the way *(values: 1)* |
| `exp_trail_delay_r` | 7 | do not trail until +N R unrealised *(values: 1.0, 3.0)* |
| `exp_trail_skip_n` | 6 | no trail for the first n bars *(values: 3, 4, 6, 8)* |
| `exp_fs_small_swing` | 3 | exit at the swing FS if that swing's own leg is under N x ATR *(values: 6.0)* |
| `exp_trail_max_dist` | 3 | cap how far the trail sits from the extreme |(values: 0.6, 1.0)* |
| `exit_fs_max_gap_h` | 2 | exit at the swing FS if it confirms within N hours of entry *(values: 4.0, 6.0)* |
| `exp_ma_trail_period` | 1 | bars in the moving average the trail uses |(values: 20)* |
| `exp_pivot_trail` | 1 | trail to the intervening extreme, armed after that extreme prints *(values: 1)* |
| `exp_profit_stage_distance_r` | 1 | trail distance once that stage is reached |(values: 0.25)* |
| `exp_profit_stage_r` | 1 | R level at which a profit stage fires |(values: 5.0)* |
| `exp_trail_delay_prevbar` | 1 | delay eligibility uses only the previous 1m bar (strict causality) |(values: 1)* |

### Risk

| knob | books | what it does |
|---|---:|---|
| `exp_partial_r` | 205 | partial close at N R *(values: 0.0, 1.0, 2.0, 3.0)* |
| `exp_cap_days` | 12 | cap a trade's duration in days *(values: 1, 12, 16, 20)* |
| `exp_risk_max_pct` | 3 | cap risk as a percent of equity |(values: 1.0, 1.5)* |
| `exp_window_r_cap` | 3 | cap accumulated R inside a window |(values: 1.0, 2.0, 3.0)* |

### Sizing

| knob | books | what it does |
|---|---:|---|
| `exp31_lb` | 13 | lookback in bars for the sizing reference |(values: 30, 50, 60)* |
| `exp_campaign_max_addons` | 6 | max add-ons allowed in a campaign |(values: 1, 2, 3, 4)* |
| `exp_campaign_max_total` | 6 | max adds in a campaign |(values: 1, 2, 3, 4)* |
| `exp_campaign_block_mixed` | 4 | block mixed-direction adds in one campaign |(values: 1)* |
| `exp_campaign_require_marked_r` | 2 | only add after the trade marks N R |(values: -0.5, 0.5)* |
| `exp_cohort_loss_n` | 2 | losses in a cohort that trigger the rule |(values: 1, 2)* |
| `exp_cohort_rearm` | 2 | allow a cohort to re-arm after closing |(values: 1)* |

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

### unclassified (generation artefact)

`exp_causal_sl` belongs with the stop-source knobs - it gates the stop on the last
CONFIRMED swing - and is left here because the generator had no bucket for it.

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

See [`closed/CLOSED_DO_NOT_REPEAT.md`](closed/CLOSED_DO_NOT_REPEAT.md) for the measurements behind the two closed rows.
