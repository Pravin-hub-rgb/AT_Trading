# P17 — ratchet freeze: the user's idea, and why the data rejects it

`exp_ratchet_freeze.py`. Control reproduces the champion exactly
(500t / +356.9R / R/tr +0.890 / PF 2.38 / DD 17.8 / std 5.55 / streak 16),
so the patch is faithful and every arm below is comparable.

## The idea

> "agar N time move up ho gaya hai long ke liye toh ab rachet ko thoda
> delay karde, now ab new swing ka bhi new banega tab trail kare"

**Once the stop has been raised N times, stop raising it.** This is
genuinely new — every closed exit arm tightens or protects
(`exp_trail_delay_r`, `exp_trail_half`, `EXP_LA4_TRAIL_TIGHTEN`,
`partial_r`). **This one LOOSENS after success.**

## The result — every arm fails, monotonically

| freeze after N | n | IS net | R/tr | PF | DD | **std** | **streak** | OOS net | year floor |
|---|---|---|---|---|---|---|---|---|---|
| **off (control)** | **500** | **+356.9R** | **+0.890** | **2.38** | **17.8** | **5.55** | **16** | **+78.5R** | — |
| 1 | 117 | −142.0R | −0.998 | 0.00 | 116.8 | 0.00 | 117 | −98.0R | FAILS |
| 2 | 297 | −161.9R | −0.354 | 0.53 | 107.9 | 2.95 | 25 | −101.0R | FAILS |
| 3 | 425 | −53.2R | +0.062 | 1.09 | 45.9 | 3.49 | 17 | −91.8R | FAILS |
| 4 | 480 | +63.3R | +0.312 | 1.47 | 28.0 | 4.06 | 17 | −36.8R | FAILS |
| 5 | 493 | +136.5R | +0.456 | 1.70 | 18.6 | 4.23 | 17 | +7.6R | FAILS |
| 6 | 498 | +197.5R | +0.574 | 1.89 | 17.8 | 4.39 | 16 | +48.2R | FAILS |

**0 of 6. Every arm is worse than the control in both eras, monotonically
approaching it as N rises** — because a higher cap is closer to no cap.

## All four falsifiers fire

- **(a)** net down in every arm, both eras
- **(b)** no arm beats the control's r_std — the best is 4.39 at N=6 vs
  the control's 5.55, but that arm has lost 159R of net
- **(c)** no arm shortens the losing streak — every arm is 16 or worse
  (N=1 and N=2 are catastrophic at 117 and 25)
- **(d)** no arm holds the year floor

## The reason, and it is the useful part

**The ratchet is not a profit-protection mechanism on this book. It IS the
profit.** The trail study already said this — `method/EXPERIMENT_LOG.md:669`,
Stage 2: *"the structural trail/holding logic is the dominant source of
payoff; simple fixed exits do not reproduce the edge."* P12's control
showed the same from the other side: replacing the trail with a 3R target
costs the book 313R.

**Freezing the ratchet is not "giving a winner room." It is removing the
mechanism that converts a 1R winner into a 24R runner.** The evidence is
right there in the shape of the failure: N=1 gives 117 trades at 22% of
the control's count and **−142R** — nearly every trade becomes a −1.0R
stop-out, because with one raise allowed the stop sits below the
structure that would have trailed it out.

**And the smoothness hope does not survive either.** The arms *do* lower
r_std (5.55 → 4.39) and that was the entire motivation. But they buy it
by giving back 159R of net and 159 fewer trades. **Smoothing by removing
the edge is not smoothing.** The user's instinct was right about the
mechanism — the variance does live in the runners — and wrong about the
lever: the runners and the variance are the same thing, so you cannot
remove one and keep the other.

## What this closes

**The ratchet-freeze family, and with it the last idea that tried to
loosen the exit.** Combined with the earlier closures (half, delay1,
tighten, partial, P10's "runner is not identifiable early"), the exit
surface is now exhausted in both directions:

- every variant that **tightens** or **protects** → rejected
- the one variant that **loosens** → rejected here, and rejected
  *decisively* (monotone, both eras, every falsifier)

**Nothing on the exit side works. The only improvement available today is
on the entry side, and it is P16's `nest1h>0.25 + age>0.5d`.**

## The honest caveat

This is a clean negative, not a null. The idea was well-motivated, the
implementation is verified (control exact), and the failure is
monotone and large rather than marginal — which is the strongest form a
rejection can take. **It is genuinely settled, not "needs more runs".**

One variant was not tested: freezing only on the *long* side, or freezing
after N raises but re-arming on a new swing as the user described. Given
that the whole-side version loses monotonically from N=1 upward, the
asymmetric version is unlikely to invert that, and the user's own
description ("ab naya swing banega tab trail kare") is closer to the
control than to a freeze.
