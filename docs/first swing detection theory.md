# The Story of First Swing Detection (v2)

## The Market Opens

Every day at 9:15, the market opens with energy. Prices spike, dip, and
explore. Within minutes, a natural range forms — a ceiling and a floor.
Somewhere inside that, a story is beginning: the first swing of the day.

Our job is to find that swing. Not with magic — by watching how price
behaves from the first bell onward. First swing only, every day starts
fresh. Nothing about previous days matters.

---

## What We're Looking At

**A** and **B** — the session's opening high and low, set from bar one
(9:15). Whichever prints first doesn't matter; they're just the two
starting reference points everything else measures against.

**Pivots** — the bounces and dips along the way. Most are just noise
markers. A few become meaningful (see Confirmation, below).

**Direction** — up (buying) or down (selling). Decided by which way price
actually breaks out of the A/B range, not by guessing.

---

## Two ways to earn a "real" swing

Both require at least one genuine break. Nothing gets called "real" on
price position alone 

### Continuation

- **A** = session high, **B** = session low.
- Price breaks **B** → prints a new, lower low. Call it **C**. Break #1.
- Price breaks **C** → prints an even lower low, **D**. Break #2.
- Two extensions in a row, same direction → **direction confirmed.**

Mirror logic for buying (extending the high twice: A → break → new high →
break → newer high).

Note: it's "extend the extreme twice," not "break one fixed level twice."
Each break has to be against a *fresh* extreme, not a re-test of the same
number.

### Reversal

- Price breaks one extreme (say **B**, the low) — first move.
- Price turns and breaks the **other original extreme** (**A**, the high)
  — **exactly one break needed here**, not two.
- Direction confirmed = the reversal side.

Important: this is specifically the *original opening* extreme, not just
any pivot along the way. Breaking some minor bounce doesn't count as a
reversal — see the Chop-confirmation Known Issue below, which is exactly
about not confusing minor bounces with real reversals.

---

## Confirmation — proving the move will hold

Once direction is confirmed, the broken level freezes as the reference
price, and the swing waits for one of two things:

**Chop-back** — price breaks through just previous pivot in the opposite
direction. Counts as confirmation; the swing still stands, the market's
just chopping before/around it.

**Sustain** — price holds beyond the frozen reference level for 7 bars
straight. This is symmetric by direction, and it's a *failure-to-extend*
pattern in both cases, not a "holding the breakout" pattern:
- Selling swing: 7 closes back **above** the broken low (price stops
  making new lows and rests above where it broke down). Note a sus for selling swing will always be above a low 
- Buying swing: 7 closes back **below** the broken high (price stops
  making new highs and rests below where it broke up). Note here sus will be below a high


Streak resets any time a fresh extreme prints in the trend direction —
that bar belongs to the move, not the hold.

**Reversal detail:** if direction flips via a reversal (not a
continuation), the reference price for sustain re-pins to whichever
extreme was just broken to cause the reversal — not the very first break
of the day. (This was a real bug — sustain was checking against the
wrong price for every reversal swing. Fixed and verified.)

Whichever confirmation fires first wins. Once either fires, the swing is
frozen — start, end, direction, and which confirmation type triggered it.

---

## The 9:29 rule — a floor, not a deadline

Nothing declares before 9:29. The opening minutes are noisy — a break at
9:16 doesn't prove anything on its own.

But this is a **floor for announcing**, not a **ceiling on when a swing
can finish forming.** If a trigger condition fires before 9:29, it's held
and re-evaluated bar by bar (it can even get overwritten by a later,
better trigger) until 9:29, when whatever is pending gets flushed and
declared. If nothing has triggered by 9:29, the engine just keeps
watching — there is **no upper time limit** on real detection. A swing
that only confirms at 10:10 or 10:20 is completely normal and expected.

---


---

## Minimum swing size

**Parked, deliberately not implemented.** The idea on the table: build a
rolling average of the 9:15–9:45 move size over the past N days, require
today's candidate to reach roughly 90% of that before Real detection is
trusted. Not wired up yet — no clean history to calibrate against.
Currently: no size floor. A 0.5-point move and a 50-point move are
treated identically as long as they meet the confirmation rules.

---

---

## The Ending

When a day resolves, it lands in exactly one of four states:

- **Real — Continuation**: confirmed by chop or sustain, tier = real
- **Real — Reversal**: confirmed by chop or sustain, tier = real


Every outcome freezes: start, end, direction, and which path produced it.
Nothing stays in limbo — every day gets one of the four states above,
eventually.