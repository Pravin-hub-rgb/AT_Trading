# 4 Backtesting Techniques Behind Winning Strategies

> **Source:** Video transcript notes → restructured study notes
> **Core idea:** 4 validation rules that separate a **real edge from statistical noise** — the same principles firms like **Renaissance Technologies** use (founded by **Jim Simons**, the highest-performing quant fund ever), just with billion-dollar budgets and smarter people. The core concepts stay exactly the same no matter how complex the implementation gets.

---

## Overview

- Every single trader should know these 4 techniques — they form the **backbone of what profitable trading is built on**.
- The exact same rules the author used to **validate and scale his own automated trading portfolio** — previous month results: **~18%**.
- These techniques helped push serious size and find profitable strategies in **all markets: futures, equities, and even crypto**.
- The author didn't invent them — they come from firms like Renaissance Technologies.

### Quote — Swashahan (one of the biggest quant firms) on their process:

> "We have analysis that we've done in the past. We have obviously databases that contain history. We have models that contain information about how to price things. We maybe tweak parameters and see how our models react to the tweaking of those parameters."

That "tweaking of parameters and seeing how models react" = **Technique 1: Parameter Sensitivity**.

### The 4 Techniques at a Glance

| # | Technique | What it catches |
|---|-----------|-----------------|
| 1 | Parameter Sensitivity | Overfitting to one "magic" parameter value |
| 2 | Walk Forward Optimization | Strategies that memorize the whole history |
| 3 | Stress Testing | Fragility under worst-case real-world conditions |
| 4 | Monte Carlo Simulations | Dependence on one lucky sequence of trades |

---

## Core Concept: Overfitting (understand this first)

The word "overfit" comes up constantly, so define it first:

- **Definition:** When your strategy **memorizes noise instead of learning real patterns** / finding a real edge (alpha) in the historical data.
- **Analogy 1:** Like creating a unique rule for every single day in your backtest — it works perfectly historically, but fails completely when live.
- **Analogy 2:** Like memorizing the answers to an exam and then taking the exam — you don't actually know the subject, you just know the answers to that one exam.
- **Why these 4 techniques matter:** they separate **real edges from statistical noise**. If you understand and implement them, you have a higher likelihood of creating profitable strategies and actually being able to find them.

---

## Technique 1: Parameter Sensitivity

**What it is:** A test that shows **how small changes in your parameter values affect performance**. This is exactly what the Swashahan clip described — tweaking parameters and watching how the model reacts.

**Bad sign — cliff edges:**
- Example: testing a moving average strategy, change the period length from **20 → 22** and it completely kills your returns.
- Before: **20% returns** → after changing to 22: **−10%**.
- Most likely **overfit** — if you had put that strategy live, it would have lost money and wouldn't have worked live.

> **Rule:** Robust strategies show **smooth performance across parameter ranges**, not complete cliff edges.

**How to visualize — Heat Map** (just one of several ways to visualize parameter sensitivity, but probably the easiest to understand):
- One axis shows one parameter value ranging; the other axis shows a second parameter value.
- The **legend** (the color infographic) shows: warmer / more yellow = **higher profitability**; darker color = **lower profitability**.
- What you want to see: a nice **cluster** of profitable values over a good range, then **slowly degrading** to less profitability — ideally an **optimum that slowly declines** toward a minimum on the opposite side.
- The far side where profitability is basically not working at all is **also a good sign** (clear boundary between working and not working).

**In practice — RSI example:**

❌ **Overfit (avoid this):**
| Parameter | Return |
|---|---|
| RSI 14 | +50% |
| RSI 15 | −10% |
| RSI 16 | +5% |

No cohesion — we're just **fitting to noise**. Performance really shouldn't spike for just **one magical number**.

✅ **Robust (what you want):**
| Parameter | Return |
|---|---|
| RSI 12 | +18% |
| RSI 14 | +22% |
| RSI 16 | +20% |
| RSI 18 | +17% |

They don't all have the exact same value — we're not looking for that — but they're in a **similar sort of range**.

**Why it matters:**
- **Markets change** — your perfect parameter today won't be perfect tomorrow.
- If your strategy only works with **one exact setting**, it's not an edge — it's most likely a lucky accident in historical data.
- Parameter sensitivity reveals whether you have a **real edge or just curve-fitted noise**.
- One of the author's **favorite tests** — run on **absolutely everything**, because it's so important that you're not overfitting and it can be hard to tell sometimes. This test is a good way to at least cover your bases for most things.

---

## Technique 2: Walk Forward Optimization

**What it is:** "This is where most backtests lie to you." It splits your data into **training (in-sample)** data and **testing (out-of-sample)** periods, then **rolls it forward through time**.

**How the roll works (example):**
- 1 year of in-sample (training data) → 0.5 years of out-of-sample (testing data) → then it **repeats itself**, rolling forward.
- It doesn't always have to be exactly 1 year / 0.5 year — it can be many different types of rolling periods — but this is the general idea of how it rolls.
- At each step, **your strategy has never seen the testing data before**.

**Why it matters:**
- If your strategy can't perform on the **out-of-sample data** (the data you haven't tested and optimized over), **it won't work live**, most likely.
- Most traders optimize over **all the data** and then are surprised why it fails live — their strategy **memorized the test answers** and doesn't actually understand the subject itself.
- With 2 years of historical data: if you try **every combination**, you're going to find something that works — e.g., 10 different moving averages + 20 different other indicators → something will look kind of good historically.
- We don't want to **torture the data** to find something that works — we want something that actually has real alpha/edge. This is a great test for that.

**What to look for — consistency between training and testing data:**
- Out-of-sample performance will **always normally be lower** than your training data — that's totally normal (you've never touched it and haven't optimized over it).
- ❌ **Bad:** Training averaging +10%/yr, +20%/yr → out-of-sample at **−10%**. Completely different = broken.
- ✅ **Good:** Training +10–20%/yr → out-of-sample at **+6%, +7%, maybe +8%**. Quite reasonable — if it works at all on out-of-sample data, that's still a really good sign.

**Mid-video note:** the author mentions a "backtest bootcamp" sale around this point — details in the [Appendix](#appendix--resource-mentioned-backtest-bootcamp).

---

## Technique 3: Stress Testing

**What it is:** Throws the **worst cases** at your strategy.

**Why it matters:** Most backtests look amazing because they're tested during **normal conditions** — but normal doesn't last forever.

**What to stress:**
- **Historical crises:** run your strategy through the **2008 financial crisis**, **2020**, and **flash crashes**.
- **Slippage increases:** what if the slippage on each trade goes from **0.01% → 0.1% → 1% → 10%**? How does that affect performance?
- **Execution delays** (rarely discussed, some find it illogical, but it's actually a really good test):

**Execution delay example 1 — crypto momentum strategy (a strategy the author runs):**
- Change signal-to-execution time from **instant → 1 to 5 days**.
- Day **0** (instant) is actually **not** the best performance — a **1-day delay performs a bit better**.
- That's a really good sign: the signal **lasts over a long enough time horizon** that even with delay — an issue on your end, can't execute fast enough, or you manually miss it — you can still capture very good returns.

**Execution delay example 2 — lower timeframe (the warning case):**
- Change execution from **instant (1 second) → 5 minutes later** and the strategy is **completely unprofitable** → worrying.
- Things do cause execution delays; **no execution is completely instant**. People assume clicking a market order gives instant execution — while that can be true, **when you scale a strategy it's not always the case**.
- Even if you do get instant execution live, you should be **a lot more comfortable with a strategy that stays profitable with some delay**, versus one that's completely unprofitable without instant execution — that's stressful and not robust.

**How to do it — manually stress your assumptions (add things to your backtest):**
1. **Double your commissions** — very easy to do; just see if the strategy survives.
2. **Triple your slippage** — normally just a configuration option.
3. **Add execution delays** — not every code/platform supports this, but sometimes you can do it with a bit of code.

**Pass condition:** ideally your strategy **still works** even if it performs a bit below optimal.

---

## Technique 4: Monte Carlo Simulations

> **Note:** the transcript's "multicolor simulations" is **Monte Carlo simulations** — so named here because the chart shows thousands of multi-colored equity curves.

**What it is:** "A reality check really no one wants to run." It **randomizes your historical trade sequences thousands of times**.

**Why it matters:**
- Your backtest is just **one possible path** through history — your strategy happened to take trades in a certain order that worked out nicely **for that particular historical backtest**.
- But what if those **same trades happened in a different sequence**?

**How it works:**
- Take your historical trades — e.g., **100 trades** — and shuffle each trade around: the **99th trade becomes the 22nd**, etc. It's constantly reshuffling.
- Visualized: the chart looks like "a huge mess" / "someone's drawn crayon all over it" — but each line is an **equity curve going in a different sequence of your historical trades**.
- This reveals your **true risk range**, because when you go live there is **no set path** you know is going to happen — **any sequencing could happen**, and you want to see how different sequencings affect the strategy.

**What to look for:**
- Expect a **nice wide range of risk tolerances** — e.g., one equity curve may draw down a lot more than all the rest.
- Yes, it would be unlucky if that happened to you live, but it **can totally happen** → you want **realistic expectations** of what you could experience live.

**The most important part — Survivability:**
- Can you **psychologically handle** the worst-case scenario?
- Can your **actual account and position sizing method** survive it?
- **Warning sign example:** if many curves average going up (e.g., "X2 curves going up") but **~10 go straight down** → be quite worried: that probably means you're **sizing way too aggressively**. With an unlucky sequence everything just dies — you don't want that live.
- **Fix:** **halve or reduce your position sizes**, or do something else to bring sizing down.

---

## Strategy Validation Checklist

Run this on every strategy before going live:

- [ ] **Parameter sensitivity** — neighboring parameter values perform in a similar range; smooth degradation, no cliff edges
- [ ] **Walk forward** — out-of-sample results reasonably consistent with training results (lower is fine, negative is not)
- [ ] **Stress test** — survives 2008 / 2020 / flash crashes, doubled commissions, tripled slippage, execution delays
- [ ] **Monte Carlo** — worst shuffled sequences don't blow up the account; sizing is survivable (psychologically + financially)
- [ ] **Not overfit overall** — strategy reflects a real edge, not memorized noise

---

## Appendix — Resource Mentioned: Backtest Bootcamp

The author promotes a **backtest bootcamp** (promo segments around ~6:09 and at the end of the video, ~10:41):

- **Why it's pitched:** explaining concepts in a video is easy, but *implementing* them is where most traders get stuck (per the author's experience).
- **What you get:**
  - Complete **code templates for all backtesting techniques** — no coding experience needed; all information to get the code up and running, and nowadays even with some AI you can learn to modify it quite quickly.
  - **Step-by-step walkthroughs** for how to backtest properly — the **full A-to-Z list** of everything you should check.
  - **Practical strategy examples** across **futures, equities, and crypto** — with examples for both **backtesting and automation**.
  - **Weekend-only bonus:** a **30-minute one-on-one call** with the author to review your strategies personally or ask direct questions.
- **Where:** website linked in the video description.
- **Who it's for:** anyone serious about building **robust and profitable strategies**.


