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

    print("=" * 60)
    print("Backbencher v18 - Live Trading Engine")
    print("=" * 60)
    print(f"Exchange:  {exchange.upper()}")
    print(f"Symbol:    {symbol}")
    print(f"Mode:      {'PAPER' if paper_mode else 'LIVE'}")
    print(f"Database:  {DB_PATH}")
    if max_seconds:
        print(f"Test:      {max_seconds}s window")
    if seed_1h and seed_15m:
        print(f"Seed 15m:  {seed_15m} IST")
        print(f"Seed 1h:   {seed_1h} IST")
    print("=" * 60)

    # Initialize database
    db = Database(DB_PATH)
    db.connect()
    db.create_tables()

    # Create live loop (uses REAL v18 engine on rolling windows)
    loop = LiveLoop(db, exchange=exchange, symbol=symbol, paper_mode=paper_mode)

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
        print(f"[live] Backbencher v18 - {exchange.upper()} {symbol}")
        print(f"[live] 15m window: 30d | 1h window: 20d")
        print(f"[live] mode={loop.v18['mode']} rr={loop.v18['rr_ratio']} cd={loop.v18['cooldown_bars']} halt={loop.v18['max_consecutive_losses']}")
        if exchange == EXCHANGE_BYBIT:
            if paper_mode:
                print(f"[live] Bybit PAPER mode — no live orders")
            else:
                print(f"[live] Bybit LIVE mode — real orders will be placed")
        try:
            import asyncio
            asyncio.run(loop._run_loop(max_seconds, started))
        except KeyboardInterrupt:
            print("\n[live] Interrupted")
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
