Yes bhai. **This is exactly the right thing to build now.** Instead of asking *“which strategy made the most R?”*, make a **Strategy Quality Scorecard** and judge every candidate through the same tests.

And I agree with your instinct: **winner distribution / gaps, DD, equity curve, curve-fitting, IS→OOS retention** should all be in it.

I’d divide it into **7 buckets**.

---

# 1. Raw profitability — "Does it actually make money?"

These are the basic gates.

### A. Net R

Obviously important, but **not the ranking metric by itself**.

A strategy making +300R with horrible concentration may be worse than one making +220R much more consistently.

### B. Expectancy

`Net R / Number of Trades`

Useful because it normalizes total return for trade count.

### C. Profit Factor

`Gross Profit / Gross Loss`

Good secondary metric.

### D. Number of trades

A +100R strategy with 25 trades and a +100R strategy with 500 trades aren't equivalent evidence.

---

# 2. Drawdown — "How painful is it?"

Don't just record **Max DD**.

You want:

### A. Maximum drawdown

Peak → trough.

### B. Drawdown as % of total return

For example:

```text
Strategy A
Net = 300R
DD = 10R

Strategy B
Net = 350R
DD = 45R
```

B has more profit, but A has dramatically better return/DD characteristics.

You can calculate:

`Net R / Max DD`

This is a useful ranking metric.

---

### C. Drawdown duration

This is **very important** for what you're looking for.

Not only:

> "How deep did it fall?"

but:

> **"How long was I underwater?"**

Record:

* longest DD duration
* average DD duration
* number of DD periods
* time to recover from maximum DD

A 15R drawdown lasting 15 trades is psychologically very different from 15R lasting 100 trades.

---

### D. Worst rolling periods

This is one of my favorites for your use case.

Calculate worst:

* 10 trades
* 20
* 30
* 50
* 100 trades

And maybe:

* worst 3 months
* worst 6 months
* worst 12 months

This catches strategies whose overall equity looks good but have horrible dead zones.

---

# 3. Equity-curve quality — "How does the money arrive?"

This is the part you're intuitively looking for.

## A. Winner spacing

Exactly what you mentioned.

Don't just count winners.

Measure the **gap between meaningful winners**.

For example:

```text
Trade #20 → +8R
Trade #21–48 → no major winner
Trade #49 → +12R
```

Gap = 28 trades.

Calculate:

* average gap between winners
* median gap
* maximum gap
* 90th percentile gap

I'd especially look at **maximum gap between +X R winners**.

Do it for:

```text
+3R
+5R
+10R
+20R
```

Because a trend follower naturally needs big winners, but if the strategy requires a +20R trade every 15 trades to survive, that's very different from one where +20R trades can disappear for 60 trades and the strategy still survives.

---

## B. Winner spread through time

Divide the backtest chronologically into equal blocks.

For example:

```text
10 blocks
20 blocks
quarterly
yearly
```

Then ask:

> Is profit being generated throughout the dataset?

Example:

```text
2023  +45R
2024  +60R
2025  +50R
2026  +55R
```

Beautiful.

Versus:

```text
2023  +10R
2024  +250R
2025  −5R
2026  +15R
```

Much more suspicious.

---

## C. Rolling expectancy

Calculate rolling:

* 20-trade expectancy
* 50-trade expectancy
* 100-trade expectancy

You want to know whether the strategy's edge periodically collapses.

---

## D. Equity-curve linearity

You can fit a simple line to the cumulative R curve and measure how much actual equity deviates from that trend.

This gives you an idea of **smoothness**, but I wouldn't make it a primary metric.

Why?

Because a real trend-following strategy can have a very non-linear equity curve while still being perfectly legitimate.

**Smoothness is nice. Stability is more important.**

---

# 4. Winner / Tail Dependence — VERY important for your strategies

This deserves its own category because you've already discovered that your trend strategy is extremely right-tailed.

Calculate:

### Remove top 1 winner

### Remove top 3

### Remove top 5

### Remove top 10

### Remove top 5%

### Remove top 10%

Then calculate:

`Remaining Net R / Original Net R`

This tells you how dependent the strategy is on exceptional trades.

---

## Winner cap test

Also:

```text
Cap winners at 5R
Cap winners at 10R
Cap winners at 15R
Cap winners at 20R
```

This is excellent for comparing your strategies.

You might discover:

### Strategy A

```text
Original: +300R
10R cap:  +100R
```

### Strategy B

```text
Original: +250R
10R cap:  +190R
```

I'd probably investigate **B much more seriously**, even though A has the higher headline return.

Because B's edge is more distributed.

---

# 5. Statistical / robustness quality

This is where we separate **"historically good"** from **"potentially robust."**

## A. Parameter sensitivity

This is huge.

Suppose your ATR buffer:

```text
0.20 → +170R
0.25 → +180R
0.30 → +184R
0.35 → +181R
0.40 → +176R
```

Excellent-looking plateau.

But:

```text
0.20 → +50R
0.25 → +120R
0.30 → +300R
0.35 → +80R
0.40 → −20R
```

Very suspicious.

You want **stable neighborhoods**, not one magical parameter.

---

## B. Rule sensitivity

Same thing for:

* lookback
* swing definition
* stop
* target
* time stop
* filters
* session rules

Ask:

> Does the edge survive reasonable neighboring definitions?

---

## C. Cost sensitivity

Run:

```text
Base costs
1.5× costs
2× costs
3× costs
```

Especially important in crypto.

A strategy that dies when costs increase 30% is much less attractive than one that survives 2× costs.

---

## D. Slippage sensitivity

Same idea.

---

# 6. IS / OOS quality

This is **one of your biggest criteria**.

Don't just record:

> IS = +300R
> OOS = +100R

Create an **OOS retention ratio**.

### Simple version

`OOS Retention = OOS expectancy / IS expectancy`

Example:

```text
IS expectancy  = +0.80R
OOS expectancy = +0.50R

Retention = 62.5%
```

That's much more informative than comparing total R when the number of trades differs.

You can also calculate:

### PF retention

`OOS PF / IS PF`

### WR retention

`OOS WR / IS WR`

### DD expansion

`OOS DD / IS DD`

And:

### Net-R retention

`OOS Net R / IS Net R`

But **expectancy retention is probably the cleanest primary one**.

---

## OOS sign consistency

This is another strong criterion.

Suppose:

```text
IS: +180R
OOS: +70R
```

Good.

But if:

```text
IS: +180R
OOS: −90R
```

Huge warning.

Even if the OOS loss isn't enough to kill the strategy, you need to understand why.

---

# 7. Curve-fitting / complexity

This is where I think you should be **very strict**, because you've already experimented with lots of filters.

## A. Number of rules

Count:

* entry conditions
* exit conditions
* filters
* session filters
* volatility filters
* time filters
* regime filters

A simple strategy with 3 rules producing +150R is much more interesting than a 17-filter monster producing +250R.

Not because simple automatically = good.

But because **every additional degree of freedom gives you another opportunity to fit historical noise.**

---

## B. Number of filters

I'd literally put this in your scorecard.

```text
0–2 filters → excellent simplicity
3–4 → reasonable
5–7 → investigate
8+ → high complexity
```

Not as a universal law—just as a **research warning flag**.

---

## C. Research history

This is even more important than filter count.

Record:

> **How many versions did we try before selecting this one?**

Because:

```text
Strategy A
3 variants tested
→ +150R
```

is different evidence from:

```text
Strategy B
847 variants tested
→ best = +300R
```

The second result has undergone much more selection pressure.

---

# 8. Trade-distribution quality

I'd add this separately.

Look at:

### Win rate

But don't overvalue it.

### Average winner

### Average loser

### Median winner

### Median loser

### Maximum winner

### Maximum loser

### Skew

And particularly:

> **Mean vs median trade**

Suppose:

```text
Mean = +1.2R
Median = −0.9R
```

That tells you immediately:

**most trades are losers and a small number of huge winners create the positive mean.**

That may be perfectly valid trend following—but you need to know it.

---

# 9. Losing-side behaviour

People obsess over winners.

I'd also measure:

### Maximum consecutive losses

### Average losing streak

### 90th percentile losing streak

### Worst loss cluster

### Worst 20-trade period

### Worst 50-trade period

This matters enormously for live survivability.

---

# 10. Regime robustness

This is something I REALLY want in your framework.

Break performance down by:

* year
* quarter
* volatility regime
* trend regime
* sideways regime
* high/low directional efficiency
* bull/bear
* high/low volatility

You don't need positive performance in every regime.

What you want to discover is:

> **Where does the strategy work and where does it struggle?**

A strategy that works beautifully during directional markets and poorly during chop isn't necessarily bad.

A strategy that has **no identifiable market behaviour associated with its success** is more concerning.

---

# 11. Cross-market robustness

Since you've already found that some alt pairs perform better than BTC, this becomes important.

Same conceptual strategy across:

```text
BTC
ETH
ALT 1
ALT 2
ALT 3
...
```

Don't necessarily demand equal performance.

Instead ask:

> Does the underlying phenomenon survive across instruments?

For each asset:

* expectancy
* PF
* DD
* WR
* tail dependence
* OOS retention

Then you can create:

**Cross-Asset Success Rate**

Example:

```text
7/10 assets profitable
```

That is potentially much more informative than BTC's +200R alone.

---

# 12. Execution realism

This is a separate gate.

Test:

* fees
* spread
* slippage
* funding
* latency assumptions
* entry price assumption
* exit price assumption

And particularly:

> **Does the strategy still work under pessimistic execution assumptions?**

A backtest that needs perfect fills is not a strategy I'd trust.

---

# 13. Data integrity

This is boring but **absolutely mandatory**.

Before comparing strategies:

* no duplicate candles
* correct timestamps
* no lookahead
* correct timezone
* no future data leakage
* correct candle-close handling
* correct intrabar assumptions
* correct SL/TP ordering
* correct missing-data handling

You already learned the painful version of this one. 😭

So I'd actually give **data/backtest integrity a PASS/FAIL gate**, not a score.

If it fails → strategy doesn't enter the leaderboard.

---

# Your actual leaderboard

I wouldn't make one giant arbitrary score like:

> `Strategy Score = 73.42`

because that can hide problems.

Instead I'd use **gates + scorecard**.

### Tier 0 — Validity

Must pass:

* no lookahead
* correct timestamps
* correct execution logic
* costs included
* reproducible results

### Tier 1 — Performance

Measure:

* Net R
* expectancy
* PF
* trade count

### Tier 2 — Equity Quality

Measure:

* Max DD
* DD duration
* recovery
* worst rolling 20/50/100 trades
* winner gaps
* profit distribution across time

### Tier 3 — Tail Dependence

Measure:

* top 1/3/5/10 removal
* 10R/15R/20R cap
* top 5% contribution
* maximum winner

### Tier 4 — Robustness

Measure:

* parameter plateau
* cost sensitivity
* slippage sensitivity
* rule sensitivity
* regime stability
* cross-asset behaviour

### Tier 5 — OOS

Measure:

* IS expectancy
* OOS expectancy
* expectancy retention
* PF retention
* OOS/DD
* OOS sign consistency

### Tier 6 — Complexity

Measure:

* number of filters
* number of parameters
* number of variants tested
* amount of historical iteration

---

# And I would rank them roughly like this

If you give me **20 strategies**, I would NOT automatically choose:

> highest Net R.

I'd prioritize something closer to:

**1. Validity**
**2. OOS performance**
**3. OOS retention**
**4. Drawdown / DD duration**
**5. Worst rolling periods**
**6. Distribution of winners through time**
**7. Tail dependence**
**8. Parameter robustness**
**9. Cost/slippage robustness**
**10. Simplicity**
**11. Cross-asset evidence**
**12. Raw Net R**

That last point is intentional.

**Net R should be a major factor, but not the king.**

Because I think what you're actually looking for is something like:

> **“I don't care if Strategy A makes 400R and Strategy B makes 250R. Give me the one whose edge is understandable, distributed, survives OOS, survives reasonable parameter changes, doesn't require 12 filters, and doesn't completely collapse when its three biggest trades disappear.”**

**That is a much better definition of “best strategy.”**

And we can turn this into an actual **strategy-ranking spreadsheet/MD specification** next: each metric gets a precise formula, PASS/WARN/FAIL thresholds, and a final ranking system so you can dump every strategy's report into it and get a comparable leaderboard.
Haan bhai, **mentioned hai** — but I’d make it much more explicit in our final scorecard.

For tail dependence, we should test **top X% of trades**, not only “top 1 / 3 / 5 / 10 trades.”

For example, if a strategy has 500 trades:

| Test     |      What we remove |
| -------- | ------------------: |
| Top 0.5% | 2–3 biggest winners |
| Top 1%   |   5 biggest winners |
| Top 2%   |                  10 |
| Top 5%   |                  25 |
| Top 10%  |                  50 |
| Top 20%  |                 100 |

Then calculate:

**Remaining Net R / Original Net R**

So if:

> Original = +300R
> Remove top 5% = +210R

then **70% of the original R remains**.

That's a very useful comparison between strategies with different trade counts.

### I would actually include BOTH

**Absolute removal**

* Remove top 1
* top 3
* top 5
* top 10

**Percentage removal**

* top 0.5%
* top 1%
* top 2%
* top 5%
* top 10%
* top 20%

Because they answer slightly different questions.

For your particular research, **top 5% and top 10% are especially important**. You're trying to distinguish:

> “This strategy has a healthy right tail”

from

> “This strategy only works because a tiny handful of trades happened to be massive.”

And I'd also record the **contribution of the top X%**, not just removal:

`Top-X% contribution = R generated by top X% / Total Net R`

That gives us a very clean **tail-dependence profile** for every strategy.

So yes — **TOP X% absolutely belongs in the final strategy-selection framework.**
Bhai, **“healthy distribution” ka koi universal number nahi hai**. Especially trend-following mein, positive skew/right tail *expected* hai. So healthy does **not** mean “every winner is roughly the same size.”

For your strategy selection, I'd define healthy more like this:

### 1. Profit should be spread across many trades / periods

Good:

> +200R total
> generated across many different trend episodes.

More concerning:

> +200R total
> but +170R came from 3 trades.

The second isn't automatically bad, but it's **highly tail-dependent**.

---

### 2. Top X% shouldn't be carrying almost everything

This is where your test becomes useful.

Imagine two 200-trade strategies:

|                     | Strategy A | Strategy B |
| ------------------- | ---------: | ---------: |
| Total               |      +200R |      +200R |
| Top 1% contribution |        25% |        60% |
| Top 5% contribution |        50% |        85% |
| Remove top 5%       |      +100R |       +30R |
| Remove top 10%      |       +65R |        −5R |

I'd much rather investigate **A**.

Not because B is necessarily curve-fitted, but because B has much greater dependence on rare events.

---

### 3. But don't demand that top 10% contribute very little

This is **really important for your trend strategy**.

If your strategy is genuinely exploiting trends, I'd actually expect:

> **Top winners to contribute disproportionately.**

That's the nature of positive-skew trend following.

So something like:

```text
Top 10% → 40–60% of profits
```

could be perfectly reasonable.

Where I'd become much more interested in investigating is something like:

```text
Top 1–2% → 70–90% of profits
```

because then the strategy's historical existence may depend on an extremely tiny number of events.

But again: **these aren't hard universal thresholds.** They're warning zones, not laws.

---

# 4. The bigger thing: winner spacing

For your particular goal, **this may actually matter more than the top-X% number.**

Suppose:

### Strategy A

```text
+8R
+3R
+5R
+11R
+4R
+7R
+3R
+15R
```

Winners are coming regularly.

Versus:

### Strategy B

```text
−1
−1
−1
−1
−1
−1
−1
−1
−1
−1
+80R
```

Same cumulative profitability might eventually happen.

But B has a much more fragile-looking equity process.

So I'd measure:

* median gap between winners
* 90th percentile winner gap
* maximum winner gap
* maximum gap between **+5R** winners
* maximum gap between **+10R** winners
* maximum gap between **+20R** winners

---

# 5. Even more important: what happens *during* the gap?

This is where your earlier test was actually excellent.

You found a **44-trade gap between 20R+ winners**, but during that period:

> +29.3R
> 15 wins / 29 losses
> Max DD 8.1R

That's actually **much healthier** than:

> 44 trades → −30R → one +40R winner saves everything.

Because your strategy demonstrated that it can generate positive expectancy **even when the giant trend doesn't appear**.

That's exactly the type of evidence I'd want.

---

# 6. So what would I call a "healthy" right-tailed strategy?

Something roughly like:

```text
Many small losses
        ↓
Some ordinary winners
        ↓
Occasional large winners
        ↓
Very large winners are helpful
        ↓
BUT the strategy doesn't completely depend on them
```

Graphically:

```text
Losses:       ████████████████████████
Small wins:   █████████
Medium wins:  █████
Large wins:   ██
Huge wins:    █
```

That's still a **right-skewed distribution**.

You don't want to turn it into:

```text
Losses:       ███████████████████████████████
Small wins:   █
Medium wins:  .
Large wins:   .
Huge wins:    .
```

just because you dislike tail dependence.

That could literally destroy the thing generating the edge.

---

# The metric I'd add to your framework

Instead of one arbitrary definition of “healthy distribution,” I'd create a **Tail Health Profile**:

### Tail concentration

* Top 0.5%
* Top 1%
* Top 2%
* Top 5%
* Top 10%

### Survival after removing tails

* Remove top 1
* top 3
* top 5
* top 10
* top 5%
* top 10%

### Temporal distribution

* maximum winner gap
* 90th percentile winner gap
* profitable months %
* profitable years %
* worst 20/50/100 trade periods

### Gap survivability

For the longest gap between major winners:

> **Did the strategy survive it profitably, or was it bleeding heavily waiting for the next monster trade?**

That last one is **very relevant to what you're looking for**.

Because I don't think you actually want a strategy with *no* huge winners.

You want:

> **“If the next monster trend doesn't come for a long time, I'm still okay.”**

That's a much better definition of a healthy trend-following distribution.
