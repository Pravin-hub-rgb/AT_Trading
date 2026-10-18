# htf_rr decomposition - is it a window knob or a target knob?

Every previous htf_rr result is unreadable, and this is why.

```
KNOB A   v7_timecap.py:80  target = entry + rr_target * risk
         unified.py:730     the LTF window closes at the HTF trade's exit
         => a longer target means a LONGER WINDOW, which means MORE
            LTF ENTRIES are admitted inside it

KNOB B   the same target sets the R booked on the HTF trade itself
```

So 3.0 -> 4.0 moves two independent things at once, and every sweep,
bucket and era comparison so far has been reading their sum. This
separates them per window.

| book | era | compare | windows | duration x | LTF entries | delta from ENTRY SET | delta from HTF BOOKING | total |
|---|---|---|---:|---:|---|---:|---:|---:|
| 107 | IS | 3 → 4 | 379 | 1.27 | 524 → 548 | -68.9 | +8.8 | -60.1 |
| 107 | IS | 2.5 → 4 | 408 | 1.42 | 488 → 548 | -11.6 | +17.9 | +6.4 |
| 107 | IS | 3 → 5 | 383 | 1.44 | 524 → 562 | +28.7 | +7.2 | +35.8 |
| 107 | OOS | 3 → 4 | 209 | 1.11 | 259 → 282 | +54.9 | +9.8 | +64.7 |
| 107 | OOS | 2.5 → 4 | 228 | 1.27 | 248 → 282 | +61.5 | +22.6 | +84.1 |
| 107 | OOS | 3 → 5 | 213 | 1.35 | 259 → 279 | +32.3 | -4.7 | +27.6 |
| 110 | IS | 3 → 4 | 379 | 1.27 | 394 → 412 | -75.3 | +8.8 | -66.5 |
| 110 | IS | 2.5 → 4 | 408 | 1.42 | 370 → 412 | +38.2 | +17.9 | +56.1 |
| 110 | IS | 3 → 5 | 383 | 1.44 | 394 → 422 | +76.7 | +7.2 | +83.9 |
| 110 | OOS | 3 → 4 | 209 | 1.11 | 190 → 196 | +79.0 | +9.8 | +88.8 |
| 110 | OOS | 2.5 → 4 | 228 | 1.27 | 174 → 196 | +89.5 | +22.6 | +112.2 |
| 110 | OOS | 3 → 5 | 213 | 1.35 | 190 → 189 | +31.2 | -4.7 | +26.5 |
| 106 | IS | 3 → 4 | 230 | 1.06 | 751 → 726 | -48.1 | +18.2 | -29.9 |
| 106 | IS | 2.5 → 4 | 257 | 1.15 | 746 → 726 | -41.2 | +16.5 | -24.7 |
| 106 | IS | 3 → 5 | 209 | 1.08 | 751 → 719 | -94.3 | +27.6 | -66.7 |
| 106 | OOS | 3 → 4 | 120 | 1.14 | 384 → 392 | +25.2 | -11.3 | +13.9 |
| 106 | OOS | 2.5 → 4 | 121 | 1.22 | 386 → 392 | +1.0 | -11.1 | -10.0 |
| 106 | OOS | 3 → 5 | 123 | 1.08 | 384 → 378 | +7.8 | -0.3 | +7.4 |
| 109 | IS | 3 → 4 | 228 | 1.07 | 754 → 723 | -54.0 | +12.3 | -41.7 |
| 109 | IS | 2.5 → 4 | 251 | 1.15 | 748 → 723 | -62.0 | +12.0 | -50.0 |
| 109 | IS | 3 → 5 | 223 | 1.09 | 754 → 702 | -97.3 | +26.3 | -71.1 |
| 109 | OOS | 3 → 4 | 116 | 1.11 | 391 → 393 | +13.4 | -5.2 | +8.2 |
| 109 | OOS | 2.5 → 4 | 116 | 1.17 | 385 → 393 | +11.0 | -3.9 | +7.1 |
| 109 | OOS | 3 → 5 | 121 | 1.11 | 391 → 380 | -6.1 | -2.1 | -8.2 |
| 108 | IS | 3 → 4 | 230 | 1.06 | 762 → 735 | -28.7 | +18.2 | -10.5 |
| 108 | IS | 2.5 → 4 | 257 | 1.15 | 753 → 735 | -22.0 | +16.5 | -5.5 |
| 108 | IS | 3 → 5 | 209 | 1.08 | 762 → 727 | -81.8 | +27.6 | -54.1 |
| 108 | OOS | 3 → 4 | 120 | 1.14 | 425 → 418 | +13.5 | -11.3 | +2.2 |
| 108 | OOS | 2.5 → 4 | 121 | 1.22 | 422 → 418 | -21.6 | -11.1 | -32.6 |
| 108 | OOS | 3 → 5 | 123 | 1.08 | 425 → 401 | -0.3 | -0.3 | -0.7 |

---

## How to read it

Read the last three columns together.

- **delta from ENTRY SET dominates** → htf_rr is a window-duration knob
  wearing a target's clothes. Raising the target is really admitting
  more LTF trades, and the question becomes *how long should a window
  stay open* rather than *how far should a target sit*. That is an
  ATR-adaptive window length, and `window_end="r_touch"` already
  decouples the two — at a cost previously measured at −130R.
- **delta from HTF BOOKING dominates** → it really is a plain target
  knob, and the extension-rate framing is right: which 3R-reachers
  extend to 4R.
- **the duration ratio** is the direct read. If the window barely
  changes length while the numbers move, the effect is Knob B. If it
  stretches, the effect is Knob A.

This census changes nothing and adopts nothing. It is the measurement
that decides which mechanism is worth building, and it was worth doing
before any state variable, because a mechanism aimed at Knob A would
be aimed at the wrong half of the effect.
