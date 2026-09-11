"""Backbencher - main entry point.

Usage:
    python main.py              # run forever
    python main.py 120          # run 120 seconds (test)
    python main.py --paper      # paper trading mode (default)
    python main.py --live       # live trading with real orders (TODO)
    python main.py --seed-1h "2026-09-09 15:00:00" --seed-15m "2026-09-10 04:30:00"
                               # seed from known backtest timestamps
"""

import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from persistence.database import Database
from live_loop import LiveLoop

DB_PATH = "backbencher.db"


def main():
    """Main entry point."""
    # Parse args
    max_seconds = 0
    paper_mode = "--live" not in sys.argv
    seed_1h = None
    seed_15m = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--seed-1h" and i + 1 < len(sys.argv):
            seed_1h = sys.argv[i + 1]
            i += 2
        elif arg == "--seed-15m" and i + 1 < len(sys.argv):
            seed_15m = sys.argv[i + 1]
            i += 2
        elif arg == "--paper":
            paper_mode = True
            i += 1
        elif arg == "--live":
            paper_mode = False
            i += 1
        else:
            try:
                max_seconds = float(arg)
            except ValueError:
                pass
            i += 1

    print("=" * 60)
    print("Backbencher - Live Trading Engine (REAL v18)")
    print("=" * 60)
    print(f"Mode: {'PAPER' if paper_mode else 'LIVE'}")
    print(f"Database: {DB_PATH}")
    if max_seconds:
        print(f"Test window: {max_seconds}s")
    if seed_1h and seed_15m:
        print(f"Seed: 1h={seed_1h}, 15m={seed_15m}")
    print("=" * 60)

    # Initialize database
    db = Database(DB_PATH)
    db.connect()
    db.create_tables()

    # Create live loop (uses REAL v18 engine on rolling windows)
    loop = LiveLoop(db)

    # Seed from timestamps if provided, otherwise normal Binance seed
    if seed_1h and seed_15m:
        loop._seed_from_timestamps(seed_1h, seed_15m)
        # Start WebSocket streamer (skip seeding in run)
        loop._running = True
        started = time.time()
        from live_loop import BinanceStreamer, asyncio, SWING, V18
        loop.streamer = BinanceStreamer(
            on_tick=loop._on_tick,
            on_15m_close=loop._on_15m_close,
            on_1h_close=loop._on_1h_close,
        )
        print("[live] Backbencher v18 - FULL simulation (WebSocket streams)")
        print(f"[live] 15m window: 30d | 1h window: 20d")
        print(f"[live] params: mode={V18['mode']} rr=3.0 cd={V18['cooldown_bars']} halt={V18['max_consecutive_losses']}")
        try:
            asyncio.run(loop._run_loop(max_seconds, started))
        except KeyboardInterrupt:
            print("\n[live] Interrupted")
        finally:
            loop._running = False
            print("[live] Loop stopped")
    else:
        # Normal run (seeds from Binance REST)
        try:
            loop.run(max_seconds=max_seconds)
        except KeyboardInterrupt:
            print("\n[main] Interrupted")

    loop.stop()
    db.close()
    print("[main] Done")


if __name__ == "__main__":
    main()

