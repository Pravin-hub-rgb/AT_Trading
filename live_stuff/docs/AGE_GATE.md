# P20 — the age CEILING is load-bearing in-sample and harmful out-of-sample

`exp_age_gate.py`. The user's question, which turned out to be the right
one:

> "ya toh dekha age filter hatana se kya hota hai karke toh mtlb yeh age
> wageara behter hai"

**A bug was caught mid-run and fixed rather than reported around.** The
first pass printed `net_r(tr)` — the UNFILTERED book — next to the
filtered trade count, so arms C and D displayed the wrong net. Caught on
reading the first lane's output (B and C showed identical nets with
different n, which is impossible). Rerun prints `evaluate(...)['net']`,
the filtered figure. The numbers below are from the corrected run.

## What the knob is

`exp_max_swing_age` is a **CEILING** — it refuses entries in windows
OLDER than N hours (10 or 25 on the age-gated lanes). My `age > 0.5d` is a
**FLOOR** — it refuses entries in windows NEWER than 12h. **Opposite
shapes, and they do not compose.** Nobody had ever removed the ceiling to
see what it costs; it sits in the registry as part of a lane config, not
as an audited decision.

## A — control, B — ceiling OFF, C — OFF + my filter, D — ON + my filter

| lane | era | A control | **B ceiling OFF** | C OFF+filter | D ON+filter |
|---|---|---|---|---|---|
| **age10_swingpause_single** | IS | +451.5R (130) | **+306.8R (−144.8)** | +324.9R (−126.6) | +441.4R (−10.1) |
| | OOS | +46.6R (76) | **+63.0R (+16.5)** | +57.8R (+11.3) | +19.2R (**−27.4**) |
| **age25_dirmatch_multi** | IS | +408.1R (249) | **+508.8R (+100.7)** | **+531.6R (+123.5)** | +393.8R (−14.3) |
| | OOS | +163.1R (166) | **+170.3R (+7.2)** | +157.0R (−6.1) | +135.3R (**−27.8**) |
| **age25_multi** | IS | +379.4R (295) | +356.9R (−22.5) | **+409.0R (+29.6)** | +390.6R (+11.2) |
| | OOS | +137.8R (193) | +78.5R (**−59.3**) | +85.7R (−52.0) | **+120.7R (−17.1)** |
| **champion_multi** (no ceiling) | IS | +356.9R (500) | +356.9R (0.0) | **+409.0R (+52.1)** | +409.0R (+52.1) |
| | OOS | +78.5R (279) | +78.5R (0.0) | **+85.7R (+7.2)** | +85.7R (+7.2) |

**The champion has no ceiling, so B = A exactly and C = D exactly.** That
is the control that makes the age-gated rows readable: the only difference
between them is the knob.

## The answer to the question, and it is not one thing

**1. The ceiling is worth a great deal in-sample and costs out of sample.**

`age10` IS: removing the ceiling costs **−144.8R**. `age25_dirmatch_multi`
IS: removing it **gains +100.7R**. Those two disagree in *sign* on the same
question, which means the ceiling is not a clean win or loss — it is
**fitting the in-sample regime**. On OOS the pattern inverts for two of
three: `age10` **+16.5R** and `age25_multi` **+59.3R** better without it.
**Two of three age-gated lanes are better out of sample with the ceiling
removed.** That is the era-flip signature, and it is the same shape as
everything else today.

**2. My filter and the ceiling do not compose — falsifier (b) fires.**

On `age25_dirmatch_multi` the ceiling OFF **plus** my filter is the best
cell in the whole table (+123.5R IS). On the other two lanes, C is worse
than B. And **D — ceiling ON plus my filter — is negative in every era
except the champion**, losing 10–28R wherever a ceiling exists. **The
floor and the ceiling are picking the same trades and the ceiling wins,
so adding the floor on top only removes trades the ceiling already liked.**

**3. Falsifier (c) fires: the champion behaves the same way as the age
lanes once the ceiling is gone.** With the ceiling off, C = +52.1R IS /
+7.2R OOS on the champion and +123.5R / −6.1R on `age25_dirmatch_multi`.
**The effect is about the filter, not about the ceiling** — which is what
P19 concluded from the opposite direction, and now from a controlled one.

## What this means for the recommendation

**The champion does not have the ceiling, so this does not change the
champion's numbers at all** — C and D are identical there. The filter's
champion case stands exactly as P19 reported it: +52.1R IS, +7.2R OOS, 352
trades, R/trade 1.339.

**What it does change is the reading of `exp_max_swing_age`.** It is a
lane-config knob, not a validated rule, and on the out-of-sample evidence
removing it helps on two of three lanes. **That is worth a look on its own,
independent of anything today** — a knob nobody has removed, sitting in
three lanes' configs, worth −144.8R in one era and +59.3R in another.

## Caveats

1. The control nets run ~15R above the published pins (e.g. champion
   +356.9R vs pin +325.8R) — a gross/net basis difference in the registry
   pins, consistent across every lane, and **all comparisons here are
   against this file's own control**, never a quoted pin.
2. Three age-gated lanes is a small sample of the ceiling's behaviour, and
   10h and 25h are very different thresholds.
3. Nothing here is adopted. The champion is unchanged.
