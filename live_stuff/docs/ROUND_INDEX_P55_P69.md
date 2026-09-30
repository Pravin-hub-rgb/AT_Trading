# The round, indexed — P55 to P69

**Every experiment run 2026-09-29, what it asked, what it found, and whether
it survives. Nothing was adopted in any of them.**

**Champion, unchanged throughout: `champion_multi_sw10` 500t / +325.8R IS,
279t / +70.1R OOS. `utcsat_multi_sw10` 454t / +359.0R IS, 253t / +60.2R OOS.
`M` = 193.4R. 0 production changes across the whole round.**

## The three tests every candidate has to pass

1. **Both eras, both lanes, same sign.** A candidate that wins only in the
   era it was built in is fitted.
2. **`|dNet| > M = 193.4R`.** A single number against a number whose
   significance was never established is not evidence.
3. **Period partition.** Calendar half-years, fixed before looking, never by
   `r_multiple` / `outcome` / `pnl`. This is the test that killed
   `cand_4h1h`, and it is applied to everything including work that predates
   it.

## The index — architecture and regime

| # | question | answer | survives? | doc / harness |
|---|---|---|---|---|
| **P55** | can the era inversion be detected at runtime? | No. Trailing 1h swing geometry separates IS from OOS by 0.01–0.10 against an IQR of ~0.75. Part B not run, per pre-registration. | **closed** | `REGIME_DETECT_P55.md` · `exp_regime_detect.py` |
| **P56** | does the 1h window's expiry earn its keep? | The expiry is **IS-fitted**: costs 121.1R/140.8R in IS, earns 101.7R/81.2R in OOS. The direction is durable without it — ~1.7× trades at PF ≥1.79 in all four cells. | **closed, documented** | `NO_EXPIRY_P56.md` · `exp_no_expiry.py` |
| **P57** | is 1h the right direction source? Should 1D help? | 1h+15m wins every cell. 1D is worse than useless as a direction source: OOS PF 0.74 / 0.56 / 0.25 under 15m / 1h / 4h. 1D+1h is the worst cell in the grid. | **closed** | `TIMEFRAME_ARCH_P57.md` · `exp_timeframe_arch.py` |
| **P58** | full 3×3 matrix — and P57 had a confound | P57 held `min_bars=10` across timeframes: a swing **count**, not a **lag**, charging slow arms up to a 24× penalty. Lag-matched, the daily verdict held (1D+1h gained 2.4× sample, still PF 0.56). **4h+1h beat the champion in OOS, both lanes.** | **matrix closed; 4h+1h became a candidate** | `TF_MATRIX_P58.md` · `exp_tf_matrix.py` |
| **P59** | why does 4h+1h cost 113R in IS? | Not a filtered champion — a **second book**. Only 4–7% of trades common. No exclusive group negative in any cell, so the IS cost is **volume, not quality**. | **superseded by P61** | `CAND_COST_P59.md` · `exp_cand_cost.py` |
| **P60** | union the two books? | **Loses 4/4 cells.** 43–46% of signals skipped by the one-slot rule. The dedup "bound" of +664.0R / +225.8R was **2.9× and 36× too high** — the single-slot constraint does not tax a union, it destroys it. | **closed** | `UNION_P60.md` · `exp_union.py` |
| **P61** | is the quality advantage stable? | **No.** 4 wins / 4 losses of 8 half-years in IS, 3-1 in OOS, and **the candidate lost every period since 2025H2** — exactly where the champion is strongest. `cand_4h1h` downgraded. Forward pass = **2 trades in 12.5 days**, a smoke test only. | **candidate killed** | `STABILITY_FORWARD_P61.md` · `exp_stability_forward.py` |
| **P66** | 30m/45m LTF — the gap P58 skipped | **The cleanest era-split in the programme.** 30m **more than doubles** the champion in OOS (+141.9R vs +70.1R, every quality measure better simultaneously) and costs 188–239R in IS. 45m agrees in 3 of 4 cells. | **closed, not adopted** | `TF_INTERP_P66.md` · `exp_tf_interp.py` |


## The index — measurement, and the owner's thread

| # | question | answer | survives? | doc / harness |
|---|---|---|---|---|
| **P62** | how much forward data does the deciding pass need? | Attempt withdrawn — `max−min` over 2–25 blocks is a badly biased-low spread estimate. "20 trades suffice" explicitly withdrawn. | **superseded by P63** | `FORWARD_NEED_P62.md` · `exp_forward_need.py` |
| **P63** | size the forward null properly | Stationary block bootstrap. Band is **89–137R at 40–70 trades**, centred near zero: a forward slice can **rule out and never confirm**, at any horizon. M is the wrong bar for it; M is a two-year null. | **method settled** | `BOOTSTRAP_NULL_P63.md` · `exp_bootstrap_null.py` |
| **P64** | ZigZag re-segmentation | **NOT COMPLETED.** The adapter builds engine-shaped, causal swing records and stamps the confirmation bar, but the engine still returns zero trades. Recorded as **no result**, not a negative one. | **open, ⅔ built** | `ZIGZAG_P64.md` · `exp_zigzag.py` |
| **P65** | Stage 64's win-streak block, never tested against the null | Numbers reproduce exactly. **Fails M in every cell** (best 10.3%). **But the period partition is the round's exception: 14 wins, 3 losses, 7 ties over 24 cells** — the only candidate both period-stable and positive in both eras. | **magnitude-failed, direction-stable** | `WINSTREAK_M_P65.md` · `exp_winstreak_M.py` |
| **P67** | is the 30m/15m split a volatility regime? | **No** — the sign tracks the era in all four cells, not the vol regime. But the champion's **OOS high-vol tercile loses money at PF 0.64 / 0.77** while the low tercile runs 2.33–4.29, consistent in all four cells. | **hypothesis closed; signal found** | `VOL_REGIME_P67.md` · `exp_vol_regime.py` |
| **P68** | volatility floor, and price on its own terms | **P67's bug fixed** — its "ATR%" was absolute ATR in dollars, so P67 never tested volatility at all. **I pre-registered the floor backwards**: P67's finding is a CEILING. **Owner's price hypothesis confirmed 4/4** — low price PF 2.60/1.68/3.08/1.72 against 2.14/1.50/2.13/1.44. | **price confirmed; floor wrong** | `VOLFLOOR_P68.md` · `exp_volfloor.py` |
| **P69** | the two corrections: ceiling + relative price | **Ceiling 0.40%: 3/4 cells positive, OOS PF doubled (1.59→3.06, 1.58→2.94), IS −9.0R, max 21.5% of M.** **Relative price dead in 4/4** (−56R to −360R) — the scale-free form of the price finding *destroys* it. | **ceiling survives OOS-only; REL closed** | `CEILING_RELPRICE_P69.md` · `exp_ceiling_relprice.py` |

## What the round established

**The champion's architecture is confirmed from every direction** — no slower
HTF, no faster HTF, no coarser LTF, no daily layer in either role, on a fair
lag-matched comparison (P57, P58, P66). **Its window expiry and several other
features are IS-fitted**, which is the same era-split signature appearing for
the seventh time (P56, P58, P59, P60, P61, P66, P69).

**The one finding that survives every test applied to it is a volatility
ceiling** — trade only when trailing ATR% is at or below ~0.40%. Three of
four cells positive, OOS profit factor roughly doubled, but IS −9.0R and
never near M.

**The owner's absolute-price observation is real, 4/4 consistent, and
untreatable.** It describes the book's character, not an edge: both halves of
that split were profitable. Its only tradable form is dead.

## Bugs found in my own harnesses this round

All were silent — none raised — and all produced a table that looked like a
result.

| run | bug | how it was caught |
|---|---|---|
| P57 | bucket width `DAY*k` built 4-**day** and 24-**day** buckets | **arithmetic**: 338 "4h" and 56 "1D" bars for 1352 days of hourly data |
| P58 | cache keyed `(scope, tf)` — `'1h'` is both HTF and LTF | **identity check**, before any cell was read |
| P60 | summed bare `r_multiple` → GROSS union vs NET champion | a 119.4R gap that was pure costs; it made the union look 216R better |
| P64 | swing records in the wrong shape | **silently empty book** — a clean table of empty rows |
| P65 | per-period dict assigned into directly | 8 ties and R/t of exactly −1.000 everywhere |
| P67 | `trailing_atr_pct` never divided by close | absolute ATR in dollars; the owner's price point fell through the missing divide |

**A table that reads all-ties, all −1.000, or all-empty is the reporting
telling you it is broken.** That is the transferable lesson, and it is why
each is written up rather than quietly re-run.

## Where this leaves things

| | |
|---|---|
| **Champion** | 1h HTF + 15m LTF. 500t/+325.8R IS, 279t/+70.1R OOS. Unchanged. |
| **Strongest survivor** | volatility CEILING at ~0.40% — OOS-only, fails IS by 9R, max 21.5% of M. Only route is the forward slice, which can rule but never confirm. |
| **Still open** | ZigZag integration (P64, ⅔ built, engine contract unmapped) |
| **Blocked on data** | Bybit perp alt data — unblocks Nemotron P6/P7 and the whole multi-instrument thread |
| **Waiting on time** | Forward pass — 40–70 trades is ~3–5 months, so roughly March 2027 |
| **Impossible as written** | Nemotron P9 Kelly: sizing cannot change net R, and the engine has no size channel |

**Nothing was adopted. Nothing should be, on this evidence.**
