# live gates, the sig book, and two pre-existing problems found on the way

Date: 2026-10-08. Harnesses: `exp_live_gates.py`, `exp_route_parity.py`,
`exp_archive_verify.py`. Engine knobs `exp_min_sl_pct` and `exp_no_opposite`,
**both default OFF**, every shipped pin reproduces.

---

# PART 1 — the minimum stop, BOTH sides, BOTH eras

`exp_min_sl_pct` skips a trade when its stop is closer than the floor. It never
widens: widening would move the risk and the 3R target together and turn the
sweep into a different book.

The engine already had a floor at 0.05% of price — $20 at 40k, smaller than
round-trip fees. The owner's question was "kitna chota SL hai actually".

## stop distance as shipped (`fsent_champ_long`)

| era | side | p0 | p5 | p25 | p50 | p95 | max |
|---|---|---:|---:|---:|---:|---:|---:|
| IS | long | 0.13% | 0.40% | 0.88% | **1.42%** | 4.40% | 8.13% |
| IS | short | 0.12% | 0.38% | 0.58% | **0.99%** | 2.75% | 4.63% |
| OOS | long | 0.11% | 0.61% | 1.54% | **2.69%** | 8.73% | 16.59% |
| OOS | short | 0.30% | 0.52% | 0.91% | **1.49%** | 4.80% | 9.59% |

**The median is not a rounding error — 1.42% on longs.** The thin tail is real
though: 2 long trades under 0.20%. And the out-of-sample long median is **2.69%**
against 1.42% in sample, so the unseen era has wider, thinner-tailed stops.

## the sweep — LONG side

**IN SAMPLE (long base = 352 trades / +343.4R)**

| floor | kept | net | expectancy | DD | R removed | **% of net lost** |
|---|---:|---:|---:|---:|---:|---:|
| 0.00% | 352 | +343.4 | 0.976 | 15.8 | 0.0 | 0.0% |
| 0.20% | 351 | +329.3 | 0.938 | 15.8 | +14.2 | **4.1%** |
| 0.30% | 343 | +285.7 | 0.833 | 15.9 | +57.7 | 16.8% |
| 0.40% | 331 | +252.4 | 0.762 | 16.3 | +91.1 | **26.5%** |
| 0.60% | 316 | +255.8 | 0.809 | 14.2 | +87.7 | 25.5% |
| 1.00% | 264 | +122.7 | 0.465 | 14.1 | +220.8 | **64.3%** |

**OUT OF SAMPLE (long base = 206 trades / +96.6R)**

| floor | kept | net | expectancy | DD | R removed | **% of net lost** |
|---|---:|---:|---:|---:|---:|---:|
| 0.00% | 206 | +96.6 | 0.469 | 12.6 | 0.0 | 0.0% |
| 0.20% | 205 | +100.6 | 0.491 | 12.6 | **−4.0** | **−4.1% (gains)** |
| 0.30% | 203 | +75.9 | 0.374 | 12.6 | +20.7 | 21.4% |
| 0.40% | 203 | +79.6 | 0.392 | 12.6 | +17.1 | 17.6% |
| 0.60% | 195 | +63.5 | 0.326 | 12.6 | +33.1 | 34.2% |
| 1.00% | 184 | +40.4 | 0.219 | 11.3 | +56.2 | 58.2% |

## the sweep — SHORT side

**IN SAMPLE (short base = 176 trades / +189.9R)**

| floor | kept | net | expectancy | DD | R removed | **% of net lost** |
|---|---:|---:|---:|---:|---:|---:|
| 0.00% | 176 | +189.9 | 1.079 | 11.3 | 0.0 | 0.0% |
| 0.20% | 175 | +141.5 | 0.808 | 17.8 | +48.5 | **25.5%** |
| 0.30% | 174 | +131.6 | 0.756 | 14.4 | +58.4 | 30.7% |
| 0.40% | 166 | +94.5 | 0.569 | 14.4 | +95.5 | **50.3%** |
| 0.60% | 133 | +60.4 | 0.454 | 15.4 | +129.5 | **68.2%** |
| 1.00% | 96 | +17.3 | 0.180 | 15.9 | +172.6 | **90.9%** |

**OUT OF SAMPLE (short base = 105 trades / +143.0R)**

| floor | kept | net | expectancy | DD | R removed | **% of net lost** |
|---|---:|---:|---:|---:|---:|---:|
| 0.00% | 105 | +143.0 | 1.362 | 7.7 | 0.0 | 0.0% |
| 0.20% | 105 | +143.0 | 1.362 | 7.7 | **0.0** | **0.0%** |
| 0.30% | 105 | +143.0 | 1.362 | 7.7 | **0.0** | **0.0%** |
| 0.40% | 102 | +147.3 | 1.444 | 7.7 | **−4.3** | **−3.0% (gains)** |
| 0.60% | 95 | +140.4 | **1.478** | **6.9** | +2.6 | 1.8% |
| 0.80% | 84 | +103.4 | 1.231 | 9.8 | +39.6 | 27.7% |
| 1.00% | 76 | +84.5 | 1.111 | 12.1 | +58.5 | 40.9% |

## the finding that actually matters

**Out of sample the short side is nearly immune to a floor up to 0.60%.** It costs
1.8% of the short book's net, and at 0.40–0.60% expectancy *improves* (1.362 →
1.478) while drawdown *falls* (7.7 → 6.9). Removing three trades made the book
better on both.

**The long side cannot take it.** 0.40% costs 26.5% in sample and 17.6% out.

**But the two eras disagree violently on shorts in sample.** A 0.40% floor costs
**50.3%** of the in-sample short book and **gains 3.0%** out of sample.

**Verdict: no floor is adoptable.** The only levels where the eras are not
catastrophically opposed are 0.20% on longs (IS −4.1%, OOS **+4.1%**) and 0.30%
on shorts out of sample — but both are inside the noise on a handful of trades,
and 0.20% on the combined book costs 62.6R in sample for 4.0R out.

**And the reason is the important part: the tight-stop trades are not the losing
ones. They are the edge.** A floor removes profitable trades because they are
profitable, not despite it. That reframes the owner's concern — if those trades
are the edge, then the book depends on placing stops a venue may not fill at the
modelled price, and **that is a cost and slippage question that no min-SL rule
answers.** The doc recommends sweeping `sl_buf_atr` and the fee model instead.

---

# PART 2 — every opposite-direction overlap, and what to do

The owner's instruction: *"we shouldn't let yaar."* Here is every single one.

## IN SAMPLE — 8 overlaps in 528 trades

| # | date | leg A | leg B | overlap | pair R |
|---|---|---|---|---:|---:|
| 1 | 2024-01-18 | short **+48.49R** (6 days) | long −1.06R | 70h | +47.42 |
| 2 | 2024-02-08 | long +3.09R | short −1.05R | 10h | +2.04 |
| 3 | 2025-08-06 | long +4.24R | short −1.25R | 21h | +2.99 |
| 4 | 2025-08-06 | long +4.29R | short −1.25R | 21h | +3.04 |
| 5 | 2025-08-07 | long +1.50R | short −1.25R | 21h | +0.25 |
| 6 | 2025-08-23 | short +6.80R | long +1.73R | 25h | +8.54 |
| 7 | 2025-08-24 | short +3.59R | long +1.73R | 25h | +5.32 |
| 8 | 2025-08-24 | short +4.68R | long +1.73R | 25h | +6.41 |

## OUT OF SAMPLE — 4 overlaps in 311 trades

| # | date | leg A | leg B | overlap | pair R |
|---|---|---|---|---:|---:|
| 1 | 2021-12-03 | short **+7.59R** | long −0.12R | 18h | +7.47 |
| 2 | 2021-12-03 | short +7.59R | long −1.06R | 3h | +6.53 |
| 3 | 2021-12-04 | short +2.31R | long −0.12R | 18h | +2.19 |
| 4 | 2021-12-04 | short +2.31R | long −1.06R | 3h | +1.25 |

## what the pattern actually is

**It is not a hedge. It is a scratch trade against a winner.**

In 9 of the 12 cases the *blocked* leg is a small loser (−1.06, −1.05, −1.25 ×3,
−0.12 ×2, −1.06 ×2) sitting against a much larger winner. The 3 exceptions are all
`+1.73R` longs in the same August 2025 cluster.

So the book's "long and short at once" is a **small losing scratch trade taken
while a big winner is already running** — not two positions netting to zero
exposure. The owner's stated worry (zero exposure, double fees) is real in
principle but this book barely does it: **12 times in 6.7 years, 1.6% of
concurrency, against 351 same-direction overlaps.**

## recommendation: yes, block it — for the reason that actually applies

| | IS | OOS |
|---|---:|---:|
| net with the lock off | +533.4 | +239.6 |
| net with the lock on | **+534.3** | **+240.6** |
| cost of the rule | **+0.9R** | **+1.0R** |

**It is free and slightly positive in both eras**, because the trades it blocks
are mostly losers. But the magnitude is noise — 12 trades. **Adopt it as a cheap
invariant that makes the book's behaviour legible, not as a risk fix, and do not
claim it as one.** It also means the live bot can never carry a long and a short
on one symbol, which removes a class of operational confusion that no backtest
measures.

---

# PART 3 — the sig book, and a misconception

`fsent_sig_full` added to the dropdown at the top. It is the **only** book here
that is **serial** (`max_positions=1`), so it never overlaps at all and the
direction-lock question does not arise for it.

## distribution — the best in the registry

| book | era | trades | net | expectancy | DD | positive months | best month share | median month |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `fsent_champ_long` | IS | 528 | +533.4 | 1.010 | 13.4 | 71% | 25% | +2.9R |
| `fsent_champ_long` | OOS | 311 | +239.6 | 0.770 | 11.9 | — | — | — |
| `atr_low` | IS | 641 | +721.3 | 1.125 | **28.9** | 67% | 18% | +5.0R |
| **`fsent_sig_full`** | **IS** | **234** | **+295.8** | **1.264** | **10.8** | **76%** | **18%** | **+3.8R** |
| **`fsent_sig_full`** | **OOS** | **152** | **+194.4** | **1.288** | **6.96** | **75%** | **15%** | **+5.9R** |

**`fsent_sig_full` has the lowest drawdown in the entire set — 6.96R out of sample,
against the shipping book's 11.88R and `atr_low`'s 14.60R — and the highest
expectancy retention in the repo: OOS expectancy / IS expectancy is
1.288 / 1.264 = 101.9%.**

It is also the best-spread book by month: 75–76% of months positive, best month
only 15–18% of the year. Compare `fsent_champ_long`, where December 2023 alone is
**76.6%** of that year.

**This is worth the owner's attention.** On distribution and drawdown it beats the
shipping book on every measure, at 234 trades instead of 528 — smaller and cleaner.

## the misconception

> "sig mai hum short he lete hai toh"

**The book takes 108 longs and 126 shorts in sample — and the LONGS make
essentially all the money.**

| era | longs | shorts |
|---|---:|---:|
| IS | 108 trades, **+293.3R** | 126 trades, **+2.5R** |
| OOS | 72 trades, **+129.8R** | 79 trades, **+64.6R** |

`exp_fs_entry_side="short"` means **the FS print is used as the entry for shorts**
— longs still enter at the break. The flag changes *where shorts enter*, not
*which side carries the P&L*. In sample the shorts entered better and still made
almost nothing, because the trends that paid were long.

---

# PART 4 — two pre-existing problems found on the way

## the pin convention, which produced three false mismatches

`exp_fastcheck` returns `n = len(tr)` on the **raw** trade list. It does not
filter `outcome == "open"`; only `_net_dd` skips open trades. Three harnesses
assumed otherwise and each reported a mismatch with an **identical net**:

- `exp_route_parity`: `fsent_sig_full` OOS "151 vs 152", net +194.44 both times
- `exp_archive_list`: `trail_skipn4` "245 vs 246", net +31.02 both times
- the first version of `exp_archive_verify`

Fixed at the root. `exp_route_parity` now calls the same
`_trade_costs` / `trade_stats` / `_net_stats` / `_net_dd` chain that wrote the
pins, so agreement is structural rather than re-derived by hand a fourth time.
**All 12 parity cells now pass**, including `fsent_sig_full`.

## 36 of 168 archive cells do not reproduce

`exp_archive_verify.py` re-derives every retired book. **132 reproduce, 36 do
not.**

**This is pre-existing and not caused by the live-gate work.** Confirmed by
stashing the engine change and re-running: **identical 132/36 split before and
after.**

The failures are the `lb30_*`, `opt_*`, `gap_b3k*` and `a4_w24_*` families. Many
show the **correct trade count with the wrong net** — the signature of pins
written on an older cost model rather than pins written wrong.

This is the same drift `_registry_before.json` was already carrying: before the
prune it failed its own check on `HEAD` with roughly 156 differing rows.

**Nothing is re-pinned.** Re-pinning 36 books from current-engine output would make
the archive look clean while destroying the only record that the old numbers
existed.

---

# verification

| check | result |
|---|---|
| `exp_fastcheck` (5 books) | PASS — both knobs inert at default |
| `exp_route_parity` | **PASS 12/12**, harness and real engine |
| `exp_archive_verify` | 132/168 reproduce, 36 pre-existing stale |
| `exp_origin_lookahead` | PASS |
| `exp_resultsdb check` | PASS |
| `tsc --noEmit` | clean |
| `npm run lint` | 206 problems, identical before and after |
| live chart API, all 3 books | return trades with `htf_windows` |

**Note the charts show very few trades** (1–7 on a 500-bar window) because the
dropdown limit is a recent-date window, not the full 6.7-year backtest. That is
the chart's range, not a defect.

Registry untouched. Shipping book unchanged at 528 / +533.37 / 13.42 IS and
311 / +239.59 / 11.88 OOS.