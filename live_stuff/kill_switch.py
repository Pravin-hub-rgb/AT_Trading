"""Kill switch — instantly flatten position + cancel all orders on Bybit.

Usage:
    python kill_switch.py              # flatten + cancel
    python kill_switch.py --status     # show position only (no action)

Works independently from the bot — can run even if bot is frozen/crashed.
Uses same .env keys as the main bot.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv(Path(__file__).resolve().parent / ".env")


def main():
    api_key = os.getenv("BYBIT_API_KEY", "")
    api_secret = os.getenv("BYBIT_API_SECRET", "")
    demo = os.getenv("BYBIT_DEMO", "true").lower() == "true"
    symbol = os.getenv("BYBIT_SYMBOL", "BTCUSDT")

    if not api_key or not api_secret:
        print("[kill] No API keys in .env — cannot connect")
        sys.exit(1)

    session = HTTP(testnet=False, demo=demo, api_key=api_key, api_secret=api_secret)
    mode = "DEMO" if demo else "LIVE"
    print(f"[kill] Connected to Bybit {mode}")

    # Check position
    try:
        resp = session.get_positions(category="linear", symbol=symbol)
        positions = resp["result"]["list"]
        pos = None
        for p in positions:
            if p["symbol"] == symbol and float(p.get("size", 0)) > 0:
                pos = p
                break
    except Exception as e:
        print(f"[kill] Position query failed: {e}")
        sys.exit(1)

    if not pos:
        print(f"[kill] No open {symbol} position — nothing to flatten")
        # Still cancel any orphan orders
        try:
            session.cancel_all_orders(category="linear", symbol=symbol)
            print("[kill] Cancelled any pending orders")
        except Exception:
            pass
        return

    side = pos["side"]
    size = float(pos["size"])
    entry = float(pos["avgPrice"])
    pnl = float(pos.get("unrealisedPnl", 0))
    close_side = "Sell" if side == "Buy" else "Buy"

    print(f"[kill] Open {side} position: {size} BTC @ {entry:.2f} PnL={pnl:+.2f}")

    if "--status" in sys.argv:
        print("[kill] --status flag — not flattening")
        return

    # Flatten with retry
    flattened = False
    for attempt in range(2):
        try:
            resp = session.place_order(
                category="linear",
                symbol=symbol,
                side=close_side,
                orderType="Market",
                qty=str(size),
                positionIdx=0,
                reduceOnly=True,
            )
            if resp.get("retCode") == 0:
                print(f"[kill] FLATTENED: {close_side} {size} BTC — order id={resp['result']['orderId']}")
                flattened = True
                break
            else:
                print(f"[kill] FLATTEN FAILED (attempt {attempt+1}): {resp.get('retMsg', 'unknown')}")
        except Exception as e:
            print(f"[kill] FLATTEN ERROR (attempt {attempt+1}): {e}")
    if not flattened:
        print("[kill] CRITICAL: COULD NOT FLATTEN — manual intervention required")
        sys.exit(2)

    # Cancel all pending orders
    try:
        session.cancel_all_orders(category="linear", symbol=symbol)
        print("[kill] All pending orders cancelled")
    except Exception as e:
        print(f"[kill] Cancel failed: {e}")

    print("[kill] Kill switch complete")


if __name__ == "__main__":
    main()
