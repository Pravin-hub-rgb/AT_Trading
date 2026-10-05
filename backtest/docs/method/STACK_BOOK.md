# The Stage-B stack book — it was already here, and it reproduces exactly

**Date:** 2026-09-27
**Harness:** `backtest/tests/exp_stack_repro.py` → `_stack_repro.json`
**Result: 24/24 documented cells reproduce to 0.1R. The stack book is real, and
we are not shipping it.**

---

## How this was found

Asked to read the docs rather than run another experiment. The right files were
`signal/EQUITY_CURVE_STUDY.md` / `method/TRAIL_MECHANICS.md` / `method/CAPITAL_STAGE_PLAN.md` — all
dated 24–26 Sep, all describing an **exit-side** candidate stack that was
measured, causality-audited, and left **default-off**.

This is the family the previous four logs missed entirely. Every one of them
worked on *entry* — which timeframe, which filter, which break kind. The stack
is about **what happens after you are in**.

## The arms

All three flags already exist in the built engine, default 0. Nothing is new.

| arm | flags | what it does |
|---|---|---|
| `half` | `exp_trail_half=1` | trail ratchet moves only halfway to the new swing candidate, so the stop stays wider |
| `half+delay1` | + `exp_trail_delay_r=1.0` | and the trail stays **off entirely** until the trade has +1.0R unrealized — "prove it first, then trail" |
| `skip_decisive` | `exp_skip_decisive=1` | skip entries tagged `use=="decisive"` (high 15m ATR%) |
| **STACK** | all three | the combination |

Worked story from `method/TRAIL_MECHANICS.md`: entry 100, SL 80, 1R = 120. Price swings
to 110, then 115 — **nothing happens**, the trade has not proved itself. At 122
(+1.1R) the trail arms. 125 → SL becomes `mid(80,125)` = 102.5. 135 → 118.75. The
trade survives a pullback that would have killed it under the baseline full-jump
trail, and still ratchets to the eventual target.

## Reproduction — 24/24

### champion_multi_sw10 (the conservative king we ship)

| arm | n IS/OOS | IS net | doc | OOS net | doc | OOS DD |
|---|---|---:|---:|---:|---:|---:|
| baseline | 500 / 279 | +325.8 | +325.8 | +70.2 | +70.2 | 53.2 |
| half | 469 / 268 | +428.6 | +428.6 | +72.8 | +72.8 | 46.6 |
| half+delay1 | 466 / 271 | +429.6 | +429.6 | +89.8 | +89.8 | 46.3 |
| skip_decisive | 500 / 222 | +325.8 | +325.8 | +99.3 | +99.3 | 33.8 |
| **STACK** | **466 / 217** | **+429.6** | **+429.6** | **+110.5** | **+110.5** | **30.6** |

**OOS: +70.2 → +110.5 (+57%) and maxDD 53.2 → 30.6 (−42%).** Both at once, on
the lane we actually ship, against numbers the docs published three days ago.

### utcsat_multi_sw10

| arm | n IS/OOS | IS net | doc | OOS net | doc | OOS DD |
|---|---|---:|---:|---:|---:|---:|
| baseline | 454 / 253 | +358.9 | +358.9 | +60.2 | +60.2 | 29.4 |
| half | 431 / 242 | +401.0 | — | +66.3 | +66.3 | 28.9 |
| half+delay1 | 428 / 244 | +411.1 | +411.1 | +87.1 | +87.1 | 29.4 |
| skip_decisive | 454 / 200 | +358.9 | +358.9 | +76.8 | +76.8 | 24.6 |
| **STACK** | **428 / 194** | **+411.1** | — | **+94.6** | — | 29.2 |

OOS +60.2 → +94.6 (+57%), same ratio as champion. Independent lane, same result.

### age10 (single) — the documented FAILURE also reproduces

| arm | n IS/OOS | IS net | doc | OOS net | doc |
|---|---|---:|---:|---:|---:|
| baseline | 130 / 76 | +435.7 | +435.7 | +43.2 | +43.2 |
| half | 118 / 71 | +418.2 | — | +28.0 | +28.0 |
| half+delay1 | 117 / 71 | +422.6 | +422.6 | +27.5 | +27.5 |

## The one thing that must not be glossed

`half+delay1` was independently **causality-audited** (Stage 19, CHECKLIST
24.24): a strict prev-bar MFE gate produces *identical* results
(champ IS 466t/+429.63, OOS 271t/+89.78). No same-bar leak, no retroactive
rewrite. So this is not a leak artifact — it is real, and it is causal.

## What this does to the audit

`method/IS_IT_RIGHT.md` concluded the shipped book is fragile: OOS mean p=0.199, three
of 279 trades carrying the result, 53.2R maxDD, 15-trade losing streak. **The
stack addresses both halves of that at once on the shipped lane:**

| | shipped | STACK | change |
|---|---:|---:|---|
| OOS net | +70.2 | **+110.5** | +57% |
| OOS maxDD | 53.2 | **30.6** | −42% |
| OOS PF | 1.34 | **1.62** (skipD) | +21% |
| OOS calmar | 0.66 | **1.47** (skipD) | +123% |
| IS net | +325.8 | **+429.6** | +32% |

And it does so **without removing a single entry in IS** (n stays 500 on
`skip_decisive`; `half+delay1` only changes exits). That matters for Rule 18 —
the slot-cascade that killed `exp_5m_confirm` cannot apply to an exit-side
change.

## Why it is still not deployed

Three real reasons, none of which is "it doesn't work":

1. **Forward n = 5/50.** The untouched forward slice has five trades against a
   pre-registered `n ≥ 50`. Every candidate in this programme is blocked on
   that, this one included. It is the binding constraint, not a judgement.
2. **age10 is destroyed.** STACK takes age10 OOS from +43.2 to −0.3. This is a
   multi-only change. Adopting it on multi means knowingly retiring the smoothest
   curve in the repo (age10: DD 8.6, PF 7.93) — or accepting that the two lanes
   are no longer interchangeable, which is a portfolio decision, not a tweak.
3. **`skip_decisive` fires 0 times in IS on multi.** A virtue (it cannot overfit
   the IS era — it literally cannot fire there) and a vice (its OOS evidence
   rests on 57 trades removed from one era, and the OOS has been inspected
   heavily across this programme).

## The methodological note, because it is the same mistake again

My first run of this harness reported **10/30 reproduced and 20 mismatches**.
That was wrong, and it was my bug: I put champion's expected values in a single
table and applied it to all three lanes. Every one of those 20 "mismatches" was
in fact an exact reproduction of that lane's own documented number.

Recorded because it is the third time in these logs that a reporting-layer error
would have produced a confident wrong conclusion if not checked — the first was
`boot()` testing against zero instead of the control (log 111), the second was
`exp_sizing_combo.run` discarding `five_m_stats` and reporting `candidates=0`
for a gate that was demonstrably firing. **When a harness disagrees with a
document, the harness is the suspect first.**

## Recommendation

* **The stack book is the answer to "improve the shipped one."** Bigger than
  anything logs 109–112 produced, on the lane we ship, improving net *and*
  drawdown together, already causality-audited and reproducible to the decimal.
* **It needs a decision, not more research.** The blockers are the forward-n
  gate and the age10 tradeoff. Neither is answerable by another backtest.
* **Do not stack the sizing queue on it yet.** All five sizing candidates
  (M2, sMZX, uMZX, ramp_mag, count_linear) key off `cur_mag_atr`, and
  `method/CAPITAL_STAGE_PLAN.md` §3 records the bridge test as **failed** — 46.5%
  agreement at order-send time against a 95% bar. They are not live-computable
  as measured. The stack has no such problem, which is precisely why it is the
  right next move.
* **No production change made.** `backend/` untouched. All three flags remain
  default 0.

| skip_decisive | 119 / 47 | +425.3 | +425.3 | +16.0 | +16.0 |
| **STACK** | **109 / 46** | **+422.3** | — | **−0.3** | — |

**age10 STACK OOS is −0.3R.** The stack destroys the single config outright.
This is the sharpest constraint in the document and not a rounding detail.
