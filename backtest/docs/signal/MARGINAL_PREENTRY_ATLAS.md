# Marginal Cohort and Pre-Entry Scene Atlas

**Instrument:** Bybit BTCUSDT perpetual only  
**Periods:** IS 2023–2026 and reused OOS 2021–2022  
**Stages:** 44–46  
**Mode:** read-only descriptive autopsy; the real trade ledger was never modified

## Executive result

Three related questions were tested:

1. Is the marginal quality of a multi add-on determined by the marked state of the positions already open?
2. Does the completed 5m path immediately before a 15m entry distinguish good trades from bad trades?
3. Can losses be reduced using a pre-entry “loss scene” without using hindsight?

The strongest durable observation is:

> **Add-ons opened while the same-direction cohort is already green are consistently profitable across every multi reference and both eras.**

However, the immediate proposed rule—block red add-ons—failed its own test because red add-ons were also profitable in every observed multi cell, although their samples were tiny. Therefore no path-true gate was justified.

The completed pre-entry 5m scenes also failed to produce a universal discriminator. The loss atlas reconfirmed that losers are mainly an outcome of post-entry path behavior, not a distinct causal entry scene.

## References and integrity

The harness uses the frozen references from `exp_thesis_5m_opposition.py`:

- low-filter BASE single;
- low-filter BASE multi;
- `fullstack_wage10_cd0_single_sw10`;
- `champion_multi_sw10`;
- `utcsat_multi_sw10`.

The low-filter BASE trade counts here are not claimed to be identical to the separate `sw20` pure-v18 geometry references. They are the exact frozen BASE ledgers used by this atlas. Current champion, UTC-Saturday, and fullstack ledgers reproduce their established baseline totals.

The IS identity gate passed before results. Both IS and OOS JSON artifacts parse successfully.

# Stage 44 — marginal cohort / campaign ladder

For every actual entry, the harness marked all positions that were open at the candidate entry timestamp using completed 1m data. It then classified the candidate as:

- `first`: no position was open;
- `green_addon`: same-direction open positions had positive aggregate marked R;
- `red_addon`: same-direction open positions had negative aggregate marked R;
- `mixed_cohort`: an opposite-direction position was also open.

This is an attribution of the actual portfolio state. It is not a post-hoc removal or counterfactual execution.

## Multi add-on results

| Reference | Era | Bucket | Trades | Net R | Avg net R | WR | PF |
|---|---|---:|---:|---:|---:|---:|---:|
| BASE multi | IS | first | 340 | +148.2 | +0.436 | 25.3% | 1.51 |
| BASE multi | IS | green add-on | 66 | +123.6 | +1.873 | 48.5% | 4.08 |
| BASE multi | IS | red add-on | 7 | +9.9 | +1.413 | 85.7% | 6.82 |
| Champion multi | IS | first | 379 | +201.5 | +0.532 | 26.6% | 1.63 |
| Champion multi | IS | green add-on | 112 | +109.6 | +0.979 | 38.4% | 2.44 |
| Champion multi | IS | red add-on | 7 | +17.2 | +2.451 | 85.7% | 76.08 |
| UTC-Saturday multi | IS | first | 349 | +190.6 | +0.546 | 27.8% | 1.66 |
| UTC-Saturday multi | IS | green add-on | 98 | +157.6 | +1.608 | 38.8% | 3.35 |
| UTC-Saturday multi | IS | red add-on | 6 | +12.2 | +2.038 | 83.3% | 54.52 |
| BASE multi | OOS | first | 183 | +1.5 | +0.008 | 21.9% | 1.01 |
| BASE multi | OOS | green add-on | 26 | +34.9 | +1.341 | 38.5% | 3.44 |
| BASE multi | OOS | red add-on | 2 | +5.9 | +2.971 | 100.0% | n/m |
| Champion multi | OOS | first | 210 | -12.5 | -0.060 | 24.8% | 0.92 |
| Champion multi | OOS | green add-on | 61 | +42.2 | +0.693 | 34.4% | 2.08 |
| Champion multi | OOS | red add-on | 5 | +39.8 | +7.969 | 80.0% | 38.79 |
| UTC-Saturday multi | OOS | first | 200 | +3.1 | +0.015 | 28.0% | 1.02 |
| UTC-Saturday multi | OOS | green add-on | 47 | +15.6 | +0.333 | 29.8% | 1.49 |
| UTC-Saturday multi | OOS | red add-on | 4 | +40.9 | +10.225 | 100.0% | n/m |

### Interpretation

Green add-ons are the only robust marginal-quality observation:

- positive in all six multi reference/era cells;
- higher WR and PF than first trades;
- only 12–22% of each multi ledger, so this is a real but minority cohort.

But the proposed `block red add-ons` rule is contradicted by the data. Red add-ons are positive too, with only 2–7 observations per cell. They are too small to trust as a strategy in themselves, but they are certainly not a demonstrated loss cohort.

The mixed/opposite-direction cohort is negative in the three IS multi cells, but it contains only 1–6 trades per cell and does not establish a stable rule.

## Cohort sequence

Sequence numbers are not universal:

- third cohort trades are excellent in current champion/king ledgers;
- the same sequence is weak in BASE multi and OOS;
- fourth/fifth cohorts turn negative in champion/king OOS;
- no fixed “only take first N” policy is justified.

### Stage 44 verdict

> Green add-ons describe a strong minority cohort. A red-add-on block is not supported, and a sequence cap is not supported. No path-true policy was run.

# Stage 45 — causal pre-entry 5m path scene

For every entry, the harness used the six completed 5m candles ending no later than the 15m entry instant. It measured:

- directional efficiency;
- consecutive-candle overlap;
- average body/range ratio;
- wick/range ratio;
- directional return over the six bars;
- recent pullback in average 5m range units;
- whether the completed 5m Walker direction opposed the trade.

No post-entry candle was used to assign the scene.

## Scene results

The most populated `overlap_chop` scene was profitable in every reference and era. For example:

| Reference | Era | Trades | Net R | Avg net R | WR | PF |
|---|---|---:|---:|---:|---:|---:|
| BASE single | IS | 81 | +8.7 | +0.107 | 23.5% | 1.11 |
| BASE single | OOS | 72 | +8.6 | +0.119 | 19.4% | 1.14 |
| Champion multi | IS | 101 | +110.5 | +1.094 | 31.7% | 2.35 |
| Champion multi | OOS | 94 | +46.1 | +0.490 | 26.6% | 1.64 |
| UTC-Saturday multi | IS | 91 | +102.8 | +1.129 | 28.6% | 2.32 |
| UTC-Saturday multi | OOS | 84 | +43.7 | +0.521 | 29.8% | 1.70 |

This contradicts the idea that visibly choppy pre-entry paths should automatically be skipped.

`wick_rejection` was strong in IS but weaker/mixed in OOS, especially on current multi references. `clean_continuation` was underpowered and negative in several OOS cells. `other_orderly_path` was generally positive but heterogeneous.

## Prior 5m direction

Opposed pre-entry 5m state was often better than alignment:

- BASE single: opposed `+76.2R` IS and `+32.3R` OOS;
- BASE multi: opposed `+163.1R` IS and `+38.6R` OOS;
- champion: opposed `+148.8R` IS and `+42.0R` OOS;
- UTC-Saturday: opposed `+153.2R` IS and `+26.2R` OOS`.

The exception was fullstack single OOS, where opposed was `-6.2R` across 29 trades. This is another reason a universal opposite-direction gate is not justified.

### Stage 45 verdict

> Completed 5m path shape contains context, but neither overlap, wick rejection, clean continuation, nor simple 5m alignment/opposition is a universal entry filter.

# Stage 46 — loss-scene atlas

The loss atlas separated trades by post-entry MFE:

- `immediate`: MFE below `+0.25R`;
- `fade`: MFE `+0.25R` to `<+0.5R`;
- `early_peak`: MFE `+0.5R` to `<+1R`;
- `giveback`: MFE at least `+1R` but final loss;
- `winner`: final positive trade.

This classification is descriptive only. MFE is not available at entry and therefore cannot become an entry rule without hindsight.

Examples:

| Reference | Era | Immediate losses | Giveback losses | Winner net R |
|---|---|---:|---:|---:|
| BASE single | IS | 66 | 77 | +397.0 |
| BASE single | OOS | 37 | 54 | +157.3 |
| Champion multi | IS | 99 | 105 | +723.7 |
| Champion multi | OOS | 63 | 68 | +274.1 |
| UTC-Saturday multi | IS | 86 | 96 | +714.1 |
| UTC-Saturday multi | OOS | 59 | 57 | +243.6 |

The result reconfirms that losses divide into immediate failures and givebacks, but it does not reveal a repeatable causal pre-entry scene. Every “loss scene” has negative net by construction; the useful information is that the larger loser group is often the giveback cohort, not that the entry scene was identifiable in advance.

### Stage 46 verdict

> The atlas confirms distributed structural losses and large runner dependence, but does not justify a new pre-entry composite filter.

# Final decision

- **Keep:** green-add-on state as a descriptive portfolio-state feature.
- **Reject:** block red add-ons; red add-ons were profitable in every observed multi cell, albeit with tiny samples.
- **Reject:** fixed cohort sequence caps; sequence quality changes by reference and era.
- **Reject:** simple pre-entry 5m direction opposition; it is often better than alignment.
- **Reject:** overlap/chop and wick-scene entry gates; neither is consistently negative.
- **No production change.**

# Artifacts

## Harness

`C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\exp_thesis_marginal_preentry_atlas.py`

## Canonical JSON

- `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_marginal_preentry_atlas_is.json`
- `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_marginal_preentry_atlas_oos.json`
