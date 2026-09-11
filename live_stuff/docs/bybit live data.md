**Here’s the clean & practical way to get both historical OHLC + live stream from Bybit for your algo.**

We will use the official `pybit` library (recommended by Bybit).

### 1. Install

```bash
pip install pybit pandas
```

### 2. Historical OHLC (for backtest / initial load)

```python
from pybit.unified_trading import HTTP
import pandas as pd
from datetime import datetime, timezone

session = HTTP(testnet=False)   # True for testnet

def get_ohlc(symbol="BTCUSDT", interval="15", limit=1000, start=None, end=None):
    """
    interval: "1", "3", "5", "15", "30", "60", "120", "240", "D" etc.
    """
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    response = session.get_kline(**params)
    
    data = response["result"]["list"]
    
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "turnover"
    ])
    
    df["timestamp"] = pd.to_numeric(df["timestamp"])
    df = df.astype({
        "open": float, "high": float, "low": float, 
        "close": float, "volume": float, "turnover": float
    })
    
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    return df[["datetime", "open", "high", "low", "close", "volume", "turnover"]]

# Example
df_15m = get_ohlc(interval="15", limit=500)
print(df_15m.tail())
```

### 3. Live WebSocket Stream (15m Kline + Ticker)

```python
from pybit.unified_trading import WebSocket
from time import sleep

# Public stream (no API key needed)
ws = WebSocket(
    testnet=False,
    channel_type="linear"          # for BTCUSDT perpetual
)

def handle_kline(message):
    """Called every time new 15m candle data comes"""
    data = message["data"][0]
    
    confirm = data["confirm"]      # True = candle just closed
    close = float(data["close"])
    high = float(data["high"])
    low = float(data["low"])
    open_ = float(data["open"])
    volume = float(data["volume"])
    start = data["start"]
    
    print(f"{'CLOSED' if confirm else 'UPDATE'} | "
          f"O:{open_} H:{high} L:{low} C:{close} V:{volume}")
    
    if confirm:
        # === YOUR ALGO LOGIC HERE ===
        # Candle just closed → check for entry signal
        print(">>> 15m candle closed! Run strategy logic")
        # place_order(...) etc.

def handle_ticker(message):
    """Real-time price updates"""
    data = message["data"]
    last_price = float(data["lastPrice"])
    # print(f"Last Price: {last_price}")

# Subscribe to 15-minute kline
ws.kline_stream(
    interval=15,
    symbol="BTCUSDT",
    callback=handle_kline
)

# Optional: also get ticker for live price
ws.ticker_stream(
    symbol="BTCUSDT",
    callback=handle_ticker
)

print("Streaming started... Press Ctrl+C to stop")
while True:
    sleep(1)
```

### Key Points for Your Strategy

- `confirm = True` → this is the **closed** candle (exactly when you want to enter).
- You only need to act when `confirm == True`.
- The stream is very stable and low latency.

---

Would you like me to combine both (historical load + live stream) into one clean class that you can plug directly into your v18 engine?

**Yes, Bybit has a proper Demo Trading mode** — this is perfect for testing your algo safely.

### What is Bybit Demo Trading?

- It’s a **separate paper-trading account** inside your real Bybit account.
- You get free virtual money (usually 50,000 USDT + some BTC/ETH).
- All trades are simulated — no real money is used.
- Order rules, fees structure, and execution are very close to live trading.
- Perfect for testing your v18 strategy before going live.

### How to Use Demo Trading with Your Algo

#### Step 1: Switch to Demo Mode
1. Log in to Bybit (app or website).
2. Click on your profile icon (top right).
3. Click **Demo Trading**.
4. You will now be in the demo account (it has its own User ID).

#### Step 2: Create API Key for Demo
1. While you are still in **Demo Trading** mode:
2. Go to **API Management**.
3. Create a new API key.
4. Give it permissions for **Unified Trading** (or Contract + Spot).
5. **Important**: Copy the API Key and Secret immediately (Secret is shown only once).

#### Step 3: Use Demo API in Python

```python
from pybit.unified_trading import HTTP

# Demo Trading session
session = HTTP(
    testnet=False,
    demo=True,                    # ← This is the key
    api_key="YOUR_DEMO_API_KEY",
    api_secret="YOUR_DEMO_API_SECRET",
)

# Example: Place a market order on Demo
response = session.place_order(
    category="linear",
    symbol="BTCUSDT",
    side="Buy",
    orderType="Market",
    qty="0.01",
    stopLoss="78000",             # optional
    takeProfit="82000"            # optional
)

print(response)
```

### Important Points

| Item                      | Demo Trading                  | Live Trading              |
|---------------------------|-------------------------------|---------------------------|
| Base URL                  | `https://api-demo.bybit.com`  | `https://api.bybit.com`   |
| WebSocket (private)       | `wss://stream-demo.bybit.com` | `wss://stream.bybit.com`  |
| Public market data        | Same as live                  | Same                      |
| Real money                | No                            | Yes                       |
| Orders keep history       | Only 7 days                   | Permanent                 |
| Rate limits               | Default (cannot upgrade)      | Higher with VIP           |

### Recommendation for You

1. First create the **Demo API key**.
2. Run your full algo on Demo for a few days.
3. Check if entries, SL placement, and exits work correctly.
4. Only after you are happy → switch to live keys.

Would you like me to give you a ready-to-use code template that can easily switch between **Demo** and **Live** with just one variable?


**Detailed Guide for Your Coder – Bybit Demo + Live Setup**

This is a complete practical guide so your coder can implement everything cleanly.

---

### 1. Bybit Demo Trading Overview

Bybit has **two different testing environments**:

| Environment     | Purpose                        | URL (REST)                  | How to create API Key                  | Real Money? |
|-----------------|--------------------------------|-----------------------------|----------------------------------------|-------------|
| **Demo Trading**| Paper trading (recommended)    | `https://api-demo.bybit.com`| Switch to Demo mode → Create API key  | No         |
| **Testnet**     | Testing new features           | `https://api-testnet.bybit.com` | Create account on testnet.bybit.com | No         |

**Use Demo Trading** for strategy testing.  
Testnet is less realistic for price action.

---

### 2. How to Create Demo API Key (Step-by-step)

1. Login to Bybit (main account).
2. Click profile icon → **Demo Trading**.
3. You are now inside Demo account.
4. Go to **API Management**.
5. Click **Create New Key**.
6. Select:
   - API Key Usage → **API Transaction**
   - Permissions → Enable **Unified Trading** (or Contract + Spot)
7. (Optional but recommended) Bind your IP address.
8. Create the key → **Copy API Key + Secret immediately** (Secret is shown only once).

---

### 3. Python Setup (Recommended Library)

```bash
pip install pybit pandas
```

---

### 4. Core Code Structure (Demo + Live Switchable)

```python
from pybit.unified_trading import HTTP, WebSocket
from time import sleep
import pandas as pd
from datetime import datetime, timezone

# ====================== CONFIG ======================
MODE = "demo"          # "demo" or "live"

if MODE == "demo":
    API_KEY = "YOUR_DEMO_API_KEY"
    API_SECRET = "YOUR_DEMO_API_SECRET"
    DEMO = True
else:
    API_KEY = "YOUR_LIVE_API_KEY"
    API_SECRET = "YOUR_LIVE_API_SECRET"
    DEMO = False

# ====================================================

# REST Session
session = HTTP(
    testnet=False,
    demo=DEMO,
    api_key=API_KEY,
    api_secret=API_SECRET,
)

print(f"Connected in {MODE.upper()} mode")
```

---

### 5. Historical OHLC (for initial data load)

```python
def get_klines(symbol="BTCUSDT", interval="15", limit=500):
    response = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    
    data = response["result"]["list"]
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "turnover"
    ])
    
    df = df.astype({
        "timestamp": int,
        "open": float, "high": float, "low": float,
        "close": float, "volume": float, "turnover": float
    })
    
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    return df[["datetime", "open", "high", "low", "close", "volume"]]
```

---

### 6. Live WebSocket Stream (15m Kline)

```python
def handle_kline(message):
    candle = message["data"][0]
    
    is_closed = candle["confirm"]          # True = candle just closed
    open_price = float(candle["open"])
    high = float(candle["high"])
    low = float(candle["low"])
    close = float(candle["close"])
    volume = float(candle["volume"])
    start_time = candle["start"]
    
    print(f"{'CLOSED' if is_closed else 'LIVE'} | "
          f"O:{open_price} H:{high} L:{low} C:{close}")
    
    if is_closed:
        # === YOUR STRATEGY LOGIC HERE ===
        # Run v18 signal detection
        # If signal → place_order()
        pass

# Public stream (no auth needed for market data)
ws = WebSocket(
    testnet=False,
    channel_type="linear"
)

ws.kline_stream(
    interval=15,
    symbol="BTCUSDT",
    callback=handle_kline
)

print("WebSocket started...")
while True:
    sleep(1)
```

---

### 7. Place Market Order + Stop Loss (Demo / Live)

```python
def place_market_order(side: str, qty: str, stop_loss: str = None, take_profit: str = None):
    """
    side: "Buy" or "Sell"
    qty: string, e.g. "0.01"
    """
    params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "side": side,
        "orderType": "Market",
        "qty": qty,
        "timeInForce": "GTC",
        "positionIdx": 0,               # One-way mode
    }
    
    if stop_loss:
        params["stopLoss"] = stop_loss
    if take_profit:
        params["takeProfit"] = take_profit
    
    response = session.place_order(**params)
    return response
```

**Example usage:**
```python
# Long entry with SL
order = place_market_order(
    side="Buy",
    qty="0.01",
    stop_loss="77500.5"
)
print(order)
```

---

### 8. Position Size Calculation (₹500 risk example)

```python
def calculate_qty(entry_price: float, stop_loss: float, risk_inr: float = 500, btc_inr_rate: float = 7000000):
    """
    risk_inr: How much INR you want to risk per trade
    """
    risk_usdt = risk_inr / (btc_inr_rate / entry_price)   # rough conversion
    stop_distance = abs(entry_price - stop_loss)
    
    qty = risk_usdt / stop_distance
    qty = round(qty, 3)          # Bybit BTCUSDT precision is 0.001
    
    return str(qty)
```

---

### 9. Important Notes for Coder

| Topic                    | Recommendation |
|--------------------------|--------------|
| **Mode Switching**       | Use one variable `MODE = "demo"` or `"live"` |
| **Position Mode**        | Always use One-way mode (`positionIdx=0`) |
| **Qty Precision**        | Always send as string, round properly |
| **Stop Loss**            | Attach at order time (safest) |
| **Error Handling**       | Always check `retCode == 0` |
| **Rate Limits**          | Demo has lower limits than live |
| **Order History**        | Demo only keeps last 7 days |

---

### 10. Recommended Workflow

1. Create Demo API key
2. Run full strategy on Demo for at least 3–7 days
3. Log every signal + order response
4. Verify SL is correctly placed
5. Only after everything looks good → switch to Live keys

---

Would you like me to also give a full working class structure (cleaner OOP version) that your coder can copy-paste?