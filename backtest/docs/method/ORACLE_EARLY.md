# P3-B — reading the oracle early. One arm survives both eras.

`exp_oracle_early.py`. Full matrix, no cells skipped: live-R floor, live-R
ceiling, window age, the 2-way interaction, and two falsifier controls.
Pre-registered falsifier is in the file's docstring and was written before
the run.

## The feature

`live_R(t) = dir × (px_1m(t) − htf_entry_px) / |htf_entry_px − htf_sl|`,
evaluated at each 15m trade's entry from the last 1m close at or before it.
**Causal by construction** — no arm can see past its own entry. The whole
matrix is a post-hoc filter over the engine's own trades, so the engine ran
once per era and every arm is compared on the *same* trade universe.

Control: IS 386t +229.0R (WR 25.9%, PF 1.89) · OOS 204t +19.8R (WR 23.5%,
PF 1.15).

## ✅ The survivor: don't enter while the 1h leg is still under water

**`live_R >= 0.00`** — take 15m trades only when the 1h leg is not below
its own entry.

| | n kept | net | **WR** | **PF** | trimmed mean |
|---|---|---|---|---|---|
| IS | 226 (59%) | +177.2R | **25.9 → 30.1%** | **1.89 → 2.27** | −0.292 → **−0.185** |
| OOS | 122 (60%) | +24.8R | **23.5 → 27.0%** | **1.15 → 1.32** | −0.352 → **−0.244** |

**Both eras, same threshold, same sign, on every metric that matters** —
win rate, profit factor, and trimmed mean all improve together. The keep
rate is nearly identical (59% / 60%), so it is not a threshold that happens
to fit one era.

**It also passes the pre-registered falsifier.** The falsifier was: beat
window-open-only information. Window-open direction alone gives
`long +166.3R / short +62.7R` (IS) and `long +1.6R / short +18.2R` (OOS) —
no consistent edge from direction. And the random-removal placebo at the
same trade count (4,000 draws) reaches **p95 = +207.6R** in IS, which the
+177.2R arm does **not** beat. So on raw net R the arm is *not* remarkable
in IS — but its **WR and PF are what carry it**, and a random subsample
cannot manufacture a WR jump from 25.9% to 30.1%. That distinction is the
result.

## ❌ Everything else failed, and the failure is informative

**Harder floors reverse sign.** `live_R >= +0.25` is −26.9R in OOS;
`>= +0.75` is −31.8R; `>= +1.00` is −30.6R with **PF 0.37**. In IS the same
arms look magnificent (+65.4R, PF 2.74 at +0.75). **The oracle's confidence
in IS is the opposite of its value in OOS.** A gate that requires the 1h
leg to be *deeply* profitable selects 15m entries that are late — chasing.

**The 2-way interaction is where the honesty is.** The best IS cell
(`live_R ∈ [0.25,0.75)`, `age > 3d`, n=28) shows **+65.2R, tm +0.897** —
flattering. The same cell in OOS (n=20) is **tm −0.152, net +65.2R on a
−4.0R book**. *A cell cannot be a finding if its era-mate inverts.* This is
exactly the failure the repo's graveyard documents, caught by printing
every cell.

**Window age is the bigger, simpler effect, and it also fails.** IS loves
`age > 0.5d` (+26.7R dNet, WR 27.2%, PF 2.25) and OOS agrees (+10.8R) —
the only age arm positive in both. But every *harder* age cut flips:
`age > 1.5d` is −13.5R in OOS, `age > 3d` is −10.0R. Same shape as the
live-R failure. **Both features have one real effect and then break.**

## The unified reading

**The finding is a boundary at zero, not a strength threshold.** Requiring
the 1h leg merely to be *not losing* helps in both eras. Requiring it to be
*winning* helps in IS and hurts in OOS. That is the signature of a
confirmation effect, not an oracle: a genuine oracle would let you demand
more confidence and get more edge. This one saturates immediately and
then inverts.

So the correct conclusion is narrower than P3-A implied: **the 1h layer's
real-time information is one bit wide — "is the 1h leg in profit or not" —
and nothing more.** The full 55.7%-WR / 8.6%-WR split from P3-A is
overwhelmingly hindsight. That is consistent with the cascade's negative
trimmed means everywhere: this is a book whose edge lives in its tail, and
tails are not knowable in advance.

## What this kills and what it opens

- **Kills:** W1's "prove-it-first" arm as originally framed. A +1R
  requirement is the failure mode, not the fix — that is the `age`/live-R
  curve turning over, measured.
- **Kills the strong form of P3-B.** The oracle is not readable early.
  Only its sign is.
- **Opens, honestly:** the `live_R >= 0` arm is the *only* candidate
  produced today that improves WR, PF and trimmed mean in both eras
  simultaneously. That is one cell worth confirming, not a family. It
  needs a pre-registered re-run as a live filter (re-running the engine
  with the gate, not post-hoc) before anyone believes it.
- **Resolves W2.** `r_touch` lost 130R because it demanded +1.5R — the
  exact demand this matrix shows inverts. It wasn't noise; it was
  over-asking.

## Caveats

1. Post-hoc filtering on one engine run. Legitimate for screening, **not**
   a confirmation — a live re-run is required.
2. The IS arm's raw net (+177.2R) sits *below* the random-removal p95
   (+207.6R). Only the WR/PF/trimmed-mean triple survives, and that is a
   weaker claim than it looks: deleting the worst 40% of trades will
   always raise a win rate.
3. Thresholds were pre-registered as a grid, but the grid was written with
   the feature in mind, so grid-wide significance is not claimed.
4. `keep%` matching across eras (59/60) is reassuring but not proof.
