Good — since you're running this on Bybit specifically, I pulled a couple of current exchange details into the checklist below so it's not just generic textbook advice. Here's a pre-launch checklist organized by category, roughly in the order you'd want to gate through them:

**1. Strategy validation (backtest)**
- [x] Tested across multiple regimes — bull, bear, chop, high/low volatility — not just one recent trend (2014-2026)
- [x] Walk-forward / out-of-sample testing done, not just curve-fit on the full dataset (2025-2026 out-of-sample)
- [x] No look-ahead bias (signals only use data that would've actually been available at that timestamp)
- [x] Costs modeled realistically: taker/maker fees, slippage, *and* funding (funding can be a real drag or tailwind on perps, not a rounding error)
- [x] Enough trades for statistical confidence — dozens isn't enough, aim for hundreds+ (313 Spot, 335 Bybit)
- [ ] Sharpe/Sortino, max drawdown, drawdown duration, win rate, and profit factor all documented (R and PF documented, Sharpe not calculated)
- [ ] Sensitivity-checked — small parameter tweaks shouldn't flip it from profitable to unprofitable (that's a sign of overfitting)
- [ ] Stress-tested against a flash-crash / gap-move scenario (in dataset but not isolated)

**2. Forward testing**
- [ ] Run on Bybit testnet against live data for a few weeks minimum (using Demo mode, not Testnet — different things)
- [ ] Paper-traded (or micro real size) through more than one market condition
- [ ] Live results roughly track backtest expectations — a big gap means something's off (data mismatch, unrealistic fill assumptions, etc.)

**3. Risk management**
- [x] Position sizing rule is coded, not "gut feel" (fixed %, vol-adjusted, etc.) (INR 250 risk from file, live conversion via RateManager singleton with disk cache)
- [x] Max leverage hard-capped in your code, independent of what the exchange allows (`MAX_LEVERAGE = 3` in config.py, enforced in `_calculate_qty()`)
- [x] Stop-loss enforced by the algo itself, on every trade (Bybit server-side Market SL, trailed via MB50 pivots, synced to exchange)
- [x] Max daily loss limit that auto-halts trading if breached (`DAILY_LOSS_MULTIPLIER = 5` in config.py → max 5R loss per UTC day, enforced in `_check_daily_loss_limit()`)
- [~] Max drawdown kill-switch — REJECTED for this algo (35% win rate, drawdowns are natural; kill-switch would halt before recovery, fighting strategy's edge)
- [ ] Liquidation buffer checked against normal BTC volatility, not just your entry margin
- [ ] Exposure/correlation limits if running multiple strategies or symbols

**4. Execution & order logic**
- [x] Order type matches intent (market / limit / post-only / reduce-only) (Market entry + Market SL)
- [x] Partial fills handled correctly (market orders fill fully, no partial logic) (market orders on BTCUSDT rarely partial-fill for small sizes; post-fill position verification confirms)
- [x] Client order IDs used so retries can't create duplicate orders (UUID `orderLinkId` per attempt in `place_market_order_retry()`)
- [x] Retry/backoff on failed calls — doesn't hammer the API into a rate-limit ban (`place_market_order_retry()` with exponential backoff + jitter, max 3 attempts, retries only transient errors)
- [x] Periodic reconciliation of local position state vs. what the exchange actually shows (startup reconciliation in Phase 15)
- [x] Graceful handling of rejected orders (bad price, insufficient margin, etc.) (retry wrapper detects non-retryable codes, logs and skips without hammering API)

**5. Bybit-specific setup**
- [x] Built on the V5 unified API (the old per-product endpoints are legacy) (pybit.unified_trading.HTTP)
- [x] API key scoped to trade-only — no withdrawal permission (Demo account keys)
- [ ] IP whitelist set on the key — note that as of February 10, 2026, IP whitelist entries on master API keys can no longer be added or removed through the API itself, so it's a manual browser-based step now
- [x] If this is a brand-new account, budget for it: new accounts face a 48-hour lockout before API key generation is even available (keys already created)
- [x] Rate limits respected — bot makes very few API calls (1-2 per trade, 15m+ apart). Worst case is 3 retry attempts on one order. Impossible to hit Bybit's 10 req/s limit with this strategy.if you exceed it
- [x] WebSocket used for order/position/fill updates instead of polling REST (cheaper on rate limits, faster) (BybitStreamer)
- [ ] Server time synced via NTP — signed requests silently fail if your clock drifts
- [x] Tick size, lot size, and min order qty pulled live from the instruments-info endpoint, not hardcoded from memory (`_fetch_instruments()` in BybitTrader, called on init, fallback to config.py)
- [x] Margin mode (isolated vs. cross) chosen deliberately, matching your risk plan (`MARGIN_MODE = "isolated"` in config.py, set via `set_margin_mode()` on startup)
- [ ] Funding mechanics understood: BTCUSDT settles funding on a fixed interval (standard 8 hours), you only pay or receive it if you're still holding the position at settlement, and the rate is normally kept within a fairly narrow band — though Bybit can widen those limits or even shift to hourly settlement during unusually volatile periods

**6. Monitoring & failsafes**
- [x] Every order, fill, and error logged with timestamps (detailed trade logging: entry, SL, rate, risk, qty, notional, fee buffer, Bybit sync status)
- [x] Alerting (Telegram/SMS/email) for errors, large drawdown, or the bot going silent (`telegram_alert.py` — entry, exit, error alerts via Telegram Bot API, free, integrated into live_loop.py)
- [x] A manual kill switch that instantly flattens positions and cancels all open orders (kill_switch.py + Ctrl+C graceful shutdown)
- [x] Auto-reconnect + state resync for WebSocket drops (BybitStreamer with backoff + gap detection)
- [ ] A plan for exchange maintenance windows or outright downtime
- [x] VPS/server redundancy thought through — what happens if your connection drops mid-position? (Bybit SL stays active on exchange server)

**7. Security**
- [x] Keys in env vars / a secrets manager — never hardcoded or committed to git (.env file)
- [x] No withdrawal permission on the trading key, period (Demo account)
- [ ] 2FA on the account itself
- [ ] A separate sub-account for the bot, isolated from other holdings

**8. Final go-live gate**
- [ ] Smallest real size that still exercises the full pipeline (not symbolic — real orders, real fills)
- [ ] You've watched it manually complete a handful of real trades before trusting it unattended
- [ ] A scale-up plan defined in advance, not decided in the moment
- [ ] A written answer to "what do I do if it hits my loss limit tomorrow" — before it happens, not after

---

### What We Fixed (2026-09-12)

| Gap | Before | After |
|-----|--------|-------|
| Risk sizing | Hardcoded $50 USDT | INR 250 from file, live CoinGecko conversion, editable via `risk_inr.txt` |
| Trail SL | Updated DB only, Bybit kept initial SL | Synced to Bybit via `set_trading_stop()` — exchange-side SL always current |
| Kill switch | None — Ctrl+C left position open | `kill_switch.py` + Ctrl+C graceful flatten + cancel |
| Position reconciliation | None | Startup reconciliation (Phase 15) |
| Hardcoded values | Fee rate, safety margin, qty precision scattered in code | All centralized in `config.py` — single source of truth |
| Rate fetching | Fetched on every trade (slow, CoinGecko API call) | Singleton `RateManager` — loads from disk (0ms), background refresh every 15 min, fallback chain: CoinGecko → ExchangeRate-API → disk cache → emergency 95.0 |
| Trade logging | Minimal `[order] PLACING: Buy 0.001 BTC` | Full detail per trade: entry, SL, TP, risk INR, risk USDT, rate, qty, notional, fee buffer, Bybit sync status |
| Legacy code | `BybitTrader.calculate_qty()` unused, `get_usdt_inr_rate()` function | Removed — replaced by RateManager + config |
| Margin mode | Not set (defaulted to Cross on UNIFIED) | Explicitly set to `isolated` via `set_margin_mode()` on startup |
| Daily loss limit | None | Added `_check_daily_loss_limit()` — max 5R loss per UTC day, halts new entries when breached, resets at midnight UTC, Telegram alert sent |

### Remaining Gaps (Updated 2026-09-13)

| Gap | Priority | Notes |
|-----|----------|-------|
| **Forward testing** | | |
| Run on Bybit demo for a few weeks | Critical | Must validate live fills match backtest expectations |
| Watch it manually complete real trades | Critical | Before trusting unattended |
| Live results track backtest | Critical | Big gap = something off (data mismatch, fill assumptions) |
| **Bybit manual steps** | | |
| IP whitelist on API key | Manual | Browser step — set when going live (can't change via API since Feb 2026) |
| 2FA on account | Manual | Browser step on Bybit account |
| Separate sub-account for bot | Manual | Browser step — isolate from personal holdings |
| **Operational decisions** | | |
| Exchange downtime plan | Manual | What to do during Bybit maintenance windows |
| Scale-up plan | Manual | Defined in advance, not decided in the moment |
| Loss limit response plan | Manual | Written answer to "what if it hits limit tomorrow" |
| **Code (nice-to-have)** | | |
| Sharpe/Sortino calculation | Nice-to-have | Not blocking go-live |
| NTP time sync verification | Low | Could cause signature failures (only live, not demo) |
| Flash-crash stress test | Nice-to-have | Already stress-tested in backtest dataset |
| Max drawdown kill-switch | Skipped | REJECTED — wrong for 35% win rate algo |
| Liquidation buffer | Covered | 3x leverage cap provides ~33% buffer |
| Exposure limits | N/A | Single symbol only |



**Clear Answer for You**

### Right Now (No Credit Card)

**Best option → Pay with Crypto (USDT from your wallet)**

| Provider          | Location   | Payment          | Price     | Difficulty | Recommendation |
|-------------------|------------|------------------|-----------|------------|----------------|
| **Cloudzy**       | Singapore  | USDT / BTC / ETH | ~$3–6     | Easy       | **Best choice** |
| Server4Crypto     | Singapore  | USDT / BTC / ETH | ~$5       | Easy       | Good alternative |
| Other crypto VPS  | Singapore  | Crypto           | $4–7      | Easy       | Okay           |

**Yes — paying with crypto from your wallet is currently the best and easiest way for you.**

UPI is almost never accepted by Singapore VPS providers (only a few Indian providers accept UPI, but they are not in Singapore).

---

### When You Get a Credit Card Later

Once you have a proper international credit/debit card, the ranking becomes:

1. **Vultr Singapore** (most recommended)
2. DigitalOcean Singapore
3. Cloudzy (still fine)

---

### Summary for You Right Now

- **Best current solution** → Cloudzy Singapore + pay with **USDT**
- No credit card needed
- Singapore location (good for Bybit)
- Easy to set up

Would you like me to give you the exact step-by-step for Cloudzy (which plan to choose + how to pay with USDT)?

