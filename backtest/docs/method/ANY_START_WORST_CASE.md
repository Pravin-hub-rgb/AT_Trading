# The worst case if you deploy on ANY date — the startup number was one lucky path

**Run 2026-10-10. `exp_anystart.py` → `_anystart.json`.**

# The flaw

Last turn the startup drawdown was reported as:

> **shipping book: 1.01% — ₹5,050, at trade 1**

The owner's objection: *"startup drawdown is uncertain. It could happen to be the
peak one, like 29%. There is uncertainty."*

**Correct, and the objection was right in a stronger form than was argued.**

1.01% was measured from **2021-01-01**, the first day of the backtest. It is one
path's number. It is not a bound.

`fsent_champ_long_htf15_htffs` has a 29.62% peak-to-trough that ran **March to
August**. Anyone who started in March saw the whole 29.62% on day one. Anyone who
started in January 2021 saw 1.05%. **Both are the same book.** Quoting the January
number as "the startup risk" is true and useless.

**The right question is not "what happened on day one of this backtest".** It is:

> **For every possible start date, if money goes in and the book is held a year,
> what is the worst peak-to-trough seen?**

That is a bound, not an anecdote, and it is the actual situation — nobody deploys
on 2021-01-01.

---

# Method

For each book, for **every** trade index, take the series from there with equity
starting at **zero**, walk forward 12 / 24 / 36 calendar months, and record the worst
peak-to-trough inside the window and the net at the end. Roughly 700 to 1,000 start
dates per book across the 5.7-year record. No backtests re-run — arithmetic on the
saved series.

| | meaning |
|---|---|
| **worst** | the single unluckiest start date in the whole record |
| **p10** | the bad-luck tail — 10% of start dates were at least this bad |
| **median** | the typical start |

---

# 1-year hold, from ANY start date

₹5,00,000 account at 1% risk, so the R figures are also account percentages.

| book | **worst DD** | **p10 DD** | **median DD** | **worst 12-month net** | **start dates profitable** |
|---|---:|---:|---:|---:|---:|
| `champ_trailhalf` | 31.68% | 10.25% | 13.53% | +20.55R | **100%** |
| `utcsat_trailhalf` | 31.29% | 11.06% | 14.31% | +20.94R | **100%** |
| `htf15_htffs` | 29.62% | 10.36% | 14.35% | +82.62R | **100%** |
| `mode_atr_low` | 28.88% | 10.44% | 13.53% | +57.14R | **100%** |
| `htfesmcl4` | 27.74% | 11.47% | 14.20% | +92.23R | **100%** |
| `utcsat_short` | 24.63% | 9.54% | 11.57% | +6.61R | **100%** |
| `champ_short` | 23.87% | 9.54% | 11.38% | +16.49R | **100%** |
| `mode_union` | 23.85% | **13.87%** | 18.23% | +49.07R | **100%** |
| `htffs` | 19.78% | 10.36% | 14.48% | +84.12R | **100%** |
| **`sig_multi_htffs`** | 17.82% | **6.85%** | **11.61%** | +71.72R | **100%** |
| `htf15` | 17.28% | 8.98% | 13.57% | +20.82R | **100%** |
| **`mcloff_htf15`** | 15.13% | 9.97% | **13.14%** | +43.84R | **100%** |
| **`mcloff`** / `nohalt` | 15.13% | **10.18%** | 13.37% | +48.13R | **100%** |
| **`champ_long`** ⭐ | **13.42%** | **10.65%** | **12.48%** | **+34.92R** | **100%** |
| **`sig_multi`** | 13.39% | **6.95%** | **8.95%** | +54.97R | **100%** |
| `sig_trail_delay1` | 13.34% | 5.69% | **7.93%** | +34.79R | **100%** |
| **`sig_full`** | **10.78%** | **5.71%** | **7.14%** | +30.98R | **100%** |
| `sig_fs_mom` | 9.14% | 6.10% | **7.11%** | +22.71R | **100%** |
| `sig_half_crossed` | 8.46% | 4.33% | **6.58%** | +6.17R | **100%** |

# 2-year hold, from ANY start date

| book | worst DD | p10 DD | **median DD** | **worst 24-month net** | profitable |
|---|---:|---:|---:|---:|---:|
| `htf15_htffs` | 29.62% | 14.35% | 20.20% | +298.65R | **100%** |
| `mode_union` | 23.85% | **18.12%** | **22.13%** | +220.34R | **100%** |
| `htfesmcl4` | 27.74% | 14.20% | 19.29% | +303.85R | **100%** |
| `htffs` | 19.78% | 14.35% | 19.11% | +294.91R | **100%** |
| **`sig_multi_htffs`** | 17.82% | **8.06%** | **11.91%** | +216.81R | **100%** |
| `htf15` | 17.28% | 13.57% | 16.86% | +182.00R | **100%** |
| **`mcloff`** | 15.13% | 13.37% | **13.60%** | +211.87R | **100%** |
| **`champ_long`** ⭐ | 13.42% | 11.88% | **12.48%** | +195.98R | **100%** |
| **`sig_multi`** | 13.39% | 7.64% | 12.28% | +200.51R | **100%** |
| `sig_trail_delay1` | 13.34% | 7.54% | **10.23%** | +100.70R | **100%** |
| **`sig_full`** | **10.78%** | **6.96%** | **9.91%** | +114.10R | **100%** |

---

# What this actually says

## 1. The startup number was wrong and the real figure is much larger

| | shipping book |
|---|---|
| startup DD from 2021-01-01 (what I reported) | **1.01%** |
| **median 1-year drawdown from any start date** | **12.48%** |
| **worst 1-year drawdown from any start date** | **13.42%** |

**The honest deploy-day expectation for the shipping book is a ~12% drawdown during
the first year, not 1%.** On ₹5 lakh at 1% risk that is **₹62,000**, not ₹5,050.

## 2. But every start date in the record was profitable within a year

**100% of start dates, every book, one year. 100% at two years.**

The worst start date the shipping book has ever had still made **+34.92R** in its
first twelve months — **+₹1,74,600** on ₹5 lakh at 1% risk.

**So the shape of the first year is: down roughly 10–14% at some point, up
substantially by the end of it.** The drawdown is certain; the loss is not.

## 3. The sig family absorbs a bad start date materially better

Median 1-year drawdown, any start:

| family | books | median DD |
|---|---|---|
| **sig** | `sig_full` **7.14%**, `sig_trail_delay1` 7.93%, `sig_multi` **8.95%**, `sig_multi_htffs` 11.61% | **6.6 – 11.6%** |
| **champ** | `champ_long` 12.48%, `htf15` 13.57%, `htffs` 14.48%, `htfesmcl4` 14.20%, `htf15_htffs` 14.35% | **12.5 – 14.5%** |

**Bad-luck tail (p10) is where the gap is clearest: `sig_full` 5.71% and
`sig_multi` 6.95% against `champ_long` 10.65% and `mcloff` 10.18%.**

That is the measure that answers the owner's actual worry. If the cycle turns
unlucky right after you deploy, the sig books are roughly **half as deep** as the
champ books.

---

# The correction, plainly

| | what I wrote | what it should have said |
|---|---|---|
| deploy-today worst case | 1.01%, ₹5,050 | **12.48% median, 13.42% worst, ~₹62,000** |
| how confident is that | stated as fact | it is one path's number and should never have been presented as the risk |

**The number was not fabricated — it is the real startup drawdown on 2021-01-01.**
It was the wrong statistic for the question, and presenting it as the deploy risk
understated the risk by an order of magnitude.

## Reproduce

```
python backtest/tests/exp_anystart.py
```

**Shipping book unchanged.**