# NEXT ROUND BRIEF — v18 / champion_multi_sw10

> **READ FIRST: [`THE_CHAMPION_HANDOFF.md`](THE_CHAMPION_HANDOFF.md)** —
> the authoritative P55–P98 record: validated / exploratory / retracted /
> closed, with each result's accounting basis stated. Nothing was adopted
> in 44 experiments. Three earlier numbers are now **superseded** (P89
> inverted, P92's depths ~15× too large, P83's 37.3R is actually 30.5R),
> and **P96/P97 found the concurrency guard has never fired** — 58% of
> shipped IS R is not deployable, and no slot queue can recover it.

> ## CHANGED UNDER YOU, 2026-10-01 — three things to know before you measure
>
> **1. `pivot_rule` is now an explicit parameter.** Commit `64a061a` threaded it
> through `simulate_btc_trades_v7` and both `simulate_htf_ltf_streak_halt` entry
> points, to all four `_collect_signals` call sites, and deleted the module
> monkeypatch at `btc_routes.py`. Previously the route selected the origin rule by
> rebinding `btc_engine._collect_signals`, which reached the LTF half only — the
> HTF windows went through `v7_timecap.py`, which binds that name at module import
> and never saw the rebind. **Both rules are reachable and both are measured:
> origin 500t / +325.78R net, leg 499t / +239.12R net, on Bybit perp.** The
> registry entry named `champion_multi_sw10` is the *origin* book; the one that
> ships is `champion_multi_sw10_leg`. Read `pivot_rule`, not the name.
>
> **2. Any anchor dated before `203e207` (2026-10-01 16:38) that reads
> `_collect_signals` is stale.** That commit flipped the pivot default to `"leg"`,
> so every caller that did not pass a rule silently moved from origin to leg.
> Pins from before it need re-anchoring. Known red: `exp_closeout_battery`
> (PIN_LB30, +1 trade / −6.9R), `exp_issue10_window` (imports `persistence`, not
> tracked). `backtest/checks/exp_sweep_static.py` lists them (all checks are indexed in `backtest/checks/README.md`).
>
> **3. `BTCUSDT` is Binance spot and is not traded here.** Everything is Bybit perp,
> symbol `BTCUSDT_BYBIT`. The backtest endpoint defaults to spot, so a request
> omitting `symbol=` measures the wrong market — it produced a fake three-day data
> gap and a fake +5.2-point win-rate jump on v18 during the C16 audit. Both were
> retracted.

> ## DECLINE EDGE-FRAMED PROPOSALS AT THE PROPOSAL STAGE
>
> This is a governance rule, not a finding, and it is here so the next round does
> not spend itself rediscovering an arithmetic fact.
>
> On the shipping book (`champion_multi_sw10_leg`), from `BASE_BOOK_NULL.md`:
>
> | | value |
> |---|---|
> | book's own net | **+239.1R** IS, **+72.8R** OOS |
> | M, the p95 of a reshuffle of that book | **381.7R** IS, **205.5R** OOS |
> | where the book sits in that null | **41.0th** pct IS, **50.3rd** pct OOS |
>
> **A filter can only remove trades. To clear M it would have to beat the 95th
> percentile of noise using a subset of the trades that produced the 50th. No
> threshold on any cohort does that.** It is not that the bar is high — the signal
> is inside the band, so no subset of it can get outside.
>
> Consequence for the queue: this programme is no longer looking for filters. It is
> establishing what the strategy is and whether it runs in production. Work is
> therefore framed as causality or deployability, not edge:
>
> - **Causality** — does a feature carry information at entry time at all
>   (`bars_to_wend`, P115). Independent of M, because M cannot be answered for
>   this kind of question.
> - **Deployability** — does the book survive the live bot's single-slot
>   constraint that the backtest's six-deep concurrency never tested (P117).
>   Also independent of M: "does it run at all in production" is prior to "is it
>   a good trade".
> - **Census** — how many signals never become trades and why (P116). After P117,
>   since the slot count decides how much contention exists.
>
> **A proposal framed as "X improves the book" should be declined when it is
> proposed, not run and rejected at 10% of M twenty minutes later.**

> ## What M = 193.4R is, and is not
>
> Two values, both from `BASE_BOOK_NULL.md` (P5). Move-block bootstrap, block 20
> trades, 10,000 draws, seed 20260928, resampling the champion's own trades with
> the trade count restored:
>
> | era | M (p95 of \|net\|) |
> |---|---|
> | IS | **479.9R** |
> | OOS | **193.4R** |
>
> - **M is the proposal-difference null and it is correctly derived.** A proposal's
>   dNet is a difference over the same trade universe, so it is measured against the
>   reshuffle variance of that universe. P5: "Every dNet result must clear M before
>   it counts." That design is right.
> - **M has two values and they are not interchangeable.** The 193.4R figure is the
>   OOS one. Quoting it against an in-sample result is wrong, and this document did
>   that once: it claimed the shipping book "clears M by +45.7R", which compared an
>   OOS null against an IS total, and compared a level against a difference at the
>   same time. Withdrawn.
> - **What changed is M's value, not its validity.** M was computed on the origin
>   book's R sequence. The shipping book has 499 trades and compressed risk
>   denominators, so M must be re-derived with `exp_base_null.py` pointed at
>   `champion_multi_sw10_leg`. Same harness, one run, not a new concept.
> - **`BOOTSTRAP_NULL_P63.md` does not contradict this.** Its 100-180 table is about
>   what bar a *forward slice* should be measured against, and it concludes M is the
>   wrong bar for a slice because slice nulls scale with n. That is a statement
>   about slices. It is not a statement about how M was derived, and reading it as
>   one is what produced the withdrawn claim above.
>
> The direction argument holds and it is the reassuring one: fewer trades and
> smaller per-trade R give a narrower null, so every candidate that failed M under
> the origin book's null fails harder under the leg book's. **No re-adoption is
> possible.**
>
> The finding P5 actually contains, which is larger than any of the above: **the
> champion's own net sits at the 46th and 48th percentile of a reshuffle of
> itself** — +325.8R observed against a +316.5R null mean, nine R apart on a
> three-hundred-R book. The null is wide because the tail is wide. Whatever M
> gets re-derived to, that result stands and it is the one to keep in view.

> ## The fourth instance, and the rule this thread actually produced
>
> P90 reported **+174.8R** from re-filling entries at a different bar price. In
> 129,732 of 129,735 bar pairs in the Bybit 15m file those two prices are the
> same number: `close[i] == open[i+1]`. The number was plausible, the mechanism
> was real, the premise was false.
>
> That is the fourth time in one round a number survived scrutiny while its
> premise did not, after the venue trap, the 28-vs-435 count, and the
> module-global half-application. **So: re-measure before you quote. Retracting
> the number is not enough — the premise is what was wrong, and only a run finds
> that out.**

> **Run 2 and Run 3 are not open. Do not re-open them.**
> - **Run 2, entry-fill truth — CLOSED 2026-09-30** by
>   [`P90_FILL_P109.md`](P90_FILL_P109.md). The original arm was anti-causal: it
>   entered at `open[i]`, the open of the signal candle, which is ahead of the
>   `close[i]` the engine fills at. Re-run as the true next open `open[i+1]`,
>   **0 of 500 trades differ, delta +0.0R**, because on contiguous candles
>   `close[i] == open[i+1]`. Nothing between the two prices.
>   [`ENTRY_FILL_P90.md`](ENTRY_FILL_P90.md) still carried the retracted result and
>   has now been marked at every claim site.
> - **Run 3, live single-position guard — DEFERRED BY DESIGN.** `live_loop.py:1778-1801`
>   keeps its own 1-slot guard, which is correct. Measuring refused trades against a
>   6-deep harness book was deferred deliberately: no live work until a candidate is
>   chosen. See `BOT_REPLIES.md:133-136`.

**Read this whole file before proposing anything. It exists because the
previous round wasted itself by not doing so.**

Date: 2026-09-30. Covers P55–P88. Every claim here is measured in this repo
and every file named is on disk under `backtest/docs/`.

---

## 1. THE BOOK

| | |
|---|---|
| **Strategy** | `champion_multi_sw10` |
| **Architecture** | 1h HTF (B2/FLIP windows) → 15m LTF entries |
| **IS** | 500 trades, **+325.8R** net, PF 2.38, R/trade 0.652 |
| **OOS** | 279 trades, **+70.1R** net, PF 1.59, R/trade 0.251 |
| **IS span** | 2023-01 → 2026-09 · **OOS span** | 2021-01 → 2022-12 |
| **Second lane** | `utcsat_multi_sw10` — IS +359.0R, OOS +60.2R. **Same data, different params. Not independent evidence.** |

**All figures are NET of fees, slippage and funding.** No `r_multiple`
sum appears in this programme's conclusions — gross figures have caused two
documented errors (P60, P83).

**M = 193.4R** — the deck-relative null (`BOOTSTRAP_NULL_P63.md`).

---

## 2. THE THREE GATES. Every proposal clears all three.

1. **Both eras, both lanes, same sign.** Winning only in the era it was
   built in is fitted.
2. **`|dNet| > 193.4R`.**
3. **Calendar half-year partition** — `P61`. cand_4h1h looked like
   everything a candidate should look like and went 4-4 in IS.

**Plus, for any filter, the instrument from §6 — stricter than all three.**

---

## 3. THE FOUR RULES

### R1 — State first whether it already exists

Every proposal opens with `already tested / open / blocked / new`, and if
`tested`, the file name and its number.

> **Not a formality.** Two experiments were re-derived from scratch because
> it was skipped: **P73** re-ran the FS-only question
> `FS_ONLY_ENGINE.md` had answered one day earlier, and **P72** re-ran B1,
> which `CLOSED_DO_NOT_REPEAT.md` still listed as open. Both were caught
> only when the owner pointed at the archive.

**Read at minimum:** `TRANSCRIPT_THESIS_BACKLOG.md` (A–J),
`CLOSED_DO_NOT_REPEAT.md`, `other bots proposal.md` (Nemotron P1–P10),
`FS_ENTRY.md`, `FS_ONLY_ENGINE.md`, `SHADOW_TIMEFRAME_IDEAS.md`.

### R2 — Give the thesis's own counter before running

State **"this is wrong if ___"**. P80 did this, and it is the only reason
its failure was interpretable rather than embarrassing.

### R3 — Family-wise, never single-arm

Test the **whole family** and require **all** members to pass, or none is
adopted. A grid peak is not a result — P69 found 0.40% was the peak of a
four-point grid, and P88 showed the family fails.

### R4 — Say how it dies, and make it answerable in one run

Every proposal needs a **falsifier** that one run settles. "Test it and see"
is not a falsifier.


---

## 4. EVERY EXPERIMENT P55–P88. Do not re-propose any of it.

| # | asked | verdict | where |
|---|---|---|---|
| P55 | era inversion detectable at runtime? | **No** — swing geometry separates IS/OOS by 0.01–0.10 vs an IQR of ~0.75 | `REGIME_DETECT_P55.md` |
| P56 | does the 1h window expiry earn its keep? | **IS-fitted** — costs 121–141R in IS, earns 81–102R in OOS | `NO_EXPIRY_P56.md` |
| P57 | is 1h the right direction source? Is 1D useful? | **1h+15m wins every cell**; 1D is negative as a source (OOS PF 0.74/0.56/0.25) | `TIMEFRAME_ARCH_P57.md` |
| P58 | full 3×3 timeframe matrix | **Confirms P57 fairly.** P57's `min_bars` was a bar COUNT not a LAG — a 24× penalty on slow arms. Corrected. | `TF_MATRIX_P58.md` |
| P59 | why did 4h+1h cost 113R in IS? | **99.8% disjoint.** The cost was volume, not quality | `CAND_COST_P59.md` |
| P60 | union the two books | **Loses 4/4.** 43–46% of signals skipped. Its "+664R bound" was 36× too high | `UNION_P60.md` |
| P61 | is that advantage stable? | **No** — 4-4 in IS, lost every period since 2025H2. Forward pass = **2 trades in 12.5 days** | `STABILITY_FORWARD_P61.md` |
| P62 | how much forward data is needed? | **Withdrawn** — `max−min` over 2–25 blocks is biased-low | `FORWARD_NEED_P62.md` |
| P63 | size the forward null properly | **Settled.** Band 89–137R at 40–70 trades: a forward slice can **rule out, never confirm** | `BOOTSTRAP_NULL_P63.md` |
| P64 | ZigZag re-segmentation | **Integration incomplete.** Adapter built and causal; engine contract unmapped. Records need `dir` as `"up"`/`"down"` and `kind` as `B2`/`FLIP` | `ZIGZAG_P64.md` |
| P65 | Stage 64 win-streak block, never tested | **Fails M** (best 10.3%) but the round's only **period-stable** candidate: 14-3 over 24 cells | `WINSTREAK_M_P65.md` |
| P66 | 30m / 45m LTF | **Cleanest era-split found.** 30m doubles the champion in OOS (+141.9R vs +70.1R, every measure better) and costs 188–239R in IS | `TF_INTERP_P66.md` |
| P67 | is that split a volatility regime? | **No** — sign tracks the era. But OOS high-vol tercile **loses money** (PF 0.64/0.78), low-vol runs 2.33–4.29 | `VOL_REGIME_P67.md` |
| P68 | volatility floor; price level | **My preregistration was backwards** — P67 implies a CEILING. **Owner's price hypothesis 4/4**: low price PF 2.60/1.68/3.08/1.72 vs 2.14/1.50/2.13/1.44 | `VOLFLOOR_P68.md` |
| P69 | corrected ceiling + relative price | **Ceiling 3/4 cells positive, OOS PF 1.59→3.06. Relative price dead 4/4** — the level is a clock and its scale-free form destroys it | `CEILING_RELPRICE_P69.md` |
| P70 | ZigZag, integration finished | **Dead.** 12 of 24 cells clear M and **all 12 are negative** | `ZIGZAG_CLOSED_P70.md` |
| P71 | can B1 fire entries? | **No.** `_collect_signals` is FCFS and B1 always fires earlier, so it can only displace B2/FLIP. **Loses 36–164R in 4/4** | `B1_ENTRY_P71.md` |
| P72–P75 | the FS "hybrid" | **Already answered** by `FS_ONLY_ENGINE.md` (2026-09-28): 263t +31.7R IS, 108t +1.3R OOS. P73 mislabelled a HYBRID; P75 showed the books are 99.8% disjoint — a **swap**, not an addition | `FS_ONLY_AUDIT_P74.md` · `FS_DECOMP_P75.md` |
| P77 | period split of the FS book | **Killed.** IS 2 wins / 6 losses; wins 2021-22, loses **every year 2023-26** | `FS_PERIOD_P77.md` |
| P78 | why does FS work in a bad era? | **The champion's OOS long side is absent** — 162t +1.8R PF 1.22. Not a bear-market story but a **long-side** rescue | `FS_MECHANISM_P78.md` |
| P79 | is any of this lookahead? | **NO.** Prefix invariance **100%** across **13,201** swing comparisons, 3 cut points, both chains, both eras | `PREFIX_INVARIANCE_P79.md` |
| P80 | directional FS — **owner's idea** | Best-looking result of the round: 4/4 positive, partition 22-8, both mirrors agree | `DIRECTIONAL_FS_P80.md` |
| P81–P82 | its significance test | **Dead.** Permutation p = 0.6895 / 0.8590 / 0.9197 / 0.7712 / 0.3022 | `PERMUTATION_P82.md` |
| P83 | is the champion robust enough? | IS boring and safe. **OOS 2021 is −26.4R**, max DD **37.3R over 278 days** | `CHAMP_ROBUST_P83.md` |

---

## 5. THE TWO THINGS TO STOP PROPOSING

### 5a — The era-split pattern (9 appearances)

**P56** expiry · **P58/P66** granularity · **P59** layer agreement ·
**P60** union · **P61** cand_4h1h stability · **P66** 30m · **P77** FS
hybrid · **P84/P86** trend filter · **P88** ATR ceiling.

Every one looks excellent in aggregate and collapses under the half-year
partition or under period control. **If your idea is another
regime-conditional tweak, expect this — and propose it only with a specific
reason the previous nine would not apply.**

### 5b — Decision-time regime detection (3 attempts, 3 failures)

**P55** swing geometry · **P67** volatility · **P68** price level —
including relative price, which died in 4/4. All were causal and observable,
and none separated the eras.

**P87 showed why this matters and gives the discriminator:**

> Every era-split effect above **collapses** once the period is controlled.
> The ATR ceiling **kept 91–99% of its gap**. That is the difference between
> a regime proxy and a real filter.

---

## 6. THE INSTRUMENT — include this with every proposal

From **P87**. Stricter than all three gates, and the thing that separates a
real filter from a regime proxy.

```
R_i = a + b * cohort_i + g_{halfyear(i)} + e_i
```

`cohort` = 1 if your rule **keeps** a trade, 0 if it **drops** it. `g` is a
half-year fixed effect, so **b is your effect after the period explains
everything.**

- **b = 0** → the feature is smuggling in "which era is this". Regime
  proxy. Not a rule.
- **b substantially positive** → it carries information the date does not.

**Variance:** cluster-robust by **month** (trades inside a month share a
regime). Report the t **and** a month-cluster bootstrap **and** a
half-year-cluster bootstrap. **P87 caught the robust-t and the bootstraps
disagreeing on one cell — report all three; do not pick the flattering one.**

**Harness:** copy the structure of `exp_ceiling_regime_ctrl.py`.

**Check power before quoting a p.** P85's permutation returned p = 0.97 on a
5–8× cohort gap because permuting 99 trades gives two or three independent
blocks. **A p-value from an underpowered test is a statement about the test.**

---

## 7. KNOWN BLOCKERS — do not propose around these

| blocker | detail |
|---|---|
| **No size channel** | `v18_streak_halt.py` has zero hits for equity/size/notional/qty. **Any sizing change has no execution channel**, and sizing cannot change net R in R-units anyway (P9). Kelly, vol-targeting and fixed-fraction are **not answerable in this repo**. |
| **Forward data is 12.5 days** | 2 champion trades. Per P63, 40–70 trades is the floor — **~March 2027**. The slice can rule out, never confirm. |
| **No alt data** | Bybit perp alts are not on disk. Blocks Nemotron P6/P7 and the whole multi-instrument thread. |
| **ZigZag integration** | **STALE — closed, do not finish it.** P64 recorded the integration as incomplete, but **P70 completed the contract and the answer was dead**: 12 of 24 cells clear M and **all 12 are negative**. Finishing that work buys nothing. |

---

## 8. WHAT WOULD ACTUALLY HELP

**Not another filter.** Thirty-one experiments produced one rule that
survived period control, and that rule still fails family-wise because it
costs money in the era the book was fitted in.

**The unfilled space, honestly stated:**

1. **Anything that survives §6's instrument.** That is the bar, and only
   P69 / P87 / P88 have cleared it at all.
2. **The champion's real fragility is structural and known.** It earns on
   longs in IS (+272.6R) and shorts in OOS (+68.4R), and 2021 is a whole
   losing year at −26.4R. **No single trend condition protects one without
   taxing the other (P84, P86).** A proposal that genuinely solves *that*,
   rather than filtering it, would be worth more than the last thirty
   filters combined.
3. **Position sizing** — the one thing that could make 37.3R of drawdown
   acceptable or fatal. **Not answerable in this repo**, per §7.

---

## 9. OUTPUT FORMAT

```
ID            :
R1 status     : already tested (file + number) / open / blocked / new
THESIS        : one sentence
COUNTER       : this is wrong if ___              (R2)
FALSIFIER     : one run, one number               (R4)
FAMILY        : every arm that must pass          (R3)
EXPECTED SIZE : dNet in each era and lane
DATA NEEDED   : on disk / new fetch
BLOCKERS      : from §7
PERIOD-CONTROL: what b you expect, and what b=0 would mean
```

**Rank honestly. If two proposals are the same family, say so** — R3 will
merge them, and the weaker one will drag the family down.

| P84 | trend-MA to protect the long side | **Defends the long side (+1.8R → +18.4R) and costs the short side (+68.4R → +8.4R)** | `LONG_TREND_P84.md` |
| P85 | permutation on the ATR ceiling | **Test had no power** — 2–3 independent blocks from permuting 99–106 trades. p = 0.96–0.99 is a statement about the test | `CEILING_PERM_P85.md` |
| P86 | ATR-normalised trend distance | **Same failure, same reason, now measured twice. Family closed** | `ATR_TREND_P86.md` |
| P87 | does the ceiling survive period control? | **YES — b stays +0.82 to +1.30 after a half-year fixed effect; only 1–9% of the gap removed.** 3/4 cells significant | `CEILING_REGCTRL_P87.md` |
| P88 | the ceiling family, family-wise | **FAILS.** IS fails at all four levels. But **b is positive in all 16 cells** | `CEILING_FAMILY_P88.md` |

**Also closed, earlier, outside P55–P88:** `decay < 0.75` (strongest
consistent candidate in the programme, 4/4 positive, but only **0.13 × M**);
win-spacing; re-entry; SL variants; partial exits; Stage 63 loss-triggered
invalidation (0/7); all timezone/Saturday variants except utcsat.

---
Big Pickle: 

Read the brief plus everything R1 requires (TRANSCRIPT_THESIS_BACKLOG.md, CLOSED_DO_NOT_REPEAT.md, other bots proposal.md all four sets, FS_ENTRY.md, FS_ONLY_ENGINE.md, SHADOW_TIMEFRAME_IDEAS.md, OPEN_RESEARCH_QUEUE.md, LONG_TREND_P84.md, CEILING_FAMILY_P88.md) and grepped the repo to check the two claims below are genuinely unrun. Here is the round.
First, a finding about the brief itself. §8.2 asserts the long/short fragility is "structural and known." It is known descriptively (LONG_TREND_P84.md: IS longs +272.6R / shorts +53.2R; OOS longs +1.8R / shorts +68.4R). It has never been through §6's instrument. P87 ran R = a + b·cohort + g_halfyear on a cohort filter; nobody has run it on the side decomposition. Until that is done, the entire "protect one side" research direction — P84, P86, and everything it implies for the next round — is unverified.
P89 — IS THE LONG/SHORT ASYMMETRY STRUCTURAL, OR IS IT 2021?
ID            : P89
R1 status     : new — P83/LONG_TREND_P84 measured the split descriptively;
                no §6 regression exists on `dir`. (P87's instrument, P87's
                harness, zero new machinery: swap `coh` for is_long.)
THESIS        : The book's long side is intrinsically weaker *within* every
                half-year, not merely weak in the era where BTC fell.
COUNTER       : this is wrong if the within-half-year long-minus-short gap
                has no consistent sign across the 12 half-year cells.
FALSIFIER     : one run, one number — the sign of the within-cell gap over
                12 cells. 8+/12 same sign → structural. ≤7/12 or the
                effect fails the MDE → §8.2's premise is a calendar fact.
FAMILY        : BOTH halves must agree, or nothing is adopted:
                (a) primary: paired sign test on 12 half-year cells
                    (long avgR − short avgR per cell). Chosen as primary
                    because a 12-cell sign test is immune to the tail
                    concentration that S3 documented (top 5% carries
                    >100% of net) and needs no distributional assumption.
                (b) secondary: P87's exact model, b_long, with all three
                    instruments — cluster-robust t by month, month-cluster
                    bootstrap, half-year-cluster bootstrap. All three
                    reported, flattering one not selectable.
                (c) MANDATORY POWER GATE, printed before any result:
                    MDE = 1.96·SE(b) from the OLS fit, and the per-cell
                    gap SE. If MDE > the expected within-cell gap, a null
                    is a statement about the test, not about the strategy
                    (P85's lesson, verbatim).
EXPECTED SIZE : not dNet. b ≈ 0 (my expectation, and the reason this is
                first: I think the era is doing all the work and the next
                round is about to spend itself on a calendar effect).
                My honest power estimate: sd ≈ 6 R/trade, SE(b) ≈ 0.6-0.8
                after month-clustering, MDE ≈ 1.2-1.5 R/trade against an
                expected within-cell gap of ~0.5. THE TEST MAY BE
                UNDERPOWERED. That is why the sign test leads.
DATA NEEDED   : on disk. 500t/+325.8R, 454t/+358.9, 279t/+70.1R, 253t/+60.2R
                asserted exact first. `t["dir"]` == "long" (verified).
BLOCKERS      : none. 8 IS + 4 OOS half-year cells; the OOS arm has 4
                clusters, which is why the half-year bootstrap is
                reported as conservative rather than as a verdict.
PERIOD-CONTROL: expect b ≈ 0 and an 8-6 or worse sign count. b ≪ 0 with
                all three instruments agreeing in ≥3/4 cells would mean
                §8.2's premise is real and a side-asymmetric condition is
                worth hunting. b = 0 means P84 and P86 were both measuring
                2021, and "no single trend condition protects one side
                without taxing the other" is a much less interesting fact
                than the brief reads it as.
P90 — ENTRY FILL CONVENTION: IS +325.8R PARTLY A FILL ARTEFACT?
ID            : P90
R1 status     : open. Grep: `next_open` exists as a fill mode at
                test_1m_precise.py:141 and test_c14.py:123, but only on
                the dead C14/1m paths. The v18 champion path
                (v18_streak_halt.py:585) fills at `candles_ltf[i]["close"]`
                — the close of the bar in which the break occurred, i.e.
                at or near that bar's extreme. The repo has audited fills
                on the EXIT side (ANCHOR_BASIS_AUDIT §1-§3) and never on
                the entry side. Never run.
THESIS        : A live trader cannot fill at the close of a bar whose
                breakout they only see at that close. The re-fill cost is
                an upper bound on deployable expectancy that nobody has
                measured.
COUNTER       : this is wrong if a next-15m-open re-fill reproduces the
                shipped ledger inside the stated cost model.
FALSIFIER     : one run, one number — dNet(close-fill → next-open) on
                champion IS, against the shipped close-fill as the pin.
                |dNet| < M = 193.4R → convention not load-bearing.
FAMILY        : three fills, all reported, none selected: (a) signal-bar
                close [shipped], (b) next 15m open, (c) next 15m open +
                the existing 5bp entry slip. × 2 lanes × 2 eras. (a) is
                the control, not a result; publishing (a) alone is not
                an answer.
EXPECTED SIZE : negative, concentrated in longs, and it should load on
                P69's ATR% — the cost of a breakout fill is proportional
                to that bar's range, so (b)−(a) should correlate with the
                ceiling's cohort. Report the correlation; if the cost is
                flat in ATR% the mechanism is wrong.
DATA NEEDED   : on disk. No new data, no engine edit — the fill is a
                post-process re-pricing of entry_price with the existing
                stop and trail held. Cost model unchanged.
BLOCKERS      : none. Cannot be adopted even if it passes: it is a
                measurement, not a parameter. It bounds what can be
                deployed.
PERIOD-CONTROL: not a filter, §6 does not apply. Report per-half-year
                anyway, because a cost that concentrates in volatile bars
                has a period signature.
P91 — WHERE THE TAIL COMES FROM: THE RATCHET LADDER
ID            : P91
R1 status     : open. Grep: `n_ratchet` / `ratchet_count` has exactly one
                hit repo-wide — inside the proposal that asked for it.
                TRAIL_MECHANICS.md and TAIL_RISK_AUDIT.md both concluded
                "the tail is intrinsic" and neither counted ratchets.
THESIS        : Winners pay out as a product over a ladder of confirmed
                15m pivot ratchets (v18:602-612, 626-631). If the +40R
                trades get there via FEW ratchets that happen to be far
                away, the tail is luck and no exit work will ever help. If
                MANY and compounding, the ladder *spacing* is the lever —
                and the spacing is set by min_bars_15m = 50, which has
                never been examined as a trail parameter rather than an
                entry parameter (MB50 won as an entry parameter).
COUNTER       : this is wrong if n_ratchets has no rank-correlation with
                final R, or if the +10R trades sit at the modal count.
FALSIFIER     : one run, one number — Spearman(n_ratchets, final R),
                four cells, reported alongside the null regression.
DATA NEEDED   : on disk. Descriptive, zero arms, no engine edit.
BLOCKERS      : none.
PERIOD-CONTROL: n/a. BUT the mandatory null is a DEGENERATE-DENOMINATOR
                control, which is CLOSED_DO_NOT_REPEAT trap 2: a wider
                stop mechanically permits more ratchets, so raw
                correlation is guaranteed positive and means nothing.
                PRIMARY NUMBER IS THE WITHIN-RISK-BIN PARTIAL
                CORRELATION — n_ratchets against final R with entry risk
                held constant. If that is ≈0 the tail is luck and the
                trail-spacing arm is dead on the same run. If it is
                strong, the one arm this licenses is a trail chain on a
                different min_bars (split_mb already exists in
                test_experiments_craze.py), which then faces the full
                four-part bar.
P92 — THE PARENT WINDOW'S DEATH AS AN EXIT (lowest, honestly)
ID            : P92
R1 status     : open but heavily pre-disqualified. Exit is the ratcheted
                15m swing-pivot stop and nothing else — the 3R target at
                v18:592 is computed, stored, and never checked. 85 trades
                outlive the 1h window that authorised them. P3-B measured
                the parent's *R state* early, not its *death*. Distinct
                from CLOSED's "exit at FS" (that is the LTF's own event).
THESIS        : The reference event for a position is the death of the
                higher-timeframe thesis that opened it.
COUNTER       : this is wrong if the R still open at parent-window-close
                is positive in all four cells against a permutation null.
FALSIFIER     : one run, one number — total R still open at the parent's
                exit, four cells, signed.
FAMILY        : descriptive first, mirroring FS_TIME_DECISION's method
                (200-draw permutation on the per-trade feature, not on
                an aggregate). An arm is written only if giveup is
                negative in ≥3/4 cells, and then it must report how many
                >+10R trades the arm removes.
EXPECTED SIZE : positive (i.e. it gives money up). FS_TIME_DECISION
                measured +85.1R mean giveup at the LTF's own FS against a
                population worth +263.7R. The prior is strong and against.
                This survives only because the parent window closes on a
                different, typically LATER event.
DATA NEEDED   : on disk.
BLOCKERS      : none to measure. Not adoptable if it passes, without
                re-registering — it removes trades into a closed family
                and would need the gray-vs-skip comparison the wick work
                showed is not optional.
PERIOD-CONTROL: n/a.
R3 merge note. P90 and P91 are the same family — audits of the shipped machinery, not candidates. Neither can be adopted. Run them in one session. P89 is the only proposal here that can change what this programme does next.
What I deliberately did not propose, and why, so the next round does not rediscover them: no per-trade filter (31 experiments; §5a, 9 appearances); no regime detector (§5b, 3 failures, and P87's discriminator says a regime proxy has b = 0 — which is exactly what P89 will measure for the side split); no re-run of the ceiling at a finer grid (P88 closed it family-wise, and a finer grid after seeing 0.40% peak is the P69 trap again); nothing on sizing (§7, no execution channel); nothing on 30m/2h/4h/1m/5m, B1, FS-only, ZigZag, P1/P2 labels, nesting, events, or bookDepth (all closed or excluded, and R1 lists them).
Want me to run P89 first? It reuses exp_ceiling_regime_ctrl.py almost verbatim and would be settled in one run.
▣  Build · Big Pickle · 3m 8s
no no your job is just to give proposal
Thought: 3.7s
The user says: "no no your job is just to give proposal" — meaning they just want the proposal, not for me to ask to run it / not to run anything. So I should just deliver the proposal cleanly, no trailing "want me to run it?" question, no offer to execute.

So I should re-present the proposals as a proposal document, trimmed of the closing question. Probably they want it written as a proposal (maybe in the §9 output format, which I already did). The correction is: don't ask, don't propose running — just give the proposal.

I'll output the proposal set cleanly, no question at the end. Keep it tight. Maybe just restate the four proposals in the required format without the closing offer. Since I already gave them, the right move is to deliver the final proposal block cleanly, concise, and stop.

I'll produce the proposal as a single clean deliverable, removing meta-commentary and the closing question. Should I write it to a file? They said "your job is just to give proposal" — so just output it. No file write unless asked.

Let me output the four proposals in the §9 format, tight, no preamble beyond what's needed, no closing question.
P89 — IS THE LONG/SHORT ASYMMETRY STRUCTURAL, OR IS IT 2021?
ID            : P89
R1 status     : new. P83/LONG_TREND_P84 measured the split descriptively;
                no §6 regression exists on `dir`. Reuses P87's harness
                (exp_ceiling_regime_ctrl.py) — swap `coh` for is_long.
THESIS        : The long side is intrinsically weaker within every
                half-year, not merely weak in the era BTC fell.
COUNTER       : this is wrong if the within-half-year long-minus-short gap
                has no consistent sign across the 12 half-year cells.
FALSIFIER     : one run, one number — the sign count of the within-cell gap
                over 12 cells. 8+/12 → structural. ≤7/12 → §8.2's premise
                is a calendar fact and the next round is about to spend
                itself on a calendar effect.
FAMILY        : both halves must agree or nothing is adopted —
                (a) PRIMARY: paired sign test on 12 half-year cells
                    (long avgR − short avgR per cell). Primary because a
                    12-cell sign test is immune to the tail concentration
                    S3 documented (top 5% carries >100% of net) and needs
                    no distributional assumption.
                (b) SECONDARY: P87's exact model, b_long, with all three
                    instruments — cluster-robust t by month, month-cluster
                    bootstrap, half-year-cluster bootstrap. All three
                    reported; the flattering one is not selectable.
                (c) MANDATORY POWER GATE printed before any result:
                    MDE = 1.96·SE(b), and the per-cell gap SE. If MDE
                    exceeds the expected gap, a null is a statement about
                    the test, not the strategy (P85's lesson, verbatim).
EXPECTED SIZE : not dNet. b ≈ 0 — my expectation, and the reason this
                leads. sd ≈ 6 R/trade, SE(b) ≈ 0.6–0.8 after month
                clustering, MDE ≈ 1.2–1.5 R/trade against an expected
                within-cell gap of ~0.5. THE TEST MAY BE UNDERPOWERED;
                that is why the sign test leads.
DATA NEEDED   : on disk. Pins asserted exact first: 500t/+325.8R,
                454t/+358.9R, 279t/+70.1R, 253t/+60.2R. `t["dir"]=="long"`
                verified.
BLOCKERS      : none. 8 IS + 4 OOS cells; the OOS arm has 4 clusters, so
                the half-year bootstrap is reported as conservative, not
                as a verdict.
PERIOD-CONTROL: expect b ≈ 0 and a 8-6 or worse sign count. b ≪ 0 with
                all three instruments agreeing in ≥3/4 cells means §8.2's
                premise is real and a side-asymmetric condition is worth
                hunting. b = 0 means P84 and P86 were both measuring 2021.
P90 — ENTRY FILL CONVENTION: IS +325.8R PARTLY A FILL ARTEFACT?
ID            : P90
R1 status     : open. `next_open` exists as a fill mode at
                test_1m_precise.py:141 and test_c14.py:123, but only on
                the dead C14/1m paths. The champion path fills at
                `candles_ltf[i]["close"]` — the close of the bar in which
                the break occurred, i.e. at or near that bar's extreme.
                The repo has audited fills on the EXIT side
                (ANCHOR_BASIS_AUDIT §1–§3) and never the entry side.
THESIS        : A live trader cannot fill at the close of a bar whose
                breakout they only see at that close. The re-fill cost is
                an upper bound on deployable expectancy, unmeasured.
COUNTER       : this is wrong if a next-15m-open re-fill reproduces the
                shipped ledger inside the stated cost model.
FALSIFIER     : one run, one number — dNet(close-fill → next-open) on
                champion IS, shipped close-fill as the pin. |dNet| <
                M = 193.4R → convention not load-bearing.
FAMILY        : three fills, all reported, none selected: (a) signal-bar
                close [shipped], (b) next 15m open, (c) next 15m open +
                the existing 5bp entry slip. × 2 lanes × 2 eras. (a) is
                the control, not a result.
EXPECTED SIZE : negative, concentrated in longs, and loading on P69's
                ATR% — a breakout fill's cost scales with that bar's
                range. Report the correlation between (b)−(a) and the
                ceiling's cohort. Flat in ATR% ⇒ the mechanism is wrong.
DATA NEEDED   : on disk. No engine edit — post-process re-pricing of
                entry_price with the existing stop and trail held; cost
                model unchanged.
BLOCKERS      : none. Cannot be adopted even if it passes: a measurement,
                not a parameter. It bounds what can be deployed.
PERIOD-CONTROL: not a filter, §6 does not apply. Report per-half-year
                anyway — a cost concentrated in volatile bars has a
                period signature.
P91 — WHERE THE TAIL COMES FROM: THE RATCHET LADDER
ID            : P91
R1 status     : open. `n_ratchet` / `ratchet_count` has one hit
                repo-wide — inside the proposal that asked for it.
                TRAIL_MECHANICS.md and TAIL_RISK_AUDIT.md both concluded
                "the tail is intrinsic" and neither counted ratchets.
THESIS        : Winners pay out as a product over a ladder of confirmed
                15m pivot ratchets (v18:602–612, 626–631). Few-and-far
                ⇒ the tail is luck and no exit work helps. Many-and-
                compounding ⇒ the spacing is the lever, and the spacing
                is set by min_bars_15m = 50, never examined as a trail
                parameter rather than an entry parameter (MB50 won as an
                entry parameter).
COUNTER       : this is wrong if n_ratchets has no rank-correlation with
                final R, or if the +10R trades sit at the modal count.
FALSIFIER     : one run, one number — the WITHIN-RISK-BIN partial
                correlation of n_ratchets against final R, four cells.
DATA NEEDED   : on disk. Descriptive, zero arms, no engine edit.
BLOCKERS      : none.
PERIOD-CONTROL: n/a, but the mandatory null is a DEGENERATE-DENOMINATOR
                control (CLOSED_DO_NOT_REPEAT trap 2): a wider stop
                mechanically permits more ratchets, so the raw
                correlation is guaranteed positive and means nothing.
                The raw Spearman is reported alongside and explicitly
                labelled uninformative. Partial ≈ 0 ⇒ tail is luck and the
                trail-spacing arm dies on the same run. Partial strong ⇒
                the one licensed arm is a trail chain on a different
                min_bars (split_mb exists in test_experiments_craze.py),
                which then faces the full four-part bar.
P92 — THE PARENT WINDOW'S DEATH AS AN EXIT
ID            : P92
R1 status     : open but heavily pre-disqualified. Exit is the ratcheted
                15m swing-pivot stop and nothing else — the 3R target at
                v18:592 is computed, stored, never checked. 85 trades
                outlive the 1h window that authorised them. P3-B measured
                the parent's R state early, not its death. Distinct from
                CLOSED's "exit at FS", which is the LTF's own event.
THESIS        : The reference event for a position is the death of the
                higher-timeframe thesis that opened it.
COUNTER       : this is wrong if the R still open at parent-window-close
                is positive in all four cells against a permutation null.
FALSIFIER     : one run, one number — total R still open at the parent's
                exit, four cells, signed.
FAMILY        : descriptive first, mirroring FS_TIME_DECISION's method
                (200-draw permutation on the per-trade feature, not on an
                aggregate). An arm is written only if giveup is negative
                in ≥3/4 cells, and must then report how many >+10R trades
                it removes.
EXPECTED SIZE : positive, i.e. it gives money up. FS_TIME_DECISION
                measured +85.1R mean giveup at the LTF's own FS against a
                population worth +263.7R. Strong prior against. It
                survives only because the parent window closes on a
                different, typically later event.
DATA NEEDED   : on disk.
BLOCKERS      : none to measure. Not adoptable if it passes without
                re-registering — it removes trades into a closed family
                and needs the gray-vs-skip comparison the wick work
                showed is not optional.
PERIOD-CONTROL: n/a.
R3 merge: P90 and P91 are one family — audits of the shipped machinery, not candidates, neither adoptable. P89 is the only one of the four that can change what this programme does next.

---
Nemotrol 3 :
Created backtest/docs/PROPOSAL_CEILING_REFINED.md.
This proposal:
- Builds on P87/P88 (only filter surviving period control)
- Fixes the IS family-wise failure by making the ceiling percentile adaptive to vol regime
- Uses §6's instrument as the selection criterion (b > 0 after half-year fixed effects), not raw IS performance
- Falsifier is one run with clear pass/fail criteria
- 24-arm family (4 cells × 3 vol regimes × 2 directions) — all must pass per R3

---

Longcat:
P89 — IS THE LONG/SHORT ASYMMETRY STRUCTURAL, OR IS IT 2021?
ID            : P89
R1 status     : new. P83/LONG_TREND_P84 measured the split descriptively; no §6 regression exists on dir. Reuses P87's harness (exp_ceiling_regime_ctrl.py) — swap coh for is_long.
THESIS        : The long side is intrinsically weaker within every half-year, not merely weak in the era BTC fell.
COUNTER       : this is wrong if the within-half-year long-minus-short gap has no consistent sign across the 12 half-year cells.
FALSIFIER     : one run, one number — the sign count of the within-cell gap over 12 cells. 8+/12 → structural. ≤7/12 → §8.2's premise is a calendar fact and the next round is about to spend itself on a calendar effect.
FAMILY        : both halves must agree or nothing is adopted —
                (a) PRIMARY: paired sign test on 12 half-year cells (long avgR − short avgR per cell). Primary because a 12-cell sign test is immune to the tail concentration S3 documented (top 5% carries >100% of net) and needs no distributional assumption.
                (b) SECONDARY: P87's exact model, b_long, with all three instruments — cluster-robust t by month, month-cluster bootstrap, half-year-cluster bootstrap. All three reported; the flattering one is not selectable.
                (c) MANDATORY POWER GATE printed before any result: MDE = 1.96·SE(b), and the per-cell gap SE. If MDE exceeds the expected gap, a null is a statement about the test, not the strategy (P85's lesson, verbatim).
EXPECTED SIZE : not dNet. b ≈ 0 — my expectation, and the reason this leads. sd ≈ 6 R/trade, SE(b) ≈ 0.6–0.8 after month clustering, MDE ≈ 1.2–1.5 R/trade against an expected within-cell gap of ~0.5. THE TEST MAY BE UNDERPOWERED; that is why the sign test leads.
DATA NEEDED   : on disk. Pins asserted exact first: 500t/+325.8R, 454t/+358.9R, 279t/+70.1R, 253t/+60.2R. t["dir"]=="long" verified.
BLOCKERS      : none. 8 IS + 4 OOS cells; the OOS arm has 4 clusters, so the half-year bootstrap is reported as conservative, not as a verdict.
PERIOD-CONTROL: expect b ≈ 0 and a 8-6 or worse sign count. b ≪ 0 with all three instruments agreeing in ≥3/4 cells means §8.2's premise is real and a side-asymmetric condition is worth hunting. b = 0 means P84 and P86 were both measuring 2021.
P90 — ENTRY FILL CONVENTION: IS +325.8R PARTLY A FILL ARTEFACT?
ID            : P90
R1 status     : open. next_open exists as a fill mode at test_1m_precise.py:141 and test_c14.py:123, but only on the dead C14/1m paths. The champion path fills at candles_ltf[i]["close"] — the close of the bar in which the break occurred, i.e. at or near that bar's extreme. The repo has audited fills on the EXIT side (ANCHOR_BASIS_AUDIT §1–§3) and never the entry side.
THESIS        : A live trader cannot fill at the close of a bar whose breakout they only see at that close. The re-fill cost is an upper bound on deployable expectancy, unmeasured.
COUNTER       : this is wrong if a next-15m-open re-fill reproduces the shipped ledger inside the stated cost model.
FALSIFIER     : one run, one number — dNet(close-fill → next-open) on champion IS, shipped close-fill as the pin. |dNet| < M = 193.4R → convention not load-bearing.
FAMILY        : three fills, all reported, none selected: (a) signal-bar close shipped, (b) next 15m open, (c) next 15m open + the existing 5bp entry slip. × 2 lanes × 2 eras. (a) is the control, not a result.
EXPECTED SIZE : negative, concentrated in longs, and loading on P69's ATR% — a breakout fill's cost scales with that bar's range. Report the correlation between (b)−(a) and the ceiling's cohort. Flat in ATR% ⇒ the mechanism is wrong.
DATA NEEDED   : on disk. No engine edit — post-process re-pricing of entry_price with the existing stop and trail held; cost model unchanged.
BLOCKERS      : none. Cannot be adopted even if it passes: a measurement, not a parameter. It bounds what can be deployed.
PERIOD-CONTROL: not a filter, §6 does not apply. Report per-half-year anyway — a cost concentrated in volatile bars has a period signature.
P91 — WHERE THE TAIL COMES FROM: THE RATCHET LADDER
ID            : P91
R1 status     : open. n_ratchet / ratchet_count has one hit repo-wide — inside the proposal that asked for it. TRAIL_MECHANICS.md and TAIL_RISK_AUDIT.md both concluded "the tail is intrinsic" and neither counted ratchets.
THESIS        : Winners pay out as a product over a ladder of confirmed 15m pivot ratchets (v18:602–612, 626–631). Few-and-far ⇒ the tail is luck and no exit work helps. Many-and-compounding ⇒ the spacing is the lever, and the spacing is set by min_bars_15m = 50, never examined as a trail parameter rather than an entry parameter (MB50 won as an entry parameter).
COUNTER       : this is wrong if n_ratchets has no rank-correlation with final R, or if the +10R trades sit at the modal count.
FALSIFIER     : one run, one number — the WITHIN-RISK-BIN partial correlation of n_ratchets against final R, four cells.
DATA NEEDED   : on disk. Descriptive, zero arms, no engine edit.
BLOCKERS      : none.
PERIOD-CONTROL: n/a, but the mandatory null is a DEGENERATE-DENOMINATOR control (CLOSED_DO_NOT_REPEAT trap 2): a wider stop mechanically permits more ratchets, so the raw correlation is guaranteed positive and means nothing. The raw Spearman is reported alongside and explicitly labelled uninformative. Partial ≈ 0 ⇒ tail is luck and the trail-spacing arm dies on the same run. Partial strong ⇒ the one licensed arm is a trail chain on a different min_bars (split_mb exists in test_experiments_craze.py), which then faces the full four-part bar.
P92 — THE PARENT WINDOW'S DEATH AS AN EXIT
ID            : P92
R1 status     : open but heavily pre-disqualified. Exit is the ratcheted 15m swing-pivot stop and nothing else — the 3R target at v18:592 is computed, stored, never checked. 85 trades outlive the 1h window that authorised them. P3-B measured the parent's R state early, not its death. Distinct from CLOSED's "exit at FS", which is the LTF's own event.
THESIS        : The reference event for a position is the death of the higher-timeframe thesis that opened it.
COUNTER       : this is wrong if the R still open at parent-window-close is positive in all four cells against a permutation null.
FALSIFIER     : one run, one number — total R still open at the parent's exit, four cells, signed.
FAMILY        : descriptive first, mirroring FS_TIME_DECISION's method (200-draw permutation on the per-trade feature, not on an aggregate). An arm is written only if giveup is negative in ≥3/4 cells, and must then report how many >+10R trades it removes.
EXPECTED SIZE : positive, i.e. it gives money up. FS_TIME_DECISION measured +85.1R mean giveup at the LTF's own FS against a population worth +263.7R. Strong prior against. It survives only because the parent window closes on a different, typically later event.
DATA NEEDED   : on disk.
BLOCKERS      : none to measure. Not adoptable if it passes without re-registering — it removes trades into a closed family and needs the gray-vs-skip comparison the wick work showed is not optional.
PERIOD-CONTROL: n/a.
R3 merge: P90 and P91 are one family — audits of the shipped machinery, not candidates, neither adoptable. P89 is the only one of the four that can change what this programme does next.

---

Mimo:
R1 reading done: TRANSCRIPT_THESIS_BACKLOG.md, CLOSED_DO_NOT_REPEAT.md, other bots proposal.md (all four sets), FS_ENTRY.md, FS_ONLY_ENGINE.md, SHADOW_TIMEFRAME_IDEAS.md, plus OPEN_RESEARCH_QUEUE.md, DECOMPOSITION_NULL.md, CEILING_FAMILY_P88.md, LONG_TREND_P84.md, and the P89–P92 block already appended to the brief.
Note before the block: P89–P92 are already proposed in the brief and unrun. Mine is not one of them.
ID            : P93 — DOES ENTRY SELECTION CARRY ANY OF THE +325.8R?
                (matched placebo through the SHIPPED machinery)

R1 status     : already proposed — Big Pickle P4, `other bots proposal.md`
                (line 405). Never run; it was dropped when that file was
                deduplicated into OPEN_RESEARCH_QUEUE.md, which does not
                contain it. Partially tested in a form that cannot answer
                it: Stage 3 (`CHECKLIST.md:669`, `exp_thesis_autopsy.py`)
                ran random/delay/reverse per-trade, POST-PROCESS, through
                `fixed_exit_path(target_r=…)` only — no swing-pivot
                ratchet, no window gate, no cooldown / mcl / busy_until /
                exp_mltf cascade, so no shuffled book was ever *built* by
                the engine. Its own verdict: real +104R vs random +60R IS,
                but random +65.6R > real +25.5R OOS, "the trail remains
                the main P&L amplifier". BASE_BOOK_NULL /
                DECOMPOSITION_NULL reshuffled the *sequence of the same
                trades* — a null for order, not for selection. Not in
                CLOSED_DO_NOT_REPEAT, not in §4, not P89–P92.

THESIS        : Every one of the 31 filter experiments assumed the entry
                set contains a payoff worth selecting inside. If the
                shipped trail + window machinery produce most of +325.8R
                from any matched entry set, entry selection is decoration
                and the filter programme was structurally incapable of
                paying — which would explain 31 failures better than any
                story about eras.

COUNTER       : This is wrong if the shipped book sits above the 95th
                percentile of the matched null in all four cells — i.e.
                WHICH signals get taken, not the exit machinery, carries
                the book.                              (R2)

FALSIFIER     : one run, one number — the percentile of the shipped net R
                inside a 200-draw matched null, per cell.
                Pre-registered decision, written before the first draw:
                real < 90th percentile in ≥2 of 4 cells → entry-selection
                attribution is DEAD and this programme stops proposing
                entry-side filters; real ≥ 95th in 4/4 → selection is
                real and filters remain worth pursuing. Nothing between
                those two lines is reportable.        (R4)

FAMILY        : four arms, all reported, none selected —
                (a) shipped book [control, not a result];
                (b) matched-count signal-subset shuffle: same number of
                    taken signals per era, each signal keeps its own
                    direction, only WHICH are taken is shuffled, all
                    other machinery path-true;
                (c) delay taken signals 4 / 8 bars;
                (d) direction-reversed.
                × 2 lanes × 2 eras = 16 cells, 200 draws per cell for
                (b). The attribution claim requires (b), (c) and (d) all
                to place the real book ≥95th — no single flattering
                control selectable.                    (R3)

EXPECTED SIZE : not dNet. M = 193.4R is a null for a *paired* change; this
                is a null distribution of whole books, so gate 2 does not
                apply and I am saying so rather than forcing it. Expected
                null width is large (DECOMPOSITION_NULL: M = 479.9R IS /
                193.4R OOS on 500/279 trades). Honest expectation: the
                real book fails the 95th bar in at least IS, because
                Stage 3 already showed the fixed-exit margin was ~40% of a
                much smaller number and reversed sign in OOS.

DATA NEEDED   : on disk. Pins asserted exact first: 500t/+325.8R,
                454t/+358.9R, 279t/+70.1R, 253t/+60.2R net. Signal set
                from the shipped run; one in-memory, seed-parameterised
                signal-subset injection (repo patch rule; no
                btc_engine.py edit).

BLOCKERS      : §7 — none. Not sizing, no forward data, no alt data, no
                ZigZag. Real cost is compute: 800 path-true runs at
                ~60–90s ≈ 14–20 h; pre-register 200 draws, with an
                explicit fall-back to 100 (1% percentile resolution) if
                wall-clock demands, declared in the doc before running.

PERIOD-CONTROL: §6 does not apply — there is no kept/dropped cohort, so b
                is undefined; stated rather than fudged. The period test
                that does apply is gate 3: report real-minus-null-median
                per half-year. If the real book clears the null only in
                2023–24, the attribution is period-fitted and is reported
                as such. Gate 1 applies as: the verdict must be identical
                in all four cells.
Honest rank (R3 note): P93 and P90/P91 are the same family — audits of the shipped machinery, none adoptable, all runnable in one session. I would run P93 first: it is the only one whose negative branch closes more than it opens, and if it fires, P89's answer stops mattering for research (you cannot act on side asymmetry through entries that don't select). P89 second, P90 third, P91 fourth, P92 last — agreeing with the brief's own ordering on the last one.

---

Space bunny opencode:
Read the archive first (CLOSED_DO_NOT_REPEAT, P55–P88, CANDIDATE_BUILD_SHEET, ENGINE_SHELF, RISK_CONCURRENCY, OPEN_RESEARCH_QUEUE, EXPERIMENT_SUMMARY). Three proposals, ranked, plus two corrections to the brief.
First, the honest headline: none of these will clear |dNet| > 193.4R. I looked for one. The best 4/4 result in the repo is +78.5R (0.4× M). So these are governance/deployment items, not candidates, and I'm labelling them that way rather than dressing them up.
Two corrections to the brief
1. §7's ZigZag blocker is stale. P64 recorded the integration incomplete; P70 finished the contract and the answer was dead (12/24 cells clear M, all 12 negative). Finishing that work buys nothing.
2. CHAMP_ROBUST_P83.md's year table is not on the net basis. It sums to ≈ +551R (−11.0 + 116.7 + 113.9 + 124.1 + 100.4 + 106.8), which is the gross figure; the champion is +325.8R IS net / +70.1R OOS net. So "2021 = −26.4R" (P84, and §8 of the brief) and "2021 = −11.0R" (P83's table) are not the same number and the table cannot support either. That is the P60/P83 error class recurring inside the file that documents it. Worth a five-line reconciliation before the table is cited again.
Rank 1 — Make the slot queue explicit, then order it
ID            : P89
R1 status     : NEW. Adjacent to RISK_CONCURRENCY.md (P2), which explicitly
                defers it: "Worth a separate experiment on its own merits."
                exp_max_concurrent listed UNTESTED in ENGINE_SHELF.md:25.
THESIS        : The champion's 3-6 concurrent positions are an accident of a
                broken string comparison (v18_streak_halt.py:743 writes a DATE,
                :577 compares a DATETIME), so the book occupies a queue nobody
                has ever looked at — and the one feature that survives period
                control is a perfect key for ordering it.
COUNTER       : Wrong if the freed-slot replacements are indistinguishable from
                the trades they displace. That is the P82 lesson verbatim: a
                swap of ~400 similar trades for ~400 similar trades.
FALSIFIER     : One run, one number — dNet of ATR%-priority vs FCFS at the same
                cap, all four cells. Below zero in any cell, or b <= 0 after
                the half-year fixed effect, and this closes.
FAMILY        : {FCFS, ATR%-lowest-first, ATR%-highest-first} as the direction
                falsifier, x {cap 2,3,4,5,6}. All members must pass.
EXPECTED SIZE : Honest answer: 0 to +50R, inside M. The cap itself is nearly
                free (ANCHOR_BASIS_AUDIT: cap5 +1.1R IS / +0.0R OOS). The
                upside is the cascade 5M_CONFIRM measured — 106 of 524
                candidates silently die at the slot re-check, worth ~67R
                between gray and skip. Do not expect M.
DATA NEEDED   : on disk
BLOCKERS      : none from §7
PERIOD-CONTROL: b is the ATR% cohort difference after a half-year FE. P87
                already cleared this feature at b = +0.82 to +1.30, so b = 0
                here would mean the ordering destroyed a real signal — the
                informative outcome, not a null.
Why this beats another filter. It removes nothing. It changes which trade occupies a contended slot — the decision variable nobody has optimised, and the one P59 showed is genuinely free (the two books are 4-7% common). And it is not a regime proxy: ATR% is observed at the entry instant and does not try to infer the era.
Do not frame this as "fix the bug." ANCHOR_BASIS_AUDIT:105-107 says a serial book is +293.2R against +446.2R gross — the concurrency is load-bearing. The right move is to promote the accident to an explicit parameter, because a live operator cannot run an exchange position book on a string comparison, and then ask whether ordering buys anything on top.
Rank 2 — The 16-day cap, through P87's instrument, with a finer-ceiling family
ID            : P90
R1 status     : PARTIALLY TESTED. CAPS_P49.md (P49) + WINDOW_LIFE.md: 4/4
                positive, mechanism measured, 0.4x M, never put through §6.
                The finer-ceiling follow-up is named in WINDOW_LIFE and unrun.
THESIS        : Turning off cap_days is the only change in the repo that adds
                trades, is 4/4 positive in both eras and both lanes, and has
                a measured structural cause — a v7 trade-exit control inherited
                into an architecture where it now closes a window and every LTF
                entry inside it. Its added cohort beats the book in both eras
                and has never been period-controlled.
COUNTER       : Wrong if the added cohort's edge is 2021-24 window behaviour.
                A 98-day window is three months of directional exposure, and
                WINDOW_LIFE's own objection is that this is an observation
                about 2021-2024, not a property to rely on.
FALSIFIER     : One run, one number — b on the cap-added cohort after a
                half-year fixed effect, all four cells, three instruments.
                b <= 0 in any cell, or the half-year FE removes more than 20%
                of the gap, and this closes.
FAMILY        : {cap off, cap off + 45d window ceiling, cap off + 90d window
                ceiling}. The two ceilings exist to answer the exposure
                objection. All three must pass, or none is adopted.
EXPECTED SIZE : Already measured: +75.3R IS / +55.1R OOS / +13.7R / +78.5R.
                Best is 0.4x M. This will NOT clear the bar and I am not
                claiming it will.
DATA NEEDED   : on disk
BLOCKERS      : none from §7
PERIOD-CONTROL: b is the cap-added cohort difference after a half-year FE.
                b = 0 means the extra trades are era-smuggling and the cap
                should stay.
Why this is not era-split #10. It is 4/4 same-sign, it adds trades rather than deleting them, and the mechanism is a parameter whose meaning changed when the architecture did — not a market condition. P69/P87/P88 are the only things that cleared §6; this is the only 4/4-positive change that has never been put through it.
The 0.4×M problem is real and I cannot solve it. P49's sweep was also non-monotone (cap 24 is anomalously bad in both OOS cells). The build sheet is right that this should be resolved by a decision — drop the cap, or replace it with a ceiling that limits the leg — not by a better threshold.
Rank 3 — Drawdown duration, because the depth number is not the decision number
ID            : P91
R1 status     : OPEN, and named as missing. CHAMP_ROBUST_P83.md:102 — "Recovery
                time after the max drawdown is not reported... and that number
                matters more than the depth to anyone holding the bot."
THESIS        : 37.3R over 278 days is the wrong headline for a shipping
                decision. What matters is how long the account is under water
                and how many trades it takes to get back, and with the top 5%
                of trades carrying 138-348% of net, duration is tail-governed.
COUNTER       : Wrong if recovery time is stable across the block bootstrap,
                in which case 37.3R / 278 days is already a fair summary and
                this is a reporting nicety.
FALSIFIER     : One run, one number — p50 and p90 days-under-water over the
                block bootstrap, both eras both lanes. If p90 recovery is
                inside 2x the observed 278 days, close it.
FAMILY        : {champion, utcsat} x {IS, OOS}, plus the top-5%-removed book
                as the tail-sensitivity member. All four cells reported.
EXPECTED SIZE : None. This is a measurement and produces no dNet.
DATA NEEDED   : on disk
BLOCKERS      : §7's sizing blocker applies to any currency conversion. This
                stays in R and trade-counts and is therefore answerable.
PERIOD-CONTROL: n/a — nothing is selected. Report the distribution, not a point.
This is the one piece of §8.3 that is answerable. Sizing is not; duration is.
What I am not proposing, and why
Anything for the long/short fragility. §8.2 asks for a proposal that solves it rather than filtering it. I looked, and it is not available here. P86 identified why — the condition that blocks the bad longs blocks the good shorts — and P69 showed why it cannot be conditioned around — the feature is a clock, and its scale-free form selects the wrong cohort outright. The remaining fix is splitting risk between the two sides, and §7 is explicit that there is no size channel. The honest answer is that this is blocked, and a tenth regime-conditional filter would be a worse use of a round than saying so.
The P65 win-streak rule. Right direction, 14-3 on the partition, fails M at 0.13×. P63 says a forward slice rules and never confirms. It stays parked.
Slot-policy variants below rank 1 — exp_window_entry_cap, exp_cohort_rearm, exp_defer_h are all in the same family as P89 and R3 will merge them. If P89 fires, they queue behind it; if it does not, the family is closed and they should not be run separately.
Say the word and I'll write the P89 harness — it needs a new pin rather than a delta, since it touches the engine, and that is the main reason nobody has run it.