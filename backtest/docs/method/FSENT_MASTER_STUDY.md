# FSENT MASTER STUDY — the complete record

Date: 2026-10-09. Every candidate registered, every arm tried, every correction.

**This is the single entry point.** It supersedes nothing above it; the detail
docs it links are the evidence, this is the argument.

---

# 0. TL;DR

The owner asked for a book that **never has a negative half-year**. The shipping
book has exactly one: `2025-H1` at **−0.69R across 60 trades**.

That cell was dissected, and the finding is that **it was never a broken regime.**
Mean trade −0.011R. 20 winners making +29.6R against 40 losers making −30.3R.
**3% of trades carry half the damage.** It is a coin flip that landed red.

And the book declaring it ships **`max_consecutive_losses = 3`**, which costs
73 trades and 64R to "fix" a −0.7R cell — because a 3-loss cutoff on a book with
a positive median trade stops the book immediately before the recovery trade that
follows every streak.

**Turning it off is worth +33R IS, +31R OOS, 73 more trades, ~2R more drawdown,
zero negative cells, and it is the only arm in the family whose period control is
positive AND powered in both eras.**

**And it already existed in the registry as `fsent_champ_long_nohalt`.** See §7.

---

# 1. The rule was the wrong tool

Applying "never negative" as a **hard filter on the half-year table** is what
produced three of the four candidate arms below — and one of them is a trap:

| arm | half-year table | period control |
|---|---|---|
| `biasmom05` | **clean, 0 negative** | **b = −0.94, t = −9.63 — FAILS** |
| `htf15` | clean, 0 negative | underpowered |
| `htfesmcl4` | clean, 0 negative | underpowered OOS |
| `mcloff` | clean, 0 negative | **powered, both eras** |

**A clean half-year table is not evidence.** `biasmom05` proves it: the trades it
admits are significantly **worse** than the ones it removes once the calendar is
controlled for. It removed `2025-H1` by deleting trades that were going to win.

**What works is a rule about behaviour during a losing run, not a rule about which
cells look clean.**

---

# 2. The candidate leaderboard

All 29 registered `fsent_*` books. **N** = in-sample net 2023-01→2026-09-13,
**O** = 2021-22 (NOT a holdout — reused data, see `OOS_IS_NOT_A_HOLDOUT.md`).

| book | n IS | N IS | dd IS | n O | N O | dd O | swing |
> ## ?? PINS UPDATED 2026-10-10
>
> The C15 window-gate bug was fixed and **every fsent pin in this document was
> re-derived**. The leaderboard below is current. Any figure quoted in the body
> text from before that date is the pre-fix measurement and is 0-5 trades stale.
> See `C15_START_SIDE_FIX.md`.
|---|---:|---:|---:|---:|---:|---:|---|
| \champ_long_htfesmcl4\ | 789 | +907.59 | 28.00 | 437 | +326.22 | 14.20 |
| \champ_long_mode_atr_low\ | 639 | +673.68 | 28.98 | 311 | +276.60 | 14.56 |
| \champ_long_mcloff_htf15\ | 558 | +615.85 | 15.13 | 296 | +279.98 | 11.45 |
| \champ_long_mode_union\ | 813 | +580.04 | 23.85 | 442 | +303.81 | 18.23 |
| \champ_long_mcloff\ | 573 | +566.20 | 15.13 | 334 | +274.36 | 14.16 |
| \champ_long_nohalt\ | 574 | +565.45 | 15.13 | 336 | +272.50 | 14.16 |
| \champ_long_htf15\ | 517 | +568.46 | 16.06 | 277 | +262.00 | 13.77 |
| \utcsat_trailhalf\ | 493 | +534.12 | 30.53 | 279 | +286.63 | 16.51 |
| \champ_trailhalf\ | 494 | +532.81 | 32.00 | 280 | +287.23 | 16.51 |
| \champ_short\ | 531 | +573.47 | 25.85 | 309 | +239.31 | 23.87 |
| \champ_long_mode_fd\ | 526 | +533.34 | 13.42 | 295 | +277.50 | 12.18 |
| \utcsat_short\ | 529 | +564.92 | 25.92 | 308 | +229.43 | 24.76 |
| \champ_long_mode_flip_quality\ | 525 | +535.28 | 13.42 | 294 | +248.61 | 11.88 |
| \champ_long\ | 526 | +533.87 | 13.42 | 311 | +243.80 | 11.88 |
| \champ_long_causalfloor\ | 513 | +526.63 | 13.62 | 306 | +233.68 | 11.88 |
| \utcsat_long\ | 522 | +513.57 | 19.44 | 308 | +244.84 | 11.88 |
| \champ_long_biasmom05\ | 485 | +499.91 | 13.42 | 287 | +216.93 | 13.66 |
| \sig_multi\ | 329 | +479.78 | 13.39 | 193 | +218.63 | 7.64 |
| \sig_trail_delay1\ | 199 | +414.11 | 13.34 | 124 | +179.51 | 7.54 |
| \sig_full\ | 234 | +291.02 | 10.78 | 153 | +190.72 | 6.96 |
| \sig_half_crossed\ | 97 | +332.15 | 9.08 | 63 | +140.99 | 7.26 |
| \sig_fs_mom\ | 235 | +262.29 | 10.05 | 152 | +165.62 | 9.14 |
| \sig_wk_pause_short\ | 302 | +206.87 | 10.60 | 179 | +128.77 | 10.53 |
| \sig_decay_crossed\ | 104 | +186.83 | 8.64 | 67 | +128.17 | 7.39 |
| \sig_sw10_short\ | 369 | +174.30 | 16.62 | 239 | +100.74 | 11.82 |
| \sig_sw20_short\ | 343 | +146.94 | 32.46 | 202 | +96.42 | 10.23 |
| \sig_sw20_short_wr\ | 343 | +146.94 | 32.46 | 202 | +96.42 | 10.23 |
| \sig_sw10_long\ | 354 | +117.53 | 21.07 | 229 | +81.06 | 13.53 |
| \both_trail_half\ | 254 | +76.58 | 31.43 | 142 | +96.91 | 14.81 |
| `fsent_dirmatch_long` / `_short` | — | (no pins) | | | | | |

---

# 3. The complete experiment ledger

Everything tried this cycle, with its verdict. **Nothing here is a guess** — each
row is a measured arm.

## 3.1 Causality — the owner's "must"

> "i wanna make sure that each trade are after fs of the prev swing this is must"

| check | what it asserts |
|---|---|
| **C1** | entry ≥ the FS print of **its own swing** |
| **C2** | the swing the **stop** came from had already printed FS |
| **C3** | the **HTF window** had already opened — the C17 shape |

**0 violations, 6 books, both eras.** Every FS trade joins exactly by `swing_no`
(352/352 IS, 206/206 OOS shipping) — not a nearest-timestamp heuristic, which is
the only kind of join that could hide the bug. Largest entry→`window_end` lead is
380.5h, so nothing trades on a window boundary. The audit **exits non-zero on any
violation**.

**The audit reported 184 violations on its first pass, and the audit was wrong.**
Every violation was exactly −19800s = 5h30m. `entry_ts` is a UTC epoch,
`fs_at_time` is naive IST. Parsing both as UTC put every FS print 5½ hours in the
future. **An audit that mis-reads the timezone cries wolf on the one question
that matters most here.** The fix asserts `entry_ts + IST_OFFSET == entry_date` on
every trade and **aborts rather than reporting a verdict**.

→ `FS_CAUSALITY_AND_HTF_EXPERIMENTS.md`

## 3.2 HTF leg length — `min_bars`

Current HTF is `min_bars=10` → 1601 swings; 15 → 1479.

| min_bars | read |
|---|---|
| 30 | +847.3R — **rejected as an isolated spike**, no plateau around it |
| **13–15** | **genuine plateau**, registered |
| 15 | IS +567.57 / DD 17.28 · OOS +254.88 / DD 16.86 · **0 negative** |

→ `HTF_SWEEP_OWNER_RULE.md`

## 3.3 HTF leg strength — `exp_bias_momentum_min`

A floor on **this 1h leg's magnitude ÷ the previous leg's**. Already runs at 0.8
on every `sig_*` book and is OFF on every `champ_*` book. Never swept on champ.

| value | champ net | dd IS | neg | sig_multi net | dd IS | neg |
|---|---:|---:|---:|---:|---:|---:|
| OFF | +773.0 | 13.4 | 1 | +739.5 | 16.3 | 0 |
| 0.5 | +718.6 | **13.4** | **0** | +672.9 | 15.3 | 0 |
| **0.8** | +660.6 | 13.6 | **0** | **+704.4** | **13.4** | 0 |
| 1.0 | +516.0 | 12.0 | 0 | +605.1 | 12.0 | 0 |
| 1.2 | +421.0 | **9.9** | 0 | +561.0 | 10.3 | 0 |

**Registered `biasmom05` (0.5)** — in-sample DD **13.42R, exactly the parent's**,
the only arm that fixes the cell without paying in drawdown. **And it FAILS the
period control at b = −0.94, t = −9.63.** Registered with that recorded.

## 3.4 HTF window opens on FS — the owner's ask

The LTF plane enters at the swing FS (`exp_fs_entry_side`). The HTF plane enters
on the **break**. Measured gap: the HTF window opens a **median 25h after** its
own direction's FS (p75 55h, max 355h); **only 1 window in 528 opens exactly on
its FS.** A real asymmetry.

`exp_htf_fs_entry` routes the HTF side through the `fs_long`/`fs_both` machinery
already in `btc_engine.py:151`.

| arm | net | dd IS | neg |
|---|---:|---:|---:|
| champ off | +773.0 | 13.4 | 1 |
| **champ + htf_fs=all** | **+1199.9** | 19.8 | **1** |
| htf15 off | +822.4 | 17.3 | **0** |
| htf15 + htf_fs=all | +1222.2 | **29.6** | **1** |
| sig_multi off | +704.4 | 13.4 | **0** |
| sig_multi + htf_fs=all | +948.3 | 17.7 | **1** |

**`flip` mode measured IDENTICAL to off** — the shipping books never read the flip
bucket. A knob that does nothing is a measurement, not a bug.

**Why it fails:** 95% of the gain sits in windows the book was not trading before;
trades per window go 2.82 → 5.78. `all` collapses flip/decisive/b2 into one
`fs_entered` set, so **the configuration that scores best is the one that stopped
distinguishing regimes.** Causality is clean (0 windows start before their FS,
`window_start − FS` exactly 0.0h) — **rejected on the merits, not on lookahead.**

**Combined with `mcl=4` it does clear every cell** — that is `htfesmcl4`, the
ceiling: IS +917.80 at DD 27.74, at the budget, bought mostly by admitting 528 new
trades, OOS effect underpowered (b = +0.03, t = 0.05).

→ `HTF_FS_ENTRY_REJECTED.md`

## 3.5 Stacking — the recurring shape

| combination | result |
|---|---|
| `htf15` + `biasmom 0.5` | +776.6 at ddIS 21.6 — **worse than `htf15` alone** (+822.4 at 17.3) |
| `biasmom05` + `htf_fs` | +822.5, ddIS 15.06 — the best of the narrow branches |
| `htf_fs` + `mcl=4` | the ceiling, but degenerate regime set |

**Two filters on the same cause do not add.** Both HTF knobs fix the weak 1h leg;
stacking them removes more than it removes. This is the same shape as every
stacking result in the repo's history.

## 3.6 Risk knobs

| knob | read |
|---|---|
| **`max_consecutive_losses`** | **the whole negative-cell story — see §4** |
| `cooldown_bars` | 8 optimal; **0 is catastrophic, ddIS 51.39** |
| `chop_thresh` | **DEAD.** 46→70 byte-identical on both books. Sits in every champ book reading like a live risk control and does nothing |
| `exp_persist` | 5 marginally better, 7 fine |
| `atr_high_thresh` / `atr_low_thresh` | the `atr_low` / `fd` modes |
| `exp_no_opposite` | available, default off, **never applied to a candidate** |
| `exp_min_sl_pct` | available, default off — dismissed, capital sizing not signal |

## 3.7 Concurrency and multi

`fsent_sig_multi` = `fsent_sig_full` with `max_positions` 1→0 and nothing else.
50 extra 2021-22 trades, 48 while a position was open, 47 same-direction;
+25.1R gained, −0.3R missed. Serial parent net +255.7R → multi +280.5R.
→ `SIG_MULTI_STUDY.md`, `SIG_MULTI_REGISTERED.md`

## 3.8 Forward

26 days, 2026-09-13 → 2026-10-09. `sig_multi` 5t −1.26R, `champ_long` 4t −0.93R,
old four 6t −5.06R. **Every candidate reads NO VERDICT (n<50).**
→ `FORWARD_TEST_PLAN.md`

---

# 4. `max_consecutive_losses` — the finding

| value | n | net | ddIS | **neg cells** |
|---|---:|---:|---:|---:|
| **0 (off)** | **912** | **+837.5** | 15.13 | **0** |
| 1 | 645 | +546.1 | **35.01** | **3** |
| 2 | 793 | +732.9 | 19.82 | 1 |
| **3 (SHIPPED)** | 839 | +773.0 | 13.42 | **1** |
| 4 | 872 | +817.1 | 15.06 | **0** |
| 6 | 897 | +783.9 | 14.78 | **0** |

**The cutoff is not protecting the book — it is cutting winners.** It costs 73
trades and 64R to buy a −0.7R cell, because it stops the book immediately before
the recovery trade that follows every streak.

**`limit=1` is the trap:** triples drawdown to 35R *and* creates three negative
cells. Cutting the book hardest is the worst setting.

## Period control — P87 instrument, the ranking that matters

`R = a + b·cohort + half-year fixed effect`, clusters = half-year, cluster-robust
SE, 4000-draw bootstrap. MDE printed with every null.

| arm | IS b (t) | OOS b (t) | verdict |
|---|---|---|---|
| **`mcl=0` / nohalt** | **+1.21 (3.37)** | **+1.86 (3.97)** | **SURVIVES + POWERED** |
| `mcl=4` | +0.06 (0.18) | +1.03 (1.62) | survives, underpowered |
| `htf_fs=all` vs sig_multi | +0.37 (0.59) | +0.12 (0.21) | 2/2, underpowered |
| `htf_fs=all` vs champ | +0.59 (2.28) | −0.06 (−0.10) | 1/2, underpowered |
| `htf15+htf_fs` | +0.55 (1.97) | −0.26 (−0.42) | 1/2, underpowered |
| `biasmom05+htf_fs` | +0.46 (1.43) | −0.42 (−1.06) | 1/2 |
| **`biasmom05`** | −0.23 (−0.37) | **−0.94 (−9.63)** | **SIGN FAILS** |

→ `MAXCONSEC_LOSSES_FINDING.md`

## The autopsy

| book | cell | n | net | mean/trade | worst-N conc. | streak |
|---|---|---:|---:|---:|---:|---:|
| `champ_long` | 2025-H1 | 60 | **−0.69** | −0.011 | **3%** | 7 |
| `champ_long`+htf_fs | 2022-H2 | 88 | −4.76 | −0.054 | **3%** | 9 |
| `sig_multi`+htf_fs | 2026-H2 | 19 | −7.01 | −0.369 | 21% | 4 |

**Every one is diffuse.** No single bad trade exists to remove.

---

# 5. Corrections log

Errors made in this cycle, and what was done about them.

| # | error | impact | resolution |
|---|---|---|---|
| 1 | causality audit parsed IST as UTC | reported **184 false violations** on the shipping book | fixed, TZ self-test now aborts rather than reports |
| 2 | period control read `per_h[c][0]` | **"better in 2 of 6 years" was the first trade's R** | re-run with P87; number **withdrawn** in `HTF_FS_ENTRY_REJECTED.md` |
| 3 | htf15 base used the wrong swing | period control printed "IDENTICAL SET" | re-run against the true `sw10` parent |
| 4 | `htf_fs` "new windows" % labelled +66% | 206 windows vs 297 is a **different set**, not +66% | corrected in the autopsy output |
| 5 | `biasmom05` recommended on a clean half-year table | **b = −0.94, t = −9.63** | withdrawn; stays registered with the failure recorded |

**Two of these five would have recommended a book that loses money.** The
half-year table is not a test, and a timezone bug in a causality audit is worse
than no audit.

---

# 6. Doc index

| doc | what it holds |
|---|---|
| `FS_CAUSALITY_AND_HTF_EXPERIMENTS.md` | the 3-check audit, the TZ bug, HTF knob comparison |
| `MAXCONSEC_LOSSES_FINDING.md` | the negative-cell autopsy, period control, the mcl finding |
| `HTF_FS_ENTRY_REJECTED.md` | window-opens-on-FS, with its withdrawal |
| `HTF_SWEEP_OWNER_RULE.md` | `min_bars` sweep, plateau vs spike |
| `REGIME_ROBUSTNESS_12_CELLS.md` | the 12-cell table, HTF/LTF definitions |
| `SIG_MULTI_STUDY.md` / `SIG_MULTI_REGISTERED.md` | the multi book |
| `FORWARD_TEST_PLAN.md` | the pre-registration contract |
| `OOS_IS_NOT_A_HOLDOUT.md` | why 2021-22 is not forward evidence |
| `PRUNE_BOOKS.md` / `BOOK_ARCHIVE.md` | 85 retired keys |

---

# 7. ⚠️ The book already existed

`fsent_champ_long_nohalt` has been in the registry with **`max_consecutive_losses = 0`**,
pins 575 / +566.60 / 15.10 / 337 / +270.90 / 14.20.

My `fsent_champ_long_mcloff` is 575 / +566.58 / 15.13 / 337 / +270.91 / 14.16 —
**the same book within 0.02R.** The only differences are `ext_stop_r` 0.0 vs 3.0
(provably inert since C17) and two explicit-vs-inherited keys.

**So the "discovery" was a re-discovery.** What was genuinely missing was not the
book — it was the **period control and the autopsy connecting it to `mcl=3`**.
Nobody had asked why the negative cell existed.

That is the actual lesson of this cycle, and it is not a flattering one:

> **A candidate can be registered and still be misunderstood.** `nohalt` sat in
> the registry with a one-line description and no evidence attached. A book is not
> understood until it has a period control and an autopsy behind it.

Both entries are kept, since the pins differ slightly and `mcloff` states
`ext_stop_r=3.0` explicitly. **They are the same candidate.**

---

# 8. What is NOT settled

1. **No arm has forward evidence.** The window is 26 days; every candidate reads
   NO VERDICT. `mcloff`/`nohalt` has the strongest historical case in the family
   and has never been scored on unseen data.
2. **The period control compares to the parent, not to zero.** A book that is
   meaningfully better than `champ_long` can still be negative in an unseen
   half-year. "0 negative cells in 12" is 12 observations, not a guarantee.
3. **`mcl=0` is a risk decision, not a signal decision.** It raises concurrent
   exposure exactly when the book is doing worst. Fine at 15R drawdown, not
   obviously fine at 29R. The signal evidence is unambiguous; the sizing
   consequence is the owner's call.
4. **`exp_no_opposite=1` was never applied to any candidate.** 12 opposite
   overlaps exist (8 IS, 4 OOS), mostly scratch losers, worth roughly +0.9/+1.0R.
5. **`chop_thresh` is dead code** that reads like a live control. Either wire it
   up or delete it.
6. **`htf15` and `htfesmcl4` were discovered after the current forward window was
   scored.** Adding them now burns the window.

---

*Shipping book unchanged: 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS,
one negative half-year, `max_consecutive_losses=3` untouched.*
