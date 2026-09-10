"""Backbencher - main entry point.

Usage:
    python main.py              # run forever
    python main.py 120          # run 120 seconds (test)
    python main.py --paper      # paper trading mode (default)
    python main.py --live       # live trading with real orders (TODO)
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
    max_seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 0
    paper_mode = "--live" not in sys.argv

    print("=" * 60)
    print("Backbencher - Live Trading Engine (REAL v18)")
    print("=" * 60)
    print(f"Mode: {'PAPER' if paper_mode else 'LIVE'}")
    print(f"Database: {DB_PATH}")
    if max_seconds:
        print(f"Test window: {max_seconds}s")
    print("=" * 60)

    # Initialize database
    db = Database(DB_PATH)
    db.connect()
    db.create_tables()

    # Create live loop (uses REAL v18 engine on rolling windows)
    loop = LiveLoop(db)

    # Run
    try:
        loop.run(max_seconds=max_seconds)
    except KeyboardInterrupt:
        print("\n[main] Interrupted")
    finally:
        loop.stop()
        db.close()

    print("[main] Done")


if __name__ == "__main__":
    main()

