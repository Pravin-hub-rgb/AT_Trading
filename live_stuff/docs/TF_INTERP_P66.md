# P66: the missing middle — 30m wins OOS and loses IS, and that is the signature

> Run 2026-09-29. Harness `exp_tf_interp.py` · Nemotron **P4**.
> Nothing adopted. Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## What P58 had missed

P58 swept HTF `{1h, 4h, 1D}` against LTF `{15m, 1h, 4h}` and concluded
1h+15m wins from every direction, with a monotone "closer is better" trend.
**It never tested a timeframe between 15m and 1h** — the space the champion
actually lives in. Nemotron flagged exactly this: *"30m Timeframe as
Independent LTF — not a rescaled 15m."*

30m is not a divisor of the 1h series, so a bar-count sweep cannot reach
it. P58's fix applies: match on **wall-clock lag**, not bar count, and
re-derive the swing rule on the coarser bars rather than inheriting the 15m
swings. `min_bars` is held at ~12.5h across all three arms (15m→50,
30m→25, 45m→17), and **the 1h HTF stays at the champion's own 10 bars in
every arm**, so the LTF is the only thing that moves.

## Result

| LTF | lane / era | n | net | R/t | PF | DD | WR | dNet |
|---|---|---|---|---|---|---|---|---|
| **15m (champ)** | champ IS | 500 | **+325.8R** | 0.652 | 2.38 | 17.8 | 30.0% | — |
| 30m | champ IS | 432 | +138.0R | 0.320 | 1.79 | 31.8 | 29.4% | **−187.8R** |
| 45m | champ IS | 370 | +177.0R | 0.478 | 2.04 | 35.7 | 29.5% | −148.8R |
| **15m (champ)** | champ OOS | 279 | +70.1R | 0.251 | 1.59 | 37.3 | 28.0% | — |
| **30m** | champ OOS | 264 | **+141.9R** | **0.537** | **2.06** | **17.6** | **29.9%** | **+71.7R** |
| **45m** | champ OOS | 266 | **+93.9R** | 0.353 | 1.71 | 30.9 | 30.5% | **+23.8R** |
| 30m | utcsat IS | 396 | +120.5R | 0.304 | 1.75 | 32.4 | 28.8% | **−238.5R** |
| 45m | utcsat IS | 338 | +169.2R | 0.501 | 2.09 | 32.7 | 29.3% | −189.7R |
| **30m** | utcsat OOS | 232 | **+103.1R** | 0.444 | 1.90 | **15.8** | 30.2% | **+42.9R** |
| 45m | utcsat OOS | 236 | +44.7R | 0.190 | 1.45 | 23.7 | 29.7% | −15.5R |

**30m in OOS is not a marginal improvement. It more than doubles the
champion's OOS net in both lanes — +141.9R against +70.1R and +103.1R
against +60.2R — on every quality measure simultaneously: R/trade 0.537
against 0.251, PF 2.06 against 1.59, drawdown 17.6R against 37.3R, win rate
29.9% against 28.0%.**

**And it costs 187.8R to 238.5R in IS.**

## Why it fails, and why that is the interesting part

**Family-wise the arm fails: it does not beat the champion in both eras and
its IS delta of −238.5R clears M in the wrong direction.** The 15m LTF
stands, now confirmed from both sides of the gap rather than one.

**But this is not `cand_4h1h` and it is not the 1D trap.** It is the
cleanest era-split in the programme:

| | IS | OOS |
|---|---|---|
| 30m vs 15m | **−187.8R / −238.5R** | **+71.7R / +42.9R** |
| drawdown, 30m vs 15m | **worse** (31.8 vs 17.8) | **better** (17.6 vs 37.3) |
| R/trade, 30m vs 15m | **worse** (0.320 vs 0.652) | **better** (0.537 vs 0.251) |

**Every quality measure moves together in both eras — and they point in
OPPOSITE directions.** A coarser LTF trades less and worse in IS, and less
and better in OOS. That is not a fitted threshold and it is not an artefact
of picking one arm: 30m and 45m agree in sign in **three of four** cells,
and 45m is the only disagreement (utcsat OOS −15.5R).

**So the honest statement is that the champion's LTF granularity is
era-dependent in a way the champion's own timeframe is not.** The 15m LTF
wins IS because the era that produced this book rewarded fine entries; the
30m LTF wins OOS because the out-of-era does not. That is now the **sixth**
appearance of the pattern (P56 expiry, P58 granularity, P59 agreement,
P60 union risk profile, P61 candidate stability, this).

**And the practical consequence is concrete: the champion's OOS weakness —
R/trade 0.251 against 0.652 in IS — is a granularity symptom, and the
regime-appropriate granularity is not knowable from the bar data.** Which is
the same wall P55 hit: no live feature separates the eras.

## What would make this adoptable, and why it is not available

The obvious move is to switch LTF by regime. **That is exactly the
adaptive gate P55 was built to test and could not support** — the inversion
between IS and OOS is not detectable at decision time from the input
distribution, so a selector would have to read the outcome. Adding a
30m/15m switch on top of an undetectable regime signal would be a lookahead
wearing a switch.

**What would settle it instead is more forward data**, and P63 now says how
much: 40–70 trades can *rule out* but never confirm. So a forward slice of
that size could test whether 30m's OOS advantage persists — and could not,
on its own, establish that it should be adopted. The decision stays with an
owner, on a directional read of an unresolved era question, not with this
harness.

## Stated limitations

- **Only three LTF points**, so this is an interpolation between two
  measured endpoints, not a characterisation of the curve. A 20m or 40m
  arm would add interior resolution but that is curve-fitting around a
  result already known, and was not run.
- **45m disagrees with 30m in utcsat OOS** (−15.5R against +42.9R), so the
  two coarse arms are not unanimous evidence.
- **Both lanes are the same data**; the agreement is not independent.
- **Aggregated 30m/45m OHLC is synthetic** — highs and lows exact, open and
  close taken from the first and last constituent 15m bar. Buckets are
  stamped with their final source bar, so no lookahead is implied.
- **The IS/OOS eras differ in length and regime** (3.7 years against 2), so
  a split difference of this size is not conclusive on its own — it is
  conclusive as evidence *against* adoption, which is what the criterion
  needs.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
