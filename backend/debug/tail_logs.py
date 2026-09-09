"""Watch the Backbencher live log without PowerShell file-locking issues.

Usage:
    python backend/debug/tail_logs.py              # watch the live log
    python backend/debug/tail_logs.py --lines 30   # last N lines then follow
    python backend/debug/tail_logs.py --once       # print once, no follow
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "src" / "live" / "_run_live.txt"


def read_all() -> list[str]:
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
        return f.readlines()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, default=25, help="lines to show before following")
    ap.add_argument("--once", action="store_true", help="print once, no follow")
    ap.add_argument("--file", type=str, default=None, help="alternate log file path")
    args = ap.parse_args()

    log = Path(args.file) if args.file else LOG_FILE
    if not log.exists():
        print(f"log file not found: {log}")
        print("is the live engine running?  python backend/src/live/main.py")
        return 1

    lines = read_all()
    # print last N
    for ln in lines[-args.lines:]:
        print(ln, end="")
    if args.once:
        return 0

    print(f"\n--- watching {log.name} (Ctrl-C to stop) ---\n")
    pos = len(lines)
    try:
        while True:
            time.sleep(1.5)
            fresh = read_all()
            if len(fresh) > pos:
                for ln in fresh[pos:]:
                    print(ln, end="")
                pos = len(fresh)
    except KeyboardInterrupt:
        print("\n[stopped]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
