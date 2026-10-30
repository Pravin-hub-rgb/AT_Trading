"""Quick test — verify Bybit demo keys work + WebSocket + REST."""
import os
import sys
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

def test_pybit_rest():
    """Test pybit HTTP session with demo keys."""
    print("=== pybit REST test ===")
    try:
        from pybit.unified_trading import HTTP
        session = HTTP(
            testnet=False,
            demo=True,
            api_key=os.getenv("BYBIT_API_KEY", ""),
            api_secret=os.getenv("BYBIT_API_SECRET", ""),
        )
        # Get wallet balance
        resp = session.get_wallet_balance(accountType="UNIFIED")
        items = resp["result"]["list"]
        found_usdt = False
        for item in items:
            for c in item.get("coin", []):
                if c["coin"] == "USDT":
                    eq = float(c.get("equity", 0) or 0)
                    av = float(c.get("availableToWithdraw", 0) or 0)
                    print(f"  USDT Equity: ${eq:.2f}")
                    print(f"  Available:   ${av:.2f}")
                    found_usdt = True
        if not found_usdt:
            print("  No USDT in account (empty demo wallet)")
        # Get position
        resp2 = session.get_positions(category="linear", symbol="BTCUSDT")
        positions = resp2["result"]["list"]
        has_pos = False
        for p in positions:
            if p["symbol"] == "BTCUSDT" and float(p.get("size", 0) or 0) > 0:
                print(f"  Position: {p['side']} {p['size']} BTC @ {p['avgPrice']}")
                has_pos = True
        if not has_pos:
            print("  No open position")
        print("  [OK] pybit REST connected")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_bybit_backfill():
    """Test Bybit REST backfill (public, no auth)."""
    print("\n=== Bybit REST backfill test ===")
    try:
        from bybit_streamer import backfill_klines_bybit
        candles = backfill_klines_bybit("BTCUSDT", "60", limit=5, demo=True)
        print(f"  Fetched {len(candles)} 1h candles")
        for c in candles[-2:]:
            print(f"  {c['open_time']} O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f}")
        print("  [OK] backfill works")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


async def _test_bybit_ws():
    """Test Bybit public WebSocket (trades + klines, 8 seconds)."""
    print("\n=== Bybit WebSocket test (8s) ===")
    try:
        import websockets
        # Demo WS returns 404 — use live WS (DNS bypass handles geo-block)
        url = "wss://stream.bybit.com/v5/public/linear"
        received = {"trades": 0, "klines": 0}
        async with websockets.connect(url) as ws:
            # Subscribe to trade + 15m kline
            sub = json.dumps({"op": "subscribe", "args": ["publicTrade.BTCUSDT", "kline.15.BTCUSDT"]})
            await ws.send(sub)
            t0 = time.time()
            while time.time() - t0 < 8:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3)
                    data = json.loads(msg)
                    topic = data.get("topic", "")
                    if "publicTrade" in topic:
                        received["trades"] += 1
                    elif "kline" in topic:
                        received["klines"] += 1
                except asyncio.TimeoutError:
                    continue
        print(f"  Trades: {received['trades']}, Klines: {received['klines']}")
        if received["trades"] > 0 or received["klines"] > 0:
            print("  [OK] WebSocket works")
            return True
        else:
            print("  [WARN] No data received")
            return False
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_bybit_ws():
    """Sync pytest entrypoint for the async WebSocket test."""
    asyncio.run(_test_bybit_ws())



if __name__ == "__main__":
    r1 = test_pybit_rest()
    r2 = test_bybit_backfill()
    r3 = asyncio.run(_test_bybit_ws())
    print(f"\nResults: REST={r1} Backfill={r2} WebSocket={r3}")
    if not r3:
        print("\nNOTE: Bybit WebSocket is geo-blocked from India.")
        print("Use a VPN (e.g. Canada) to test WebSocket streaming.")
