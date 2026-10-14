# RECOVERY TIME AND THE LADDER — how long was the account under water

**RE-RUN 2026-10-14 on the corrected chain (2,840 swings / 7,734 marks).**
The version this replaces was measured 2026-10-10, before the B1 arming fix
(`77711a6`), V13 (`88ecd00`) and the volatile-B1 / same-bar pivot work
(`5d6cab2`, `d71304f`).

Harness `exp_recovery_time.py`, artifact `_recovery.json`, 26 books.

---

## Two numbers that are not the same

An earlier write-up of this study quoted `maxUW` — the longest run of consecutive
trades spent below a peak — as "recovery time". **That conflated a stretch with a
duration.** The owner was right to push back on it.

| | meaning |
|---|---|
| **maxUW** | longest run of trades below a peak. A STRETCH. How long the account was underwater at its worst point in history. |
| **recovery** | trades from the BOTTOM of the max drawdown until equity passes the peak that preceded it. A DURATION. Strictly less than maxUW, often far less. Only this one answers "how long until I was back where I started". |

Everything in the first table below is **recovery**, not maxUW.

## The real recovery

| book | maxDD (R) | % @1% | peak → trough | trades to recover | days | months |
|---|---|---|---|---|---|---|
| `fsent_champ_long_mode_union` | 47.61 | 47.61 | 2023-03-13 → 2023-08-17 | **38** | 67 | 2.2 |
| `fsent_champ_trailhalf` | 29.38 | 29.38 | 2023-02-09 → 2023-06-17 | **41** | 128 | 4.2 |
| `fsent_champ_long_mcloff_htf15` | 28.38 | 28.38 | 2023-02-09 → 2023-06-17 | 41 | 128 | 4.2 |
| `fsent_champ_long_htf15` | 26.26 | 26.26 | 2023-02-09 → 2023-06-17 | 38 | 128 | 4.2 |
| `fsent_champ_long_mode_fd` | 25.94 | 25.94 | 2023-02-09 → 2023-06-17 | **49** | 128 | 4.2 |
| `fsent_champ_long` | 25.08 | 25.08 | 2023-02-09 → 2023-06-17 | **5** | 6 | 0.2 |
| `fsent_champ_long_mode_chop` | 25.08 | 25.08 | 2023-02-09 → 2023-06-17 | 5 | 6 | 0.2 |
| `fsent_champ_long_causalfloor` | 24.47 | 24.47 | 2023-02-09 → 2023-06-17 | **4** | 5 | 0.2 |
| `fsent_champ_long_mcloff` | 23.30 | 23.30 | 2023-02-09 → 2023-06-03 | 9 | 17 | 0.6 |
| `fsent_utcsat_long` | 23.81 | 23.81 | 2023-06-23 → 2023-10-14 | 6 | 9 | 0.3 |
| `fsent_champ_long_mode_atr_low` | 48.76 | 48.76 | 2023-02-15 → 2023-10-12 | **3** | 2 | 0.1 |
| `fsent_champ_long_htf15_htffs` | 29.76 | 29.76 | 2023-02-09 → 2023-10-12 | **2** | 2 | 0.1 |

## THE FINDING: depth and duration are UNRELATED, and that reorders the books

`fsent_champ_long_mode_fd` has a 25.94R drawdown and needs **49 trades / 128 days**
to recover. `fsent_champ_long` has a 25.08R drawdown — 0.86R shallower — and needs
**5 trades / 6 days**. `mode_atr_low` has the deepest drawdown in the whole table
at 48.76R and recovers in **3 trades / 2 days**.

**Ranked by depth, `fd` is the mildest book here. Ranked by how long you are
stuck, it is the worst.**

- `fsent_champ_long_htf15` vs `fsent_champ_long_mode_chop`: nearly identical
  drawdown (26.26 vs 25.08), and one takes **38 trades / 128 days** to recover
  while the other takes **5 trades / 6 days**. Seven times the wait for 1.18R more
  depth.
- `fsent_champ_long_causalfloor` recovers in 4 trades. `fsent_champ_long_mode_fd`
  at a comparable drawdown needs 49. That is a 12× difference in time-under-water
  at the same pain.

**The owner's own reading — "how long was I underwater?" — is answered by this
column and not by maxDD.** A book chosen on maxDD alone can be picked one that
ties a book for depth and ties it for 12× the recovery.

## Only one book never recovered

`fsent_sig_multi`, maxDD 13.43R, trough 2026-09-10 — **that is the last bar of the
record**, so its recovery is unmeasurable rather than failed. It should not be
counted as a book that did not recover; it is a book whose worst drawdown is
still open at the end of the sample.

## THE LADDER — where the account was, every 6 months

Account value as a percentage of where it **started**, not of its peak.

| book | 21-07 | 22-01 | 22-07 | 23-01 | 23-07 | 24-01 | 24-07 | 25-01 | 25-07 | 26-01 |
|---|---|---|---|---|---|---|---|---|---|---|
| `fsent_champ_long` | 63% | 117% | 213% | 222% | 244% | 373% | 418% | 459% | 461% | 550% |
| `fsent_champ_long_mcloff` | 62% | 119% | 215% | 220% | 248% | 378% | 425% | 471% | 475% | 568% |
| `fsent_champ_long_htffs` | 70% | 139% | 319% | 313% | 413% | 634% | 747% | 841% | 855% | 961% |
| `fsent_champ_long_htf15_htffs` | 81% | 150% | 351% | 346% | 444% | 660% | 767% | 861% | 880% | **1001%** |
| `fsent_sig_multi` | 41% | 76% | 144% | 199% | 272% | 298% | 391% | 459% | 503% | 530% |
| `fsent_sig_full` | 35% | 58% | 104% | 150% | 170% | 194% | 216% | 272% | 310% | 323% |
| `fsent_sig_multi_htffs` | 58% | 105% | 166% | 201% | 274% | 333% | 437% | 525% | 566% | 611% |

**Every row dips at 21-07** — that is the record's opening period and is shared by
all of them, so it says nothing about the book. The books separate from 22-07
onward.

**The serial signal books start much flatter**: `sig_full` is at 35% at 21-07 and
still only 104% at 22-07, against `htf15_htffs` at 81% and 351%. Single-position
books earn slowly; the multi books earn fast and carry the deeper drawdowns.

## What changed against the 2026-10-10 run

Same structural shape — several books with similar maxDD and very different
recovery times. The absolute numbers are smaller because the corrected chain
trades less. **The depth-vs-duration independence is not new and is now measured
on correct marks**, which is what matters: it is the recommendation-relevant
result in this document, and it was previously resting on a broken chain.

Nothing adopted. Shipping book unchanged.