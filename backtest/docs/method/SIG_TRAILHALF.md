# exp_trail_half on the single-position sig ladder: same failure, except once

Date: 2026-10-07. Engine post-C17. Harness: `exp_sig_trailhalf.py`.
Control: `fsent_sig_full` (no trail_half). All books `max_positions=1`.

## Why this was re-measured rather than assumed

On the multi book, `exp_trail_half` earned **+42.5R OOS** and was rejected:
removing the top five trades collapsed the advantage to **+0.77R**, and drawdown
rose 2.37x. That verdict was reached by the framework in
`finding optimal book.md`, not by net R.

Three sig books carry `exp_trail_half=1` and all three build on `fsent_sig_full`,
which does not have it — so the knob is isolable here. **But the base is a
different base**: `fsent_sig_full` is `max_positions=1`, and closing half a
position interacts with a position-slot gate differently than it does on a multi
book. So the champion's verdict does not transfer and had to be re-measured.

## The knob, isolated (OOS, knob forced to 0 on the same book)

| book | knob ON net | knob OFF net | Δ net | Δ net after top-5 removed | Δ drawdown |
|---|---:|---:|---:|---:|---:|
| `fsent_sig_trail_delay1` | +182.00 | +196.10 | **−14.10** | **−32.82** | +0.50 |
| `fsent_sig_half_crossed` | +142.10 | +130.30 | +11.80 | **−10.90** | −0.10 |
| `fsent_both_trail_half` | +96.90 | +71.30 | +25.60 | **+10.48** | **−2.80** |

In sample the same knob is worth **+144.70R, +145.30R and +34.20R** — enormous.

## Two of the three fail the same way the multi book failed

**`fsent_sig_trail_delay1`** — the knob *costs* 14R out of sample and 33R once the
tail is removed. Its +418.50R in sample is not a knob effect worth having.

**`fsent_sig_half_crossed`** — +11.80R out of sample, but **−10.90R** after
removing the top five. The entire gain is the tail. Identical failure mode to the
multi book, confirmed on a different book with a different position gate.

## The third is a genuinely different result — and it is still not adoptable

**`fsent_both_trail_half`** is the one book where the knob is real:
**+25.60R out of sample, +10.48R of which survives removing the top five**, and
drawdown **improves by 2.80R**. That is a knob that helps and is not a tail
artifact, which is more than any other trail_half arm in the repo has shown.

**The book around it is still not adoptable**, and that is the part that matters:

| | net | top5 share | minus top 5 | minus top 10% |
|---|---:|---:|---:|---:|
| `fsent_sig_full` (control) | +194.4 | 55.0% | +87.4 | +10.6 |
| `fsent_sig_trail_delay1` | +182.0 | 69.1% | +56.3 | −0.0 |
| `fsent_sig_half_crossed` | +142.1 | 77.6% | +31.8 | +19.0 |
| `fsent_both_trail_half` | **+96.9** | **105.7%** | **−5.5** | **−46.0** |

Its top five trades are **more than its entire net**. Remove them and the book is
negative. A real knob inside a fragile book is still a fragile book.

## The honest summary

- The knob is **not** transferable from the multi book, and on two of three sig
  books it fails the same tail test that closed it there.
- On `fsent_both_trail_half` the knob is **real** — the first trail_half arm in
  the repo where the benefit survives tail removal. Worth recording, because if
  the trail_half idea is ever revisited, that is the arm to start from.
- **No sig book is promoted.** The top of the sig ladder remains
  **`fsent_sig_full`** — +194.4R OOS at **6.96R drawdown**, and unlike the others
  it stays positive with its top 10% removed (+10.6R).

## One caveat on the isolation

`fsent_sig_trail_delay1` also carries `exp_trail_delay` and
`fsent_sig_half_crossed` also carries the decay gate, so their headline nets
differ from the control for two reasons at once. The "knob OFF" rows force only
`exp_trail_half` to 0 and are the numbers to judge the knob by — the ones in the
first table above.

**Nothing changed. No book promoted, no pins touched.**