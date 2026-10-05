# Regime Structure Autopsy (Stage Z1 descriptive + Z2 path-true) — added 2026-09-26

Origin: research round on regime-dependence / sideways detection / wick-vs-body magnitude /
rolling multi-day volume (ChatGPT discussion, user round 2026-09-26). Prior art is explicit:
15m ER20 gates (F6), entry-bar rvol gates, volume router, chop-band lane — all DEAD; shipped
machinery = engine `_chop_series_1h` + `atr_high` mode. The era-split autopsy (LOG 2026-09-24)
never included market-structure variables — that gap is what this stage fills, descriptive-first.

- Harness Z1: `backtest/tests/exp_regime_structure_autopsy.py` → `_regime_structure_is.json` / `_regime_structure_oos.json`
- Harness Z2: `backtest/tests/exp_regime_structure_sizing.py` → `_regime_structure_sizing_results.json`
- Identity gate IDENTICAL both runs; smoke PASS (351t/+211.7R); engine untouched (post-process).
- Lanes: champion_multi_sw10 / utcsat_multi_sw10 / fullstack_wage10_cd0_single_sw10 (fullstack = reference only).
- Causal cutoff `entry_ts + 900` (entry-bar close); all features from bars completed before cutoff.
- Tercile edges computed on IS pooled trades, applied unchanged to BOTH eras (OOS bucket shares then show true distribution shift).

## Z1 — features (24, all 1h plane)

| Family | Features |
| --- | --- |
| V1 chop | engine chop level (lb=14) 5 fixed bins; trailing-200 chop percentile |
| V2 efficiency | Kaufman ER20 / ER50 terciles |
| V3 swing churn | sw10-chain direction flips last 48h/96h (chain alternates ⇒ flips ≈ swing density); mean confirmed-swing duration 96h |
| V4 wick magnitude (user ask) | last 6/12×1h: % bars wick>body, >2×, >3×; median & max total_wick/(body+ε); Σwick/ATR14; direction-specific OPPOSING wick (upper for longs / lower for shorts) Σ/ATR14 + % opposing>body |
| V5 compression | median \|body\|/ATR14 (12 bars); 48h range %; small-body % (body/ATR<0.5) |
| V6 rolling volume (user ask) | 1h volume → UTC-daily: 7d/14d/30d sums, trailing-90d percentile of 7d sum (<20/20-80/>=80 bands), 7d÷prev-7d ratio, log10 absolute (no download; 1h CSV has volume both eras) |

**Pre-registered survivor rule (fixed before run):** same-sign top-vs-bottom tercile across all 4 rule cells (champion/utcsat × IS/OOS) AND monotone in ≥3/4 cells AND extreme buckets n≥15.

## Z1 — result: 3 of 24 SURVIVE

| Feature | Direction (better) | IS edge | Survivor check |
| --- | --- | --- | --- |
| `er50` | LOW ER50 = choppy tape wins | Q1 ≤ 0.0767 | same-sign ✓, mono 3/4 |
| `wick_gt3x_pct12` | HIGH wick>3×body share wins (rejection/indecision) | Q3 > 33.30 | same-sign ✓, **mono 4/4** |
| `vol7_prev7` | DECLINING 7d-vs-prev-7d participation wins | Q1 ≤ 0.846 | same-sign ✓, **mono 4/4** |

Pooled bucket tables (n / avgR, all three lanes):

```
er50            IS: <=0.08 +1.62 | 0.08-0.18 +1.22 | >0.18 +0.47
                OOS: <=0.08 +0.57 | 0.08-0.18 +0.43 | >0.18 +0.06
wick_gt3x_pct12 IS: <=25 +0.92 | 25-33.3 +0.96 | >33.3 +1.27
                OOS: <=25 +0.03 | 25-33.3 +0.39 | >33.3 +0.52
vol7_prev7      IS: <=0.85 +1.70 | 0.85-1.06 +0.90 | >1.06 +0.72
                OOS: <=0.85 +0.87 | 0.85-1.06 +0.26 | >1.06 -0.03
```

Notable near-misses (failed the pre-registered rule): `wick_body_max12`, `wick_atr12`
(same-sign but mono 2/4 — non-monotone mid-tercile spike), `flips48` (same-sign, mono 1/4,
n fail), `vol7d_pct90` (same-sign, mono 1/4), `small_body_pct12` (mono 2/4). All other
features era-flipped or patternless: chop level/percentile, ER20, flips96, dur96, all other
wick sub-features, med_body_atr, range48_pct, vol7d/log_vol7 absolute.

**Era-shift table (distribution, not payoff):** `range48_pct` — OOS puts 75% of entries in the
widest tercile vs 33% IS (2021-22 = wide-range era, consistent with ATR ~1.6-2× OOS);
`vol7d` — OOS 59% in the lowest volume tercile vs 33% IS (2021-22 lower absolute participation
than the 2024-25 mania); chop/ER/wick shares shift only mildly. **Across every feature, OOS
avgR is below IS within the same bucket** — structure explains within-era differences, it does
not explain the era level-shift itself (consistent with Study 2: OOS consistent with luck).

## Z2 — path-true sizing on the 3 survivors (pre-registered)

Pass = dNet>0 AND `curve_better` in all 4 cells (2 lanes × 2 eras); flags from causal features;
identity = same trade-key sequence; engine untouched.

| Arm | Rule | champion dNet IS/OOS | utcsat dNet IS/OOS | curve 4/4 | Verdict |
| --- | --- | --- | --- | --- | --- |
| A | ×1.5 size where `er50 ≤ 0.0767` (n 167/84, 142/81) | +110.3 / +17.3 | +110.5 / +23.4 | ✓ | **PASS** |
| B | ×1.5 size where `wick_gt3x_pct12 > 33.3` (n 121/70, 112/62) | +74.1 / +18.3 | +71.9 / +23.4 | ✓ | **PASS** |
| C | ×1.5 size where `vol7_prev7 ≤ 0.846` (n 166/81, 146/76) | +106.5 / +32.2 | +112.3 / +40.4 | ✓ | **PASS** |
| D | skip `vol7_prev7 > 1.064` (predicted FAIL) | −71.5 / +10.8 | −67.2 / +23.4 | ✗ | FAIL era-flip |

Equity details (flat → arm): champion IS DD 27.7→32.0 (A) but ulcer 14.62→12.38, calmar
3.202→3.713; champion OOS calmar 0.659→0.790/0.810/0.828; utcsat IS calmar 4.619→4.786/
5.293/5.245; utcsat OOS DD 29.4→29.8/29.9/33.2 with calmar 1.025→1.403/1.396/1.516. Arm D's
IS bleed (−71.5/−67.2, both curve False) despite positive OOS confirms the pre-registered
era-flip prediction — gate CLOSED.

## Risk statement / caveats (adoption = user's decision)

- **A/B/C are likely one correlated family** — low ER50 (chop), wick-heavy indecision candles,
  and declining 7d participation all describe the same "quiet contracting tape". Flagged shares
  (A ~33%, B ~24%, C ~33%) overlap heavily; stacking all three ×1.5 would double/triple-size the
  same trades. Deploy at most ONE flag, or cap combined exposure.
- ×1.5 on ~24-33% of trades ≈ +1.1-1.2× total exposure bump — same risk class as Stage X/Y arms.
- OOS dNet (+17..+40) rides the same weak OOS baseline (champion net +70, calmar 0.66); Study 2
  (LOG 76's neighbour, LOG 74) says the OOS edge overall is consistent with luck — these deltas
  inherit that caveat.
- Small-N: none (all flagged n ≥ 62).
- Tericile edges are IS-derived only (no OOS peek); bucket membership is fully causal.
- Pre-registered comparisons X vs Y vs M2 vs Z sizing candidates: COMPLETED 2026-09-26 -
  side-by-side in `method/EXPERIMENT_SUMMARY.md` (Comparison section at end of file).

## Z3 - volume-reduction gate sweep (trade-count control; user goal pre-registered)

User goal fixed BEFORE the official run: from ~500 trades get ~400ish (keep 70-90% of
book) with average R per trade SAME OR BETTER. Rule (G-RULE, pre-registered in
`exp_vol_threshold_gate.py` docstring): kept% in [70,90] AND avgNet/trade >= baseline
AND maxDD(R) <= baseline - all 4 cells (champion/utcsat x IS/OOS). Strict rule
(dNet>0 + curve_better 4/4) reported as reference (expected fail: every threshold
removes net-positive IS trades). Arms: keep `vol7_prev7 <= thr` for
thr in {0.846, 0.90, 0.95, 1.00, 1.064, 1.10, 1.15, 1.20, 1.25, 1.30} (None-features
kept, same semantics as arm D); removal-only post-process, survivor key order asserted,
identity gate IDENTICAL, smoke PASS 351t/+211.7R.

**G-RULE PASS: thr = 1.15 and thr = 1.20.** thr = 1.20 is the exact user target:

| thr | kept n (ch IS / uts IS / ch OOS / uts OOS) | kept% | avgNet/trade flat -> gate | maxDD flat -> gate | dNet IS / OOS |
| --- | --- | --- | --- | --- | --- |
| 1.20 | 398 / 360 / 216 / 196 | 80/79/77/78% | +0.652->+0.665 / +0.791->+0.829 / +0.251->+0.342 / +0.238->+0.386 | 27.7->27.0 / 21.2->19.7 / 53.2->38.2 / 29.4->20.8 | -61.1/-60.5 / +3.6/+15.5 |
| 1.15 | 376 / 346 / 205 / 189 | 75/76/74/75% | +0.652->+0.689 / +0.791->+0.874 / +0.251->+0.346 / +0.238->+0.397 | 27.7->27.1 / 21.2->20.4 / 53.2->38.0 / 29.4->20.8 | -66.6/-56.6 / +0.8/+14.9 |

(kept n order = IS champion / IS utcsat / OOS champion / OOS utcsat; flat books are
500/454/279/253.)

Failures at other thresholds: 0.846-1.10 miss kept>=70% (1.10 also worsens utcsat IS
maxDD 21.2->23.8 despite passing the other two criteria); 1.25/1.30 fail avgNet/trade
(champion IS dips to +0.636/+0.604 vs +0.652 baseline - the marginal kept trades are
below average).

**Cost at the passers:** IS total net -17-19% (the skipped volume-rising tail is still
net-positive in IS, just below average); OOS net IMPROVES (+0.8..+15.5 - skipped tail is
net-negative OOS). ddDur mixed (champion IS 72->82 at 1.20, OOS 149->112). calmar:
champion IS 3.202->2.676, utcsat IS 4.619->4.133, champion OOS 0.659->0.965, utcsat OOS
1.025->1.815. PF/WR at 1.20: champion IS 1.81->1.82 / 27.8->28.4%. All 10 arms +
full metrics in `_vol_threshold_gate_results.json` (no best-of hiding).

Caveats: post-process removal without chain re-timing (same as all prior gates);
thresholds ranked after the read-only descriptive sweep (exploratory - every arm
printed); ulcer excluded from the rule (sparse-book peak-denominator pathology at
aggressive cuts); OOS deltas ride the weak OOS baseline (Study 2 luck caveat).

## Capital-scaling lever (Z flags) - user note

Same convention as M2 (checklist 24.60): **present capital 1x sizing everywhere** -
the Z2 A/B/C arms are a FUTURE lever, not a live change. When capital has grown /
becomes flexible: **1.5x lot on trades flagged by ONE chosen Z-flag** (A: `er50 <=
0.0767`, B: `wick_gt3x_pct12 > 33.3`, C: `vol7_prev7 <= 0.846` - pick ONE; union of all
three is 63-65% of the book, stacking flags would over-expose), 1x on everything else.
When capital/risk-budget is TIGHT (want fewer trades, shallower DD): **volume-reduction
gate - take only trades with `vol7_prev7 <= 1.20`** (user goal: ~400/500 trades, avg
R/trade same-or-better, maxDD lower in all 4 cells; thr 1.15 for a deeper cut).
Sizing flag and gate can combine; TESTED PATH-TRUE 2026-09-26 (checklist
24.81, log 86): the gate FAILS G-RULE 3/6 path-true, gate+M2 vs flat FAILS 4/6,
M2 marginal on the gated book PASSES 6/6 - combined lever NOT adoptable, and
the vol gate itself is retracted for adoption (Z3 verdict update below).

## Z3b - gate sweep on flags A and B (er50, wick) - same user goal

Same G-RULE and setup as Z3 (kept 70-90% AND avgNet/trade >= baseline AND maxDD(R)
<= baseline, all 4 cells). Grids: IS-pooled feature quantiles at keep-targets
{35..85}%; EXPLORATORY bridge thresholds er50 {0.20, 0.205, 0.21} added after the
first run showed er50|0.1989 missing the 70% floor by 0.2pp (uts IS 69.82%).
`wick_gt3x_pct12` is a 12-bar share (multiples of 8.33) so only 3 arms exist:
>=25 (70-75% kept), >=33.3 (~48%), >=41.7 (~24%). Harness `exp_ab_gate_sweep.py`
-> `_ab_gate_sweep_results.json`; None-features kept; identity asserted; smoke PASS.

**G-RULE PASS: er50 <= 0.20 ONLY (and EXPLORATORY - knife-edge):**

| cell | flat -> gate net | kept% | avgNet/trade | maxDD |
| --- | --- | --- | --- | --- |
| IS champion | 325.8 -> 265.1 (dNet -60.7) | 73% | +0.652 -> +0.722 | 27.7 -> 25.7 |
| IS utcsat | 358.9 -> 311.1 (dNet -47.8) | 71% | +0.791 -> +0.966 | 21.2 -> 20.3 |
| OOS champion | 70.2 -> 58.6 (dNet -11.6) | 72% | +0.251 -> +0.293 | 53.2 -> 28.7 |
| OOS utcsat | 60.2 -> 62.3 (dNet +2.1) | 76% | +0.238 -> +0.326 | 29.4 -> 20.0 |

Knife-edge: 0.1989 fails the kept floor (uts IS 69.82%), 0.205 fails uts IS maxDD
(21.4 > 21.2). Post-hoc threshold selection -> HIGH selection risk; OOS champion net
is below flat (-11.6) even though avg/trade improves.

**wick >= 25 FAIL** (the only goal-zone wick arm): kept 70-75% all cells, avgNet
better 4/4, OOS dNet +16.6/+5.7, but IS champion maxDD 27.7 -> 29.9 (+2.2R) breaks
the rule. Every other er50 arm fails kept% or maxDD in some cell (full table in JSON).

**Verdict: the pre-registered Z3 volume gate (thr 1.15/1.20) remains the only
grid-derived passer and is strictly better on OOS net (er50|0.20 OOS champion -11.6
vs vol|1.20 +3.6).** er50|0.20 recorded as exploratory near-pass; wick gate closed
for reduction (stays sizing-only, flag B).

**PATH-TRUE UPDATE (2026-09-26, checklist 24.81, log 86): the Z3 vol-gate
recommendation is RETRACTED for adoption.** Rerun path-true (predicate injected
pre-state-mutation; identity IDENTICAL x6; formula parity 0/1692): G-RULE FAIL
3/6 - kept 77.7-80% everywhere, but avgNet drops in champion IS (0.652->0.603),
utcsat IS (0.791->0.752) and age10 OOS (0.569->0.412), and champion IS maxDD
goes 27.7->42.6 (post-process had 27.7->27.0). Cascade vs post-process dNet:
champion IS -61.1->-87.4, champion OOS +3.6->-4.6 SIGN FLIP, utcsat IS
-60.5->-86.0, utcsat OOS +15.0->+10.8. Same class as the Stage-B wick gate
(0/4 path-true): post-process removal = UPPER BOUND, never adoptable
(AGENT_COORDINATION rule). Only SIZING flags remain leverage candidates.
