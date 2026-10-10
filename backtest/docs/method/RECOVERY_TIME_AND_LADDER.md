# How long the drawdown actually lasted — and a correction

**Run 2026-10-10. `exp_recovery_time.py` → `_recovery.json`.**

# The error

Last turn I wrote:

> "the worst peak-to-trough on the shipping book is 13.42%, which at 1% risk is
> ₹67,100 and takes about 49 trades and two years of calendar time to make back."

**That is wrong, and badly wrong.** I quoted `maxUW` — the longest run of
consecutive trades spent below a peak — and called it the recovery time. Those are
two different measurements:

| | what it measures | shipping book |
|---|---|---|
| **maxUW** | the **longest stretch** spent below a peak, anywhere in 5.7 years | 49 trades |
| **recovery** | how long from the **bottom of the deepest dip** until equity passes the peak that preceded it | **5 trades** |

maxUW is a *stretch*. Recovery is a *duration*. It is strictly less, and here it
is **ten times less**.

**The owner was right to push back and the number does not survive checking.**

---

# The corrected recovery — ₹5,00,000 account, 1% risk per R

1R = ₹5,000.

| book | max DD | **% of account** | **₹ loss** | peak → trough | **recovered in** | **calendar** |
|---|---:|---:|---:|---|---|---|
| `champ_trailhalf` | 31.68R | 31.68% | **₹1,58,424** | 04-20 → 09-19 | 13 trades | **34 days** |
| `utcsat_trailhalf` | 31.29R | 31.29% | ₹1,56,472 | 04-20 → 09-19 | 13 trades | 34 days |
| `htf15_htffs` | 29.62R | 29.62% | ₹1,48,116 | 03-19 → 08-12 | 31 trades | **62 days** |
| `mode_atr_low` | 28.88R | 28.88% | ₹1,44,402 | 02-08 → 07-31 | 17 trades | **22 days** |
| `htfesmcl4` | 27.74R | 27.74% | ₹1,38,713 | 03-19 → 08-12 | 32 trades | 63 days |
| `utcsat_short` | 24.63R | 24.63% | ₹1,23,148 | 01-18 → 06-11 | 39 trades | 82 days |
| `champ_short` | 23.87R | 23.87% | ₹1,19,340 | 01-18 → 06-11 | 23 trades | 49 days |
| `mode_union` | 23.85R | 23.85% | ₹1,19,233 | 03-16 → 06-17 | 72 trades | **128 days** |
| `utcsat_long` | 20.66R | 20.66% | ₹1,03,302 | 04-20 → 09-19 | 22 trades | 73 days |
| `htffs` | 19.78R | 19.78% | ₹98,909 | 03-19 → 06-18 | **2 trades** | **2 days** |
| `sig_multi_htffs` | 17.82R | 17.82% | ₹89,110 | 11-19 → 02-12 | 5 trades | **14 days** |
| `htf15` | 17.28R | 17.28% | ₹86,379 | 03-13 → 06-03 | 8 trades | **16 days** |
| `mcloff_htf15` | 15.13R | 15.13% | ₹75,650 | 12-01 → 01-28 | **3 trades** | **3 days** |
| **`mcloff`** / `nohalt` | 15.13R | 15.13% | **₹75,650** | 12-01 → 01-28 | **3 trades** | **3 days** |
| `causalfloor` | 13.62R | 13.62% | ₹68,083 | 09-13 → 11-17 | 5 trades | 3 days |
| `biasmom05` | 13.47R | 13.47% | ₹67,335 | 07-11 → 09-26 | 3 trades | 4 days |
| **`champ_long`** ⭐ shipping | **13.42R** | **13.42%** | **₹67,092** | 09-13 → 11-17 | **5 trades** | **3 days** |
| `sig_multi` | 13.39R | 13.39% | ₹66,958 | 12-05 → 02-07 | 8 trades | 26 days |
| `sig_trail_delay1` | 13.34R | 13.34% | ₹66,707 | 06-19 → 09-18 | 8 trades | 36 days |
| `sig_full` | 10.78R | 10.78% | ₹53,919 | 06-19 → 09-18 | 8 trades | 36 days |
| `sig_fs_mom` | 9.14R | 9.14% | ₹45,681 | 07-19 → 10-20 | 6 trades | 18 days |
| `sig_half_crossed` | 8.46R | 8.46% | ₹42,297 | 06-16 → 10-10 | 1 trade | 49 days |

## The correction in one line

| | I said | it actually is |
|---|---|---|
| **shipping book, worst dip** | ₹67,100 and **49 trades ≈ 2 years** | ₹67,092 and **5 trades, 3 days** |

**Every book in the family recovered from its maximum drawdown within 34 to 128
calendar days.** The longest is `mode_union` at four months. None took two years.

`htffs` recovered from a ₹98,909 dip in **two days**.

---

# The ladder — what you actually see on a chart

The owner described the equity curve as a staircase, and that is exactly right.
Each column is the account value as a **percentage of where it started**, not of
its peak. At 1% risk, 100% means the original ₹5 lakh.

| book | 21-07 | 22-01 | 22-07 | 23-01 | 23-07 | 24-01 | 24-07 | 25-01 | 25-07 | 26-01 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`champ_long`** ⭐ | 46% | 78% | 170% | 239% | 268% | **411%** | **470%** | **527%** | 526% | **664%** |
| **`mcloff`** | 43% | 90% | 197% | 270% | 299% | **455%** | **514%** | **572%** | 572% | **714%** |
| `htffs` | 54% | 121% | 304% | 299% | 410% | **624%** | **764%** | **915%** | 923% | **1050%** |
| `htf15_htffs` | 73% | 123% | 308% | 303% | 396% | **610%** | **761%** | **925%** | 942% | **1082%** |
| `sig_multi` | 40% | 85% | 161% | 239% | 310% | 358% | 426% | 506% | 541% | 612% |
| `sig_full` | 39% | 80% | 137% | 214% | 253% | 285% | 352% | 402% | 420% | 461% |
| `sig_multi_htffs` | 61% | 131% | 208% | 254% | 372% | 478% | 626% | 742% | 785% | 845% |

## Reading the ladder

**Every single mark is above 100%.** The lowest any book sits at any six-month
checkpoint in five and a half years is **39%** (`sig_full` at mid-2021) and
**40%** (`sig_multi` at mid-2021). Everything after mid-2021 is above 100% and
rises.

**The shipping book at ₹5 lakh and 1% risk:**

| when | account |
|---|---:|
| start (Jan 2021) | ₹5,00,000 |
| Jan 2023 | ₹11,95,000 |
| **Jan 2024** | **₹20,55,000** |
| Jan 2025 | ₹26,35,000 |
| **Jan 2026** | **₹33,20,000** |

**One flat step exists — 2025-01 at 527% to 2025-07 at 526%.** Seven months of
going nowhere. That is the worst calendar stretch in the record, and it is 1.1%
of difference, not a 13% hole.

## The three durations, kept apart

| | shipping book | what a deployer cares about |
|---|---:|---|
| **startup DD** — dip below where you put the money in | 1.01% = ₹5,050, at trade 1 | how bad is day one |
| **recovery from max DD** — trough back to prior peak | **5 trades, 3 days** | how long is one bad episode |
| **maxUW** — longest stretch below water, anywhere | 49 trades | how bad can the *longest* dry spell get |

The 49 is real and it is not nothing — it is the longest stretch where the
account was below a previous high, somewhere in the middle of the record. But it
is **not** the cost of the 13.42% drawdown, and quoting it as that cost overstated
the experience by about an order of magnitude in time.

---

# What this changes

Nothing about which book is preferred, and nothing about the gates.

- The 13.42% is real: ₹67,092 at 1% risk on ₹5 lakh.
- The episode lasted **from September to November in one year** and was over in
  **three days** once it bottomed.
- The thing that actually tests patience is not any single drawdown. It is that the
  account **spends most of its life below its previous high** — 80.3% of the time
  for the shipping book — and that there is a 49-trade stretch somewhere in the
  record where nothing new is printed for a long time.

**Those are different problems and they should not be described with one number.**
The previous version of this document did exactly that.

## Reproduce

```
python backtest/tests/exp_recovery_time.py
```

**Shipping book unchanged.**