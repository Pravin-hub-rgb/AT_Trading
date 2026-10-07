# Equity lens: is ext_stop_r removable, and what does the halt-off curve look like

Date: 2026-10-07. Harness: `backtest/tests/exp_equity_lens.py`. Engine post-C17.
Books: `fsent_champ_long` (base) and `fsent_champ_long_nohalt`.

## Q1 - REMOVE ext_stop_r? YES

    era  n        trade lists identical  equity curve identical  net
    IS   528/528  True                  True                   +533.37 both
    OOS  311/311  True                  True                   +239.59 both

Not "equivalent" and not "within tolerance" - **byte-identical**, and the entire
equity lens (`ulcer`, `sortino`, `calmar`, `uw_pct`, `max_dd_dur`, `max_uw`,
`max_streak`, `pos_month_pct`, `worst_month`) compares equal field by field. The
equity curve is not similar, it is the same curve.

C17 removed the straddle that the knob used to patch, and that left the knob with
nothing to do. It is a guard with no work left, not a tuned value.

**Two cautions on how it gets removed.**

1. `fsent_champ_long` itself is left untouched. That key is the shipped
   champion and the repo's control: nine harnesses read it
   (`_strip.py`, `_halt_sweep.py`, `_fsent_ablation.py`, `_multi_half.py`,
   `_multi_half_autopsy.py`, `_cooldown_sweep.py`, `exp_fs_small_swing.py`,
   `exp_signal_metrics.py`, `exp_signal_causal_dirmatch.py`), and the graveyard
   text of ten other books cites it by name. Changing its params, even to a
   provable no-op, changes what that name means. The knob is set to `0.0` in the
   new `fsent_champ_long_nohalt` entry instead.
2. **Never omit the key.** `BP` carries `ext_stop_r=1.5`, so deleting the field
   from a book's params does not mean "off" - it inherits 1.5, which is a live
   filter that blocks 122 IS and 86 OOS signals on this book. Write `0.0`.

## Q2 - nohalt under the full lens

`max_streak` here is the longest run of **consecutive losses**
(`exp_equity_quality.py`), so lower is better on it too.

| metric | IS base | IS nohalt | d | | OOS base | OOS nohalt | d |
|---|---:|---:|---:|---|---:|---:|---:|
| n | 528 | 575 | +47 | | 311 | 337 | +26 |
| **net** | 533.37 | 566.59 | **+33.2** | | 239.59 | 270.91 | **+31.3** |
| max_dd | 13.42 | 15.13 | WORSE +1.71 | | 11.88 | 14.16 | WORSE +2.29 |
| max_dd_dur | 23 | 25 | WORSE +2 | | 30 | 33 | WORSE +3 |
| max_uw | 49 | 54 | WORSE +5 | | 31 | 35 | WORSE +4 |
| **ulcer** | 16.79 | 11.40 | **better -5.39** | | 14.23 | 13.94 | **better -0.29** |
| **sortino** | 756.2 | 800.4 | **better +44.2** | | 355.1 | 404.5 | **better +49.4** |
| calmar | 10.83 | 10.20 | WORSE -0.63 | | 10.09 | 9.56 | WORSE -0.52 |
| recovery | 39.75 | 37.45 | WORSE -2.30 | | 20.17 | 19.13 | WORSE -1.05 |
| max_streak | 11 | 11 | same | | 15 | 16 | WORSE +1 |
| pf | 3.088 | 3.019 | WORSE -0.068 | | 2.688 | 2.775 | better +0.087 |
| pos_month_pct | 71.1 | 71.1 | same | | 66.7 | **75.0** | better +8.3 |
| worst_month | -8.66 | -8.78 | better | | -8.10 | -8.10 | better |
| worst_year | 108.19 | 108.71 | WORSE | | 78.33 | 91.01 | WORSE |

### Which profile is this

The graveyard profile is total R up **and** max DD up **and** ulcer up - more
total bought with a deeper and more persistently painful curve. This is not that.
Uner drops sharply (IS 16.79 to 11.40) and sortino rises in both eras, meaning
the *typical* path got meaningfully smoother. What pays for it is the worst case:
max DD +1.7 IS and +2.3 OOS, drawdown duration +2 and +3 trades, longest losing
run 15 to 16 out of sample.

That is the shape more trades naturally produce, and it is a trade rather than a
free lunch - something has to pay for a smoother average, and here it is the tail.
Every direction agrees across both eras except IS profit factor and IS longest
losing run, which are flat.

OOS positive months 66.7% to 75.0% is the strongest single number here: the book
stops money in three more months out of fifteen.

### What it is not

It is not a risk reduction. The halt exists to bound loss streaks; removing it
lengthened the longest losing streak out of sample and deepened the worst
drawdown. If live capital has a drawdown budget or a consecutive-loss limit, this
costs that budget. It buys total R and a smoother typical path by taking more
trades, not by taking less risk.
