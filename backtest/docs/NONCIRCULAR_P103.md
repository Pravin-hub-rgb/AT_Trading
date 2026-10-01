# P103 - bars_to_window_end IS ARITHMETIC, NOT A SIGNAL

Branch: agents/champion-reality-audit
Date: 2026-09-30. Net accounting, IS, v19 champion.

## THE CLAIM BEING TESTED

P94 found that the trades which outlive their HTF window carry almost all
of the profit. P95 attributed the split to bars_to_window_end. The
reported AUC was 0.843-0.867.

An AUC that high would make this the obvious next filter. Before building
it, the claim has to survive one question: is the feature knowable when
the trade is entered?

## WHY IT CANNOT BE

A trade "outlives its window" exactly when

    bars_to_window_end > bars_held

Both sides of that inequality are determined by when the trade exits. The
HTF window has no fixed length: `window_end="exit"` means it closes when
the 1h trade exits, plus a 16-day cap. At the moment of entry, the window
end is unknown. So is the hold. The comparison can only be evaluated
after the fact.

The label is not merely correlated with the feature. The feature is a
restatement of the label.

## THE MEASUREMENT

Two features, same label, both scored by AUC against "outlived its window":

    AUC bars_to_window_end     (post-outcome, circular)   0.842
    AUC bars_since_window_open (causal, knowable at entry) 0.472

bars_since_window_open is the honest substitute: how far into the window
the entry sits. It is knowable at entry, because the window's OPEN is
known the moment the flip candle closes. 0.472 is a coin flip. The
entry-time information does not exist.

The 0.842 was never a signal. It measured the engine restating itself.

## THE COHORTS, ON THIS RUN

    outlived window : n=400   +22.0R gross   (+0.055R per trade)
    inside window   : n= 99  +487.0R gross   (+4.92R per trade)

499 of 500 trades matched a covering window. Gross, not net: costs come
to roughly 183R across the book, taking 509R gross to 325.8R net.

Note the cohort sizes. Earlier write-ups recorded 103 trades at
+481.6R for the profitable side, and this run puts it at 99 trades and
+487.0R. Same object, inverted label - what P94 called "outlived" is
"inside" here. The magnitude agrees to within the cost model.

Neither cohort is losing. The large one is merely flat: 400 trades that
net out to almost nothing, carrying costs.

## RULING

Do not build a bars_to_window_end threshold family. There is no entry-time
feature that predicts this split, so any threshold will fit the outcome
and will not survive contact with live data. This is the P80/P82 shape:
a post-hoc partition that looks excellent in-sample and has nothing to
act on in production.

The lead is closed. It is the only live lead the P55-P100 rounds
produced, and it does not survive being written down.

## WHAT WOULD MAKE THIS LIVE-ACTIONABLE

A feature known at entry that predicts remaining window life, e.g. the
1h regime's own trailing slope, or a volatility-state feature. Neither has
been measured. If the search is reopened, the first gate is the causal
one: report AUC for a feature knowable at entry, and treat any
post-outcome feature as disqualified rather than as a discovery.