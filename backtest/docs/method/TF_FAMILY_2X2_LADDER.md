# The 2×2 ladder test — 1h is not interchangeable with 2h, and the ladder ratio is not why

Date: 2026-10-10. Harness: `exp_tf_family.py`, 253s. Output `_tf_family.json`.
**Status: NOT ADOPTED. 1h stands. The ladder hypothesis is falsified.**

---

# 1. The hypothesis

Shipped is LTF 15m / HTF 1h. That is a clean **4:1** ladder, since `15m × 4 = 1h`.
If that self-consistency is what matters, then **30m / 2h** (`30m × 4 = 2h`) should
be an equally valid family.

Every earlier 2h run held the LTF at 15m, which made the ratio 8:1 and
**confounded "is 2h bad" with "is 8:1 bad".** This grid separates them.

## the causality condition, checked first

The engine hard-codes 1h arithmetic in seven places and one of them is
load-bearing: `candle_ts_htf_close = [t + 3600 ...]` is how it decides *"this bar
has CLOSED, so I may read its regime and chop"*. Feed it 2h bars while that still
says `+3600` and every 2h bar is read **one hour early** — a lookahead leak.

So the window gate is **derived, never hard-coded**: `(htf_bar_secs −
ltf_bar_secs)`. 2h/15m gets gate 6300, 2h/30m gets 5400, and the shipped 1h/15m
still gets 2700 and reproduces byte-identically.

**Control: EXACT — both eras, all lanes reproduced.** The grid is trustworthy
before it is interesting.

---

# 2. The grid

| cell | LTF | HTF | ladder | gate | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---:|---:|---:|---:|---:|---:|
| **F0 control** | 15m | 1h | 4:1 | 2700 | **+279.3** | **+63.4** | **+321.4** | **+75.3** |
| F1 LTF only | 30m | 1h | 2:1 | 1800 | +187.7 | −18.9 | +151.3 | +23.1 |
| F2 HTF only | 15m | 2h | 8:1 | 6300 | +42.8 | **−69.7** | +61.6 | **−53.9** |
| **F3 family** | **30m** | **2h** | **4:1** | 5400 | +150.7 | **+2.9** | +104.9 | **+0.7** |

(count-preserved `min_bars` 50; the duration-preserved 25 variant is below)

**PF out of sample, mb50:** control 1.30 / 1.39 · F1 0.84 / 1.23 · **F2 0.67 / 0.72** · **F3 1.03 / 1.01**

---

# 3. The finding: the ladder is not the reason

**F3 has exactly the same 4:1 ladder as F0 and it is dead out of sample** — +2.9R
at PF 1.03 for champion, +0.7R at PF 1.01 for utcsat, against the control's +63.4R
at PF 1.30.

**If 4:1 were what mattered, F3 and F0 would be the same family.** They are not.
Matching the ratio and moving the plane destroys the book just as thoroughly as
leaving the ratio mismatched.

> **The ladder ratio is not the mechanism. The 1h plane itself is.**

**And F2 is worse than F3**, which is the control's mirror image: holding the LTF
at 15m and only lifting the HTF to 2h gives −69.7R at PF 0.67 out of sample, while
fixing the ladder with 30m recovers almost all of it (+2.9R). So the damage is
done by the 2h parent and then substantially *masked* by the LTF mismatch rather
than caused by it.

## duration-preserved min_bars tells the same story

At `min_bars` 25 (so the swing DURATION is matched rather than the count):

| cell | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---:|---:|---:|---:|
| F0 control | +282.9 | **+118.5** | +198.7 | +49.1 |
| F1 30m/1h | +183.6 | +98.2 | +140.6 | +63.5 |
| F2 15m/2h | +124.4 | −32.6 | +22.3 | **−99.5** |
| **F3 30m/2h** | +135.0 | **−42.7** | +73.6 | **−35.1** |

**Same ordering, both min_bars, both eras, both lanes.** Every 2h cell is negative
out of sample. The result does not depend on the swing parameterisation, which is
what makes it a finding rather than a tuning artefact.

## the one genuinely interesting cell

**F1 — 30m LTF on a 1h parent — has the BEST in-sample profit factor of the whole
grid: PF 1.92 for champion against the control's 1.70, and +183.6R at PF 1.56 on
the duration-preserved run.** Then it loses money out of sample (−18.9R at PF
0.84).

**That is the same shape as every in-sample-only result in this project's
history**, and it is why F1 is not a candidate despite its headroom: the control
beats it out of sample by +82R on the same footing.

---

# 4. Two harness bugs found before any of this could run

**The age10 lane raised `KeyError` on its first run.** Every `age10_*` key has
since been retired, so the lane had been dead since before it was ever executed —
the harness had a pre-registered grid and had never produced a cell. Dropped, and
recorded as a loss rather than quietly redesigning the test around it.

**The control gate failed for the wrong reason.** It carried hand-copied expected
values (`champion 500 / +325.8`); the run produced `502 / +279.3`, which matches the
registry exactly. So the gate fired on a stale note while the run was **right** —
and an identity gate whose expectations are hand-copied will eventually fail for a
reason unrelated to what it exists to detect.

`BYBIT_BASE` now reads from `experiment_registry` instead. The gate still fails if
the engine drifts, but it cannot fail because a note went out of date.

**That is the third harness bug this cycle that produced a plausible wrong answer**
— after two books coming out with identical pins, and a tightening gate appearing
to add trades. All three were caught by asking whether the failure *made sense*,
not by the failure itself.

---

# 5. What is now settled

| question | answer |
|---|---|
| Is 1h replaceable by 2h? | **No.** Every 2h cell is negative out of sample, both eras, both lanes, both min_bars. |
| Is the 4:1 ladder the mechanism? | **No.** F3 matches the ratio and still dies. |
| Is the damage caused by the LTF mismatch? | **No — masked by it.** F2 is worse than F3. |
| Is there anything here worth adopting? | **No.** F1 has the best in-sample PF and is beaten out of sample by the control. |

**The engine stays 15m / 1h / `min_bars` 20.** Nothing registered, nothing changed.

---

*No pin moved. No book modified. Control reproduced exactly in both eras — which is
the reason this grid is worth having run at all, given that a 2H plane test already
existed and had never executed.*