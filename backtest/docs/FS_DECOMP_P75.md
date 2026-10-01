# P75 — DECOMPOSITION. It is not an addition. It is a 99.8% different book.

> Run 2026-09-29. Harness `exp_fs_decomp.py`. **Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> Resolves the third of P74's five outstanding items.

## The question

P73 reported 646 trades and +405.2R against a 500-trade +325.8R control, and
the owner's reading — "+150 trades for +70R" — assumed the FS arm **adds**
to the champion's book. P74 confirmed nothing established that. Trades are
matched here on `(entry_ts, direction)` — the same path-true key used in
P59, never a realised field.

## Result

| lane / era | SURVIVORS | DROPPED | NEW | dNet |
|---|---|---|---|---|
| champion IS | **1** (+5.4R) | **499** (+320.4R) | **645** (+399.8R) PF 2.97 | +79.4R |
| champion OOS | **1** (−1.1R) | **278** (+71.3R) | **363** (+233.9R) PF 2.81 | +163.4R |
| utcsat IS | **2** (+4.0R) | **452** (+354.9R) | **590** (+275.6R) PF 2.51 | −78.2R |
| utcsat OOS | **1** (−1.1R) | **252** (+61.3R) | **325** (+199.3R) PF 2.79 | +138.7R |

**One trade in common in IS. One in OOS. Two out of 454 on utcsat.**

## What that settles

**The two books are 99.8% disjoint.** This is not the champion's book with
extra trades bolted on; it is a different book that happens to be measured
against the champion.

```
champion IS:  500 trades  =  1 survivor  +  499 dropped
FS hybrid IS: 646 trades  =  1 survivor  +  645 new
                               ------         -------
                         dNet = +399.8R − +320.4R = +79.4R
```

**So "+146 trades for +79.4R" was wrong in a specific way, and the truth is
less flattering and more interesting.** The champion did not gain 146
trades; **it lost 499 profitable ones and acquired 645 different ones.**
The champion's dropped cohort was worth **+320.4R in IS and +71.3R in OOS** —
it was not a pile of losers being pruned. It was a good book, thrown away.

**What the hybrid actually is: an FS-entry book that happens to beat the
champion by a little, while containing almost none of it.** And it is a
genuinely different object from the champion — which is why the whole
framing of P73 was wrong, and why "+79.4R" was never a measure of "more
trades".

## Why the disjointness is total, and not a matching artefact

The routed `decisive` path stops emitting break entries entirely — it emits
one FS signal per swing instead. **Every trade the champion took through
`decisive` is therefore structurally unable to appear in the hybrid**, and
trades reached via the untouched `flip` / `b2` paths are a small minority
that mostly moved, because a different trigger changes which signals win the
one-slot race and the cooldown ordering.

**One or two coincidences in ~500 is what the untouched paths should
produce.** So the decomposition is not a matching failure; it is the
mechanism working exactly as the audit said it would.

## The cell that now makes sense

**utcsat IS is −78.2R and it is the one cell where the NEW cohort is worse
than what it replaced**: champion dropped **+354.9R** (R/t 0.785, PF 2.61)
against a NEW cohort of **+275.6R** (R/t 0.467, PF 2.51).

**Everywhere else the NEW cohort is better than the dropped one:**

| lane / era | DROPPED R/t | NEW R/t | NEW better? |
|---|---|---|---|
| champion IS | +0.642 | +0.620 | marginally no |
| champion OOS | +0.256 | **+0.644** | **yes, 2.5×** |
| utcsat IS | +0.785 | +0.467 | **no — and this is the −78.2R** |
| utcsat OOS | +0.243 | **+0.613** | **yes, 2.5×** |

**So the entire result, including its failure, is decided by whether the FS
cohort beats the break cohort on R/trade.** In both OOS cells it does, by
about 2.5×. In utcsat IS it does not, by 0.6×. And in champion IS it is a
wash, with the +79.4R coming from *more* trades rather than better ones.

**That is the honest characterisation, and it is a different claim from
P73's.** P73 said the FS arm produced a better book. It did — but the
comparison is between two books that share one trade, and the win comes
from OOS R/trade alone.

## What is now settled, and what is not

**Settled by this run:**
- The arm is a replacement, not an addition. The champion's dropped cohort
  was profitable in all four cells.
- The result is carried by OOS R/trade (2.5× on both lanes) and is a wash in
  champion IS.
- utcsat IS's −78.2R is not noise around a positive mean — it is the cell
  where FS entries are genuinely worse than break entries, which is exactly
  the direction `FS_ENTRY.md` warns about.

**Still not settled — the other two of P74's items:**
- **The P61 period partition is still not run.** And this decomposition
  makes it *more* necessary, not less: a claim that now rests entirely on
  OOS R/trade is precisely the claim that a half-year split could kill.
- **`FS_ENTRY.md`'s 4/4 inversion is still unchecked**, and now there is a
  sharper way to ask it: in champion IS, where the FS cohort is only a wash,
  is the swing-size distribution of the NEW cohort inverted relative to the
  DROPPED one, as that document predicts it must be?

## Status

**Still not adopted, and the registration stays withdrawn.** What changed is
that the arm is now *understood* rather than merely impressive: it is an
FS-entry book that is 2.5× better per trade than the break book in OOS, at a
wash in champion IS and 0.6× in utcsat IS, containing one trade in common
with the champion.

**That is a real finding about FS entries in the champion pipeline, and it
is a much smaller claim than "more trades AND better quality".** The period
partition and the swing-size inversion check are the two things that would
make it adoptable or kill it, and neither has been run.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
