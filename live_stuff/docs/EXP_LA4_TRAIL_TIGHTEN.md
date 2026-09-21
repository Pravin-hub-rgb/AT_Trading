# EXP LA4: Trail Tightening Hypothesis

**Date:** 2026-09-20
**Status:** REJECTED
**Harness:** `exp_la4_trail_tighten.py` (CRAZE patch with `exp_trail_tighten_r` + `exp_trail_tighten_pct`)

## Theory

The loss autopsy found 224.8R left on the table from MFE giveback:
- 72 trades reached MFE >= 3R (total +808.5R)
- Only captured +583.7R (gave back 224.8R)
- 39 trades gave back >50% of their MFE

The current trail follows swing lows (for longs) without any profit protection.
When a trade reaches 5R MFE and then reverses to 2R, the trail doesn't kick in
until the swing low is hit — which might be at 1R or even -1R.

## Hypothesis

If we tighten the trail after MFE reaches a threshold, we capture more of the
existing MFE without destroying the runners.

## Implementation

Added `exp_trail_tighten_r` and `exp_trail_tighten_pct` as CRAZE patch parameters.
Applied in both coarse and fine trail paths. When MFE (in R) reaches the threshold,
the SL is raised to `entry + direction * mfe_r * tighten_pct * risk`.

## Results

### ANCHOR (lb14, fine fills, baseline +166.7R)

| Thr | Pct | Trades | NET | Delta | WR | DD | PF |
|---|---|---|---|---|---|---|---|
| 1.5 | 0.4 | 403 | -54.9 | -221.6 | 42.9 | 31.5 | 1.16 |
| 2.0 | 0.4 | 379 | -43.5 | -210.2 | 36.1 | 30.7 | 1.19 |
| 3.0 | 0.4 | 367 | -4.1 | -170.8 | 32.4 | 29.2 | 1.36 |
| 4.0 | 0.4 | 356 | +43.9 | -122.8 | 31.7 | 22.9 | 1.57 |
| **5.0** | **0.4** | **351** | **+54.1** | **-112.6** | **31.1** | **24.5** | **1.62** |

### OPTIMAL (cd10 + w24 + persist2 + mltf + chop55, fine fills, baseline +226.0R)

| Thr | Pct | Trades | NET | Delta | WR | DD | PF |
|---|---|---|---|---|---|---|---|
| 1.5 | 0.4 | 343 | -19.1 | -245.2 | 46.6 | 17.2 | 1.34 |
| 2.0 | 0.4 | 334 | +18.4 | -207.6 | 42.8 | 16.4 | 1.54 |
| 3.0 | 0.4 | 325 | +73.9 | -152.1 | 39.7 | 13.2 | 1.83 |
| 4.0 | 0.4 | 319 | +125.9 | -100.1 | 37.6 | 14.2 | 2.09 |
| **5.0** | **0.4** | **318** | **+163.4** | **-62.7** | **37.4** | **15.5** | **2.30** |

### Monster Analysis

| Config | Baseline monsters (>10R) | Best tighten monsters | Lost |
|---|---|---|---|
| ANCHOR | 10 (43.6+37.0+31.8+31.4+18.7+16.7+15.8+12.9+12.7+10.4) | 4 (31.4+18.7+12.9+12.7) | 6 monsters (-155.3R) |
| OPTIMAL | 12 (37.0+31.8+31.4+29.1+18.7+18.6+16.7+15.8+13.4+13.0+12.9+10.4) | 6 (31.4+29.1+18.7+18.6+13.4+12.9) | 6 monsters (-similar) |

## Verdict: REJECTED

Trail tightening kills monsters. The 224.8R MFE giveback is the COST of letting winners run.

**Key insight:** You cannot capture the giveback without also cutting the monsters.
The same mechanism that lets trades reach 40R also lets some trades give back from 20R to 10R.
This is the variance/reward tradeoff — it is NOT a bug, it is the price of asymmetric payoff.

The top 10 monsters (>10R) produce 49% of all gross wins. Even the most conservative
tightening (thr=5.0, pct=0.4) kills 6 of them, losing -112.6R on anchor and -62.7R on OPT.

Lower thresholds are even worse — thr=1.5 loses -221R to -246R.

## Conclusion

MFE giveback cannot be "fixed" by trail tightening. The 224.8R giveback is structural:
it is the price the system pays for the 10 monsters that produce 49% of gross wins.
Any mechanism that tries to protect profits will also kill the monsters.

**Actionable alternative:** Instead of trail tightening (which hurts ALL winners), focus on:
1. Skip <12 bars post-filter: +100.8R anchor, +119.6R OPT (theoretical ceiling)
2. Skip 12-24h window age: +36.3R anchor, -15.3R OPT (lane-dependent)
3. w24 wage gate: already adopted (+78.3R on OPT)
