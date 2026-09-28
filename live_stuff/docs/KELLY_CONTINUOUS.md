# CONTINUOUS KELLY — the repo's first principled sizing number, and the
# halt hypothesis was half wrong.

Date: 2026-09-28. `exp_kelly_continuous.py` → `_kelly_continuous.json` 73.8s.

## Part A — is the loss-halt the cause of the era split in autocorrelation?

`exp_quant_autopsy.py` found IS ACF(lag1) +0.0651 (inside band) vs OOS
+0.4981 (four times outside). The hypothesis was that
`max_consecutive_losses=3` causes it: in IS the halt fires often and chops
the loss sequence into runs of ≤3, mechanically de-correlating; in OOS it
fires less and raw correlation survives.

**The hypothesis was half right, and the half that was wrong is the half
that mattered.**

| era | halt k=3 (shipped) | halt k=0 (off) | Δ ACF1 |
|---|---|---|---|
| IS | +0.0651 **inside** ±0.0877 | +0.1317 **outside** ±0.0830 | **+0.0666** |
| OOS | +0.4981 **outside** ±0.1173 | +0.4813 **outside** ±0.1096 | −0.0168 |

- **IS: the halt IS the mechanism.** Disabling it moves ACF1 by +0.067 and
  pushes the book from inside the band to outside it. The shipped halt
  genuinely de-correlates IS.
- **OOS: the halt is NOT the mechanism.** Disabling it moves ACF1 by −0.017
  — nothing. The correlation is +0.498 either way.

**So the OOS autocorrelation is real.** It is not an artefact of how often a
rule fires, and it is not explained by anything in this file. It is a
property of the traded sequence in that era, and it is the single largest
unexplained structure found in this session.

That is stated as a finding, not a rule. An effect present in one era and
absent in the other is not something to trade on, and the same-sign bar
that closed a dozen other directions closes this one.

## Part B — continuous Kelly, long-run corrected

Binary Kelly `2p−1` was negative in both eras and is the wrong functional:
the book is heavy-tailed (17 trades ≥ +10R carry IS), so mean ≠ win rate.
The correct even-odds criterion is `f* = μ/σ²`, and with serially
correlated bet returns σ² must be the **long-run** variance (Newey-West /
Bartlett, automatic bandwidth `K = ⌊4(n/100)^(2/9)⌋`):

    σ²_LR = σ² · (1 + 2·Σ_{k=1..K} (1 − k/n)·ρ_k)

| | μ (R/trade) | σ² naive | f* naive | σ² long-run | **f* corrected** |
|---|---|---|---|---|---|
| IS (500t) | — | — | — | — | **+0.0409** |
| OOS (279t) | +0.37894 | 25.4998 | +0.0149 | 57.2730 | **+0.0066** |

**The correction is not cosmetic in OOS — it halves the bet twice over.**
ρ₁ = +0.4981 inflates the long-run variance from 25.50 to 57.27, which
**shrinks the bet fraction by 55.6%** (+0.0149 → +0.0066). A naive
`μ/σ²` on the OOS book would have recommended more than twice the correct
size. That is precisely the failure mode the arXiv:2003.02743 result is
about, and it is why Part A mattered enough to run.

Fractional (the only actionable form — full Kelly on an estimated edge is
famously over-bet):

| | full | half | quarter |
|---|---|---|---|
| IS | +0.0409 | **+0.0205** | +0.0102 |
| OOS | +0.0066 | **+0.0033** | +0.0008 |

## What the answer to "what size" actually is

**Half-Kelly says bet 0.2% (IS) / 0.33% (OOS) of bankroll per trade.**

That is the first number in this repo derived from the mathematics rather
than inherited or swept. It is also a *small* number, and the smallness is
the finding: at ~0.3% per trade and ~136 trades/year, compounding does
almost nothing, which is consistent with the book's actual character — a
low-win-rate, tail-concentrated book whose edge is real but not
geometric.

**It is not a recommendation to size up, and two things are still missing
before it means anything:**

1. **The two eras disagree by 6×** (+0.0205 vs +0.0033). A sizing rule
   needs one number, and averaging them or picking the flattering one is
   exactly the multiplicity this repo forbids.
2. **The engine has no size channel.** `v18_streak_halt.py` has zero hits
   for equity/size/notional — this repo's own handover lists that as an
   open engineering item. There is nowhere to *apply* f* even if it were
   agreed.

## Verdict

- **Part A: hypothesis half-refuted, and the surviving half is the
  interesting one.** IS's near-zero ACF is manufactured by the halt; OOS's
  +0.498 is not manufactured by anything and remains unexplained.
- **Part B: a real, first-principles sizing number exists and is small.**
  The autocorrelation correction is material (−55.6% in OOS), so ignoring
  it would have doubled the bet on exactly the era where the book behaves
  differently.
- **Neither is adoptable.** Part A fails the same-sign bar; Part B fails on
  era disagreement and has no execution channel.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
