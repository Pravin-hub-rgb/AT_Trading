# P87 — THE INSTRUMENT P85 ASKED FOR. The ceiling survives period control
# in three of four cells, and the disagreement between instruments is the
# finding.

> Run 2026-09-29. Harness `exp_ceiling_regime_ctrl.py`. **NOT ADOPTED.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **The ceiling is not a regime proxy. Three of four cells survive a
> half-year fixed effect and a month-cluster bootstrap. One cell fails, and
> the two instruments disagree about it — which is why this is unresolved
> and not adopted.**

## The question

P69's ATR% ceiling at 0.40% removes trades that are **net negative in OOS**
(−41.6R and −37.1R, PF 0.78 both lanes) and worth nothing in IS. P85's
permutation test came back p = 0.96–0.99 and was correctly declared
uninformative — block-permuting 99–106 trades yields two or three
independent blocks.

**But p = 0.97 was never the right question either.** Every other finding in
this round is an era-split: the expiry (P56), granularity (P58, P66), the
candidate's stability (P61), layer agreement (P59), the long-side defect
(P78). **If the ceiling's power is one more of those, it is a regime proxy
rather than a filter — and a regime proxy is not a rule, because P55, P67
and P68 all failed to make the eras separable at decision time.**

## The model

```
R_i = a + b * cohort_i + g_{halfyear(i)} + e_i
```

`cohort` is 1 for a trade the ceiling **keeps**, 0 for one it **drops**. The
`g` term is a half-year fixed effect, so **b is the cohort difference after
everything the period explains.** Cluster-robust variance by **month** —
trades inside a month share a regime, which is exactly why P85's raw
p-value was unusable — plus month-cluster and half-year-cluster bootstraps.

## Result

| lane / era | **b (period-adjusted)** | raw gap | shrink | t (month-cluster) | month boot p | half-year boot p |
|---|---|---|---|---|---|---|
| champion **IS** | **+0.8165** | +0.8763 | 7% | **+1.66** | **0.0027** | 0.0150 |
| champion OOS | **+1.2965** | +1.3803 | 6% | +2.25 | **0.0013** | **0.0000** ✅ |
| utcsat IS | **+1.1214** | +1.2355 | 9% | +2.30 | **0.0005** | **0.0000** ✅ |
| utcsat OOS | **+1.2972** | +1.3071 | 1% | +2.22 | **0.0008** | **0.0000** ✅ |

## Finding 1 — it is NOT a regime proxy, and that is the real news

**The half-year fixed effect removes only 1–9% of the gap.**

| | raw | after control | removed |
|---|---|---|---|
| champion IS | +0.8763 | **+0.8165** | 7% |
| champion OOS | +1.3803 | **+1.2965** | 6% |
| utcsat IS | +1.2355 | **+1.1214** | 9% |
| utcsat OOS | +1.3071 | **+1.2972** | 1% |

**Every other era-dependent effect in this programme collapsed when the
period was controlled.** This one barely moves. **The ceiling is not
smuggling in "which era is this" — it carries information the date does
not.**

**That is a categorically different result from P55, P67 and P68**, and it
is the first thing found this round that a live system could act on: **it
does not require separating the eras at decision time.**

## Finding 2 — the instruments disagree on champion IS, and that is unresolved

| instrument | champion IS verdict |
|---|---|
| cluster-robust t (month, 45 clusters) | **+1.66 — FAILS** the conventional 1.96 |
| month-cluster bootstrap, 4000 draws | p = 0.0027 — **PASSES** |
| half-year-cluster bootstrap, 1000 draws | p = 0.0150 — **PASSES** |

**A t of 1.66 with 45 clusters is not robust**, and the small-sample
distribution of a cluster-robust t is not normal — the standard reason to
distrust the 1.96 threshold and prefer the bootstrap. **But the two are not
equivalent instruments, and the honest statement is that they disagree.**

**The other three cells do not have this problem**: t of +2.22 to +2.30 with
bootstraps at p ≤ 0.0013 and p = 0.0000 on the conservative resample.


## Verdict

**NOT ADOPTED — one of four cells fails, and the failing cell is the one
the other two instruments pass.**

**But the reason it fails is now known and is not "no signal".** It is a
power problem in the fitted era: champion IS keeps 395 and drops 105, the
dropped cohort is worth +6.0R rather than negative, and there is less to
find. **In OOS — never fitted — the dropped cohort is negative and b is
+1.30 with p ≤ 0.0013 on both instruments and both lanes.**

**What would change the verdict, in order:**

1. **A pre-registered grid re-read.** The 0.40% ceiling is a peak of P69's
   four-point grid and is not family-wise. Testing all four under **this**
   instrument costs nothing and settles whether the IS cell fails at every
   level or only at the chosen one. **The obvious next experiment; not run.**
2. **More data.** 105 dropped IS trades is a small cohort; the OOS leg with
   173 is comfortable, and that is where the evidence is.
3. **The forward slice**, which per P63 can rule and not confirm — and a
   rule that fails only in the era it was fitted and passes in the one it was
   not is precisely what a forward slice is for.

## Stated limitations

- **Both lanes are the same data.** Their agreement is encouraging and is
  not independence.
- **The half-year fixed effect has 8 and 4 levels**, and with 45 or 24
  month-clusters the cluster-robust t is approximate at best.
- **The month bootstrap resamples clusters with replacement and refits**,
  which assumes the cluster is the unit of independence. An assumption,
  not a proof.
- **The ceiling level is a grid peak** and this run does not fix that.
- **p-values are the smallest across the cluster choices**, so they are the
  most favourable reading available.

## Status

**NOT ADOPTED. UNRESOLVED, and much closer to alive than at P85.**

The key change since P85: **this is no longer "a test that could not
resolve it". It is "an effect that survives period control, passes three
cells outright, and fails one on a robust-t threshold while passing it on
both bootstraps".** The honest next move is the four-point grid under this
same instrument, not another filter.

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
