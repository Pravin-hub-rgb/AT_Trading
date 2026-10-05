# P14 — under the user's new bar, 4 singles and 64 pairs clear it. Read the
# selection warning before the numbers.

`exp_newbar_search.py`. Pins reproduced first (IS 500t/+325.8R, OOS
279t/+70.1R).

## The bar changed, and the old bar was the wrong question

Everything today was scored against P5's null (M = 479.9R IS / 193.4R
OOS). The user was right that this asks *"is this skill?"* when the
question is *"is this a better book?"*, and set a new bar:

| | old | **new** |
|---|---|---|
| IS net | > 479.9R | **≥ 280R** |
| OOS net | > 193.4R | **> +70.1R** (must not lose) |
| IS trades | 500 | **≤ 380** |

**This is not a weakening — it is the only route to a resolvable result.**
A 500-trade book cannot clear 480R, so demanding it guarantees every arm
fails and teaches nothing. A smaller book has a smaller M. That is
exactly why P12's U1 arm, which I dismissed for firing my own
"trade-deletion" falsifier, is the shape being asked for here. **That was
my mis-framing, not a refutation of the arm.**

## Four singles clear the bar

| arm | IS n | **IS net** | IS WR | IS PF | IS DD | OOS n | **OOS net** | OOS WR | OOS PF |
|---|---|---|---|---|---|---|---|---|---|
| **decay<0.75** | 307 | **+383.9R** | 33.6% | 3.34 | **13.8** | 147 | **+84.2R** | 29.3% | 2.05 |
| nest1h>0.4 | 309 | +339.7R | 33.3% | 3.02 | 26.8 | 178 | +74.1R | 26.4% | 1.78 |
| **age>1.0d** | 364 | +331.4R | 33.0% | 2.76 | 22.1 | 180 | **+95.9R** | 28.9% | 1.99 |
| **live_r>0.0** | 345 | +317.2R | 33.3% | 2.82 | 21.1 | 177 | **+87.4R** | 29.4% | 1.96 |

All four beat the champion on **both** eras while cutting 27–39% of trades.
`decay<0.75` — **the user's own structural signal from P11** — is the best
on IS net, win rate, PF and drawdown simultaneously: **+383.9R at 33.6%
WR, PF 3.34, DD 13.8R, from 307 trades instead of 500.**

Best OOS is `age>1.0d` at **+95.9R** (vs the champion's +70.1R).

## And 64 pairs clear it

Top 15 by worst-era ratio:

| pair | IS n | IS net | IS PF | IS DD | OOS n | OOS net | OOS PF |
|---|---|---|---|---|---|---|---|
| **decay<0.75 + age>0.5d** | 263 | **+397.1R** | 3.83 | **13.1** | 111 | **+94.9R** | 2.49 |
| **nest1h>0.4 + live_r>0.0** | 226 | +363.0R | **4.11** | 15.9 | 114 | +95.1R | 2.52 |
| nest1h>0.25 + hour!=6 | 374 | +396.1R | 2.94 | 17.7 | 215 | +88.5R | 1.78 |
| **decay<0.75 + nest1h>0.25** | 242 | **+409.1R** | 4.13 | **11.7** | 123 | +86.0R | 2.24 |
| nest1h>0.25 + age>0.5d | 352 | +409.0R | 3.13 | 18.2 | 176 | +85.7R | 1.88 |

`decay<0.75 + nest1h>0.25`: **+409.1R IS at PF 4.13 with DD 11.7R from 242
trades.** That is 500 → 242 trades (−52%) with IS net **up 26%** and
drawdown **down 40%**.

## The number that should worry you: 64 of ~200 pairs

**Roughly a third of all pairs meet a bar I set after looking at the
data.** That is not a discovery rate, it is a grid searching two eras.

**Concretely: `hour!=3`, `hour!=6`, `hour!=9`, `hour!=15` all appear in the
top 15.** Four different hours, all "helpful", all nonsense — BTC has no
reason to care that hour 3 was banned. **That is the selection effect
made visible, and it is the reason none of this is adoptable today.**

## What is genuinely different from a grid artifact

Three things survive that kind of scrutiny, and they are not the pairs:

1. **`decay<0.75` was found before this search and predicted before it.**
   P11 reported, from a descriptive autopsy with no bar in mind, that
   `decay ≥ 0.75` is the *worst* cohort in the study (20.3% WR) and that
   decay 0.25 holds the book. This search confirms that prediction
   quantitatively. **A pre-registered prediction that holds is worth more
   than a grid that finds something.**

2. **`age>1.0d` and `nest1h>0.4` are the same fact seen twice** — the
   book's R is made later in a window, which is also W1's untested
   duration idea and P1-P's nesting gradient. Three independent probes,
   one direction.

3. **`live_r>0.0` is the P3/P4 family**, rejected 0/7 as a *flip* and as a
   *floor* on a different config. As a plain "the 1h leg is not losing"
   filter on the real champion it gives +317.2R IS / +87.4R OOS. **The
   family was killed in a form that does not generalise.**

## The honest verdict

**There is a real, pre-predicted, two-era improvement available, and it is
smaller, faster and cleaner than the champion. But 64 pairs clearing a
post-hoc bar means the bar is not a bar — it is a target fit to noise.**

**What I would actually do with this:**

- Take **`decay<0.75` alone**. It is a single threshold, pre-predicted by
  P11, from the user's own hypothesis, that improves both eras on net,
  WR, PF and drawdown while cutting 39% of trades.
- **Ignore the pairs entirely** until the forward slice exists. A pair
  chosen from 64 candidates that clear a bar is worth roughly nothing.
- Re-run the chosen arm on the **forward slice at n≥50**, which is the
  only arbiter that has not been used to select anything.

**And the thing this whole exercise actually proves:** the champion is
*too big*. 500 trades at 30% WR is a book whose edge is 6.8% of entries.
Cutting it to 300 makes it faster, cleaner, lower-drawdown and
out-of-sample better. **The improvement was available the whole time — it
just required accepting a smaller book, which is the opposite of what
every prior experiment in the repo was trying to do.**
