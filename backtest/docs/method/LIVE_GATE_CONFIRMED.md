# P3-C — `live_R >= 0` confirmed as a real gate. It survives a live re-run.

`exp_live_gate.py`. This is the confirmation P3-B's post-hoc screen could
not provide: the gate now sits **inside the engine loop**, the engine never
"decides to skip", and trade count, sequence and maxDD all change the way
they would in production.

## How it was done, and why the numbers are trustworthy

`to_intervals` (v18_streak_halt.py:226) turns each 1h HTF trade into a
5-tuple `(start, end, dir, entry_px, sl)`, and the LTF layer may only enter
while a matching interval contains its timestamp. So "only trade while the
1h leg is in profit" is exactly equivalent to **splitting each window into
its maximal sub-runs where `live_R >= floor`** and emitting each sub-run as
its own interval with the same dir/px/sl. Same representation, finer
partition, no new concept and no trading logic touched.

**Identity gate, run first, and it passed exactly:**

| | original | patched (floor=None) |
|---|---|---|
| IS | 396t +227.5R WR 26.3% PF 1.87 tm −0.288 DD 19.6R | **byte-identical** |
| OOS | 242t +22.7R WR 24.4% PF 1.14 tm −0.334 DD 25.6R | **byte-identical** |

If this had not matched, every arm below would have been void.

## The result

| floor | IS | OOS | both? |
|---|---|---|---|
| None (control) | 396t +227.5R PF 1.87 | 242t +22.7R PF 1.14 | — |
| −0.50 | 350t +182.9R PF 1.79 | 218t +18.2R PF 1.13 | no |
| −0.25 | 293t +220.8R PF 2.16 | 194t +23.2R PF 1.18 | MIXED |
| **−0.10** | **254t +236.4R** WR 29.1% PF 2.48 | **165t +25.1R** WR 23.0% PF 1.22 | **YES** |
| **+0.00** | **224t +257.1R** WR 31.2% PF 2.88 | **141t +33.5R** WR 24.1% PF 1.36 | **YES** |
| +0.10 | 196t +215.0R PF 2.77 | 131t +10.7R PF 1.12 | no |
| +0.25 | 165t +197.2R PF 2.96 | 108t +10.0R PF 1.13 | no |
| +0.50 | 111t +170.4R **WR 37.8% PF 3.80** | 64t **−11.8R PF 0.74** | no |
| +0.75 | 66t +73.8R PF 3.00 | 38t −10.7R PF 0.62 | no |
| +1.00 | 32t +19.5R PF 2.12 | 20t −9.9R **PF 0.28** | no |

### `floor = 0.00`, in full

| | IS | OOS |
|---|---|---|
| net | +227.5 → **+257.1R** | +22.7 → **+33.5R** |
| trades | 396 → 224 (**−43%**) | 242 → 141 (**−42%**) |
| WR | 26.3 → **31.2%** | 24.4 → 24.1% |
| PF | 1.87 → **2.88** | 1.14 → **1.36** |
| trimmed mean | −0.288 → **−0.015** | −0.334 → −0.360 |
| **maxDD** | **19.6 → 10.3R** | 25.6 → 27.2R |

**IS improves on every axis including drawdown, which halves.** OOS
improves on net and PF and trades 42% fewer, but **maxDD worsens slightly
and trimmed mean does not move** — so the OOS gain is a smaller sample
getting a bit luckier, not a better book. That asymmetry is the honest
reading and it is why this is a candidate, not an adoption.

## What the sweep proves that the screen could not

**The peak is exactly at zero, and it is a peak, not a plateau.**
`+0.00` is the local maximum in **both** eras simultaneously — IS +257.1R
and OOS +33.5R both beat every neighbour on either side. That is what a
real effect looks like. It also independently reproduces what the
post-hoc screen found, from a completely different code path, which is the
strongest cross-check available today.

**And the inversion is confirmed as a real inversion, not a screening
artefact.** `+0.50` posts the *best* IS numbers in the whole sweep (WR
37.8%, PF 3.80) and simultaneously the worst OOS (PF 0.74). `+1.00` reaches
**PF 0.28** OOS. The post-hoc screen said "demand more confidence and it
inverts"; the live engine says the same thing with a different trade
sequence and different drawdowns. **That is now settled twice.**

**W2 is fully closed.** `r_touch` lost 130R at +1.5R because +1.5R is deep
into the inverting region. Not noise, not a bug — over-asking, and now
measured rather than inferred.

## What it does NOT prove

1. **OOS maxDD got worse** (25.6 → 27.2R) and OOS trimmed mean did not
   improve. The OOS case is 141 trades; the edge is real in direction but
   thin in robustness.
2. **The grid was pre-registered but written with the feature in mind**, so
   this is not a family-wise-corrected result. `0.00` is a round number
   found on a grid — which is the single most suspicious thing about it, and
   also the most natural one (it needs no fitting at all: "don't trade
   while the HTF leg is under water").
3. **One seed, two eras.** No forward slice has been touched, correctly —
   P5's null must exist before that slice means anything.
4. Not tested: interaction with `mode="atr_high"`, with
   `max_consecutive_losses=3`, or with any other champion knob. This gate
   is orthogonal and could plausibly stack — or could double-count.

## Recommendation

**Worth carrying as the leading candidate; not yet adopted.** The next
thing that would actually move it from candidate to result is P5 (the base
book null), because +29.5R IS has to be compared against what a reshuffle
of the same book produces. If M exceeds 29.5R, this is nothing.
