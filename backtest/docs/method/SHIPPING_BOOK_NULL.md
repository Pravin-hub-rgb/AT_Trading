# The shipping book has never cleared a significance test — and that is the finding

Date: 2026-10-08. Engine post-C17. Harness: `exp_permute_shipping.py`.
Book: `fsent_champ_long`. Control: `fsent_sig_full` (identical trades — the
self-test). Draws 4000, seed 20261008, gate p < 0.05.

## The gap this closes

`fsent_champ_long` is `exp_fs_entry_side="long"`. That means longs enter on the
swing **FS (failure-swing) print** and shorts stay on the **break**. That is
P80's directional-FS architecture — verbatim.

P80's arms were the best-looking result of their entire round: **four of four
cells positive**, the period partition holding everywhere (22 wins, 8 losses),
both mirror directions agreeing. And P82's permutation test killed it in every
cell — **p = 0.69 to 0.92**. It was a swap of ~400 trades for ~400 trades.

**But P82 tested `champion_multi_sw10`, and this book is not that lane.** It
differs in five parameters:

| param | champion_multi_sw10 | fsent_champ_long |
|---|---|---|
| mode | `b2_vs_flip_chop` | `atr_high` |
| cooldown_bars | 10 | 8 |
| exp_persist | absent | 7 |
| pivot_rule | absent | leg |
| ext_stop_r | 1.5 | 0.0 |

So P82's p = 0.69 does not transfer. Neither does P80's +184.8R. **The shipping
book's significance claim has simply never been tested on itself.**

## The result

| book | era | dNet | **p** | significant |
|---|---|---:|---:|---|
| `fsent_sig_full` (control) | IS | +0.00R | 1.0000 | no — correct, identical trades |
| `fsent_sig_full` (control) | OOS | +0.00R | 1.0000 | no — correct |
| **`fsent_champ_long`** | **IS** | **+237.54R** | **0.7398** | **NO** |
| **`fsent_champ_long`** | **OOS** | **+45.15R** | **0.9123** | **NO** |

Decomposition asserted exact in every cell (P82's lesson — survivors do **not**
cancel):

- IS: 528 NEW, 234 DROPPED, 0 survivors, dNet **+237.54R**, p = **0.7398**
- OOS: 311 NEW, 151 DROPPED, 0 survivors, dNet **+45.15R**, p = **0.9123**

The control arm is the harness's own self-test: the book and its control produce
identical trades, so dNet must be exactly 0 and p must be exactly 1. It is. **The
harness is not returning p = 0.74 by accident — it returns p = 1.00 when the
answer is genuinely zero.**

## What this means, stated carefully

**The book is not being removed and should not be.** It remains the base every
other result in the repo is measured against, its pins reproduce, and it is what
the owner trades. Nothing here argues for a parameter change.

What this means is narrower and more useful: **the ARCHITECTURE was adopted on
the strength of P80's result without ever clearing a null.** Every other proposal
in this programme was required to clear exactly this bar — P82 exists precisely
because P80 looked too good to accept un-tested. The champion was not held to it,
because the bar did not exist when it was adopted.

> **The +237R in sample and the +45R out of sample are real numbers on real
> trades. They are not distinguishable from a random reassignment of the same
> trades.** That is not the same as saying the book is noise. It is saying the
> *trigger change* — FS vs break — is not, on this evidence, distinguishable from
> picking a different set.

## The caveat I cannot resolve and will not hide

P82's own note says the survivor term contributed **+28.6R of P80's +184.8R** and
that the books are **99.8% disjoint**. Here the disjointness is **100%** — zero
survivors in both eras. So the two books share no trades at all.

That makes the test the most powerful one available, and also the most
unfavourable one for the null to hide behind: with zero survivors, the entire
dNet is "NEW minus DROPPED", and the permutation asks whether swapping which of
the union's trades are new and which are dropped could have produced something
this large. **It could have — 74% of the time in sample, 91% out.**

## What would settle it

Not a better test. More data. Per P63, a forward slice can **rule out, never
confirm** — and the OOS leg at p = 0.91 is a 151-trade era. At the champion's
rate that is roughly **5–6 months of genuinely new data** (`STABILITY_FORWARD_P61`
puts the 60–70-trade floor at about March 2027).

Two honest readings, and I am not going to pretend to know which is right:

1. **The book is a real edge that the permutation cannot resolve** because the
   available sample is small relative to a 237R effect.
2. **The book is a lucky subset** and the era-to-era net (533R IS → 240R OOS, a
   55% decay on a book that trades 528 → 311) is the tell.

The repo's own convention is to publish the null whatever it says, and to state
what it does not prove. Both readings stay open until the forward data arrives.

**Nothing adopted. No book promoted, removed, or re-pinned.**