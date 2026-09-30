# NEXT ROUND BRIEF — v18 / champion_multi_sw10

**Read this whole file before proposing anything. It exists because the
previous round wasted itself by not doing so.**

Date: 2026-09-30. Covers P55–P88. Every claim here is measured in this repo
and every file named is on disk under `live_stuff/docs/`.

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
| **ZigZag integration** | P64 is ⅔ built. The missing piece is the consumer contract, not the segmenter. |

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
