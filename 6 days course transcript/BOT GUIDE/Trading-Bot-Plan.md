# Trading Bot Plan

## Goal
Build a chart-based trading assistant that follows the theory from the six sessions:
- build overview first
- detect swing structure
- decide buying/selling bias
- wait for confirmation
- mark support/resistance and trade phases
- simulate paper trades before live execution

---

## Core trading theory to encode

### 1) Overview before entry
The market must be read in context before trade execution.

The bot must decide:
- bullish / bearish / neutral
- buy-side or sell-side bias
- where the likely support and resistance zones are
- whether price is near a recent high or recent low

### 2) Recent swing highs and lows matter most
The bot must detect:
- recent swing high
- recent swing low
- higher highs / lower highs
- higher lows / lower lows

These define the current market structure.

### 3) Near highs = likely resistance; near lows = likely support
This is a critical rule.

- Near a recent swing high -> likely resistance zone
- Near a recent swing low -> likely support zone
- But the bot must not act blindly just because price is near a top or bottom
- It should wait for the level to reject or accept

### 4) Buying vs selling plan depends on the overview
- If the market is in a bullish overview, buy around support or on retracement after weakness
- If the market is in a bearish overview, sell around resistance or on failed continuation
- If the market is neutral, do not force trades

### 5) Weak vs strong swing matters
The bot should identify:
- strong buying swing
- weak buying swing
- strong selling swing
- weak selling swing

Example logic:
- weak selling swing in bullish overview = possible support / buy setup
- weak buying swing in bearish overview = possible resistance / sell setup

### 6) Confirmation before execution
The setup should only trigger after the chart shows confirmation.

Examples of confirmation:
- support holds after rejection
- higher low forms after a weak selling swing
- resistance rejects after a weak buying swing
- lower high forms after a weak buying swing
- a clean breakout or break of structure candle

---

## Bot architecture

### Level 1 — Data layer
Use OHLC data and live candles.

Each candle should have:
- timestamp
- open / high / low / close
- volume
- previous day high / low
- current day high / low
- current session start / end

### Level 2 — Structure engine
Detect:
- recent swing highs and lows
- higher highs / lower highs
- higher lows / lower lows
- support zones
- resistance zones
- current range and breakout state

### Level 3 — Overview engine
Compute:
- bullish / bearish / neutral
- strength of trend or range
- present support/resistance profile
- current market phase

### Level 4 — Intraday phase engine
This engine is the most important for the live view.

It should classify:
- first selling swing
- first buying swing
- weak selling swing
- weak buying swing
- support created
- resistance created
- continuation phase
- reversal phase
- trade-ready phase

### Level 5 — Decision engine
The bot decides trade intent using the current overview and swing behavior.

Examples:
- bullish overview + weak selling swing + support hold = buy plan
- bearish overview + weak buying swing + resistance rejection = sell plan
- neutral overview = wait

### Level 6 — Trade execution simulation
Paper trading engine:
- open long / short
- stop loss
- target logic
- partial exits
- auto exit on SL / target
- risk-per-trade control

---

## Example rules

### Buy setup rule
Trigger buy when:
- overview is bullish
- price is near support or has formed a higher low
- selling swing is weak
- support holds after rejection
- confirmation candle appears

Then:
- entry on retracement or support hold
- SL below the recent support zone
- target at next resistance / reward multiple

### Sell setup rule
Trigger sell when:
- overview is bearish
- price is near resistance or has formed a lower high
- buying swing is weak
- resistance rejects and fails to continue upward
- confirmation candle appears

Then:
- entry on rejection or failed continuation
- SL above resistance zone
- target at next support / reward multiple

### Neutral rule
If overview is unclear:
- no trade
- wait for a clear swing or confirmation

---

## UI features to add on the chart

### 1) Support / resistance zones
- draw support lines in green
- draw resistance lines in red
- shade ranges for demand and supply

### 2) Swing labels
Mark:
- HH = higher high
- LH = lower high
- HL = higher low
- LL = lower low

### 3) Overview labels
Show on-screen status like:
- "Overview: Bullish"
- "Overview: Bearish"
- "Overview: Neutral"

### 4) Phase label
Show:
- "Weak selling swing"
- "Support created"
- "Resistance rejected"
- "Buy-ready"
- "Sell-ready"

### 5) Arrow overlays
Use arrows to show likely directional expectation:
- green arrow = buy expectation
- red arrow = sell expectation
- yellow arrow = uncertain / wait state

### 6) Trade panel
Display:
- current bias
- support/resistance zones
- last swing type
- trade setup status
- SL and target
- paper trade PnL

---

## State machine design

A simple state machine is the cleanest way to implement this.

Possible states:
- neutral
- bullish-overview
- bearish-overview
- weak-selling-swing
- weak-buying-swing
- support-created
- resistance-created
- buy-ready
- sell-ready
- trade-active
- target-hit
- stop-hit

Transition examples:
- neutral -> bullish-overview
- bullish-overview -> weak-selling-swing
- weak-selling-swing + support created -> buy-ready
- buy-ready + confirmation -> trade-active
- trade-active -> target-hit or stop-hit

---

## Backtesting and replay
Before real trading, the bot should support:
- historical replay of candles
- marking of support/resistance
- detecting phases and decisions
- logging trade actions
- evaluating win/loss rates

This proves the theory works with historical data before using live execution.

---

## Execution philosophy
The bot should not say:
- "Buy now" blindly

It should say:
- "Overview is bullish. Market is near support. Weak selling swing is forming. Support is holding. Buy trigger is active."

That is the right kind of trading intelligence from this theory.

---

## Minimum viable version
The first version should focus on:
1. Recent swings
2. Support and resistance zones
3. Overview bias
4. Weak vs strong swing detection
5. Buy/sell trigger states
6. Paper trade simulation

Do not start with full broker integration.
First build the market logic and chart overlays.

---

## Final output target
The final app should feel like a smart trading view overlay that:
- reads recent structure
- identifies overview
- detects weak/strong swings
- marks support/resistance
- shows live trade bias
- tests theory through paper trading
- acts only on confirmation and structure

This is the practical version of the six-session theory as a bot.
