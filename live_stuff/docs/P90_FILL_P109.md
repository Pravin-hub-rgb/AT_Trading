# P109 - P90 FILL ARM WAS ANTI-CAUSAL. The next-open idea was never tested.

Branch: agents/champion-reality-audit
Date: 2026-09-30. Backtesting only.

Source: `reality of champion followup.md` (mimo), verified here.

## THE ARM THAT WAS NAMED "NEXT 15M OPEN"

`exp_entry_fill.py:122-130`:

    e  = int(t["entry_ts"])     # v19:730 -> candles_ltf[i]["ts"], bar START
    j  = bs.bisect_left(ts, e)  # j == i, the signal bar itself
    px = op[j]                   # signal bar's OPEN

The shipped engine fills at `candles_ltf[i]["close"]` (v19:617). The arm
labelled "next open" filled at `candles_ltf[i]["open"]`, which is the same
bar and 15 minutes earlier.

So the arm was not late, it was early. It entered before the signal was
confirmed. Whatever number it produced, it was not a next-open test.

## WHAT THE TRUE NEXT-OPEN IS WORTH

Measured on the champion, all 500 trades:

    arm                          trades differing    R delta
    open[i]  (as P90 ran it)         500/500        large and meaningless
    open[i+1] (true next open)         0/500         +0.0R

Zero of 500 differ, because the candles are contiguous:
`close[i] == open[i+1]` on every trade in the book. The true next-open
price and the shipped close-fill price are the same number.

The user's original suggestion - enter at the open of the candle after the
signal candle closes - is already what the engine does. It was proposed,
implemented as an experiment, and the experiment reported a large number
because the implementation was wrong. The correct version of the test
returns zero, not because the idea was bad but because there is nothing
between the two prices.

## ON MY OWN FIRST FIGURE FOR THE open[i] ARM

The delta this note first recorded for the `open[i]` arm was +6262R. That
number is mine and it is wrong. Recomputing r as `(exit - px) / |px - sl|`
without rebuilding the whole exit path double-counts the move, exactly as
the docstring in `exp_entry_fill.py` warns: it inflates without bound. I
have left the row as "large and meaningless" rather than quote a figure I
cannot defend. The pin is unaffected and the shipped fill is untouched.

## WHAT P91 SAID, AND WHY IT WAS RIGHT FOR THE WRONG REASON

P91 retracted the +174.8R claim and attributed it to a denominator
artefact. The number was indeed retracted. The stated reason was not the
operative one: the arm was filled one bar before the signal was confirmed.
A denominator discussion does not catch that, and a reader who accepted the
reason would conclude the arm was otherwise sound.

## STATUS

- The user's next-open idea: correct, and already implemented in the
  shipped engine. Nothing to change.
- P90's +174.8R: retracted. Reason recorded incorrectly, corrected here.
- P91: conclusion stands, reasoning corrected.