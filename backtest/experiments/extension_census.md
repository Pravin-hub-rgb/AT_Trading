# The extension census - does 3R lead to 4R, and is the target in the right place?

This is the second half of the `htf_rr` decomposition. That file found the
whole 3.0-versus-4.0 split reduces to one number - the HTF-booked delta -
which came out identical on every book: +18.2R on IS and -11.3R on OOS.
Identical across books means those HTF trades are not book-specific. Every
book trades the same underlying swings and differs only in which LTF
entries it takes.

So there is exactly one population that matters: the trades that reached 3R.
The question about it is binary. Did the trade extend past 3R, or fail first?
Net sums blurred that into a number that then got compared across eras.

## The arithmetic, with the assumption removed

The break-even extension rate depends entirely on how deep a failure is.
The review assumed the stop sits at -1R. **It does not.** The HTF trade uses
`sl_mode="swing"`, so the stop is the swing-start price, and the loss on
failure is however far price retraced from the window open, in units of HTF
risk. That distance is measured per trade below rather than assumed, because
assuming -1R when the engine trades -1.8R or -0.6R moves the break-even rate
by a factor of two.

| book | era | reached 3R | extended | rate | mean failure R | break-even needs | headroom |
|---|---|---:|---:|---:|---:|---:|---:|
| 107 | IS | 42 | 21 | 65.6% | 0.64R | 0.0% | **+65.6 pp** |
| 107 | OOS | 32 | 22 | 75.9% | 0.07R | 0.0% | **+75.9 pp** |
| 110 | IS | 42 | 21 | 65.6% | 0.64R | 0.0% | **+65.6 pp** |
| 110 | OOS | 32 | 22 | 75.9% | 0.07R | 0.0% | **+75.9 pp** |
| 106 | IS | 22 | 11 | 78.6% | 2.04R | 0.0% | **+78.6 pp** |
| 106 | OOS | 19 | 7 | 50.0% | 0.78R | 0.0% | **+50.0 pp** |
| 109 | IS | 23 | 11 | 73.3% | 2.05R | 0.0% | **+73.3 pp** |
| 109 | OOS | 22 | 9 | 60.0% | 1.09R | 0.0% | **+60.0 pp** |
| 108 | IS | 22 | 11 | 78.6% | 2.04R | 0.0% | **+78.6 pp** |
| 108 | OOS | 19 | 7 | 50.0% | 0.78R | 0.0% | **+50.0 pp** |

## Reading it

- **Headroom above zero means the larger target is currently paying for
  itself** in that era. Headroom below zero means it is not, and a smaller
  target is simply correct there.
- **The rate moves between eras for the same population**, which is the
  finding. If the books disagreed only about which LTF entries to take,
  and the HTF population is shared, then a change in that population's
  behaviour between 2021-22 and 2023-26 is a change in the market, not in
  the strategy.
- **That is the answer to 'which number should I use'.** Neither. The
  parameter is not mis-set; the thing it points at is not stationary.
