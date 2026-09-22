# AI Brainstorm Prompt — BTC Perp Swing Trading Edge Discovery

## The System (What We Have)

We have a **BTC perpetual futures backtesting engine** that trades 15-minute candles using signals derived from 1-hour swing structure. The system has been running live for 2+ years and we're trying to find new edges before deploying a corrected version.

### Pipeline: 1h → 15m

1. **1h Swing Engine** (`firstswing.py`): Analyzes 1h OHLC candles and detects swing breaks. Three types of break marks:
   - **B1**: First break — locks the engine into a direction. Informational only (not tradeable).
   - **B2**: Second break — confirms the leg. Tradeable. This is the ROBUST signal type.
   - **FLIP**: Opposite-direction break — previous leg dies without B2. Tradeable. This is the CURVE-FITTED signal type.

2. **HTF Window Generation**: Each 1h break mark creates a "window" — a time range during which 15m entries are allowed. Three window sets are pre-computed:
   - `intervals_flip`: Only FLIP break windows
   - `intervals_b2`: Only B2 break windows  
   - `intervals_decisive`: Both B2 and FLIP windows

3. **Mode Selection** (THE KEY MECHANISM): At each 15m signal, the engine decides which window set to use based on market regime:
   - `b2_vs_flip_chop`: B2 windows when chop>61.8, FLIP windows otherwise
   - `union`: BOTH window sets simultaneously (NEW — our best finding)
   - `dynamic_chop`: Adaptive percentile-based chop threshold

4. **15m Signal Collection**: Collects B2 and FLIP signals from 15m swing structure.

5. **Entry**: When a 15m signal falls inside an active HTF window AND direction matches, enter at 15m close.

6. **Stop Loss**: Swing start price ± 0.25×ATR(14, 15m). Trail via swing ratchet.

7. **Target**: 3R fixed target.

### Filters (Applied Post-Signal, Pre-Entry)

- **Weekend Skip**: No entries on Saturday/Sunday (IST). +17.7R OOS improvement.
- **mag_ratio >= 3.0**: Only enter when swing magnitude > 3× 20-bar ATR range. +17.8R OOS. Cuts 82% of trades.
- **Bias Momentum >= 0.5**: Ratio of consecutive 1h swing magnitudes. +2.0R OOS.
- **Extension Gate**: Skip if price already moved >1.5R from HTF entry.

### The Engine's Internal Parameters

- `ext_stop_r = 1.5`: Maximum extension from HTF entry
- `chop_thresh = 61.8`: Choppiness Index threshold for B2/FLIP switch
- `cooldown_bars = 10`: Minimum bars between entries
- `max_consecutive_losses = 3`: Halt after 3 consecutive losses
- `sl_buf_atr = 0.25`: SL buffer as ATR multiple
- `htf_rr = 3.0`: HTF R target
- `window_end = "exit"`: Window closes at HTF trade exit

### Cost Model

- Fee: 0.055% per side
- Entry slippage: 0.005%
- Exit slippage: 0.010%
- Funding: 0.01% per 8 hours (FIXED rate)

### Data

- **IS (In-Sample)**: 2023-2026 BTC/USDT 15m + 1h candles from Bybit
- **OOS (Out-of-Sample)**: 2021-2022 BTC/USDT (unseen data)
- No volume data (hardcoded zeros)
- No order book data

---

## What We've Found

### The Core Edge

The **regime-based mode switch** is the core edge:
- B2 (confirmation) signals work in **choppy** markets
- FLIP (reversal) signals work in **mild chop** (55-62 chop index)
- Neither works everywhere

The **union mode** (both windows simultaneously) with mag3+wknd+bm05 filters is the best config:
- OOS: +63.2R, DD=6.0, N/D=10.53, IS/OOS=4.6x
- 55 trades over 2 years

### What We Know Works

1. **Mode-level regime classification** (chop-based B2/FLIP switch)
2. **Weekend skip** (structural edge in thin markets)
3. **mag_ratio filter** (big swings = conviction, small swings = noise)
4. **Bias momentum** (consecutive swing magnitude ratio)
5. **Union windows** (cross-window opportunities)

### What We Know Fails

1. **Signal-level selectors** (htf_dir, ltf_dir, htf_mag) — direction/magnitude don't help
2. **Wick reject** — false positive from post-hoc bias
3. **Room filter** — reversed on OOS
4. **Wage gate** — hurts with mag_ratio
5. **Swingpause** — hurts with mag_ratio

### The B2 vs FLIP Finding

| Signal | IS | OOS |
|---|---|---|
| B2 | 185t +14.7R | 90t +38.8R |
| FLIP | 159t +193.6R | 81t -18.4R |

FLIP is curve-fitted (+193.6R IS, -18.4R OOS). B2 is robust.

---

## What We're Looking For

We need **genuinely new ideas** at the following levels:

### Level 1: Engine Structure
- Can we improve the swing detection itself?
- Should we use different timeframes (30m, 2h, 4h)?
- Is the 3R target optimal? Should it be dynamic?
- Is the trail mechanism optimal?

### Level 2: Mode Selection
- Is chop the best regime classifier? What about ADX, Hurst exponent, volatility regime?
- Should the mode be multi-timeframe?
- Can we use machine learning for regime classification?
- Should we have more than 2 modes (B2 vs FLIP)?

### Level 3: Signal Quality
- Can we improve B2 signal quality further?
- Can we make FLIP signals less curve-fitted?
- Should we use additional confirmation before entry?
- Can we use limit orders instead of market orders?

### Level 4: Risk Management
- Is 3R target optimal?
- Should we use position sizing based on regime?
- Should we use partial exits?
- Is the trail mechanism optimal?

### Level 5: Market Microstructure
- Can we use order flow data?
- Can we use funding rate data?
- Can we use open interest data?
- Can we use liquidation data?

### Level 6: Cross-Asset
- Can we use ETH or other assets as leading indicators?
- Can we use DXY, S&P500, or bonds as regime filters?
- Can we use stablecoin flows?

### Level 7: Time-Based Patterns
- Are there session-based edges (Asian, London, NY)?
- Are there day-of-week edges beyond weekend?
- Are there month-of-year edges?
- Are there halving cycle edges?

---

## Constraints

1. Must work on BTC perpetual futures
2. Must be backtestable on 15m candles (no tick data)
3. Must not use look-ahead bias (all filters use only past/current data)
4. Must have reasonable trade count (>20 trades per year for statistical significance)
5. Must generalize from IS to OOS (IS/OOS ratio < 5x)
6. Must have DD < 10R with filters for live deployment

---

## What We Need

Please brainstorm **genuinely creative, non-obvious ideas** that we haven't considered. Think about:

1. **Academic research** on regime detection, swing trading, crypto markets
2. **Structural edges** that are not curve-fitted
3. **Cross-domain ideas** from other fields (physics, biology, information theory)
4. **Contrarian ideas** that go against conventional trading wisdom
5. **Combinations** of existing edges that we haven't tested

For each idea, explain:
- What the idea is
- Why it might work (structural reasoning)
- How we would test it
- What data we would need
- Risk of curve fitting

---

## Our Brainstorm — Creative Ideas from Research + Our Findings

### Idea A: HMM Regime Detection (Replace Chop with Hidden Markov Model)
- **What:** Use a 2-3 state HMM trained on returns + volatility to detect regimes (trending, ranging, distressed). Route B2/FLIP based on HMM state instead of chop threshold.
- **Why:** HMM detects regime transitions earlier than indicator thresholds. Multiple papers (RegimeNAS, Springer 2026) show HMM-based regime detection outperforms fixed thresholds for crypto.
- **Test:** Train HMM on 2023-2024 data, apply to 2025-2026 IS and 2021-2022 OOS.
- **Data needed:** None extra (15m OHLCV sufficient for returns/volatility features).
- **Curve fit risk:** Medium — HMM has fewer parameters than our current system.

### Idea B: Funding Rate as Regime Filter
- **What:** Use Bybit's real-time funding rate as a regime indicator. High positive funding (>0.03%/8h) = crowded longs → use B2 windows (continuation). Negative/low funding = crowded shorts → use FLIP windows (reversal).
- **Why:** Funding rate reflects leveraged positioning. Extreme funding = crowded trade = likely reversal. This is a STRUCTURAL edge from market microstructure, not price action.
- **Test:** Fetch historical funding rates from Bybit, map to LTF bars, test as mode selector.
- **Data needed:** Bybit funding rate history (available via API).
- **Curve fit risk:** Low — funding rate is an exogenous variable, not derived from price.

### Idea C: Open Interest Change as Trend Confirmation
- **What:** Rising OI + rising price = strong trend → B2 windows. Falling OI + rising price = weak trend → FLIP windows.
- **Why:** OI confirms whether price moves have conviction. Price up + OI up = new money entering = real trend. Price up + OI down = short covering = temporary.
- **Test:** Fetch OI history, compute OI change over 4h, use as secondary filter.
- **Data needed:** Historical OI data from Bybit.
- **Curve fit risk:** Low — OI is exogenous.

### Idea D: Multi-Mode Ensemble (Soft Weighting)
- **What:** Instead of hard B2 vs FLIP switch, use soft weighting. At each signal, compute probability of choppy regime (from chop, ATR%, OI, funding). Weight B2 and FLIP windows by this probability. Enter if weighted signal quality exceeds threshold.
- **Why:** Binary switches lose information. Soft weighting allows the system to express uncertainty about regime.
- **Test:** Implement weighted interval matching in engine.
- **Data needed:** None extra.
- **Curve fit risk:** Medium — more parameters but each is justified.

### Idea E: Regime Transition Detection
- **What:** Detect when regime is CHANGING (not just what it IS). During transitions, reduce position size or skip entries. Transitions are detected by rapid chop changes, OI spikes, or funding rate flips.
- **Why:** Regime transitions are the most dangerous periods for any strategy. Avoiding them improves DD.
- **Test:** Add transition detection to engine, measure DD improvement.
- **Data needed:** None extra.
- **Curve fit risk:** Low — defensive mechanism, not offensive.

### Idea F: Volatility Clustering (GARCH)
- **What:** Use GARCH(1,1) to predict next-period volatility. Use predicted vol to adjust entry thresholds (wider in high vol, tighter in low vol).
- **Why:** Volatility clusters — high vol periods follow high vol. Predicting vol regime helps with position sizing and SL placement.
- **Test:** Fit GARCH on rolling window, test as entry filter.
- **Data needed:** None extra.
- **Curve fit risk:** Low — well-established model.

### Idea G: Cross-Asset Regime (ETH/BTC Ratio)
- **What:** Use ETH/BTC ratio momentum as regime filter. When ETH outperforms → risk-on → B2 windows. When BTC outperforms → risk-off → FLIP windows.
- **Why:** ETH/BTC ratio reflects crypto market risk appetite. Risk-on environments favor continuation, risk-off favor reversals.
- **Test:** Fetch ETH/BTC ratio, compute momentum, test as mode selector.
- **Data needed:** ETH 1h candles.
- **Curve fit risk:** Low — exogenous variable.

### Idea H: Session-Based Mode Selection
- **What:** Use trading session (Asian/London/NY) as secondary mode filter. Asian session: more ranging → B2. London/NY: more trending → FLIP.
- **Why:** Different sessions have different market participants and volatility profiles. Asian session is historically more ranging.
- **Test:** Add session detection to engine, test as mode modifier.
- **Data needed:** None extra (timestamps available).
- **Curve fit risk:** Low — well-known market structure.

### Idea I: Liquidation Cascade Filter
- **What:** Detect liquidation cascades (rapid OI drops + large price moves). During cascades, skip entries (market is chaotic). After cascade settles, enter with reduced size.
- **Why:** Liquidation cascades create temporary disorder. Trading during them is gambling, not edge capture.
- **Test:** Detect cascades via OI drops >5% in 1h, measure skip improvement.
- **Data needed:** OI data.
- **Curve fit risk:** Low — defensive.

### Idea J: Adaptive Target (Dynamic R-Multiple)
- **What:** Instead of fixed 3R target, use adaptive target based on volatility regime. High vol → wider target (4-5R). Low vol → tighter target (2R).
- **Why:** Fixed targets leave money on the table in high vol and hold too long in low vol.
- **Test:** Compute ATR percentile, adjust target dynamically.
- **Data needed:** None extra.
- **Curve fit risk:** Medium — needs careful calibration.

### Idea K: Fractal Dimension as Regime
- **What:** Compute fractal dimension of price series. Low FD (<1.3) = trending → FLIP. High FD (>1.5) = mean-reverting → B2.
- **Why:** Fractal dimension measures market complexity. Simple markets trend, complex markets range.
- **Test:** Compute FD on rolling window, test as mode selector.
- **Data needed:** None extra.
- **Curve fit risk:** Low — well-established concept.

### Idea L: Entropy-Based Regime
- **What:** Compute Shannon entropy of returns distribution. Low entropy = predictable → B2. High entropy = random → FLIP.
- **Why:** Entropy measures information content. Low entropy markets have exploitable structure.
- **Test:** Compute entropy on rolling window, test as mode selector.
- **Data needed:** None extra.
- **Curve fit risk:** Low — information-theoretic measure.
