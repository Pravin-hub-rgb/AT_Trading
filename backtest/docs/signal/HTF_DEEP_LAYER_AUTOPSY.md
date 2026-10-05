# Deep HTF-Layer Autopsy (Bybit BTCUSDT perpetual only)

Every prior autopsy measured the **15m LTF trade ledger**. This one measures
the **1h HTF parent layer itself**, plus the causal mapping from a parent HTF
campaign onto its child LTF trades.

Scope: BTCUSDT Bybit perpetual. IS 2023-2026, true OOS 2021-2022. 7 references.
Read-only; no production or engine change.

Harness: `backtest/tests/exp_thesis_htf_deep_atlas.py`
JSON: `_thesis_htf_deep_atlas_is.json`, `_thesis_htf_deep_atlas_oos.json`

## Correction applied before reporting

The first run reported `map 0.0%` on every row. Cause: `parent_health_at()`
was passed the **child** LTF timestamp but computed its 1m scan start from
`entry_ts + 3600`, always after the child entry. `end < start` held for every
trade, so all trades resolved to `no_parent` and Stages 67/68 were built on an
empty join. Fixed by passing the **parent's own** entry timestamp; coverage
verified 0.0% -> 99.7-100% before the reported runs. Pre-fix Stage 67/68
numbers are invalid and were discarded.

## Stage 65 - HTF window anatomy

IS counts: flip 355, decisive 331, b2 309. OOS: flip 204, decisive 210, b2 194.
Median duration by close reason (OOS): `sl` 17.6h, `target` 36.4h.
Median flip-window gap: IS 24.5h, OOS 25.8h. Direction-switch rate: IS 50.6%,
OOS 44.8%.

**Caveat:** HTF windows use a fixed 3R target and 16-day cap, so R by outcome
is near-degenerate (`sl` -1.0R, `target` +3.0R, `time` ~+1.0R). Stage 65 R
averages carry little information; duration, MFE/MAE and Stage 66 forward
excursions are the informative fields.

## Stage 66 - Window-death reversion vs placebo (strongest result)

P(opposite >=1R) after window close, vs unconditional base-rate placebo built
from the same 1m data at median window risk. Identical across all 7
references (HTF layer is config-independent). OOS:

| close reason | h6 | h12 | h24 | h48 | h72 |
|---|---|---|---|---|---|
| `sl` | 0.244 (+0.093) | 0.304 (+0.049) | 0.427 (+0.046) | 0.520 (+0.013) | 0.591 (+0.013) |
| `target` | 0.313 (+0.162) | 0.405 (+0.149) | 0.557 (+0.177) | 0.618 (+0.112) | 0.672 (+0.094) |
| `time` (16d) | 0.000 (-0.151) | 0.000 (-0.255) | 0.074 (-0.306) | 0.074 (-0.433) | 0.074 (-0.504) |

Placebo: h6 0.151, h12 0.255, h24 0.380, h48 0.507, h72 0.578.

Two opposite conclusions:

- **Target-capped windows genuinely revert** - above placebo by +0.09 to
  +0.18 at every horizon.
- **Time-capped (16-day) windows do NOT revert** - below placebo everywhere,
  reaching -0.50 at h72, with h12 P=0.000. A window that died of old age has
  already spent its volatility; there is no reversion edge to harvest.

## Stage 67 - Window-age decay of child LTF value

Gross R by causal age of the governing HTF window at entry. **Young windows
are negative in 12/12 cells** (3 references x 2 eras x 2 young buckets):

| scope | reference | 0-6h | 6-12h |
|---|---|---|---|
| IS | champion multi | n=42 avg -0.135 | n=29 avg -0.427 |
| IS | utcsat multi | n=43 avg -0.155 | n=27 avg -0.736 |
| IS | pure single | n=35 avg -0.343 | n=27 avg -0.210 |
| OOS | champion multi | n=17 avg -0.148 | n=22 avg -0.249 |
| OOS | utcsat multi | n=15 avg -0.101 | n=21 avg -0.227 |
| OOS | pure single | n=18 avg -0.221 | n=15 avg -0.236 |

Past 12h it is era-dependent and not a stable gate: `12-24h` is +1.035 (IS
champion) but -0.040 (OOS champion); `336h_plus` is +3.750 (IS) vs -0.800 (OOS).

**Actionable gap:** `fullstack_wage10_cd0_single_sw10` already carries
`exp_wage_h=10`, but `champion_multi_sw10` and `utcsat_multi_sw10` have **no**
window-age gate. This is the first quantified justification for giving the
multi references the protection the single reference already has.

## Stage 68 - Parent HTF health (marked R) at LTF entry

Child value peaks in the mildly-positive parent zone. IS champion: `<-0.5R`
+1.713 (n=32), `-0.5..0` +0.110 (n=117), `0..0.5` **+1.444** (n=129),
`0.5..1.0` **+1.560** (n=96, WR 44.8%), `1..3` +0.322 (n=125). OOS champion:
`0..0.5` +0.759, `0.5..1.0` +0.878, `1..3` +0.101.

The `0.0-1.0R` band is best in both eras and all references; value decays past
1R and the deep-negative bucket is inconsistent. Context, not a safe gate.

## Stage 69/70 - Competing window arbitration

Flip and b2 window sets overlap almost completely yet disagree on direction
about half the time: IS 109,217 overlapping pairs (54,663 same-dir vs 54,554
opposite-dir); OOS 39,298 pairs. The HTF layer is effectively two
near-independent chains with a regime router choosing between them - "the HTF
window" is not a single object.

## Stage 71 - Consecutive-window sequence

Tautological: with a fixed 3R target and 16-day cap, outcome->R is
near-deterministic, so `next_window_r` mostly restates the outcome mix. No
independent signal; not used for conclusions.

## Verdict

Descriptive, no production change. Three usable findings:

1. **Window-death asymmetry (highest value).** Target-capped windows revert
   above placebo; time-capped windows sit far below and offer no reversion.
   Any HTF "dead window" concept must distinguish the two.
2. **Young-window decay.** 0-12h child entries negative in 12/12 cells, and
   the multi references lack the age gate the single reference already has.
   Clearest candidate for one narrow path-true test.
3. **Parent-health sweet spot.** Child value peaks when the governing parent is
   +0.0 to +1.0R marked, decaying past 1R.

Stage 67 warrants exactly one pre-registered path-true test (`exp_wage_h` on
champion/utcsat multi); stages 65/66/70/71 remain context.

## Path-true test outcome (Stage W, 2026-09-25) — EXHAUSTED

The single pre-registered test above was run: `exp_wage_h` in {6,10,12,24} on `champion_multi_sw10` and `utcsat_multi_sw10`, IS + OOS, identity IDENTICAL (`exp_wage_multi_pathtrue.py`, CHECKLIST 24.70). **Result: FAIL on the strict pre-registered rule (same wage, dNet>0 on all 4 cells).** IS is negative for every arm on both lanes (champion w6 -28.1 / w10 -17.1 / w12 -32.1 / w24 -81.9; utcsat -40.8 / -24.9 / -7.4 / -82.1) and IS maxDD inflates (champion 17.8 -> 25.0). OOS: champion negative for all arms; utcsat alone positive (w10 +20.6, w12 +17.4) = era-flip. w24's -81.9/-82.1 exactly replicates the anchor-audit -82R DEAD row.

**Reading:** the S67 0-12h buckets are descriptively negative in 12/12 cells, but path-true gating removes those trades AND re-times the multi-position chain (exp43 removal-vs-chain-shift mechanism), flipping the sign. Descriptive bucket averages are not path-true gates. **Wage family is now CLOSED on champion/utcsat multi; the 24.69 open item is exhausted.** No production change.


## Stage X outcome (2026-09-25) - break-quality measures: 4/5 era-flip, one conditional-pass sizing flag

Phase 1 (`exp_htf_break_measures.py`, fixed pre-set bins, measures attached
causally at window open, child trades inherit the governing window, mapping
coverage 99.8-100%):

- **vol_ratio / body_atr / disp_atr / b1_gap: era-FLIPPED, dead.** vol_ratio
  <0.75: IS avg -0.147/-0.121 vs OOS +1.459/+1.649 (the BEST bin OOS, both
  lanes). body_atr 1.0-1.5 is the worst IS bin but a good OOS bin, while <0.5
  is good IS / worst OOS. disp_atr mirrors body_atr. b1_gap <8 is IS-bad /
  OOS-best (and stale-B1 gating is a closed family regardless).
- **risk_pct (window stop distance / entry):** bin [1.0,2.0) is below-rest
  average in 4/4 cells but the band nets POSITIVE in IS (champion +65.2,
  utcsat +94.6) -> a skip-gate on it fails upfront by construction. Bin <1.0
  is the top bin in 4/4 cells (IS +0.74/+0.92 avg, n=46/39; OOS +10.19/+8.53
  avg, n=7/9 - small).

Phase 2 (`exp_htf_break_sizing.py`, post-process, pre-registered pass = dNet>0
AND curve_better in all 4 cells):

- **A (x1.5 size where parent risk_pct < 1.0): PASS 4/4 WITH THE
  PRE-REGISTERED SMALL-N CAVEAT (OOS flagged n=7/9).** dNet +23.9/+36.6
  (champion IS/OOS), +23.4/+39.5 (utcsat); curve_better True x4; books
  +325.8->+349.6 / +358.9->+382.3 IS, +70.2->+106.8 / +60.2->+99.7 OOS;
  dDD IS -2.0/-1.0 (worse), OOS +2.8/+1.1 (better).
- **B (skip parent risk_pct in [1.0,2.0)): FAIL era-flip** (IS -65.2/-94.6,
  OOS +19.6/+19.1) -> gate closed.
- **C (skip parent vol_ratio < 0.75): FAIL era-flip** (IS +8.7/+5.8,
  OOS -46.7/-52.8) -> gate closed.

**Reading:** break-bar quality at the 1h window level does not generalize
across eras on this architecture - same lesson as 24.70 (descriptive buckets
flip once removal re-times the chain). The single surviving arm is a sizing
flag whose OOS evidence rests on 7-9 trades: same class as the Stage O M2
flag but with far thinner OOS support, so it stays conditional (small-n
caveat travels with it) and is not a production flag. Adoption decision is
the user's (RESEARCH POLICY). CHECKLIST 24.71 / LOG 71.
