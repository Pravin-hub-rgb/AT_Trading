"""Centralized config — all trading params in one place.

No hardcoded values in live_loop.py or bybit_order.py.
Edit this file or risk_inr.txt to change params (some need restart, some don't).

Values source:
  - Bybit V5 API docs (fees, precision)
  - v18_params.py (strategy params)
  - Ghoststreak best practices (rate manager, position sizing)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# =============================================================================
# EXCHANGE
# =============================================================================

EXCHANGE = os.getenv("BYBIT_EXCHANGE", "bybit")
SYMBOL = os.getenv("BYBIT_SYMBOL", "BTCUSDT")
BYBIT_DEMO = os.getenv("BYBIT_DEMO", "true").lower() == "true"

# =============================================================================
# RISK MANAGEMENT
# =============================================================================

# Risk per trade in INR — read from risk_inr.txt (edit file, no restart)
# Fallback to this if file missing
DEFAULT_RISK_INR = 250.0

# Max leverage — hard cap, rejected if implied leverage exceeds this
MAX_LEVERAGE = 3

# Balance safety — never use more than this fraction of available balance
BALANCE_SAFETY_MARGIN = 0.95

# When position is sized down, use this fraction of available
SIZED_DOWN_FRACTION = 0.9

# Margin mode: 'isolated' (each position has own margin) or 'cross' (shared margin pool)
# Isolated = safer, only that position's margin at risk on liquidation
# Cross = default on Bybit UNIFIED, entire account at risk
MARGIN_MODE = "isolated"

# Daily loss limit = risk_inr * DAILY_LOSS_MULTIPLIER
# If total R lost in a day exceeds this, bot halts until next day
# 5x = 5 consecutive losses (matches streak halt threshold but time-based)
DAILY_LOSS_MULTIPLIER = 5

# =============================================================================
# FEES & SLIPPAGE (Bybit VIP 0)
# =============================================================================

# Bybit taker fee per side (0.055%)
TAKER_FEE_PCT = 0.055

# Fee rate as decimal for calculations: 0.055% = 0.00055
TAKER_FEE_RATE = TAKER_FEE_PCT / 100.0

# Entry slippage (conservative estimate)
ENTRY_SLIP_PCT = 0.005

# Exit slippage (conservative estimate)
EXIT_SLIP_PCT = 0.010

# =============================================================================
# POSITION SIZING
# =============================================================================

# BTCUSDT precision — 0.001 BTC increments
QTY_PRECISION = 3
MIN_BTC_QTY = 0.001

# =============================================================================
# RATE MANAGER
# =============================================================================

# How often to refresh INR/USDT rate (seconds)
RATE_UPDATE_INTERVAL = 900  # 15 minutes

# After this many seconds without update, force emergency rate
RATE_STALE_SECONDS = 24 * 3600  # 24 hours

# Emergency fallback rate (INR per USDT)
EMERGENCY_RATE = 95.0

# File to cache rate on disk
RATE_CACHE_FILE = Path(__file__).resolve().parent / "last_rate.json"

# =============================================================================
# WEBSOCKET
# =============================================================================

# Window sizes for rolling data
WINDOW_DAYS_15M = 30
WINDOW_DAYS_1H = 20
CAP_DAYS = 16

# Status print interval (seconds)
STATUS_INTERVAL = 30

# =============================================================================
# LOGGING
# =============================================================================

# Trade log level — set True for detailed per-trade logs
VERBOSE_TRADE_LOG = True
