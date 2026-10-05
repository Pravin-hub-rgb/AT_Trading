# P115 — bars_to_wend carries no information. P95's 0.847 AUC was the identity.

Branch: agents/champion-reality-audit
Date: 2026-10-01. Backtesting only. Harness: `exp_p115_bars_to_wend.py`.

P95 reported AUC 0.843–0.867 for `bars_to_wend` separating trades that outlive
their HTF window from those that do not, and called it causal because it is
computable at entry. **That number is the label, not the feature.** P95's label
was `exit_ts > window_end`, which is `hold > bars_to_wend`. The feature and the
label shared a variable, so the AUC was partly arithmetic.

## Pre-registered, before the run

Three AUCs with labels **not** defined from the feature, and a stop rule: if the
duration AUC sits at 0.50, stop, because the other two then answer a dead
question. A null was recorded in advance as an acceptable, publishable outcome so
it could not be reinterpreted afterwards.

## The result

| label | origin IS | origin OOS | leg IS | leg OOS | reads |
|---|---|---|---|---|---|
| (1) bwe → bars_held > 96 | 0.472 | 0.533 | 0.470 | 0.537 | **identity** |
| (2) bwe → r_multiple > 0 | 0.510 | 0.485 | 0.508 | 0.493 | **identity** |
| (3) bwe → \|move\| / ATR > 1.0 | 0.596 | 0.600 | 0.594 | 0.601 | n = 20/252 — noise |

(1) is identity in all four cells. **The pre-registered falsifier fired.** There is
no entry-time signal in `bars_to_wend`.

## The stop rule mattered

(3) reads 0.594–0.601, which on a naive threshold flags as separating in the leg
OOS cell. Its positive class is **20 trades out of 252**. That is noise, and the
pre-registered (1) is what stopped a false positive being written up. AUC without
its n is not evidence.

## C16 did not cause this

`bars_to_wend` is built from window intervals and entry timestamps, neither of
which the pivot rule reaches. Mean bwe is 379.9 bars on the origin book and 380.8
on the leg; the duration AUC moves 0.472 → 0.470. So P95's finding was not a
pre-C16 artefact — it is the identity on **both** books. Half the point of running
the leg arm was to establish that, and it did.

## Two things P95 got wrong besides the circularity

**Unit error, confirmed.** P95 quotes 458.8 bars and then calls it "about 76
days". At 15m, 458.8 bars is **4.78 days**. The 76.6-bar mean IN is **0.80 days**,
not 13. Both cells of the "mechanism" paragraph were off by roughly 16×, which
made a three-day window read as a quarter.

**bars_held, never reported.** Label (1) needs it and P95 does not give it: IS
mean 116.5 bars, median 58, p90 291; OOS mean 100.1, median 63, p90 266. The
median sits at 58–63, so the 96-bar threshold splits the book 310/499 rather than
250/250, and the AUC is still 0.47.

## Consequence

**P94 and P95 die as rules and stay descriptive.** Anything that rests on
`bars_to_wend` being a predictive structure has to be re-read as "long holds win",
which is the tail-concentration finding restated — `method/MASTER_CANDIDATES_V2.md`
measured the top 5% of tail at 221.7% of OOS net.

Per the governance rule now in `method/NEXT_ROUND_BRIEF.md`, this is not an edge
question and M was never the right instrument for it. The question was causality:
does the feature carry information at entry time. It does not.

P94 itself is unaffected — its claim is about the outlive cohort's quality gates,
not about the feature, and its b = +4.9 figures are r_multiple-based. What dies is
the framing that a countdown feature can act on.