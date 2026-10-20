"""Backbencher - main entry point.

Usage:
    python main.py                                      # run forever
    python main.py 120                                  # run 120 seconds (test)
    python main.py --paper                              # paper trading mode (default)
    python main.py --live                               # live trading with real orders
    python main.py --exchange bybit --symbol BTCUSDT    # Bybit demo trading
    python main.py "2026-09-07 03:00:00" "2026-09-07 05:30:00"
                                       # seed: arg1=15m start, arg2=1h start (IST)
                                       # timestamp IS the first candle (no lookback)
    python main.py "2026-09-07 03:00:00" "2026-09-07 05:30:00" --exchange bybit
                                       # seed Bybit from specific timestamps
"""

import sys
import time
import re
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from persistence.database import Database
from live_loop import LiveLoop, EXCHANGE_BINANCE, EXCHANGE_BYBIT
from book import BOOK_CODE, BOOK_NAME
import config

DB_PATH = "backbencher.db"


def main():
    """Main entry point."""
    max_seconds = 0
    paper_mode = "--live" not in sys.argv
    seed_1h = None
    seed_15m = None
    exchange = EXCHANGE_BINANCE
    symbol = "BTCUSDT"
    positional_timestamps = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--paper":
            paper_mode = True
            i += 1
        elif arg == "--live":
            paper_mode = False
            i += 1
        elif arg == "--exchange" and i + 1 < len(sys.argv):
            exchange = sys.argv[i + 1].lower()
            i += 2
        elif arg == "--symbol" and i + 1 < len(sys.argv):
            symbol = sys.argv[i + 1].upper()
            i += 2
        elif re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', arg):
            positional_timestamps.append(arg)
            i += 1
        else:
            try:
                max_seconds = float(arg)
            except ValueError:
                pass
            i += 1

    # Positional timestamps: arg1=15m, arg2=1h
    if len(positional_timestamps) >= 2:
        seed_15m = positional_timestamps[0]
        seed_1h = positional_timestamps[1]
    elif len(positional_timestamps) == 1:
        print("[main] Need 2 timestamps: python main.py '15m_time' '1h_time'")
        sys.exit(1)

    # Auto-detect exchange from symbol
    if symbol.endswith("_BYBIT"):
        exchange = EXCHANGE_BYBIT
        symbol = symbol.replace("_BYBIT", "")

    # Book params come from book.py (book 107). The internal name
    # v18_instrument is kept for compatibility; it no longer selects params.
    v18_instrument = f"{symbol}_BYBIT" if exchange == EXCHANGE_BYBIT else symbol

    print("=" * 60)
    print(f"Backbencher - Book {BOOK_CODE} Live Trading Engine")
    print("=" * 60)
    print(f"Exchange:  {exchange.upper()}")
    print(f"Symbol:    {symbol}")
    print(f"Book:      {BOOK_CODE} {BOOK_NAME}")
    print(f"Mode:      {'PAPER' if paper_mode else 'LIVE'}")
    print(f"Database:  {DB_PATH}")
    if max_seconds:
        print(f"Test:      {max_seconds}s window")
    if seed_1h and seed_15m:
        print(f"Seed 15m:  {seed_15m} IST")
        print(f"Seed 1h:   {seed_1h} IST")
    # Risk config
    from live_loop import read_risk_inr
    from rate_manager import RateManager
    rm = RateManager()
    rm.update()
    risk_inr = read_risk_inr()
    rate = rm.get_rate()
    risk_usdt = risk_inr / rate
    print(f"Risk:      INR {risk_inr:.0f} = ${risk_usdt:.2f} USDT (rate INR {rate:.2f}/USDT)")
    print(f"Risk file: risk_inr.txt (edit to change, no restart)")
    print(f"Max lev:   {config.MAX_LEVERAGE}x")
    print("=" * 60)

    # Initialize database
    db = Database(DB_PATH)
    db.connect()
    db.create_tables()

    # Create live loop (uses the vendored unified engine on rolling windows)
    loop = LiveLoop(db, exchange=exchange, symbol=symbol, paper_mode=paper_mode,
                    v18_instrument=v18_instrument)

    # Set leverage + margin mode on exchange (if connected)
    if loop.trader and loop.trader.is_connected:
        loop.trader.set_leverage()
        loop.trader.set_margin_mode()
        print(f"[main] Exchange setup: {config.MAX_LEVERAGE}x leverage, {config.MARGIN_MODE.upper()} margin")

    def _graceful_shutdown(loop):
        """Flatten position + cancel orders on Ctrl+C.

        Creates a fresh pybit session so shutdown isn't affected by the
        main session's state after asyncio.run() tears down the event loop.
        """
        try:
            from pybit.unified_trading import HTTP
            from dotenv import load_dotenv
            import os
            load_dotenv(Path(__file__).resolve().parent / ".env")
            api_key = os.getenv("BYBIT_API_KEY", "")
            api_secret = os.getenv("BYBIT_API_SECRET", "")
            demo = os.getenv("BYBIT_DEMO", "true").lower() == "true"
            if not api_key or not api_secret:
                print("[shutdown] No API keys — skipping flatten")
                return
            session = HTTP(
                api_key=api_key, api_secret=api_secret,
                demo=demo, testnet=False,
            )
            symbol = os.getenv("BYBIT_SYMBOL", "BTCUSDT")
            # Check position
            resp = session.get_positions(category="linear", symbol=symbol)
            pos = None
            for p in resp["result"]["list"]:
                if p["symbol"] == symbol and float(p.get("size", 0)) > 0:
                    pos = p
                    break
            if pos:
                side = "Sell" if pos["side"] == "Buy" else "Buy"
                qty = pos["size"]
                print(f"[shutdown] Flattening {pos['side']} {qty} BTC...")
                close_resp = session.place_order(
                    category="linear", symbol=symbol, side=side,
                    orderType="Market", qty=qty, positionIdx=0,
                )
                if close_resp.get("retCode") == 0:
                    print("[shutdown] Position flattened")
                else:
                    print(f"[shutdown] Flatten failed: {close_resp.get('retMsg', 'unknown')}")
            else:
                print("[shutdown] No open position")
            # Cancel all open orders
            try:
                session.cancel_all_orders(category="linear", symbol=symbol)
                print("[shutdown] Orders cancelled")
            except Exception as e:
                print(f"[shutdown] Cancel error: {e}")
        except Exception as e:
            print(f"[shutdown] Flatten error: {e}")

    def _start_streaming():
        """Start WebSocket streamer and run the event loop."""
        loop._running = True
        started = time.time()
        if exchange == EXCHANGE_BYBIT:
            from bybit_streamer import BybitStreamer
            loop.streamer = BybitStreamer(
                on_tick=loop._on_tick,
                on_15m_close=loop._on_15m_close,
                on_1h_close=loop._on_1h_close,
                demo=True,
                symbol=symbol,
            )
        else:
            from live_loop import BinanceStreamer
            loop.streamer = BinanceStreamer(
                on_tick=loop._on_tick,
                on_15m_close=loop._on_15m_close,
                on_1h_close=loop._on_1h_close,
            )
        print(f"[live] Backbencher - Book {BOOK_CODE} - {exchange.upper()} {symbol}")
        print(f"[live] 15m window: 30d | 1h window: 20d")
        print(f"[live] mode={loop.v18['mode']} ext_stop={loop.v18['ext_stop_r']} cd={loop.v18['cooldown_bars']} halt={loop.v18['max_consecutive_losses']}")
        if exchange == EXCHANGE_BYBIT:
            if paper_mode:
                print(f"[live] Bybit PAPER mode — no live orders")
            else:
                print(f"[live] Bybit LIVE mode — real orders will be placed")
        try:
            import asyncio
            asyncio.run(loop._run_loop(max_seconds, started))
        except KeyboardInterrupt:
            print("\n[live] Interrupted — flattening position...")
            _graceful_shutdown(loop)
        finally:
            loop._running = False
            print("[live] Loop stopped")

    # Seed from timestamps if provided, otherwise try crash recovery
    if seed_1h and seed_15m:
        loop._seed_from_timestamps(seed_1h, seed_15m)
        _start_streaming()
    else:
        # Try crash recovery — read last swing endpoints from DB
        recovered = loop._recover_from_crash()
        if recovered:
            _start_streaming()
        else:
            print("[main] No previous state found — provide timestamps:")
            print("  python main.py '15m_time' '1h_time' --exchange bybit")
            print("  Example: python main.py '2026-09-07 03:00:00' '2026-09-07 05:30:00' --exchange bybit")

    loop.stop()
    db.close()
    print("[main] Done")


if __name__ == "__main__":
    main()
