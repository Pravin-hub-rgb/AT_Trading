# Both open caps — P4 `cap_days`, and the 1d-vs-2d question

> Run 2026-09-29. Harness `exp_caps.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> Closes P4 in the queue. **Does not settle 1d-vs-2d — see the last section.**

## Two void runs, recorded because they looked like findings

**PART 2, run A: "cap_days is inert."** Every value from 6 to 32 produced a
byte-identical book. That was a harness bug. The v18 module does
`from src.btc.engines.v7_timecap import simulate_btc_trades_v7` **inside
the function body**, so the name binds at *call* time, not at exec time. The
patch was installed, `build_module()` ran, and the `finally` restored the
original before the engine was ever invoked. The patch never applied.
`cap_days=16` matched the control only because the unpatched default is also
16. A probe holding the patch across the call gives 586t/+401.1R at
`cap_days=0` and 233t/−16.5R at 1 — the parameter is emphatically not inert.

**PART 1, run A: capped the wrong age.** It capped *window* age, which is
W1's question and W1 is already closed. P38's cap is on the age of the legs
the decay feature reads. Corrected here to the age of the **oldest of the
last 4 confirmed buying legs**.

Lesson, now the third time this session: a suspiciously clean result —
"every arm identical" — was a bug, not a null.

---

## PART 2 — P4 `cap_days`: the 16-day cap is costing P&L, 4/4

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| `cap_days=16` (shipped) | 500t +325.8R | 279t +70.1R | 454t +359.0R | 253t +60.2R |
| **`cap_days=999` (no cap)** | **586t +401.1R** | **313t +125.2R** | **535t +372.6R** | **284t +138.7R** |
| **dNet** | **+75.3R** | **+55.1R** | **+13.7R** | **+78.5R** |
| extra trades | +86 | +34 | +81 | +31 |

**Removing the cap is 4/4 positive and adds trades rather than removing
them.** That is the opposite of what a brake does, and the reason is
visible in the sweep: **the cap only ever truncates windows that are still
open and still working.** Every value from 1 to 12 is worse than 16; every
value from 20 upward is better. The 16 sits at the bottom of a valley.

**`cap_days=0` and `cap_days=999` give identical books** (586t/+401.1R,
313t/+125.2R) — v7 guards against zero and treats it as no cap. So "0" is
not a separate arm and is not reported as one.

### The honest limits

- **Largest dNet is +78.5R against M = 193.4R.** Real, 4/4, and still well
  inside the null. It does not clear the bar on its own.
- **The sweep is not monotone.** `cap_days=24` is anomalously bad in both
  OOS cells (champ −74.6R, utcsat −57.1R) while 20 and 32 on either side
  are fine. That non-monotonicity is itself evidence that a good single
  value is partly noise, and it is why the direction ("cap off") is the
  finding rather than any particular number.
- **No arm beats 16 in both eras by more than noise**, so under the
  pre-registered P3 rule this is *not* a pass. It is a direction worth
  taking further, not an adoption.

---

## PART 1 — the 1d-vs-2d question, and an honest failure to answer it

**The on-record P38 numbers do not reproduce.** The build sheet lists
`CAP 1d` at +56.6R IS / +17.4R OOS. Sweeping the leg-age cap over
0.5–7 days produces nothing close:

| leg cap | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| none (≈7d) | +34.2R | +7.5R | +3.8R | +9.9R |
| 4.0d | −48.0R | +9.7R | −71.1R | +11.2R |
| 3.0d | −160.7R | −29.5R | −171.2R | −19.7R |
| 2.0d | −216.7R | −75.1R | −236.5R | −63.1R |
| ≤1.5d | 11 trades | 7 trades | 11 trades | 6 trades |

**A 1-day cap is not a viable threshold on this definition.** The measured
age of the oldest of the last four buying legs is **p50 = 3.05 days,
p90 ≈ 4.9 days, max 6.6 days** (champion). A 1-day cap retains 3 trades.
Whatever P38's "CAP 1d" was measuring, it was not this quantity.

**So the 1d-vs-2d decision cannot be answered from this run**, and the
`+56.6R / +17.4R` row on the build sheet should be treated as
**not reproduced** until the original definition is recovered. Recorded
rather than quietly left in place.

**What is confirmed is the direction the cap points:** the cap helps in OOS
and hurts in IS at every value, and removing it entirely is the best arm.
That is the same era-flip seen in W1 and in the leg-position ordering, and
it is the third time the book has said the same thing — **the split is a
regime difference, not a parameter to tune.**

---

## Verdict

**P4 is closed with a direction: the 16-day cap costs R in all four cells
and removing it is 4/4 positive. It does not clear M, so it is documented,
not adopted.**

**1d-vs-2d is not closed. The on-record numbers did not reproduce and a
1-day cap is non-viable on the leg-age definition. Needs the original P38
definition recovered before the question can be asked.**
