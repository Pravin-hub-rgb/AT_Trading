# DECAY — the theory, the autopsy, and the age cap

`exp_structural_decay.py` (P11) found it. `exp_gray_brutal.py` (P15) proved it
causal. `exp_decay_stale.py` (P38) completed it. This file is the theory as
it now stands, including the two things that were wrong in the first telling.

---

## 1. What the feature is

A **buying leg** is a stretch where buyers pushed price up. It has a
**low** — the price where that leg began. Buyers who entered there hold
their stop at that low. **If price trades below it, those buyers are
stopped out.**

    decay = of the last 4 CONFIRMED 15m buying legs,
            the fraction whose low has since broken

    0.00  all four supports intact
    0.25  one gave way
    0.50  two gave way
    0.75  three gave way
    1.00  all four gave way

The rule is **`decay < 0.75`** — refuse the trade when three or four of the
last four buying supports are gone. `decay_pair()` lives at
`exp_decay_switch.py:139`; `legs_by_dir()` at `:117`.

Causality was proven in P15 by hand and re-run twice since: only legs
confirmed at or before the entry, only 1m bars up to the entry. **last 1m
bar read = entry bar minus 0s.** Nothing after it enters the calculation.

---

## 2. The logic, and the part that was wrong

**The user's original framing:**

> *"long ke liye buying swing ke low break ho raha hai to mat lo — buyers weak
> ho gaye. Aur short ke liye bhi yahi lagta hai."*

The long half is straightforward. The short half is where the first telling
went wrong, and it is worth writing down exactly why.

**The assumption embedded in it:** buyers being repeatedly stopped means
price is going down, therefore a short should be in profit.

**P37 read the short side directly instead of inferring it** — mean gross R
by buying-decay bucket, split by side, champion:

| buying decay | LONG n | meanR | SHORT n | **meanR** |
|---|---|---|---|---|
| 0.00–0.25 | 46 | +0.358 | 16 | −0.406 |
| 0.25–0.50 | 70 | +0.748 | 32 | **+1.725** |
| 0.50–0.75 | 77 | **+3.330** | 66 | **+0.972** |
| **0.75–1.00** | 80 | +0.178 | 113 | **−0.063** |

**Shorts are at their best at 0.50–0.75 (+0.97R) and at their worst once
buyers are fully gone (+0.75 → −0.06R).** So the assumption is not merely
inconvenient, it is inverted from what happens:

    buyers 2 of 4 stopped  →  buyers weak, sellers strong  →  short works
    buyers 3-4 of 4 stopped →  buyers finished             →  short dies too

When every buying support is gone the tape is not trending down, it is
going **sideways or up** — the buyers who were supposed to defend already
left, and the next leg belongs to whoever is fresh. **The feature is not a
direction signal. It is a no-trade-zone detector.** That is why blocking
*both* sides on the same number beats judging each side by its own
structure, and it is why the mirror loses (P24, P31, P36 — six lanes,
all negative).

---

## 3. The age cap — a genuine gap in the rule

`decay_pair()` filters to **buying** legs and then takes the last four of
them. It does **not** cap how old they are. A 15m buying leg is roughly
2.5h (`min_bars 50`), so four of them span about ten hours of buying
structure — but selling legs fall between them, so the calendar span is
longer, and there is no ceiling on it at all.

The user's question — *"last ke 4 swing buying dhoondhta hai sach mein? agar
bahut poorane hain toh unka kya impact padega"* — is the right one.

Measured (P37): **415 of 500** entries read legs fresher than one day, 71
read 1–2 days, and only **14** read 2–4 days — and those 14 average
**−0.006R**, i.e. nothing.

Two opposite uses were possible and both were run (P38):

| | what it does to a stale-leg trade |
|---|---|
| **GRAY** | drops it outright |
| **CAP** | leaves it ungated — decay is not consulted |

**The stale trades are good, not bad:**

| lane | era | stale n | stale meanR | stale net |
|---|---|---|---|---|
| champion | IS | 85 | +0.808 | +68.7R |
| champion | OOS | 48 | +1.416 | +68.0R |
| utcsat | IS | 86 | +1.046 | +90.0R |

So GRAY is the wrong move and CAP is the right one.

### Result — champion, NET basis, both pins matched

| rule | n | IS dNet | OOS dNet |
|---|---|---|---|
| A no filter | 500 | +0.0R | +0.0R |
| B current — block whenever decay ≥ 0.75 | 307 | +34.2R | +7.5R |
| G GRAY the stale ones | 415 | **−53.1R** | **−62.0R** |
| **E CAP 2d** — the user's idea, don't gate at 2d+ | 321 | +32.5R | **+25.1R** |
| **C CAP 1d** | 364 | **+56.6R** | +17.4R |

utcsat, same shape: G −73.3R / −50.2R, CAP 1d +50.2R / +5.8R, current
+3.8R / +9.9R.

**CAP 1d totals +74R across the two eras, CAP 2d +57.6R, current +41.7R.**
Both caps beat the current rule; 1d leads in-sample, 2d leads out of sample,
and the choice between them is not settled here.

**Note the direction of the fix.** The win comes from *not* gating stale
entries, not from gating them harder. A stale decay reading is not evidence
against the trade — it is absence of evidence, and the rule was treating it
as evidence.

---

## 4. How the rule should be used

**GRAY, not SKIP.** P33 settled the slot question: the engine drops a
signal either way, but holding the slot is worth **+51.6R IS / +22.0R OOS**
over freeing it, because the signals behind a filtered trade are not better
than the ones filtered. Implementation is one line before the LTF loop —
drop the bar from `filtered` — and the whole thing is in
`exp_decay_gray_skip.py`.

**Still not adopted.** 2025 is −22.3R worse than the champion. Every dNet
here is on the NET basis (`net_r()`); the older decay docs quote against a
+356.9R gross control and are understated by ~31R as a result. And the
forward window is 5 trades against a pre-registered floor of 50.
