# THE CHAMPION HANDOFF — P55 to P98

<!-- MARK-CORRECTION-NOTICE -->
> **MARK-CORRECTION NOTICE (2026-10-14). — SUPERSEDED ON EVERY FIGURE.**
>
> This page opens with `champion_multi_sw10`, **IS 500t +325.8R A** /
> **OOS 279t +70.1R**, M = 193.4R. **All three are superseded.**
>
> The engine was corrected at the mark level on 2026-10-11 to 2026-10-13 (B1
> arming fix, V13, volatile-B1 colour rule, same-bar duplicate-pivot fix).
> Chain **2753 swings / 7505 marks** → **2840 / 7734**.
>
> | | this page (Sept 2026) | corrected chain |
> |---|---|---|
> | champion | `champion_multi_sw10` | **`fsent_champ_long`** |
> | IS | 500t / +325.8R | 497t / **+466.92R** / dd 25.08 |
> | OOS | 279t / +70.1R | 281t / **+215.32R** / dd 11.20 |
>
> Also: **69 books were retired on the same date** (any era negative → out), so
> `champion_multi_sw10` itself is retired — OOS −45.20R. It no longer resolves in
> the registry. See `docs/method/RETIRED_BOOKS.md`.
>
> The reasoning below is kept as the dated record it was; the numbers it reasons
> about are not current. Current: `docs/method/SCORECARD_LEADERBOARD.md`, and
> `python exp_pinverify.py` to verify anything.
<!-- /MARK-CORRECTION-NOTICE -->

**The authoritative record. Validated / exploratory / retracted, with the
accounting basis each result is actually stated on.**

Dated 2026-09-30. Champion `champion_multi_sw10`, 1h HTF + 15m LTF.
**IS 500t +325.8R · OOS 279t +70.1R. M = 193.4R.**
`utcsat_multi_sw10` — IS +359.0R, OOS +60.2R. **Same data, different
params. Not independent evidence.**

**Nothing was adopted across 44 experiments. No production file was
edited. The pin was asserted every run, never moved.**

---

## THE COST BASE — read this before any number below

| | n | gross | **NET** | cost | % of gross |
|---|---|---|---|---|---|
| champion IS | 500 | +445.2R | **+325.8R** | 119.4R | 26.8% |
| champion OOS | 279 | +105.7R | **+70.1R** | 35.6R | 33.7% |
| utcsat IS | 454 | +466.5R | **+359.0R** | 107.5R | 23.0% |
| utcsat OOS | 253 | +92.6R | **+60.2R** | 32.4R | 35.0% |

**A quarter to a third of every book is cost** (`P98`). Every headline in
this programme is NET unless a row says otherwise.

---

## PART 1 — VALIDATED. Would survive an audit.

| # | question | basis | result |
|---|---|---|---|
| **P79** | is the swing layer lookahead-dependent? | net, both eras | **NO.** 100% prefix invariance across **13,201** swing comparisons, 3 cut points, both chains. The layer is replayable by construction. |
| **P91** | is +325.8R a close-fill artefact? | **cost-free, descriptive** | **NO.** Re-filling at the next 15m open does not change it. **The shipped figure is the pessimistic one.** |
| **P57/P58** | is 1h the right source? is 1D useful? | net | **1h+15m wins every cell.** 1D negative as a source. |
| **P96** | is the concurrency guard working? | net, 4 arms + placebo | **NO — it has never fired.** Date-vs-datetime string compare. See Part 3. |
| **P97** | can a correct slot queue recover it? | net, caps 1–8 | **NO — the queue is empty.** Seven caps, one book. |
| **P98** | is the recorded analysis on a net basis? | net per trade | **NO for P89/P92.** Corrected. |

## PART 2 — EXPLORATORY. Real structure, not adoptable.

| # | finding | why it is not adoptable |
|---|---|---|
| **P94** | outlive cohort: 103 trades (20.6%), **+481.6R NET**, PF 15.05, 24-0 half-year partition | **0.81× M**, and selected on a **post-outcome** event — circular as a rule |
| **P95** | `bars_to_window_end` separates the cohorts, **AUC 0.843–0.867 in 4/4** | separation, not a threshold. Also: the 16× unit bug below |
| **P93** | trades outliving their window average **+4.9R**; inside-window **−0.16R** | the "weak" 80% were never bad entries |
| **P69/P87** | ATR ceiling **survives period control** (b = +0.82 to +1.30) | IS fails at all four levels; filtering costs money. **Do not rerun.** |
| **P65** | Stage 64 win-streak block: 14-3 on partition | **0.13× M** |
| — | `decay < 0.75`: 4/4 positive | **0.13× M** |

## PART 3 — RETRACTED or CORRECTED. Do not quote the old number.

| # | as recorded | **verified** |
|---|---|---|
| **P96/P97** | — | **Concurrency guard never fires.** 500t → 395t serial: **−188.1R IS**, and **OOS goes to −13.3R, PF 1.10**. |
| **P97** | — | **E2 "0 overlaps, PASS" is a false PASS.** `test_cat_e.py` checks only `zip(tr,tr[1:])` on a 330-trade config. Champion IS: **maxconc 6, 152 overlapping pairs.** |
| **P89** | shorts stronger; **protect the long side** | **INVERTED.** On net the long side is worse: champ OOS long **PF 1.01**, +22.1R gross → **+1.4R net**. Recommendation **withdrawn**. |
| **P92** | worst episode **445.2R**; depths 265R median | **30.5R.** Double-subtraction bug. Wrong by an order of magnitude. |
| **P83** | max DD **37.3R** | **30.5R** on a correct algorithm. **Every doc carrying 37.3R is stale.** |
| **P94** | +506.2R, dNet **0.93× M** | **+481.6R net, 0.81× M.** Gross-vs-net comparison. |
| **P90** | next-open **+500.6R** | **RETRACTED** in P91 — R-denominator artefact. |
| **P91** | absolute return figures | **OMIT COSTS.** Descriptive, **not an account curve.** **⚠️ 2026-10-01: its long/short split claim is RETRACTED — `abs_return()` ignored `t["dir"]`, so profitable shorts were read as losses. The fill result survives; the split does not. See `method/FILL_ABSOLUTE_P91.md`.** |
| **P95** | OUT cohort "76 days", IN "13 days" | **16× unit bug.** Correct: **4.78 days / 114.7 hours** and **0.80 days / 19.2 hours**. |
| **P57** | `min_bars` as a lag | was a bar **COUNT** — a 24× penalty on slow arms, corrected in P58 |


---

## PART 4 — CLOSED. Never rerun as new.

| # | asked | verdict |
|---|---|---|
| P55 | era inversion detectable at runtime? | **No** — geometry separates IS/OOS by 0.01–0.10 vs IQR ~0.75 |
| P56 | does window expiry earn its keep? | **IS-fitted** — costs 121–141R in IS, earns 81–102R in OOS |
| P60 | union the two books | **Loses 4/4.** 43–46% of signals skipped. Its "+664R bound" was 36× too high |
| P61 | is cand_4h1h stable? | **No** — 4-4 in IS, lost every period since 2025H2 |
| P63 | size the forward null | **Settled.** 40–70 trades: forward can **rule out, never confirm** |
| P64/P70 | ZigZag | **Closed dead** by P70. 12 of 24 cells clear M and **all 12 are negative** |
| P66 | 30m / 45m LTF | **Cleanest era-split found** — 30m doubles OOS, costs 188–239R in IS |
| P71 | can B1 fire entries? | **No** — `_collect_signals` is FCFS; B1 can only displace. Loses 36–164R in 4/4 |
| P73/P74 | the FS "hybrid" | **Withdrawn** — it was a swap, not an addition (books 99.8% disjoint) |
| P77 | period split of FS book | **Killed** — wins 2021-22, loses **every year 2023-26** |
| P80–P82 | directional FS (**owner's idea**) | **Best-looking result of the round** — 4/4 positive, 22-8 partition. **Permutation: p = 0.69–0.92** |
| P84/P86 | trend-MA, ATR-normalised trend | **Family closed** — both defend longs, tax shorts |
| P67/P68 | volatility / price regime detection | **Failed** — all causal and observable; 3 failures |
| P88 | adaptive ATR ceiling | **Closed.** Do not rerun — P49 already tested `cap_days` removal |

**The era-split pattern appeared 10 times (P56, P58, P66, P59, P60, P61,
P77, P84/86, P88, P95) and every one collapses under the half-year
partition or period control.** P87 found why: every era-split effect
**collapses** once the period is controlled, while the ATR ceiling **kept
91–99% of its gap.**

---

## PART 5 — THE TWO THINGS THAT MATTER MOST

### 1. The champion is not a position policy. (`P96`, `P97`)

```
v18:743  busy_until = candles_ltf[exit_idx]["date"]   -> "2026-09-30"
v18:577  if busy_until and bar_time <= busy_until:    -> "2026-09-30 14:00:00"
```

Python string compare: `"2026-09-30 14:00:00" <= "2026-09-30"` is **always
False**. The guard has never blocked a same-day re-entry.

| | shipped | **correct guard** |
|---|---|---|
| champion IS | 500t **+325.8R**, maxconc 6 | 395t **+137.7R**, maxconc 1 |
| champion OOS | 279t **+70.1R**, maxconc 5 | 230t **−13.3R**, PF 1.10 |

**58% of shipped IS R is unavailable to a bot whose guard works.** And the
fix **cannot be rescued by a slot queue** — `exp_max_concurrent` 1→8
returns one book, because the MTF/LTF re-entry sequence always holds the
only slot.

**Same defect in `btc_engine.py:693`, `v7_timecap.py`, `v8_3r_trail.py`,
`v9_conditional_cap.py`.** `v8_break_entry.py` already uses correct integer
index discipline, so this is a regression, not a missing feature.

### 2. 80% of the book is a losing sub-book nobody can explain. (`P94`, `P98`)

| | n | **NET** | PF |
|---|---|---|---|
| outlive cohort | 103 | **+481.6R** | 15.05 |
| **inside cohort** | **396** | **−156.9R** | **0.58** |
| champion | 500 | +325.8R | 2.38 |

**The champion books a −157R drag on 79% of its trades.** P95 shows *time
in the window*, not price, separates them. **Not adoptable** (circular,
0.81× M) — but it is the only live lead left.

---

## PART 6 — BLOCKED

| | |
|---|---|
| **Position sizing / live currency DD** | **Not answerable in this engine.** No size channel; sizing cannot change net R in R-units. |
| **Forward pass** | 12.5 days, **2 champion trades**. P63 needs 40–70 → **~March 2027.** Can rule out, never confirm. |
| **Bybit perp alt data** | Not on disk. Blocks Nemotron P6/P7. |
| **Live state, restarts, 1m replay** | Unvalidated. |

## PART 7 — NEXT

1. **Pre-registered causal `bars_to_window_end` threshold family** — P95's
   lead. Must fix the 16× unit bug first.
2. **Entry-attribution** — does the trail/window machinery produce most of
   +325.8R from *any* matched entry set?
3. **Why the champion books the −157R inside cohort.**
4. **Audit the live bot's guard** (`btc_engine.py:693`) — capital is at
   risk there, unlike the backtest.
5. **Do NOT rerun:** P49 cap removal, P88 adaptive ceiling, P64 ZigZag,
   P71 B1, P73/P74 FS hybrid.

---

**44 experiments. One shippable book, three open leads, and a
concurrency guard that has never once done the job it was written for.**
