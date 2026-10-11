"""Trace the FIRST leg, bar by bar, on the committed engine.

compute_btc_swings:156-157 breaks out of the while loop the moment one swing fails to
declare, so "0 swings" always meant the first leg never completed. That is a narrow
question: which of the four steps - seed, B1, direction establish, chop pivot break -
stopped happening.

Print every bar of the first leg and mark the transitions.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
candles = list(candles)
flow = list(flow)

eng = SwingEngine({"minBars": 50})
PREV = {"state": None, "armed": None, "dir": None}

print("=" * 108)
print("FIRST LEG, BAR BY BAR  -  the committed engine declares this swing at bar 61")
print("=" * 108)
print("  bar  time              bs   state    dir   armed  e_hi      e_lo      target_hi  target_lo  marks")
print("  " + "-" * 105)
for i, c in enumerate(flow[:120]):
    eng.process_bar(c, i)
    th = eng._chop_target_high()
    tl = eng._chop_target_low()
    mk = ",".join(m.kind for m in eng.break_marks) if eng.break_marks else ""
    flag = ""
    if eng.state != PREV["state"]:
        flag += " <-STATE"
    if eng.armed != PREV["armed"]:
        flag += " <-ARMED"
    if eng.dir != PREV["dir"]:
        flag += " <-DIR"
    if eng.break_marks:
        flag += " <-MARK"
    if eng.declared:
        flag += " *** DECLARED ***"
    if i < 70 or flag or eng.declared:
        print("  %-4d %-18s %-4d %-7s %-5s %-6s %-9.1f %-9.1f %-10s %-10s %-5s%s"
              % (i, str(c.date)[11:16], eng.bars_seen, eng.state, eng.dir or "-",
                 eng.armed, eng.e_hi.px, eng.e_lo.px,
                 (("%.1f" % th.px) if th else "None"),
                 (("%.1f" % tl.px) if tl else "None"),
                 mk, flag))
    PREV = {"state": eng.state, "armed": eng.armed, "dir": eng.dir}
    if eng.declared:
        print()
        print("  first leg COMPLETED at bar %d (%s)" % (i, str(c.date)[:16]))
        print("  fs_at=%s confirmed=%s breaks=%s"
              % (eng.last_chop_cross_time, eng.confirmed_at_time,
                 [(m.kind, m.time, m.px) for m in eng.break_marks]))
        break
else:
    print()
    print("  first leg did NOT complete in 120 bars")
    print("  final: state=%s dir=%s armed=%s bars_seen=%d marks=%s"
          % (eng.state, eng.dir, eng.armed, eng.bars_seen,
             [(m.kind, m.px) for m in eng.break_marks]))
