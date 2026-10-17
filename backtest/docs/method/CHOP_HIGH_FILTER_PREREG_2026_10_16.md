# CHOP-HIGH FILTER - ONE OOS REVEAL, PRE-REGISTERED 2026-10-16

Written BEFORE the OOS era is opened. Committed before the run. The point of
this file is that whatever comes back, it means what it says.

## WHAT IS BEING TESTED

C2 characterised the corrected IS chain and found a RISK pattern, not a return
one:

    bucket                  n    mean   maxDD   maxStreak
    chop HI / atr LO      106   +1.190    5.67         7
    chop HI / atr HI      143   +0.923    5.08         5
    chop LO / atr LO      142   +1.524   14.43        17
    chop LO / atr HI      106   +0.818    9.62         8

HIGH CHOP roughly halves drawdown and shortens the worst losing streak two to
threefold. ATR contributes nothing on either axis, so ATR is dropped and only the
chop filter is carried.

The question: **does the risk reduction survive on 2021-22, or was it another
artefact of a chain that has already surprised this repo three times?**

## THE EXACT TEST

Book: `fsent_champ_long`, both eras, unchanged.
Filter: keep a trade only if the chop value at its entry is at or above the
IS-derived median (chop p50 = 10.39, from the book's own 497 IS trades).
Nothing else moves. No threshold is tuned here - the median is already fixed.

Measured on OOS, five numbers, no more:

    trades kept / dropped
    net R, and what fraction of the unfiltered net survives
    max drawdown, and the ratio to the unfiltered book
    worst losing streak, and the ratio
    per-trade R, so a smaller book cannot flatter itself on total

## WHAT EACH OUTCOME MEANS - DECIDED NOW, NOT AFTER

**A. OOS drawdown ratio at or below 0.65, and net retains 80% or more.**
    The risk reduction carried. Build a chop-high mode in unified.py, register
    it, and let it compete on the same terms as everything else. This is the
    only outcome that authorises engine work.

**B. OOS drawdown ratio at or below 0.65, but net retains less than 80%.**
    A real trade-off, not an improvement. Present both sides and let the owner
    decide. No engine work either way.

**C. OOS drawdown ratio above 0.65.**
    The IS risk pattern does not carry. Close the idea permanently, write it to
    CLOSED_DO_NOT_REPEAT.md with both eras, and do not revisit it. No engine work.

**In all three cases the OOS era is now spent.** It has been used to decide, so
it stops being a check. Every book measured from here is measured on IS plus the
forward window only. That is the cost of one reveal and it is paid once, not
renegotiated afterwards.

## WHAT THIS IS NOT

Not a search. One filter, one threshold, already chosen. Not a knob sweep - no
value is tuned on OOS. Not an advertisement - outcome A authorises a
registration, not adoption, and the new book would then face the same gauntlet
everything else faces.

## THE HONEST PRIOR

The correct chain has already contradicted four things this repo believed about
the old one. The most likely outcome is C. Writing C down in advance is what
makes that result usable rather than disappointing.