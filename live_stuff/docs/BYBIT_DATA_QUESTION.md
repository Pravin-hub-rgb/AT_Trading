# Question: Downloading Bybit BTCUSDT Perp Data When API is Geo-Blocked

## Context
We want to backtest our v18 swing-trading strategy on **Bybit BTCUSDT perpetual** data because we plan to trade on Bybit live. However, Bybit's API (`api.bybit.com`) is unreachable from our machine — DNS resolution fails entirely (`getaddrinfo failed`), likely because Bybit is geo-blocked in India.

Binance API works fine from the same machine.

## What we need
Bybit BTCUSDT linear perpetual OHLC data in 15m and 1h timeframes, covering 2023-01-01 to present (same as our Binance dataset).

## Questions
1. **Alternative data source**: Is there a mirror/proxy of Bybit's API that works from India? Or a third-party provider (e.g. CCXT pro, data dump sites, Kaggle datasets)?
2. **VPN/proxy approach**: Would routing the download through a proxy/VPN be reliable, or is there risk of data gaps?
3. **Data parity assumption**: How close is Bybit BTCUSDT perp to Binance BTCUSDT perp in practice? If they're nearly identical (~$1-5 spread on $80K), can we just use Binance perp data and treat it as "close enough" for Bybit live?
4. **If we use Binance perp as proxy**: Our existing `data/btc-fut/BTCUSDT_15m.csv` already has Binance perp data (129K candles). The v18 backtest on that gave +218R net. Is that a realistic enough proxy for Bybit, or are there structural differences (funding rate impact, wick behavior, liquidation cascades) that would materially change results?

## Our setup
- CSV format: `timestamp,open,high,low,close,x,y` with IST wall-clock timestamps
- Engine: v18 streak-halt, 1h HTF + 15m LTF
- Binance perp backtest: 320 trades, +264.6R gross, +218.4R net (fee=0.05%/side, 2pts slippage)
