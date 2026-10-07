# exp_trail_half: more R, fewer trades, and 2.4x the drawdown

Date: 2026-10-07. Engine post-C17. Harness: `exp_trailhalf.py`. Books:
`fsent_champ_trailhalf`, `fsent_utcsat_trailhalf`.

## What the owner asked

Two registered books carry `exp_trail_half=1`, both marked CANDIDATE, and both
pin **more net R than the book being traded**:

| book | n IS | net IS | DD IS | net OOS | n OOS | DD OOS |
|---|---:|---:|---:|---:|---:|---:|
| **`fsent_champ_long`** (yours) | 528 | 533.37 | **13.42** | 239.59 | 311 | **11.88** |
| `fsent_champ_trailhalf` | 496 | 536.19 | 31.68 | **282.08** | 282 | 16.45 |
| `fsent_utcsat_trailhalf` | 497 | 534.46 | 31.29 | **281.49** | 281 | 16.45 |

+42.5R out of sample looks like a clear upgrade. Both books' pins reproduce
exactly (`exp_fastcheck.py` PASS, both eras), so this is not a stale-number
problem.

## What the knob is actually worth

Each book measured against **itself**, `exp_trail_half` 1 vs 0, everything else
where the registry has it. That isolates the knob; comparing the two books to
each other does not, since they also differ in `pivot_rule` and `ext_stop_r`.

| book | era | n | net | PF | max DD | streak | ulcer |
|---|---|---:|---:|---:|---:|---:|---:|
| champ_trailhalf | IS | 496 | +536.19 | 2.97 | 31.7 | 15 | 37.2 |
| champ_trailhalf | IS, off | 525 | +533.39 | 2.85 | **13.4** | 11 | **16.8** |
| | | **−29 trades** | **+2.80** | | **×2.37** | | |
| champ_trailhalf | OOS | 282 | +282.08 | 2.92 | 16.4 | 14 | 23.4 |
| champ_trailhalf | OOS, off | 313 | +239.58 | 2.75 | **11.9** | 15 | **14.2** |
| | | **−31 trades** | **+42.50** | | **×1.38** | | |
| utcsat_trailhalf | IS | 497 | +534.50 | 2.97 | 31.3 | 15 | 36.4 |
| utcsat_trailhalf | IS, off | 526 | +465.00 | 2.81 | **20.7** | 14 | **21.6** |
| | | **−29 trades** | **+69.50** | | **×1.51** | | |
| utcsat_trailhalf | OOS | 279 | +281.50 | 2.92 | 16.4 | 14 | 23.4 |
| utcsat_trailhalf | OOS, off | 310 | +238.80 | 2.68 | **11.9** | 15 | **14.3** |
| | | **−31 trades** | **+42.70** | | **×1.38** | | |

Outlier bar, the same one that closed chop routing: profitable with the single
best trade removed in every arm (+236.7R / +213.5R champ IS, +236.2R / +212.6R
utcsat OOS). **This is a real effect, not a tail artifact.**

## The shape nobody asked about, and it is the whole answer

`exp_trail_half` **takes fewer trades and earns more per survivor** — because it
closes half at an intermediate point, which removes the small remaining move.
That is where the +42R comes from.

The cost is that the trades it keeps run longer and further, so the drawdown goes
with them:

| | IS max DD | OOS max DD | IS ulcer | OOS ulcer |
|---|---:|---:|---:|---:|
| your book | **13.42** | **11.88** | 16.8 | 14.2 |
| trail_half on | **31.68** | 16.45 | 37.2 | 23.4 |
| multiple | **×2.37** | ×1.38 | ×2.21 | ×1.65 |

And on your book specifically, the losing streak gets **worse in sample**: 11 →
15. OOS it improves, 15 → 14. The eras disagree, which is the pattern this repo
keeps meeting.

## Why the two books say the same thing

`fsent_champ_trailhalf` gains +2.8R in sample, `fsent_utcsat_trailhalf` +69.5R.
Same knob, same OOS result to within 0.2R (+42.5 / +42.7), same trade count
(282 / 281), same drawdown (16.45 both). They are not two independent results.
The `utcsat` variant changes `pivot_rule` to `leg_no_entry` and it makes almost
no difference out of sample. **Treat this as one result, not two.**

## Verdict

**The knob works. I am not recommending the book, and the reason is drawdown.**

There is already a written rule for exactly this situation, in
`EQUITY_LENS_EXT_AND_NOHALT.md` — halt stays ON while the live max-DD budget
does not comfortably cover the book's own tail. Applying it here:

    your book needs     11.88R
    trail_half needs    16.45R   (+4.57R for +42.5R)

Same structure as the halt decision, and the same trade: a certain ~4.6R of extra
drawdown for a measured R gain. Whether that is worth it depends on your budget,
not on the backtest. **If the budget is 11.88R, trail_half is out. If it is
comfortably above 16.45R, it is a real candidate** — and the OOS figure is the
honest half of the argument, because the in-sample gain is only +2.8R on this
book.

Two things to know before that decision:

1. Its OOS drawdown is 16.45R and its in-sample drawdown is 31.68R. If in-sample
   is the more relevant bound for a rule with this few trades, the number that
   matters is 31.68, not 16.45.
2. The two books are one result, not two, so there is no replication here.

**Nothing changed.** No book promoted, no pins touched.