# min_bars 25 vs 50 — forensic autopsy

**Date:** 2026-09-27 · **Harness:** `exp_mb_forensic.py` → `_mb_forensic.json` (481s) · **Companion table:** `method/TF_METRICS_TABLE.md` (48 cells, full metric set) · **Status: no adoption. Shipped min_bars 50 stays.**

## The puzzle that started this

Same asset, same params, same timeframes (15m/1h), only the LTF swing length changed:

| | min_bars 50 (12.5h swing) | min_bars 25 (6.25h swing) | winner |
|---|---|---|---|
| IS 2023-26 | **+325.8R** | +272.8R | 50 by 53R |
| OOS 2021-22 | +70.2R | **+128.6R** | 25 by 58R |

A clean inversion. If the cause can be pinned down it becomes a *conditional*
rule, which is worth far more than either fixed choice.

## Phase 1 — the full metrics table

`method/TF_METRICS_TABLE.md` has all 48 cells (4 LTF/HTF cells × 2 min_bars × 2 eras ×
3 lanes) with the full `equity_quality` set: n, net, avgR, wr, PF, maxDD,
dnet/yr, sortino, calmar, ulcer, max_streak, pos-month %, worst month, pos-year
%, worst year. This is a re-run, not a patch of the old numbers — the earlier
`_tf_family.json` stored only n/net/PF/DD, so the two files are not
interchangeable.

Shipped pair (15m/1h), champion, for orientation:

| | n | net | avgR | wr | PF | maxDD | dnet/yr | uw% | pos-mo% |
|---|---|---|---|---|---|---|---|---|---|
| mb50 IS | 500 | +325.8 | +0.65 | 27.8 | 1.81 | 27.7 | 88.8 | 90.4 | 51.1 |
| mb50 OOS | 279 | +70.2 | +0.25 | 27.2 | 1.34 | 53.2 | 35.1 | 95.0 | 37.5 |
| mb25 IS | 818 | +272.8 | +0.33 | 27.3 | 1.42 | 66.4 | 74.3 | 92.8 | 40.0 |
| mb25 OOS | 535 | +128.6 | +0.24 | 27.5 | 1.33 | 45.8 | 64.3 | 94.4 | 50.0 |

## Phase 2 — the inversion is not statistically significant

Bootstrapped per-trade edge difference (mb25 − mb50), 20k resamples, resampling
**trades**:

| Era | mb50 avgR | mb25 avgR | trades | per-trade diff | 95% CI | p |
|---|---|---|---|---|---|---|
| IS | +0.652 (n=500) | +0.334 (n=818) | ×1.64 | −0.318R | [−0.892, +0.216] | 0.259 |
| OOS | +0.251 (n=279) | +0.240 (n=535) | ×1.92 | **−0.011R** | [−0.507, +0.475] | 0.974 |

**Neither difference is significant, and both CIs straddle zero.**

The OOS row is the important one. The per-trade edge of mb25 over mb50 is
**−0.011R — indistinguishable from identical.** So the OOS "mb25 wins by 58R" is
**not a quality advantage at all.** It is a *volume* effect: mb25 takes 1.92× the
trades at the same edge per trade, so it banks roughly twice the total. There is
no OOS outperformance to explain.

The IS row is a genuine volume-vs-quality trade: mb25 gains 64% more trades but
each is worth about half as much (0.334 vs 0.652), and the two roughly cancel.

## The mechanism, stated plainly

`min_bars_15m` is a **trade-frequency dial, not an edge dial.** Shortening the
LTF swing from 12.5h to 6.25h finds more swings, which admits more entries — 1.6×
to 1.9× more depending on era — at essentially unchanged per-trade expectancy in
OOS and roughly halved in IS.

That reframes the whole question. "Which swing length is better?" has no answer
without also fixing position size, because at the same size mb25 is a
1.6-1.9× bigger bet.
# END_MARKER

## Year-by-year — the inversion is one year, not a regime

| Year | mb50 | mb25 | 25 − 50 |
|---|---|---|---|
| 2023 | +86.9 | +141.3 | **+54.4** |
| 2024 | +88.8 | +17.3 | −71.5 |
| 2025 | +68.8 | +75.8 | +7.0 |
| 2026 | +81.3 | +38.4 | −42.9 |
| 2021 (OOS) | **−26.4** | +19.3 | +45.7 |
| 2022 (OOS) | +96.6 | +109.3 | +12.7 |

IS flips sign three times in four years — that is a coin flip, not a regime. The
whole OOS "preference" is **2021**, where mb50 happened to go negative and mb25
happened not to. A two-year total decided by one year is the definition of a
noisy signal.

## The one lead: a causal volatility split

Trailing 24h realised volatility at entry, terciles **fitted on IS only**, the
same absolute edges applied to OOS. `delta` = mb25 − mb50 net:

| vol bucket | IS delta | OOS delta | sign agrees? | OOS n (mb50) |
|---|---|---|---|---|
| low | −43.6 | −43.8 | yes (50 wins) | 7 |
| mid | +40.5 | +48.4 | yes (25 wins) | 19 |
| high | +11.4 | +28.1 | yes (25 wins) | 63 |

The *pattern* is mechanistically sensible — in slow tape a long swing filters
better, in fast tape a short one adapts faster — and the sign agrees across eras
in all three buckets.

**It is still not a rule, and I am not treating it as one:**

- The OOS low-vol bucket has **n=7** trades. A −43.8R delta on 7 trades carries
  no information.
- With 3 buckets, all three signs agreeing is **p=0.25 by chance**. Two agreeing
  out of three is what noise delivers.
- The tercile edges come from IS, so OOS bucket membership shifts with that era's
  volatility distribution; "n=7" is a symptom of that, not an accident.

This is a **hypothesis worth a pre-registered sweep with adequate n**, not a
conditional rule. Adopting it now would be mining three buckets for the one that
transfers.

## Two things this autopsy did not settle

1. **The comparison is not risk-matched.** mb25 at equal position size is a
   1.6-1.9× larger bet. maxDD moved 27.7 → 66.4 in IS (2.4×) but 53.2 → 45.8 in
   OOS (0.86×). An honest "which swing length" question needs mb25 at half size.
   Nobody has run that, and it is the obvious next arm.

2. **age10 disagrees with the live lanes and deserves its own look.** age10 OOS:
   mb50 +43.2R (n=76, avgR 0.57) vs mb25 **+120.1R** (n=194, avgR 0.62). Here the
   shorter swing is better on *quality* as well as volume — the only cell in the
   grid where that is true. age10 is default-off and structurally different, so
   it is not evidence about champion/utcsat, but "age10 wants a different swing
   length" is a real observation.

## Verdict

- **Neither headline difference is significant** (p=0.26 IS, p=0.97 OOS).
- **The OOS advantage of mb25 is entirely volume**, at an unchanged per-trade
  edge (−0.011R). It is not evidence of a better swing length.
- **No adoptable conditional rule exists yet.** The volatility-tercile pattern is
  the best lead and it is not strong enough — 7 trades in the decisive bucket.
- **Shipped min_bars 50 stands.** Engine unchanged.
- Next arms, in order: (a) risk-matched mb25 at half size; (b) a pre-registered
  volatility sweep with n large enough to matter; (c) age10 separately.

