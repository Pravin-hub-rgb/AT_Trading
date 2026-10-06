# FS signal tweaks — trail_half / decay / both-side

Measured 2026-10-06 by `backtest/tests/_sig_fs_tweaks.py`, reading both eras
from the engine (closed trades only, same `net_r` basis as the pins). Nothing is
transcribed by hand; raw card at `backtest/tests/_sig_fs_tweaks.json`, table at
`backtest/tests/_sig_fs_tweaks.md`.

## Question

`fsent_sig_full` is short-only and long by every OOS metric (152 trd, +190.9,
avgR +1.256, PF 3.35, DD 7.0). Two ideas on the table:

1. Add the *trailing-half* family (`exp_trail_half=1`, optionally
   `exp_trail_delay_r=1.0`) on top of the same stack.
2. Add the P36 *decay gate* (`exp_decay_mode` 1/3/4, thr 0.75, legs 4) on top
   of the same stack, or stacked with trail_half.
3. Rescue the *both-side* lane (`exp_fs_entry_side="both"`, same stack) with
   the same two levers.

## Result — short_full

| arm | IS n | IS net | OOS n | OOS net | OOS R/trd | OOS PF | OOS DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | 234 | +291.0 | 152 | +190.9 | +1.256 | 3.35 | 7.0 |
| trail_half | 203 | +427.4 | 128 | +154.0 | +1.203 | 3.02 | 7.5 |
| trail_half+delay1 | 199 | +414.1 | 123 | +179.5 | +1.460 | 3.45 | 7.5 |
| decay_own_side | 190 | +332.7 | 110 | +139.3 | +1.267 | 3.52 | 6.3 |
| decay_crossed | 104 | +186.8 | 67 | +128.2 | +1.913 | 4.60 | 7.4 |
| decay_buying_block | 133 | +331.8 | 72 | +92.3 | +1.282 | 3.57 | 5.4 |
| half+own_side | 166 | +485.0 | 94 | +121.3 | +1.291 | 3.26 | 7.3 |
| half+crossed | 97 | +332.2 | 62 | +141.0 | +2.274 | 4.85 | 7.3 |

## Result — both_full

| arm | IS n | IS net | OOS n | OOS net | OOS R/trd | OOS PF | OOS DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | 294 | +41.3 | 168 | +70.6 | +0.420 | 1.74 | 17.6 |
| trail_half | 255 | +75.5 | 141 | +96.9 | +0.687 | 2.15 | 14.8 |
| trail_half+delay1 | 246 | +67.0 | 131 | +90.0 | +0.687 | 2.10 | 13.7 |
| decay_own_side | 238 | −6.1 | 141 | +77.7 | +0.551 | 1.99 | 14.5 |
| decay_crossed | 126 | +48.2 | 68 | +60.7 | +0.892 | 2.51 | 7.4 |
| decay_buying_block | 185 | +29.2 | 103 | +39.1 | +0.380 | 1.66 | 16.2 |
| half+own_side | 209 | +34.8 | 116 | +92.2 | +0.794 | 2.35 | 10.6 |
| half+crossed | 114 | +68.1 | 64 | +55.7 | +0.870 | 2.31 | 11.5 |

## Read

1. **`trail_half` does not lift the champion's OOS total.** IS +427.4 is real,
   OOS total +154.0 is below base (+190.9) with fewer trades. `trail_half +
   delay1` is the one cell that improves OOS R/trd (+1.460, n=123) and PF
   (3.45) — a per-trade lift bought with a 19% trade-count cut, not a total-R
   improvement. Keep watching, do not adopt.
2. **The decay gate is the interesting one.** `decay_crossed` takes the book
   from avgR +1.26 to +1.91 and PF 3.35 to 4.60, with DD unchanged at 7.4 and
   OOS total still +128.2 on n=67. `half+crossed` (trail_half + decay_crossed)
   pushes R/trd to +2.27 at n=62 with IS +332 (above base). These are
   *trade-filter* shapes: they half the book but keep it profitable and
   smoother. Whether that survives a sample this small is the open question,
   and it is why nothing is pinned.
3. **The both-side lane does not rescue.** Base +70.6 OOS; trail_half +96.9 is
   the best cell, still below the short-only book, and `decay_own_side` cuts IS
   to −6.1. The lane stays weak; no tweak measured here changes that.
4. **`fsent_sig_full` base is still the OOS-net leader.** Nothing here beats
   +190.9 with comparable trade count and drawdown. That is the honest headline.

## Follow-up — mirror check

`backtest/tests/_sig_fs_mirror.py` ran the three interesting cells on the two
sibling books (`fsent_sig_fs_mom`, `fsent_sig_wk_pause_short`). Raw card:
`backtest/tests/_sig_fs_mirror.json` / `.md`.

| book | OOS base | half+delay1 | decay_crossed | half+crossed |
|---|---|---|---|---|
| fsent_sig_full | +190.9 / +1.256 / PF 3.35 | +179.5 / +1.460 / 3.45 | +128.2 / +1.913 / 4.60 | +141.0 / +2.274 / 4.85 |
| fsent_sig_fs_mom | +165.6 / +1.090 / PF 3.31 | +150.6 / +1.369 / 3.25 | +117.2 / +1.750 / 4.57 | +130.4 / +2.103 / 4.56 |
| fsent_sig_wk_pause_short | +128.8 / +0.719 / PF 2.41 | +123.9 / +0.953 / 2.56 | +87.5 / +1.055 / 2.96 | +91.4 / +1.252 / 3.00 |

The shape repeats on all three books: trail_half+delay1 lifts R/trd ~+25%,
decay_crossed ~+55-75%, half+crossed ~+75%, each trading OOS total net and
trade count for a sharper book. That is a real family-level effect, not a
curve-fit on one book. It is still a filter shape, not a free lunch — the
totals come down, so adopting it means choosing "same edge, fewer trades,
smoother curve" over "more total R". Nothing is pinned.

## Multi-plane check on the FS leader pair (2026-10-06)

Same lens on `fsent_champ_long` / `fsent_utcsat_long` (`_multi_half.py`,
cards in `_multi_half.json/.md`):

| book | arm | IS net | OOS n | OOS net | OOS R/trd | PF | DD |
|---|---|---:|---:|---:|---:|---:|---:|
| fsent_champ_long | base | +528.9 | 309 | +245.0 | +0.793 | 2.76 | 11.9 |
| | **trail_half** | +530.7 | 278 | **+287.0** | +1.032 | 3.00 | 16.5 |
| | half+delay1 | +644.4 | 257 | +256.2 | +0.997 | 2.75 | 15.3 |
| | decay_crossed | +208.5 | 136 | +135.3 | +0.995 | 2.94 | 8.3 |
| fsent_utcsat_long | base | +510.5 | 308 | +244.2 | +0.793 | 2.75 | 11.9 |
| | **trail_half** | +532.0 | 277 | **+286.4** | +1.034 | 3.00 | 16.5 |
| | half+delay1 | +605.0 | 256 | +255.6 | +0.999 | 2.74 | 15.3 |
| | decay_crossed | +192.3 | 135 | +134.5 | +0.996 | 2.92 | 8.3 |

On this family plain `exp_trail_half=1` **lifts** OOS net ~+17% (+245 → +287)
with R/trd ~+30%, PF 2.76→3.00, at the cost of DD 11.9→16.5 and ~10% fewer
trades. It repeats on both mirrors, so it is not one book. This is *opposite*
to the signal-plane read (trail_half cut the totals there). It is now a
candidate, not an adopted change; a proper gate (re-run exp_port_differential,
cohort autopsy, path-true check) is the precondition before adopting.

### The gate (run 2026-10-06)

**1. `exp_port_differential.py`: PASS.** The ladder's `trail half` case -
which wraps `exp_trail_half=1` - is MATCH both eras, n=414/+282.41 IS,
n=214/+70.71 OOS: the shipped engine books the same trades in the same order
as the patched one. So `trail_half` is in the shipped binary and can be run in
production. The decay gate is **not yet in that ladder** (no `exp_decay_mode`
case), which is why the decay cells above are candidate-only by default.

**2. Cohort autopsy** (`_multi_half_autopsy.py`, `_multi_half_autopsy.json`):
trail_half does not change the entry trigger. Matching entries: fsent_champ_long
OOS 244 of 309 base trades survive, 65 removed, 34 added - the ratchet's
freed-slot + timeout interplay. Of the surviving trades, only 10 exit
identically; 234 exit differently: improved=45, degraded=189, median exit delta
−0.10R. The improved ones are big and win the sum: +42.1R on OOS exit-side
alone, matching the +245.0→+287.0 total lift. fsent_utcsat_long is the same
picture to a digit (+42.3R exit-delta, improved=45/degraded=188).

So the recipe is not "trailing catches more". It is: **most exits trimmed a
little (med −0.10R), a few exits much better (tail capture), and the freed/
added slot dynamics net out**. The equity cost: winners get more spaced out -
3R+ winner gaps OOS median 2 bars → 26 bars, same count (~34) - i.e. the
smoother-draw boosting comes from letting fewer trades run further, not from
more wins. That is exactly WHY it trades tail timing for total R, and why the
DD widened to 16.5. It is a trade you can size and it is reproducible.

**Adoption gate: still NOT adopted.** The OOS lift is carried by exit-tail
capture plus added/removed slot dynamics - a 3R+-gap widening from 2 to 26
bars - so we want one more check before shipping: `exp_fastcheck` on
`fsent_champ_trailhalf` / `fsent_utcsat_trailhalf` themselves, plus a
forward-period replay if a buffer exists.

