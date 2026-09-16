# VPS Requirements — Backbencher v18

## Why a VPS?

Backbencher runs 24/7 — it needs to be always-on to catch signals and place trades.
Your laptop can't do this reliably (sleep, restarts, internet drops).

## What the Bot Actually Uses

| Resource | Usage | Notes |
|----------|-------|-------|
| CPU | ~0.1 vCPU | Swing engine processes ~500 candles once per 15m close. No heavy math. |
| RAM | ~50-100 MB | SQLite + swing state + WebSocket buffers. Python process is tiny. |
| Storage | ~10 MB | SQLite DB + logs. |
| Network | 1 WS connection + occasional REST | 1-2 API calls per trade (1.7 trades/week). WebSocket is lightweight. |

## What Actually Matters

| Factor | Why |
|--------|-----|
| **Uptime** | Bot must stay running 24/7, reconnect on drops |
| **Network stability** | Dropped connection = missed trade (but SL stays on Bybit, so money is safe) |
| **Location** | Closer to Bybit servers = lower latency (Singapore/Hong Kong ideal, but 15m strategy doesn't care about ms) |

## Recommended Specs

| Spec | Value | Why |
|------|-------|-----|
| vCPU | 1 | More than enough |
| RAM | 1 GB | Headroom for OS + Python |
| Storage | 10 GB | SSD, plenty for logs + DB |
| Location | Singapore/HK | Closest to Bybit servers |
| Price | $4-6/month | Hetzner CX22 ($4.50), DigitalOcean ($6), Vultr ($5) |

## Don't Overkill

2 vCPU / 4GB RAM is a waste — you'd use 5% of it.

## Don't Underperform

Shared CPU is fine, but avoid "burstable" instances that throttle after 30 seconds of activity.

## VPS Providers (Tested for Bybit)

| Provider | Cheapest Plan | Location | Price |
|----------|--------------|----------|-------|
| Hetzner | CX22 | Singapore | $4.50/mo |
| DigitalOcean | Basic Droplet | Singapore | $6/mo |
| Vultr | Cloud Compute | Singapore | $5/mo |
| AWS Lightsail | instance | Singapore | $5/mo |

## After VPS Setup

1. Install Python 3.10+
2. Clone the repo
3. Install dependencies: `pip install -r requirements.txt`
4. Add `.env` with Bybit + Telegram keys
5. Run: `python main.py --exchange bybit --symbol BTCUSDT`
6. Set up as systemd service for auto-restart
