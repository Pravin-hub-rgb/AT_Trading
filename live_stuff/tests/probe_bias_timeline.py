"""BIAS-TIMELINE PROBE - is the 1h bias built from sw10, and how often does
it flip?

WHY THIS PROBE EXISTS
====================
The 2-of-3 multi-swing bias proposal operates on the 1h bias timeline, so
before building anything I need to know HOW that timeline is constructed -
and the last time I assumed that, I assumed swings were Elliott waves and
wasted a full run (PROBE 1's lesson).

Three things must be established, not assumed:
  1. the bias windows come from the 1h chain (sw10), not the 15m chain;
  2. what a "window" actually is - a start, an end, a direction, and where
     the end comes from;
  3. how fast the direction alternates, because a 2-of-3 rule only means
     something if flips are frequent enough for the filter to bite.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u probe_bias_timeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

IST = ROOT / "backend/src/btc/engines/htf_ltf/v18_streak_halt.py"


def main():
    from exp_5m_confirm import load_book
    import scalp_1m_engine as E

    print("=" * 78)
    print("  BIAS-TIMELINE PROBE")
    print("=" * 78)

    # --- 1. where does the window come from? read the source, don't infer
    src = IST.read_text(encoding="utf-8")
    print("\nPROBE A - what builds the HTF windows?")
    for line in src.splitlines():
        if "simulate_btc_trades_v7(candles_htf" in line:
            print(f"  {line.strip()[:96]}")
    print("  => the windows are 1h trades; to_intervals() turns each into "
          "[entry_ts, exit_ts, dir, px, sl]\n")

    # --- 2. what are the windows, empirically
    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        w = E.htf_windows(data["c1h"], data["sw10"], fine_ltf=data["fine"])
        dirs = [x[2] for x in w]
        flips = sum(1 for a, b in zip(dirs, dirs[1:]) if a != b)
        # 1h chain for the 2-of-3 comparison
        from src.btc.btc_routes import _compute_swings
        from src.walker import FlowCandle
        flow = [FlowCandle(date=c["date"], open=float(c["open"]),
                           high=float(c["high"]), low=float(c["low"]),
                           close=float(c["close"])) for c in data["c1h"]]
        sw1h = _compute_swings(flow, "continuous", min_bars=10)
        sdirs = [1 if s.get("dir") == "up" else -1 for s in sw1h]
        sflips = sum(1 for a, b in zip(sdirs, sdirs[1:]) if a != b)
        print(f"  [{scope}] 1h bars {len(data['c1h']):,}   "
              f"1h swings {len(sw1h):,}")
        print(f"  [{scope}] BIAS WINDOWS {len(w):,}   "
              f"direction flips {flips} ({100.0*flips/max(len(w)-1,1):.1f}%)")
        print(f"  [{scope}] 1h swing dir alternation {sflips}/"
              f"{len(sw1h)-1} ({100.0*sflips/max(len(sw1h)-1,1):.1f}%)")
        print(f"  [{scope}] mean window length "
              f"{sum(x[1]-x[0] for x in w)/max(len(w),1)/3600:.1f} hours")
        # a 2-of-3 rule on the swing chain: how many swings would it keep?
        keep = 0
        for i in range(2, len(sdirs)):
            last3 = sdirs[i-2:i+1]
            if last3.count(1) >= 2 or last3.count(-1) >= 2:
                keep += 1
        tot = max(len(sdirs) - 2, 1)
        print(f"  [{scope}] a 2-of-3 rule on the swing chain would KEEP "
              f"{keep}/{tot} swings ({100.0*keep/tot:.1f}%)")
        print()


if __name__ == "__main__":
    main()
