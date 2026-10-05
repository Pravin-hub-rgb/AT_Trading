# Independent Quantitative Research in Crypto Markets

## Career-Gap Learning & Interview Notes

> **Simple description:**\
> I spent this period doing independent quantitative research on crypto
> markets, focusing on systematic trading strategy development,
> backtesting, market-structure research, and robustness testing.

------------------------------------------------------------------------

# 1. First: What does "Quant" actually mean?

**Quant** is short for **quantitative**.

It does **not** mean quantum physics. 😄

In finance, quantitative work means using:

-   numbers
-   data
-   mathematics
-   statistics
-   algorithms
-   programming

to study markets or make decisions systematically.

### Simple example

A discretionary trader might say:

> "This breakout looks strong."

A quantitative researcher asks:

> "Can I define what 'strong' means mathematically, test it over
> thousands of historical observations, and determine whether the
> condition is associated with better outcomes?"

That difference is the basic idea behind quantitative research.

------------------------------------------------------------------------

# 2. What is Quantitative Trading Research?

Quantitative trading research is the process of investigating whether
**measurable patterns in market data can be converted into systematic
trading rules**.

A typical research loop is:

``` text
Market Observation
       ↓
Hypothesis
       ↓
Rule / Mathematical Definition
       ↓
Historical Backtest
       ↓
Statistical Analysis
       ↓
Robustness Testing
       ↓
Out-of-Sample Validation
       ↓
Paper / Shadow Trading
       ↓
Live Evaluation
```

The important part is that the researcher is not simply looking for a
strategy that made money historically.

The goal is to understand:

> **Why did it work, under what conditions did it work, and how
> sensitive is the result to reasonable changes?**

------------------------------------------------------------------------

# 3. What I Actually Worked On

My research focused primarily on **crypto market behavior and systematic
trading strategies**.

The work included:

### Market-structure research

Studying:

-   swing highs and swing lows
-   directional movement
-   multi-timeframe structure
-   breakouts
-   continuation
-   reversals
-   trend persistence
-   sideways/choppy conditions

### Strategy development

Converting observations into explicit rules.

For example:

> If a directional structure appears on the 1-hour timeframe, does a
> particular 15-minute structure occurring in the same direction produce
> a measurable edge?

The important thing is that the statement can be converted into rules
that a computer can evaluate.

### Backtesting

Running those rules over historical BTCUSDT data to measure:

-   number of trades
-   winning trades
-   losing trades
-   average return
-   profit factor
-   maximum drawdown
-   trade distribution
-   yearly performance
-   monthly performance
-   losing streaks
-   large-winner dependence

### Robustness research

Testing whether the result survives reasonable changes such as:

-   stop-loss parameters
-   volatility parameters
-   trading-session filters
-   time-based conditions
-   different market periods
-   removal/capping of unusually large winners
-   different market regimes

### Regime research

Investigating why a strategy performs differently during:

-   strong trends
-   sideways markets
-   high-volatility periods
-   low-volatility periods
-   persistent directional movement
-   frequent reversals

------------------------------------------------------------------------

# 4. An Example of a Quantitative Hypothesis

Suppose I notice:

> "My strategy seems to perform badly when recent 1-hour candles have
> lots of long wicks."

That observation alone is **not yet quantitative research**.

I need to define it.

For example:

``` text
Body = |Close - Open|

Upper Wick = High - max(Open, Close)

Lower Wick = min(Open, Close) - Low

Total Wick = Upper Wick + Lower Wick
```

Then I can define:

``` text
Wick Ratio = Total Wick / Body
```

And ask:

> During the previous 6 one-hour candles, what happens when 4 or more
> candles have Total Wick \> Body?

Now I have a measurable condition.

I can compare:

``` text
Trades WITHOUT condition
vs.
Trades WITH condition
```

and examine:

-   win rate
-   average R/trade
-   profit factor
-   drawdown
-   trade count
-   large winners
-   losing streaks

That is a simple example of **turning a market observation into a
quantitative research question**.

------------------------------------------------------------------------

# 5. What is a Backtest?

A **backtest** applies a defined trading strategy to historical market
data as though the strategy had been operating during that historical
period.

Example:

``` text
BTCUSDT historical candles
          ↓
Strategy rules
          ↓
Entry
          ↓
Position management
          ↓
Exit
          ↓
Profit/Loss
          ↓
Performance statistics
```

The purpose is not to prove that the future will behave exactly like the
past.

Instead, it helps answer:

> "Would this idea have produced a meaningful result under these
> historical assumptions?"

------------------------------------------------------------------------

# 6. What is R?

In systematic trading research, using **R** makes results easier to
compare.

If:

``` text
1R = the amount initially risked on a trade
```

then:

-   loss of the initial risk = **−1R**
-   profit equal to initial risk = **+1R**
-   profit twice the initial risk = **+2R**
-   profit ten times the initial risk = **+10R**

Example:

If the strategy risks ₹500 per trade:

``` text
−1R = −₹500
+1R = +₹500
+5R = +₹2,500
```

This lets us compare trades without depending on the absolute position
size.

------------------------------------------------------------------------

# 7. Important Performance Metrics

## Win Rate

Percentage of trades that are profitable.

``` text
Win Rate = Winning Trades / Total Trades
```

A high win rate does **not automatically mean a strategy is good**.

A strategy could win 70% of the time but have very large losses.

Another strategy could win only 30% but have much larger winners.

------------------------------------------------------------------------

## Average R per Trade

``` text
Average R = Total Net R / Number of Trades
```

This gives a rough measure of the average outcome per trade.

------------------------------------------------------------------------

## Profit Factor

Conceptually:

``` text
Profit Factor =
Gross Profit / Absolute Gross Loss
```

For example:

``` text
Gross Profit = +400R
Gross Loss   = −200R

PF = 400 / 200
   = 2.0
```

------------------------------------------------------------------------

## Maximum Drawdown

Maximum drawdown measures the largest peak-to-trough decline in the
equity curve.

Example:

``` text
Equity: 100R
        120R  ← peak

        110R
         95R
         88R  ← trough

Maximum Drawdown = 32R
```

A strategy can have high total returns and still experience
uncomfortable drawdowns.

------------------------------------------------------------------------

## Expectancy

Expectancy estimates the average outcome per trade based on the
distribution of wins and losses.

A simplified form is:

``` text
Expectancy =
(Win Probability × Average Win)
−
(Loss Probability × Average Loss)
```

Example:

``` text
Win rate       = 30%
Average win    = +4R
Average loss   = −1R

Expectancy =
(0.30 × 4) − (0.70 × 1)

= 1.2 − 0.7
= +0.5R/trade
```

This is why **win rate should never be examined alone**.

------------------------------------------------------------------------

# 8. Right-Tailed Strategies

Some trend-following systems naturally have:

``` text
Many small losses
Some small wins
A few very large winners
```

Example:

``` text
−1R
−1R
−0.5R
+0.5R
−1R
−1R
+8R
−1R
−1R
+15R
```

The strategy can still be profitable.

This is called a **right-tailed return distribution** because unusually
large positive outcomes can contribute a substantial portion of total
returns.

This creates an important research question:

> Is the strategy profitable only because of a handful of historical
> trades?

That leads to robustness testing.

------------------------------------------------------------------------

# 9. Winner-Dependency Testing

One useful robustness test is to remove the largest winners.

Suppose:

``` text
Original result = +360R
```

Then calculate:

``` text
Remove largest winner
Remove largest 3 winners
Remove largest 5 winners
Remove largest 7 winners
Remove largest 10 winners
```

This does **not** prove the strategy will survive the future.

But it tells us how dependent the historical result was on exceptional
trades.

Another approach is to cap winners:

``` text
No winner can exceed +20R
No winner can exceed +15R
No winner can exceed +10R
```

If profitability remains positive under reasonable haircuts, that
provides additional information about the distribution.

------------------------------------------------------------------------

# 10. Market Regimes

A strategy does not have to perform equally well in every market
condition.

For example, a trend-following strategy may naturally behave differently
during:

``` text
Strong directional trend
        ↓
Frequent continuation
        ↓
Potentially favorable
```

versus:

``` text
Sideways market
        ↓
Repeated breakouts + reversals
        ↓
Potentially more failed trades
```

Instead of simply saying:

> "This is a sideways market."

I can try to measure it.

For example:

### Directional Efficiency

``` text
Efficiency =
|Net Price Change|
---------------------------
Sum of Absolute Price Changes
```

A market that travels a lot but ends near where it started has low
efficiency.

A market that consistently moves in one direction has higher efficiency.

This can then be tested against strategy performance.

------------------------------------------------------------------------

# 11. Multi-Timeframe Research

One of the main ideas I investigated was using different timeframes for
different purposes.

For example:

``` text
1H
↓
Higher-level directional structure

15M
↓
Execution / entry structure
```

The research question can be:

> Does higher-timeframe directional structure combined with
> lower-timeframe confirmation produce a measurable advantage?

This is different from simply saying:

> "1H + 15M feels better."

The quantitative approach requires an exact definition that can be
reproduced by code.

------------------------------------------------------------------------

# 12. What Does "Systematic" Mean?

A systematic strategy has predefined rules.

For example:

``` text
IF condition A
AND condition B
AND condition C

THEN enter.

IF stop condition occurs
THEN exit.

IF trailing condition occurs
THEN update stop.
```

The goal is to reduce dependence on moment-to-moment subjective
judgment.

A systematic strategy does not necessarily mean it is automated live.

It can first exist as:

1.  Research code
2.  Backtest
3.  Paper/shadow system
4.  Automated execution system

------------------------------------------------------------------------

# 13. Research vs. Overfitting

This is one of the most important concepts.

Testing different ideas is **not automatically overfitting**.

Research naturally involves:

``` text
Idea
↓
Test
↓
Learn
↓
Modify
↓
Test again
```

The problem occurs when the same historical dataset is repeatedly used
to make increasingly specific decisions and then the final result is
treated as though it were untouched evidence.

For example:

``` text
Test strategy
↓
Find losing trades
↓
Add filter
↓
Test
↓
Find remaining losing trades
↓
Add another filter
↓
Test
↓
Repeat many times
```

Eventually the strategy may become highly adapted to that historical
sample.

That is why a research process should eventually reach:

> **Freeze the strategy → validate it on data that was not used to make
> the final decisions.**

------------------------------------------------------------------------

# 14. Development Data vs Validation Data

A practical research process is:

## Development

Use historical data to:

-   discover ideas
-   test hypotheses
-   fix bugs
-   compare reasonable alternatives
-   understand failures
-   develop the strategy

## Validation

Once the final rules are frozen:

-   stop modifying the rules
-   test the exact strategy on untouched data

## Live / Shadow Validation

Then observe how the strategy behaves on genuinely new market data.

The key distinction is:

> **A dataset cannot be both repeatedly used for development and
> honestly described as untouched final evidence.**

That does not make the development work useless.

It simply means the role of the dataset has changed.

------------------------------------------------------------------------

# 15. Why Cross-Instrument Testing Matters

A strategy developed on BTCUSDT can also be tested on another market.

For example:

-   ETH
-   XAUUSD
-   other liquid instruments

The question is not necessarily:

> "Does exactly the same parameter work everywhere?"

Instead:

> "Does the underlying market phenomenon exist outside the original
> instrument?"

For example, if the research hypothesis is about multi-timeframe swing
continuation, testing another instrument can provide evidence about
whether the phenomenon is specific to BTC or potentially more general.

Different markets can require different:

-   volatility parameters
-   session handling
-   costs
-   position sizing
-   execution assumptions

------------------------------------------------------------------------

# 16. What Makes This Quantitative Research Rather Than Random Backtesting?

The difference is the **research process**.

Random backtesting:

``` text
Try indicator
↓
Change parameter
↓
Look at profit
↓
Try another parameter
↓
Pick the biggest number
```

Research-driven development:

``` text
Observation
↓
Hypothesis
↓
Precise definition
↓
Predefined experiment
↓
Backtest
↓
Analyze distribution
↓
Challenge the result
↓
Robustness test
↓
Freeze
↓
Validation
```

The second process is much closer to quantitative research.

------------------------------------------------------------------------

# 17. What I Have Learned

Through this work, I have been learning about:

### Programming

-   Python
-   data processing
-   backtesting engines
-   time-series data
-   strategy implementation
-   automated testing

### Quantitative methods

-   probability
-   statistics
-   expectancy
-   distributions
-   drawdown
-   risk/reward
-   parameter sensitivity
-   robustness testing
-   out-of-sample validation

### Market research

-   market structure
-   volatility
-   trend persistence
-   breakouts
-   reversals
-   market regimes
-   multi-timeframe analysis

### Research methodology

-   hypothesis formation
-   experimental design
-   avoiding look-ahead bias
-   avoiding data leakage
-   understanding overfitting
-   separating development from validation

------------------------------------------------------------------------

# 18. How to Explain the Career Gap

If someone asks:

> **"What were you doing during this period?"**

A natural answer is:

> "I spent the period doing independent quantitative research on crypto
> markets. I was studying market structure and developing systematic
> trading strategies using historical market data. I built and tested
> backtesting systems in Python, investigated different market regimes,
> analyzed risk and drawdowns, and worked on robustness and
> out-of-sample validation. It was essentially an independent research
> and programming project rather than employment at a company."

If they ask:

> **"Were you actually trading professionally?"**

Do not imply that you were employed by a trading firm.

Say:

> "No, it was independent research. My focus was on learning the
> research process, programming the experiments, and understanding
> whether the ideas held up under systematic testing."

------------------------------------------------------------------------

# 19. How to Put It on a Resume

### Independent Quantitative Researcher --- Crypto Markets

**Independent Research Project**

-   Conducted quantitative research on cryptocurrency market structure
    and systematic trading strategies.
-   Developed Python-based backtesting workflows for historical market
    data.
-   Researched multi-timeframe swing structure and trend-continuation
    behavior.
-   Evaluated strategies using return distributions, win rate,
    expectancy, profit factor, drawdown, and trade-level statistics.
-   Performed robustness testing through parameter sensitivity,
    winner-dependency analysis, and historical regime analysis.
-   Investigated market conditions associated with strategy performance,
    including directional efficiency, volatility, and potential
    sideways/choppy regimes.
-   Studied out-of-sample validation, data leakage, look-ahead bias, and
    overfitting in systematic strategy development.

------------------------------------------------------------------------

# 20. What NOT to Claim

Keep the description honest.

Avoid saying:

> "I worked as a professional quant."

unless you actually worked in that role.

Avoid:

> "I developed a profitable hedge-fund strategy."

unless there is real evidence and professional context supporting that
claim.

Better:

> "I conducted independent quantitative research and developed
> systematic trading strategies as a personal research project."

That is both credible and accurate.

------------------------------------------------------------------------

# 21. The One-Line Version

If you only have 10 seconds:

> **"I was doing independent quantitative research on crypto markets,
> mainly systematic strategy development, Python-based backtesting, and
> market-regime analysis."**

If they ask what that means:

> **"Basically, I take market observations, turn them into measurable
> rules, test them on historical data, analyze the results, and then try
> to determine whether the behavior is robust rather than just a
> historical coincidence."**

------------------------------------------------------------------------

# 22. The Bigger Picture

The most useful way to think about this work is:

``` text
                 MARKET DATA
                     │
                     ▼
              OBSERVATION
                     │
                     ▼
                HYPOTHESIS
                     │
                     ▼
             MATHEMATICAL RULE
                     │
                     ▼
                BACKTEST
                     │
                     ▼
          ┌──────────┴──────────┐
          ▼                     ▼
       RESULTS              FAILURES
          │                     │
          └──────────┬──────────┘
                     ▼
             ROBUSTNESS TEST
                     │
                     ▼
             FROZEN STRATEGY
                     │
                     ▼
          OUT-OF-SAMPLE TEST
                     │
                     ▼
              PAPER / LIVE
```

That is the core of what **independent quantitative trading research**
means.

------------------------------------------------------------------------

## Final takeaway

You don't need to be a PhD mathematician to describe this work as
quantitative research.

The important part is that you are **using data and measurable rules to
investigate market behavior systematically**.

The deeper mathematical/financial techniques can be learned
progressively.

Your current work already sits at the intersection of:

**Programming + Data Analysis + Market Research + Statistics +
Systematic Trading.**

That combination is what makes the project useful as a learning
experience --- and potentially useful as a portfolio/research project
when presented honestly and reproducibly.
