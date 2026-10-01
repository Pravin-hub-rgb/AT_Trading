"""BIAS WINDOW THEORY - what actually closes a 1h bias window, and when?

THE QUESTION BEING ASKED
========================
The user asked whether a bias window closes at -1R, +3R or a 16-day cap,
and whether those happen "within 3 days". That is a question about
MECHANISM, and this session's standing rule is: read the code, then
measure - never assume.

WHAT THE CODE SAYS (v18_streak_halt.py, verified line by line)
=============================================================
  :214  htf_rr=3.0        "HTF (1h) fixed R target - controls when window
                            closes"
  :215  window_end="exit"  "exit" = HTF trade exit (SL/target/16-day cap)
                            [default, +331R]
        "r_touch" = first touch of ext_stop_r 1.5R  [tested: +200.6R, -130R]
  :222  simulate_btc_trades_v7(..., rr_target=htf_rr, trailing="off",
                               breakeven_r=0.0, sl_mode="swing", cap_days=16)
  :242  wend = _r_touch_end(...) if window_end=="r_touch" else exit_ts

And v7_timecap.py:
  :1   "v7 - Time Cap for 1h Flip Fixed 3R. Exits at market if hold >
        cap_days."
  :22  cap_days: int=30, 0 = off   (the caller passes 16)
  :36  cap_bars = int(cap_days*86400 / interval)

So the shipped theory is: **a window is a 1h swing's leg, opened at its
entry, closed when that leg hits +3R, hits its -1R swing stop, or has run
16 days.** Three exits, and `r_touch` (close at +1.5R) was TESTED and
REJECTED at -130R.

The question is which of the three actually fires, and in what time. The
probe already showed a mean window length of 76.1h (IS) / 66.0h (OOS),
i.e. ~3 days, so if 16 days is the cap then the cap cannot be the binding
constraint - something else closes windows far earlier. This measures it.

MEASURED
========
For every window: how it ended, in R terms and in days held.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))


def main():
    from exp_5m_confirm import load_book
    from src.btc.btc_routes import _compute_swings
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    from src.walker import FlowCandle

    print("=" * 84)
    print("  BIAS WINDOW THEORY - which exit actually fires, and when?")
    print("=" * 84)
    print("  code: htf_rr=3.0, cap_days=16, window_end='exit'")
    print("        r_touch (close at +1.5R) was tested and REJECTED (-130R)\n")

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        c1h = data["c1h"]
        flow = [FlowCandle(date=c["date"], open=float(c["open"]),
                           high=float(c["high"]), low=float(c["low"]),
                           close=float(c["close"])) for c in c1h]
        sw = _compute_swings(flow, "continuous", min_bars=10)
        tr = simulate_btc_trades_v7(c1h, sw, entry_break="decisive",
                                   sl_mode="swing", rr_target=3.0,
                                   trailing="off", breakeven_r=0.0,
                                   skip_first=True, fine=data["fine"],
                                   cap_days=16)
        tr = tr if isinstance(tr, list) else tr
        closed = [t for t in tr if t.get("outcome") != "open"]
        oc = Counter(t.get("outcome", "?") for t in tr)
        days = [(int(t["exit_ts"]) - int(t["entry_ts"])) / 86400.0
                for t in closed]
        days.sort()
        rs = [float(t["r_multiple"]) for t in closed]
        print(f"  [{scope}] 1h swings {len(sw):,}   HTF windows {len(tr):,}"
              f"   closed {len(closed):,}")
        print(f"    outcome mix: {dict(oc)}")
        for k, v in oc.items():
            print(f"      {k:<8} {v:>4}  {100.0*v/max(len(tr),1):>5.1f}%")
        if days:
            q = lambda p: days[int(p * (len(days) - 1))]  # noqa: E731
            print(f"    days held: p10 {q(.1):.2f} p25 {q(.25):.2f} "
                  f"MED {q(.5):.2f} p75 {q(.75):.2f} p90 {q(.9):.2f} "
                  f"max {days[-1]:.2f}")
            print(f"    within 3 days : {sum(1 for d in days if d <= 3)}/"
                  f"{len(days)} ({100.0*sum(1 for d in days if d<=3)/len(days):.0f}%)")
            print(f"    hit 16d cap   : {sum(1 for d in days if d >= 15.9)}"
                  f"/{len(days)}")
        print(f"    R: med {sorted(rs)[len(rs)//2]:+.2f} "
              f"mean {sum(rs)/len(rs):+.2f}  >=+3R {sum(1 for x in rs if x >= 2.9)}"
              f"  <=-1R {sum(1 for x in rs if x <= -0.9)}")
        print()


if __name__ == "__main__":
    main()
