# exp_persist sweep - fsent_champ_long (post-C17)

Grid against the shipping base (halt=3, ext_stop_r=0.0), both eras.

| exp_persist | IS n | IS net | IS dd | OOS n | OOS net | OOS dd |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 525 | 467.30 | 20.00 | 325 | 234.60 | 13.20 |
| 2 | 526 | 509.20 | 16.30 | 327 | 239.70 | 13.40 |
| 3 | 528 | 523.30 | 12.90 | 321 | 244.60 | 11.70 |
| 4 | 526 | 519.30 | 13.50 | 312 | 245.30 | 11.90 |
| 5 | 528 | 533.40 | 13.40 | 313 | 242.80 | 11.90 |
| 6 | 528 | 527.00 | 13.80 | 314 | 244.10 | 11.90 |
| 7 ** | 528 | 533.40 | 13.40 | 311 | 239.60 | 11.90 |

Shipping value marked ** is unchanged by this sweep. Harness `exp_persist_sweep.py`.

## The `persist=5` advantage is one trade

`persist=5` is the only value not worse in either era, so it is worth being precise
about why, because "no worse in either era" sounds stronger than it is.

In IS, `persist=5` and `persist=7` produce the **byte-identical trade list**.
The entire difference is OOS, and it is 22 trades out of 311-313:

    12 trades only at persist=5    sum +6.01R
    10 trades only at persist=7    sum +2.82R
                                  delta +3.19R

One trade carries more than the whole advantage:

    1653868800   long @ 29336.5, SL 29074.14, exit 31400.0   +7.647R

Drop that single trade and `persist=5` is **-4.46R WORSE** than shipping, not better:

    full delta(5-7)                     +3.19R
    without 1653868800 (+7.647R)        -4.46R
    without that and 1656421200         -1.09R

That trade is a 2.2-day long from 29336 to 31400, and only 13 of 313 OOS trades
clear +7.6R (p99 is +18.79R, so the book has a genuine fat right tail and this
sits in it). So this is one tail draw deciding a knob value, not a systematic edge
at 5 versus 7.

**Verdict: `exp_persist=7` stands.** The grid shows 7 is not uniquely tuned in IS -
5, 6 and 7 are all within noise of each other, and 3 and 4 buy a little OOS at an
IS cost, which is the era-split pattern already seen six times in this repo. But
the one value that looked free was not free; it was a single outlier. Re-tuning on
that is fitting the knob to one trade.

Read this alongside the binds audit: `exp_persist` BINDS, it is just not finely
tuned, and 7 is a defensible point inside a flat region rather than a sharp peak.

## Why the -5.0R OOS in the audit row above was not left to stand

The audit table probes `exp_persist` with **0**, and reports -66.1R IS / -5.0R
OOS. The IS half of that says "clearly keep it". The OOS half says something
nastier if read literally: the knob's entire out-of-sample value is 5R, which is
small enough to ask whether 7 is even earning its place, and whether a smaller
number does the same work. That question is what this sweep answers, and it is
not answerable from the probe: one endpoint cannot distinguish "tuned" from
"binds".

The audit row is left unchanged, because it is correct **as a probe**. It says
`exp_persist=0` costs 66R in sample and 5R out of it. That is a true statement
about a different question, and swapping it for this sweep's numbers would make
the audit answer a question it was not asked.
