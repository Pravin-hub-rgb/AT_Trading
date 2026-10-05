# P16 — the smoothness bar turns out to be a real filter. 3 arms survive.

`exp_smooth_search.py`. Pins reproduced first.

## The objective was inverted, and correctly

Previous bar: `IS ≥ 280R, OOS > +70.1R, trades ≤ 380` — maximise net
subject to a size cap. **That objective is what produced a book that
gains +22R in 2023, +22R in 2024, −22R in 2025 and +9R in 2026.** A book
that swings 45R year to year is not smooth.

The user's reframing: *net can drop to 300R, R/trade can drop to 1.0,
but it has to be smooth.* So the search now **trades net and R/trade away
to buy smoothness.**

## The champion, on smoothness terms

```
n=500  net=+356.9R  R/tr=+0.890  PF=2.38  DD=17.8R
std=5.55   max losing streak=16   worst year=+102.2R
by year:  2023:+113.9  2024:+122.3  2025:+102.2  2026:+106.8
```

**That is the real shape of the problem: a 16-loss streak, and a per-trade
standard deviation of 5.55R on a +0.890R average.** The book works
because a few trades are enormous, and that is exactly what is not smooth.

## Hard floors

| floor | value |
|---|---|
| IS net | ≥ 300R |
| IS R/trade | ≥ 1.00 |
| IS trades | ≤ 420 |
| OOS net | > +70.1R |
| **every IS year** | **≥ the champion's same year** ← the 2025 fix |

The year floor is enforced against the **champion's own year**, so no arm
can win by being excellent in three years and terrible in one — which is
exactly how `decay<0.75` failed.

**No composite score is used.** A composite lets a good term hide a bad
one. Ranking is lexicographic: worst-year first, then max losing streak,
then r_std.

## **3 arms out of ~200. That is the headline.**

| arm | n | net | **R/tr** | PF | DD | **std** | **streak** | **worst yr** | OOS n | OOS net |
|---|---|---|---|---|---|---|---|---|---|---|
| `age>0.5d + hour!=12` | 406 | +400.7R | +1.164 | 2.88 | 18.4R | 6.08 | **16** | **+104.0R** | 203 | **+95.5R** |
| `nest1h>0.25 + hour!=12` | 361 | +423.0R | +1.348 | 3.18 | 19.2R | 6.40 | 15 | +103.5R | 214 | +81.2R |
| **`nest1h>0.25 + age>0.5d`** | **352** | **+409.0R** | **+1.339** | **3.13** | 18.2R | 6.47 | **13** | +102.2R | 176 | +85.7R |

Compare to the champion: **R/trade +0.890 → +1.339 (+51%)**, net
+356.9R → +409.0R, PF 2.38 → 3.13, **losing streak 16 → 13.**

## The best candidate: `nest1h>0.25 + age>0.5d`

| | champion | **this arm** |
|---|---|---|
| trades | 500 | **352** |
| IS net | +356.9R | **+409.0R** |
| **R/trade** | +0.890 | **+1.339** |
| PF | 2.38 | **3.13** |
| max losing streak | 16 | **13** |
| **every year ≥ champion** | — | ✅ |
| OOS net | +70.1R | **+85.7R** |

**It is better on net, better on R/trade, shorter streak, better PF,
better OOS — and it survives the year floor that killed `decay<0.75`.**
It is also the arm with the **shortest losing streak of the three**, which
is the smoothness term the user actually named.

## The thing that is still not solved

**Every surviving arm still has r_std ≈ 6.1–6.5, *above* the champion's
5.55.** The search made the book better on every ratio and **did not make
it less variable per trade.** That is honest and it is the limit of what
these seven features can do.

**Which is the real answer to "smooth hona chahiye": you cannot buy
smoothness with an entry filter on this book.** The variance is in the
trade outcomes themselves — the champion's winners are 10R+ runners
(`method/RUNNER_LIVE.md`: 6.8% of trades carry +151% of P&L) and **a book made
of runners is inherently spiky.** Cutting entries makes the average
better without making the distribution narrower.

**If smoothness is the real goal, the lever is the exit — and the entire
exit family is closed.** The trail/half/delay/tighten/partial experiments
are all rejected, and `P10` showed the runner is not identifiable early
enough to manage. **So the honest position is: this is the smoothest book
available from entry-side filters, and its per-trade variance cannot be
reduced further from here.**

## Caveats, stated before anyone adopts

1. **Still a grid.** 3 survivors out of ~200 is a much better filter than
   64, but the three were selected on the same two eras.
2. **`hour!=12` appears in two of the three**, and I have already shown
   today that hour filters are how a grid manufactures results. The third
   arm (`nest1h>0.25 + age>0.5d`) is the only one with **no hour term**,
   which is why it is the recommendation.
3. The forward slice at n≥50 remains the only unselected arbiter.

## Recommendation

**Take `nest1h>0.25 + age>0.5d`** — it is the only candidate with no
hour-of-day component, and it is better than the champion on net,
R/trade, PF, losing streak and OOS simultaneously while cutting 30% of
trades. Freeze it, run it forward, and if it holds, it replaces the
champion.

**And record what this exercise actually established:** the champion's
problem is not that it is too small or too large. **It is that it is
spiky, and spikiness is a property of trailing exits on a fat-tailed
book that no entry filter can fix.**
