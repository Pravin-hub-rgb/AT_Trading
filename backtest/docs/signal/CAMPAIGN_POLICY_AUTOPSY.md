# Stage 47 — Causal Campaign Policy Sweep

**Instrument:** BTCUSDT Bybit perpetual only  
**Periods:** IS 2023–2026 and true/reused OOS 2021–2022  
**Mode:** default-off, test-only, path-true campaign policy sweep  
**Production change:** none

## Question

Can a multi strategy improve by controlling the number or portfolio state of additional entries inside one parent HTF campaign?

The sweep tested 17 policies on seven references:

- exact baseline;
- require existing same-direction marked cohort R above `-0.5R`, `0R`, or `+0.5R`;
- maximum total entries per HTF window: 1, 2, 3, or 4;
- maximum add-ons per HTF window: 1, 2, 3, or 4;
- block only when the active cohort is mixed/opposite;
- four green-state/cap combinations.

The marked state is calculated from completed 1m data up to the candidate signal-bar close. Skipped entries are not post-hoc removals: the engine continues from the next candidate and recomputes cooldown, halt, active positions, and later entry eligibility. Every reported variant is therefore a complete strategy ledger.

References:

- `pure_v18_single`, `pure_v18_multi`;
- `literal_v18_single`, `literal_v18_multi`;
- `fullstack_wage10_cd0_single_sw10`;
- `champion_multi_sw10`;
- `utcsat_multi_sw10`.

The identity gate passed:

```text
Shipped:     340 trades / +225.3R
Patched-off: 340 trades / +225.3R
IDENTICAL
```

## Main finding

No campaign policy was a robust improvement to the full strategy.

### Green-state requirements

Requiring the existing same-direction cohort to be green was consistently neutral-to-harmful:

- `green_require_m05` blocked only 0–7 entries per cell and slightly reduced net R;
- `green_require_0` and `green_require_p05` blocked more trades and reduced both average R and total R;
- the `-0.5R` arm is effectively a no-op on current multi references;
- stricter thresholds were materially worse.

This agrees with Stage 44: green add-ons are a strong descriptive cohort, but requiring only green add-ons is not supported because red add-ons were also positive, albeit in small samples.

### Total/add-on caps

`max_total_3` improved the reused OOS current multi ledgers, but destroyed the development-period ledgers.

| Reference | IS baseline → cap 3 | OOS baseline → cap 3 |
|---|---:|---:|
| Pure multi | +272.5R → +130.9R | +44.3R → +45.6R |
| Literal multi | +279.4R → +132.5R | +72.3R → +73.1R |
| Champion multi | +325.8R → +107.7R | +70.2R → +95.8R |
| UTC-Saturday multi | +358.9R → +111.2R | +60.2R → +98.4R |

This is the same era-dependent saturation pattern as the earlier HTF-window entry-cap experiment. The cap produces a smaller, lower-frequency strategy; it does not improve the full strategy.


## Full current-multi comparison: `block_mixed`

| Reference | Era | Policy | Trades | Gross R | Net R | Net R/trade | WR | Avg win | Avg loss | Payoff | PF | Max DD | 10R+ runners | Blocked |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Champion | IS | baseline | 500 | +445.2 | +325.8 | +0.652 | 30.0% | +5.114 | -0.919 | 5.56 | 2.38 | 27.7R | 17 | 0 |
| Champion | IS | block mixed | 498 | +447.2 | +328.3 | +0.659 | 30.1% | +5.114 | -0.919 | 5.56 | 2.40 | 27.7R | 17 | 2 |
| Champion | OOS | baseline | 279 | +105.7 | +70.2 | +0.251 | 28.0% | +3.649 | -0.890 | 4.10 | 1.59 | 53.2R | 6 | 0 |
| Champion | OOS | block mixed | 276 | +105.0 | +69.6 | +0.252 | 27.9% | +3.674 | -0.894 | 4.11 | 1.59 | 54.9R | 6 | 4 |
| UTC-Saturday | IS | baseline | 454 | +466.5 | +358.9 | +0.791 | 30.8% | +5.391 | -0.918 | 5.87 | 2.62 | 21.2R | 18 | 0 |
| UTC-Saturday | IS | block mixed | 453 | +467.5 | +360.4 | +0.796 | 30.9% | +5.391 | -0.918 | 5.87 | 2.63 | 21.2R | 18 | 2 |
| UTC-Saturday | OOS | baseline | 253 | +92.6 | +60.2 | +0.238 | 29.6% | +3.381 | -0.904 | 3.74 | 1.58 | 29.4R | 4 | 0 |
| UTC-Saturday | OOS | block mixed | 251 | +91.9 | +59.6 | +0.237 | 29.5% | +3.402 | -0.903 | 3.77 | 1.57 | 29.4R | 4 | 4 |

## Why the lower trade count does not mean “better quality”

The reported policies are not summaries of only the surviving trades. They are complete reruns:

```text
candidate blocked -> portfolio state remains unchanged
-> next eligible candidate is evaluated
-> later trades and path effects are recomputed
```

Therefore:

- fewer trades means the policy removed opportunities from the full strategy;
- a higher R/trade does not compensate when total R collapses;
- the cap’s OOS improvement is not a free quality upgrade because it gave up `200R+` in IS on the current multi references;
- the mixed block is effectively neutral because it touched too few candidates.

## Verdict

- `green_require_*`: rejected;
- `max_total_*`: rejected as a full-strategy improvement; retained only as evidence of era-dependent HTF-window saturation;
- `max_addons_*`: rejected; these are equivalent to shifted total-entry caps in this engine path;
- `block_mixed`: not adopted; near-neutral and inconsistent across eras/current references;
- no production change.

## Files

Harness:

```text
C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\exp_thesis_campaign_policy.py
```

Canonical results:

```text
C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_campaign_policy_results_is.json
C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_campaign_policy_results_oos.json
```

The policy kwargs and accounting live only in the test-only superset `test_experiments_craze.py`; `backend/` and the live engine were not changed by this experiment.

