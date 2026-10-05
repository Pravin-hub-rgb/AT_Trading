# P107 - CONCENTRATION MEASURED, AND THE +137.33R RECONCILED

Branch: agents/champion-reality-audit
Date: 2026-09-30. Settles two items opened in CORRECTIONS_P106.

## 1. CORRELATED-CLUSTER RISK - MEASURED, SMALL

`method/reality of champion followup.md` raised the right objection. exp_mltf opens
positions inside one 1h window and they are same-direction by
construction, so the exposure is concentration, not just size. Measured
on the champion, IS:

    trades in an overlap cluster : 176 of 500 (35.2%)
    clusters                     : 73
    clusters entirely one side   : 71 of 73 (97%)

    cluster size: 2 -> 51,  3 -> 16,  4 -> 5,  6 -> 1

    clustered trades gross       : +527.1R
    single trades gross         : -81.9R

So the clustering is real and the entire book depends on it. 324
non-overlapping trades are net negative gross.

The magnitude, however, is not what the structure implies:

    worst single cluster        : -0.97R
    losing clusters             : 18 of 73 (25%), totalling only -10.4R
    clusters of 4 or more       : all positive, worst +6.84R
    median cluster              : +1.74R
    largest cluster             : +49.85R

Trailing exits stagger the cluster. The positions do not all stop out
together because the swing trail ratchets each one at its own bar. So the
worst simultaneous adverse event in the whole history is under 1R, not 6R.

The objection stands as a structural fact and fails as a risk magnitude.
This is a "measure before funding" item that measures small. It does not
become a reason to refuse multi-position.

## 2. THE LIVE NUMBER - RECONCILED, AND MY +78.50R WAS ALSO WRONG

P106 reported that the live configuration gives 369t / +78.50R against a
claimed 351t / +137.33R, and recorded it as unsettled. That was my error,
twice over.

The golden test does two things my run did not:

1. It uses `SWING["min_bars_1h"]` = 20 for the 1h swing chain, not 10.
2. It costs with `_trade_costs(tr, fee, 0.0, entry_slip, exit_slip)`.
   `run_experiment.net_r` subtracts a separate funding term on top.

Replicating both, live config, v18 engine, fine fills:

    sw20 (golden chain)   n=351  gross=+211.72  net=+137.33  PF=1.907
    sw10 (my earlier run)  n=369  gross=+170.12  net= +94.21  PF=1.675
    golden test claims     n=351  gross=+211.72  net=+137.33  PF=1.907

Exact match on every figure. The live configuration is pinned at 351t /
+137.33R as documented. Nothing is unsettled. My +78.50R figure was wrong
and should not be cited.

## 3. THE DIVERENCE THAT MATTERS IS NOT PARAMS

`champion_multi_sw10` runs on a 1h swing chain with min_bars=10. The live
loop and the golden test run min_bars=20. This is the seventh divergence
and the only one that is structural rather than parametric. The name
`champion_multi_sw10` encodes it: sw10.

So PORT_SCOPE_P105 understated the port. It is not three params. It is:

    1. swap v18 for v19
    2. set mode=atr_high, cooldown_bars=8, ext_stop_r=3.0
       (sl_buf_atr 0.01, chop_thresh 58.0 and max_consecutive_losses 3
       already match)
    3. move the 1h swing chain from min_bars 20 to min_bars 10

Step 3 is the one with no precedent in this repo. Every previously
recorded baseline used min_bars 20.

## STANDING POSITION

The champion remains v19, IS 500t/+325.78R, OOS 279t/+70.15R. The live
configuration remains pinned at 351t/+137.33R. The gap between them is
three parameters and a swing chain, not a defect in either.