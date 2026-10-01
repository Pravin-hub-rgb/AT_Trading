# P102 - THE CHAMPION, CANONICAL. One file, one number.

Branch: agents/champion-reality-audit
Date: 2026-09-30. Supersedes the framing in CHAMPION_DEPLOYABILITY_P99.md.

## THE ONE SENTENCE

**The champion is `backend/src/btc/engines/htf_ltf/v19_champion.py`.
It is IS 500t / +325.78R and OOS 279t / +70.15R, net, on both eras.**

There is no second strategy hiding in this repo. v18 and every `exp_*`
knob in the harness are research scaffolding.

## WHAT v19 IS

v18_streak_halt.py plus the two behaviours the pinned champion needs,
written as ordinary code. Not a source patch, not a flag.

    1. No position limit. The one-position gate is removed and busy_until
       is never armed, so a window may hold overlapping entries. This is
       the "multi" in champion_multi_sw10.
    2. Regime hysteresis. On a regime flip, keep trading the previous
       regime for 7 consecutive disagreements before switching.

Four lines changed. v18 is untouched and stays for comparison.

## VERIFIED WITHOUT ANY HARNESS

exp_v19_proof.py and exp_v19_oos.py import nothing from
test_experiments_craze. They call v19 directly, with the three
harness-only kwargs dropped.

    IS  n=500  net=+325.78R  PF=2.384  maxconc=6   pin: 500 / +325.8
    OOS n=279  net=+70.15R   PF=1.591  maxconc=5   pin: 279 / +70.1

Both eras match. The pin does not depend on the harness.

## CORRECTIONS TO P99

P99 said: "Every single-axis arm is negative OOS. Only the multi-position
book is positive OOS, so the features are load-bearing and must be ported."

The measurement is right. The reading was not. Arms A and B are configs
nobody chose, not rival strategies. Arm A's -13.3R OOS is not evidence
against the champion; it is the result of subtracting features from a
strategy that was defined with them. P99 also described arm A as
"production-as-is". It was not. The live bot runs a different param set
entirely, from backtest/engine/v18_params.py, which differs in six
values. Arm A was an artificial build.

The genuine finding from P99 is narrower and stands: the two features are
load-bearing. Removing them from the champion does not produce a better
strategy, it produces a different one.

## VERIFIED CLEAN

| check | result | where |
|---|---|---|
| pin reproducibility | 500t/+325.8R exact | exp_champion_true.py |
| harness independence | both eras match | exp_v19_proof.py, exp_v19_oos.py |
| HTF gate lookahead C12/C14/C15 | fixed in code | HTF_GATE_AUDIT_P101.md |
| C14-narrow residual | +1.4R, 3 trades | HTF_GATE_AUDIT_P101.md |
| fillability, close vs next open | 500/500 identical, 0R | exp_fillability.py |

## REJECTED AS CIRCULAR

bars_to_window_end separates the profitable cohort at AUC 0.842, but the
separation is arithmetic, not predictive. See P103.

## STILL OPEN

Forward lane has 2 champion trades over 12.5 days. Nothing here is a
ruling on live merit. A meaningful one needs 40-70 trades, roughly March
2027.