# period control on mode="flip_quality" — the arm is in-sample inert

Date: 2026-10-08. Engine post-C17. Harness: `exp_flip_period.py`.
**Not adopted, and not adoptable on this evidence.**

## What this was supposed to settle

`MODE_CONFIRM2_RIGHT_LANES.md` found `flip_quality` ahead of `fsent_champ_long`
on all three books of its family with drawdown flat or better. That result is
real and it is a single number, which is why this file exists.

The framework's discriminator (`CEILING_REGCTRL_P87`): fit

    R = a + b * cohort + half-year fixed effect + e

and read `b`. The ATR% ceiling kept 91–99% of its effect under this control, which
is why it was accepted as a filter. Every other regime-conditional tweak in this
repo collapsed toward zero. `b` is the arm's information *after* the calendar
explains everything, so `b ≈ 0` means the arm is a label for the era.

## Two bugs in my own harness, both of which flattered the arm

I have to record these because the first run produced a confident result and it
was an artifact.

**1. Survivors were labelled cohort=1.** The first version gave a t-statistic of
**7.672** on `fsent_champ_long`. That number means nothing: it was the regression
observing that the arm's 527 surviving trades beat one dropped trade. Survivors
belong to neither cohort — they are trades both books took, so they carry no
information about the mode. P82's lesson was that survivors do not cancel *when
their R moves*; here they cancel exactly, `+0.00R` in all six cells, because the
mode only changes entry selection and never the exit of a trade both books took.
The honest cohort is the disagreement set: **NEW** (arm took, base didn't) versus
**DROPPED** (base took, arm didn't).

**2. The half-year partition compared the base against itself.** The base side
accumulated only from dropped trades, so in any cell where nothing was dropped the
base printed `+0.0` and the arm "won" the cell for free. It printed **8 of 8** on
`fsent_champ_short` IS, a cell where both books took identical trades. Both sides
are now the full per-cell net of each book.

The partition on the corrected metric is also not flattering:

| book | era | arm ahead | tied |
|---|---|---:|---:|
| `fsent_champ_long` | OOS | 2 of 4 | 1 |
| `fsent_utcsat_long` | OOS | 2 of 4 | 1 |
| `fsent_champ_short` | OOS | 3 of 4 | 1 |

## The result

| book | era | NEW | DROPPED | raw gap/trade | b after control | shrink | t (month) | powered |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `fsent_champ_long` | IS | 0 | 1 | not estimable | — | — | — | n/a |
| `fsent_champ_long` | OOS | 31 | 48 | +0.0610 | **+0.2122** | 96% | 0.485 | **no** |
| `fsent_utcsat_long` | IS | 0 | 0 | not estimable | — | — | — | n/a |
| `fsent_utcsat_long` | OOS | 31 | 48 | +0.0610 | **+0.2122** | 96% | 0.485 | **no** |
| `fsent_champ_short` | IS | 0 | 0 | not estimable | — | — | — | n/a |
| `fsent_champ_short` | OOS | 37 | 55 | +0.5871 | **+1.3963** | 97% | 2.016 | yes |

Both bootstraps agree with the point estimates (month-cluster `+0.153` and
`+1.255`; half-year-cluster `+0.123` and `+1.289`), so the point estimates are not
an artifact of one clustering choice.

## Why this is a fail, stated plainly

**The mode does nothing in sample.** On all three books, in IS, the arm and the
base take the same trades: 0 new, and on two of the three books 0 dropped. On
`fsent_champ_long` IS the entire `+1.41R` "improvement" is **one trade** — the
arm drops a single loser and keeps everything else.

**Every R of disagreement is out of sample.** All three IS cells are
non-estimable because there is no disagreement to measure. The mode's entire
effect lives in the OOS window. A tweak that is inert on 528 in-sample trades and
active only on the era it was tuned against is the regime-proxy case, and it is
precisely what this instrument was built to catch.

**On the two long books the surviving effect is inside the noise.** `b = +0.2122`
against an MDE of `0.8569` — the effect is roughly a quarter of what the test can
even detect. 96% of the raw gap is explained by the calendar. That null is a
statement about the test as much as about the arm, but a candidate whose only
clean result is underpowered cannot be adopted on it.

**The one powered cell is the wrong book.** `fsent_champ_short` OOS holds up
(`b = +1.3963`, t `2.016`, above its MDE) — and that is the FS-short mirror, a
different architecture, carrying 23.9R of drawdown, and it is where the entire
`+54.01R` came from. It is one book of one architecture being measured on one
era. It cannot carry the other five cells.

## What happened to the candidate's standing

`flip_quality` is no longer "closest to adoptable". It is **disqualified on the
same grounds as the other three modes**: it buys its gain with era, not with
information. The drawdown-neutral property that made it look special is still
true and still not sufficient — being harmless is not the same as being useful.

The four candidate books remain registered and pinned. None promoted.
`fsent_champ_long` unchanged: 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS.

## Note for whoever picks this up

The three IS cells are not estimable, so this instrument **cannot** be extended to
answer whether the mode has any in-sample merit — there is nothing to measure.
If this mode is to be revisited, the question is not "does it survive period
control" but "what would make it act in sample at all", which is a question about
`chop_thresh` (the branch reads it; the key is not in this book's config) and not
about this data. The 0.35 threshold that looked peaky on OOS is a candidate for
the same question, and it has the same in-sample-inert problem to answer first.