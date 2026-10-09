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



---

Bhai, done. We’ll make both documents: one for explaining your career gap in web-development interviews, and another for understanding and defending your quantitative research if an interviewer asks about it.

The key is that your quant work should show initiative and technical learning, while your React/Next.js projects remain the main focus when applying for developer jobs.

## Document 1: Career gap and interview preparation

Career Gap — Web Developer Interview Notes

# Career Gap — Web Developer Interview Notes

## 1. My main answer

**Question: What have you been doing since graduation?**

After graduation, I spent time building my technical skills through independent projects and research. One of my major projects involved studying cryptocurrency market behaviour and developing Python-based backtesting workflows to test systematic trading ideas. This involved working with historical data, implementing strategy logic, debugging, analysing results, and checking how performance changed under different market conditions.

Alongside that, I continued working on web development projects using technologies such as React and Next.js. I’m now focused on starting my professional career in software development, contributing to a team, and continuing to improve my skills through real-world work.

## 2. If they ask why I didn't get a job earlier

I wasn't able to transition into a full-time role immediately after graduation. I spent that time learning independently and working on technical projects. Looking back, I could have approached the job search more consistently, but I've learned a lot through building and testing projects. My priority now is to turn that practical experience into professional software development experience.

## 3. If they ask whether I worked as a professional quant

No. It was independent research rather than employment at a trading firm. I explored systematic trading ideas, worked with historical market data, and developed backtesting workflows as a personal technical project.

## 4. What I learned from the research

* Python-based data processing and strategy implementation.

* Debugging and checking whether code produces logically correct results.

* Analysing performance using win rate, expectancy, profit factor and drawdown.

* Testing how results change across different market conditions.

* Understanding why a promising backtest does not automatically prove a strategy will work in live markets.

* Breaking a broad problem into hypotheses, experiments and measurable results.

I should only claim skills and tasks I can personally explain and demonstrate.

## 5. Why am I applying for web development now?

I want to build my career in software development. I enjoy building applications and working with frontend technologies, APIs, databases and backend logic. My independent projects have helped me practise problem-solving, and I now want to work with an experienced team, improve my engineering fundamentals, and learn how production software is built and maintained.

## 6. Questions I should prepare for

**Tell me about yourself.**
Prepare a 45–60 second introduction focused on web development, your strongest projects, your technical skills and the role you want.

**What is your strongest project?**
Explain the problem, your contribution, the tech stack, one difficult technical challenge and how you solved it.

**What did you actually build yourself?**
Clearly distinguish what you implemented, what you used AI assistance for, and what you understand well enough to modify or debug.

**Why should we hire you despite your gap?**
Focus on relevant project work, willingness to learn, fundamentals and readiness to contribute. Don't become defensive about the gap.

**Why should we hire you if your DSA is weak?**
Be honest about your current level. Demonstrate your JavaScript fundamentals, problem-solving approach and willingness to practise DSA rather than pretending to be strong at it.

## 7. Important rules

* Do not describe independent research as employment.

* Do not claim professional trading experience or institutional quant experience.

* Do not exaggerate Python, statistics or machine-learning expertise.

* Do not give a long, apologetic explanation of the gap.

* Keep the same honest story in your resume and interviews.

* For developer roles, lead with web development projects rather than trading research.

**My one-line career-gap explanation:**

I used the period after graduation to develop my technical skills through independent programming projects and quantitative market research, and I'm now focused on starting my career in software development.

## Document 2: Quantitative research — technical interview notes

Independent Quantitative Research in Crypto Markets

# Independent Quantitative Research in Crypto Markets

## 1. What was the project?

I explored whether systematic trading rules could identify repeatable opportunities in cryptocurrency markets. The work involved studying market structure, developing strategy hypotheses, implementing rules in Python-based backtesting workflows, and analysing their historical performance.

This was an independent research project, not professional employment or proof of a profitable live trading system.

## 2. What is quantitative trading research?

Quantitative trading research uses data, mathematical reasoning, statistical analysis and programmed rules to investigate trading hypotheses.

The general workflow is:

1. Form a hypothesis.

2. Define objective entry and exit rules.

3. Implement those rules.

4. Test them against historical data.

5. Include transaction costs and realistic execution assumptions.

6. Evaluate risk, returns and robustness.

7. Test on data not used to develop the strategy.

The goal is not simply to find a profitable backtest. It is to investigate whether the observed performance is credible and repeatable.

## 3. What is a backtest?

A backtest simulates how a trading strategy would have behaved on historical market data.

A reliable backtest must model the rules accurately, including signal timing, order execution, stop-loss behaviour, fees and slippage. Incorrect assumptions or look-ahead bias can make results appear much better than they really are.

A backtest is evidence about historical behaviour, not a guarantee of future performance.

## 4. Strategy hypothesis and implementation

A hypothesis might be that a particular market structure or price movement contains information about subsequent price direction.

The process is to translate the idea into precise rules, implement those rules, and examine the outcomes across a sufficiently broad dataset.

A strategy should not be judged solely on its total profit. The distribution of wins and losses, drawdowns, trading costs, market conditions and dependence on a small number of large winners also matter.

## 5. Key performance metrics

### Win rate

The percentage of completed trades that are profitable.

Win rate alone cannot determine whether a strategy is profitable.

### R-multiple

R represents the initial risk assigned to a trade.

If the planned risk is ₹500, a result of +2R represents ₹1,000 profit, while −1R represents a ₹500 loss, before accounting for any costs not already included.

### Expectancy

Average profit or loss per trade, expressed in R.

A simplified formula is:

Expectancy = (Win rate × Average winning R) − (Loss rate × Average losing R)

For example, if a strategy wins 30% of trades, averages +4R on winners, and averages −1R on losers:

Expectancy = (0.30 × 4) − (0.70 × 1) = +0.50R per trade.

This is a hypothetical example, not a result from my research.

### Profit factor

Gross profits divided by gross losses, using positive magnitudes for both totals.

A profit factor above 1 indicates that gross profits exceed gross losses over the tested period, but does not establish that the strategy will remain profitable.

### Maximum drawdown

The largest peak-to-trough decline in the cumulative equity or R curve.

Drawdown helps describe how difficult the strategy might be to sustain through losing periods.

## 6. Right-tailed strategies and winner dependence

Some trend-following strategies make small losses relatively frequently but occasionally capture much larger moves.

This can result in a low win rate alongside positive overall expectancy.

However, it creates an important research question: how much of the total result depends on a few unusually profitable trades or months?

Useful checks include:

* Removing the largest winning trade and measuring the effect.

* Examining the top 5, 10 or 20 winners.

* Comparing monthly, quarterly and yearly results.

* Checking whether performance survives different market conditions.

Large-winner dependence is not automatically a flaw. It becomes a concern when the remaining results reveal that the strategy has little evidence of a repeatable edge.

## 7. Market regimes

Markets behave differently across trending, ranging, high-volatility and low-volatility conditions.

A strategy may perform well in one environment and poorly in another. Breaking results down by time period and market condition helps reveal this dependence.

However, regime labels should be defined consistently rather than selected after observing which conditions were profitable.

## 8. Multi-timeframe research

A multi-timeframe strategy uses information from more than one chart interval.

For example, a higher timeframe such as 1 hour may determine directional structure, while a lower timeframe such as 15 minutes determines the entry.

The important implementation questions include:

* Was the higher-timeframe candle fully closed before its information was used?

* Was the lower-timeframe entry taken at a realistic time?

* Were stop-losses and trailing exits simulated using data available at that point?

* Could the backtest access information that would not have been available in live trading?

These checks help prevent timing errors and look-ahead bias.

## 9. Overfitting and validation

Overfitting occurs when a strategy is adjusted to fit historical data so closely that the apparent edge does not generalise to unseen data.

A stronger research process separates:

* **Development data:** used to create and refine the hypothesis.

* **Validation data:** used to compare candidates and identify weaknesses.

* **Out-of-sample data:** held back from strategy development for a more independent evaluation.

Repeatedly changing parameters after examining out-of-sample results gradually turns that data into development data too.

Testing another instrument or time period can provide additional evidence, but it does not automatically establish robustness.

## 10. Costs and realistic execution

Trading costs can include exchange fees, bid-ask spread, slippage and, for perpetual futures, funding payments.

A strategy that appears profitable before costs may become unprofitable after costs. Execution assumptions must also match the actual rules: for example, a signal generated at candle close cannot normally be filled at an earlier price from that same candle.

## 11. Skills developed

Through this independent work, I practised:

* Translating hypotheses into explicit rules.

* Working with historical market data.

* Implementing and debugging backtesting logic.

* Analysing returns, risk and drawdowns.

* Investigating market-period differences.

* Checking how assumptions affect results.

* Evaluating the limitations of historical simulations.

I should describe these as skills practised through independent research, not as evidence of professional quant experience.

## 12. How I explain the project in an interview

I worked on an independent quantitative research project involving cryptocurrency market data. I explored systematic trading ideas, implemented strategy rules in Python-based backtesting workflows, debugged the simulations and analysed performance using metrics such as expectancy and drawdown. A major lesson was that results can be misleading if execution assumptions, costs or backtesting logic are incorrect. The project gave me practical experience with programming, debugging and data-driven investigation.

## 13. Questions I must be able to answer honestly

* What specific hypothesis did I test?

* What data did I use, and what time period did it cover?

* How did I implement the entry and exit logic?

* How did I account for fees and slippage?

* What bugs or incorrect assumptions did I discover?

* How did I calculate expectancy and drawdown?

* What did I do to reduce overfitting?

* Which parts did I code myself, and where did I use AI assistance?

* What are the limitations of my findings?

If I cannot explain a particular implementation or result, I should say so rather than bluffing.

## 14. The main takeaway

The most defensible achievement is not a claim that I discovered a guaranteed profitable strategy. It is that I worked through a technical research process: forming hypotheses, programming rules, testing them, finding implementation errors, evaluating risk and questioning whether the results were trustworthy.

## How to use these two documents

* For job applications: use Document 1 to prepare your gap explanation and Document 2 to refresh the concepts before an interview.

* On your resume: prioritise your React/Next.js projects and relevant development skills. Include the quant project only if you can explain your actual contribution.

* Before interviews: practise explaining one real bug you found in the backtester, what caused it, and how you verified the correction. A specific example you genuinely understand is stronger than memorising a long list of technical terms.

And bhai, one important thing: you don't have to convince a web-development interviewer that you're a quant researcher. You need to show that you kept learning, built things, can explain your work honestly, and are ready to grow as a developer.
