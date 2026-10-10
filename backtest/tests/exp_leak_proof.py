"""The lookahead trade, named, with the candles printed.

The claim under test: the window gate admits LTF entries before the HTF window
candle closed. The owner asked to see an actual trade rather than a count, so this
prints the whole chain for each leaked trade - the 1h window candle and when it
closed, the 15m entry candle, and the gap between them.

THE ALGEBRA, FROM THE ENGINE'S OWN CODE

The trade record says, in the engine's own comment at unified.py:1470:

    "window_start + 3600 is when the governing 1h bias candle closed,
     i.e. the earliest instant the trade could have been known.
     entry_ts - that is the lead time."

So the gate SHOULD require entry_ts > window_start + 3600.

What the gate actually says (unified.py, window membership):

    _floor < bar_ts + 900
    _floor = s + 2700

and entry_ts IS candles_ltf[i]["ts"], which is the same thing as bar_ts - the 15m
bar's OPEN. So the gate is:

    s + 2700 < entry_ts + 900
=> entry_ts > s + 1800

The window is knowable at s + 3600. So the gate permits an entry up to
1800 SECONDS - 30 minutes - before the window is knowable. The trades that
actually used that band only reached 900 seconds, which is why counting them
shows 15 minutes rather than 30.

C15 recorded the start-side fix as `s + 2700 < bar_ts`, which is exactly
`s + 3600 < bar_ts + 900` - the correct form, with no extra +900 on the entry
side. C17's doc quotes that as "that half is correct and is the C15 fix". The
implementation does not match it.
"""
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402

HTF_CLOSE = 3600
LTF_CLOSE = 900
GATE_BUDGET = HTF_CLOSE - LTF_CLOSE                   # 2700, what the floor uses


def hm(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def find(candles, ts):
    for c in candles:
        if int(c["ts"]) == int(ts):
            return c
    return None


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}

    print("=" * 96)
    print("THE ALGEBRA")
    print("=" * 96)
    print("  engine comment  : 'window_start + 3600 is ... the earliest instant the trade")
    print("                    could have been known'")
    print("  entry_ts       = candles_ltf[i]['ts']   (the 15m bar's OPEN, == bar_ts)")
    print("  gate           : _floor < bar_ts + 900, with _floor = s + 2700")
    print("  => requires    : s + 2700 < entry_ts + 900   =>   entry_ts > s + %d" % (GATE_BUDGET - LTF_CLOSE))
    print("  knowable at    : s + %d" % HTF_CLOSE)
    print("  => the gate permits an entry up to %d seconds (%.0f min) before the window"
          % (HTF_CLOSE - (GATE_BUDGET - LTF_CLOSE), (HTF_CLOSE - (GATE_BUDGET - LTF_CLOSE)) / 60))
    print("     is knowable. The 2700 is meant to absorb the 900 LTF settle; applying it")
    print("     to entry_ts AND then adding another 900 is what makes it loose.")

    for era in ("is", "oos"):
        d = E[era]
        c1h, c15 = d["c1h"], d["c15"]
        o = sim(c1h, get_swings(d, "sw10"), c15, d["sw15"], fine_ltf=d["fine"],
                **EXPERIMENTS["fsent_champ_long"]["params"])
        trades = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
        bad = [t for t in trades
               if int(t["window_start"]) + HTF_CLOSE - int(t["entry_ts"]) > 0]
        if not bad:
            continue
        print("\n" + "=" * 96)
        print("%s: %d leaked trades" % (era.upper(), len(bad)))
        print("=" * 96)
        for t in sorted(bad, key=lambda x: int(x["entry_ts"])):
            ws = int(t["window_start"])
            et = int(t["entry_ts"])
            lead = ws + HTF_CLOSE - et
            hc = find(c1h, ws)
            lc = find(c15, et)
            print("\n  trade #%d  %s  %s  R %+.2f"
                  % (t["trade_no"], t["dir"].upper(), hm(et), net_r([t])))
            print("    HTF window candle (1h)  opens  %s   closes %s"
                  % (hm(ws), hm(ws + HTF_CLOSE)))
            if hc:
                print("      its OHLC              O=%.1f H=%.1f L=%.1f C=%.1f"
                      % (hc["open"], hc["high"], hc["low"], hc["close"]))
            print("    LTF entry candle  (15m) opens  %s   closes %s"
                  % (hm(et), hm(et + LTF_CLOSE)))
            if lc:
                print("      its OHLC              O=%.1f H=%.1f L=%.1f C=%.1f"
                      % (lc["open"], lc["high"], lc["low"], lc["close"]))
            print("    >>> entry bar OPENS %.0f minutes BEFORE the 1h window candle closes."
                  % (lead / 60.0))
            print("    >>> at the entry bar's open, the 1h window candle's CLOSE is unknown.")
            print("        A live trader on this bar does not know the window exists yet.")
            print("        gate required entry_ts > %s   |   actual entry_ts = %s"
                  % (hm(ws + HTF_CLOSE), hm(et)))

    # the fix, on the same books
    print("\n" + "=" * 96)
    print("THE FIX - floor set to 3600, which makes the gate require")
    print("          entry_ts > s + 3600 + 900 - comfortably past the close")
    print("=" * 96)
    for era in ("is", "oos"):
        d = E[era]
        for floor in (2700, 3600, 7200):
            o = sim(d["c1h"], get_swings(d, "sw10"), d["c15"], d["sw15"],
                    fine_ltf=d["fine"],
                    **{**EXPERIMENTS["fsent_champ_long"]["params"],
                       "exp_window_floor_s": floor})
            tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
            leak = sum(1 for t in tr
                       if int(t["window_start"]) + HTF_CLOSE - int(t["entry_ts"]) > 0)
            print("  %-4s floor=%-5d trades=%4d  leaked=%2d  net=%+8.2f"
                  % (era.upper(), floor, len(tr), leak, sum(net_r([t]) for t in tr)))
    print("\n  floor 7200 is the registered book: fsent_champ_long_causalfloor.")
    print("  3600 is the causal minimum and also removes every leaked trade;")
    print("  7200 additionally clears the 2025-H1 cell, which is why it was chosen,")
    print("  and that extra choice is selection pressure, not arithmetic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())