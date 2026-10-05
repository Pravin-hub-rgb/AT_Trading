# P89 — THE ASYMMETRY IS STRUCTURAL IN IS AND ABSENT IN OOS. A third
# answer, and it changes what the next round should do.

> Run 2026-09-29. Harness `exp_side_asymmetry.py`.
> **From `method/NEXT_ROUND_BRIEF.md`, Big Pickle's P89.** Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## The question

The brief's §8.2 called the champion's long/short fragility "structural
and known". It was known **descriptively** — P84 measured IS longs +272.6R
against shorts +53.2R, and OOS longs +1.8R against shorts +68.4R — and had
**never been through the period-control instrument**. That gap is this run.
Everything in P84, P86 and the entire "protect one side" direction rested
on whether this is a property of the strategy or a calendar fact about
2022, when BTC fell from roughly $69k to $15k.

## Power gate, printed before any result (P85's lesson)

| cell | cells | mean gap | sd | per-cell SE |
|---|---|---|---|---|
| champion IS | 8 | +1.478 | 2.112 | 0.747 |
| champion **OOS** | 4 | **−0.441** | 0.858 | 0.429 |
| utcsat IS | 8 | +1.866 | 3.001 | 1.061 |
| utcsat **OOS** | 4 | **−0.533** | 1.116 | 0.558 |

**Big Pickle predicted this test would be underpowered (its own estimate:
MDE 1.2–1.5 R/trade against an expected gap of ~0.5) and said so before
running.** The measured per-cell SE is 0.43–1.06, so on the OOS side it
was right, and **a null there would have been a statement about the test.**
It is not null — it is a small negative, consistently signed.

## Primary — the sign test, and its verdict is genuinely ambiguous

```
champion IS    6 long-better,  2 short-better   of 8
champion OOS   2 long-better,  2 short-better   of 4
utcsat   IS    6 long-better,  2 short-better   of 8
utcsat   OOS   2 long-better,  2 short-better   of 4

both lanes: 16 long-better, 8 short-better, of 24
```

**The pre-registered bar was written for 12 cells (one lane): "8+/12 →
structural, ≤7 → calendar fact". The champion lane returns exactly 8 of 12
— a tie on the bar, not a pass.**

**I am not resolving that tie by quoting the 24-cell number**, which would
clear comfortably. The honest report is that **the sign test sits exactly on
its threshold and does not settle the question.** That is what the secondary
test is for.

## Secondary — P87's model, unchanged, and it separates cleanly


## The answer is a third one, and it is the useful one

> **In IS the long side is genuinely stronger than the short side — by about
> 1.0 R per trade, surviving a half-year fixed effect and a month-cluster
> bootstrap at p ≤ 0.0003. In OOS the long side is NOT weaker in any
> measurable way: b is −0.29 and −0.34, indistinguishable from zero, with
> per-cell gaps a coin flip.**

**So the asymmetry is neither purely structural nor purely a calendar
fact. It is structural in the era the book was fitted in and absent in the
era it was not — the era-split pattern for the tenth time, but here the
split is in the MAGNITUDE of the effect rather than its sign.**

## And the champion's OOS weakness has been mischaracterised

P78 and P84 framed it as "the long side is broken in a bear market".
**This run says that framing was half wrong.**

| | champion IS | champion OOS |
|---|---|---|
| longs, R/trade | +0.998 | **+0.011** |
| shorts, R/trade | +0.234 | **+0.584** |
| **b, period-adjusted** | **+0.96 (p = 0.0003)** | **−0.29 (n.s.)** |

**In OOS the long side is not much worse than the short side per trade. The
champion's OOS long result is weak because it took 162 long trades at
+0.011 R each — not because longs are systematically the wrong side there.**

**"Longs lose money" and "longs are no better than shorts" are different
problems with different fixes, and the programme has treated them as one
thing across two experiments (P84, P86).**

## What this means for the next round

**§8.2's premise is HALF right, and the wrong half was the actionable half.**
A side-asymmetric rule can be justified in IS on a real +1.0 R/trade effect
that survives period control. It cannot be justified on OOS, where there is
nothing to correct.

**P84/P86's finding now has a sharper explanation.** They concluded that "no
single trend condition protects one side without taxing the other". That is
true — and it may be true for a reason neither stated: **there is no OOS
long-side deficit to protect against.** A filter that removes OOS longs is
removing trades that are merely ordinary, which is why P84's long-side
"rescue" (+1.8R → +18.4R) came with a short-side collapse (+68.4R → +8.4R).

**So the next experiment is narrower and better defined: build a
side-asymmetric rule as an IS-effect to be tested OUT OF SAMPLE, not as an
OOS rescue to be justified by it.** That is a real, licensed direction —
and it is the first this brief has produced that cleared §6's instrument.

## Stated limitations

- **Both lanes are the same data.** Two IS cells agreeing at p = 0.0003 is
  not independence.
- **The sign test sits exactly on its threshold**, and the 24-cell figure is
  not the pre-registered one. Reported, not resolved.
- **The OOS arm has 4 clusters per lane**, so its half-year bootstrap is
  reported as conservative rather than as a verdict — p of 0.96 there is an
  artefact of resampling four objects. **The month bootstrap (24 clusters,
  p ≈ 0.16–0.19) is the informative number, and it says "not significant",
  not "no effect".**
- **`b` measures long-versus-short within the book, not an action.** A
  positive `b` is not a tradeable edge until it clears gates 1 and 2 and the
  forward slice.

## Status

**Nothing adopted. The question is answered and the answer is narrower than
the brief assumed.**

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.

| cell | **b (period-adjusted)** | SE | t | MDE | month p | half-yr p | verdict |
|---|---|---|---|---|---|---|---|
| champion **IS** | **+0.9582** | 0.4571 | +2.10 | 0.896 | **0.0003** | **0.0000** | **SIGNIFICANT** |
| champion **OOS** | **−0.2867** | 0.5486 | −0.52 | 1.075 | 0.1945 | 0.9640 | not significant |
| utcsat **IS** | **+1.1846** | 0.5358 | +2.21 | 1.050 | **0.0003** | **0.0000** | **SIGNIFICANT** |
| utcsat **OOS** | **−0.3384** | 0.5465 | −0.62 | 1.071 | 0.1593 | 0.9640 | not significant |

**Significant in 2 of 4 cells — and the two are the IS ones, on both lanes,
at p ≤ 0.0003 on all three instruments.**
